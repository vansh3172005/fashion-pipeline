"""Flat 2-D garment images.

For every scraped item the product photos (the store publishes several
angles: front, back, side, detail, on-model) are downloaded, the garment is
cut out so that *only the item* remains (no model, no background), and each
usable angle is saved as a square transparent PNG:

    web/flat/<site>/<product id>/view_1.png, view_2.png, ...

Segmenters:
  * ``cloth`` (default) - rembg's ``u2net_cloth_seg`` model. It separates
    upper-body, lower-body and full-body clothing from the person wearing it,
    so on-model photos become garment-only cut-outs. Needs ``pip install
    rembg[cpu]``; the 176 MB model downloads on first use to ~/.u2net.
  * ``plain`` - no ML: removes a flat studio background by colour distance.
    Fine for flat-lay/packshot photos; keeps the model on on-model photos.
    Used by the offline tests.

Views are rejected when the cut-out is empty, fills the frame or touches three
image edges (detail close-ups), or is fragmented (segmentation failed); exact
duplicates are dropped. The garment pixels also yield a colour breakdown used
to fill a missing secondary colour.
"""
import colorsys
import io
import logging
import shutil
import time
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import numpy as np
from PIL import Image

try:
    from scipy import ndimage
except ImportError:  # pragma: no cover - scipy ships with rembg
    ndimage = None

log = logging.getLogger("imaging")

MIN_AREA, MAX_AREA = 0.02, 0.70
MIN_LARGEST_SHARE = 0.75
MAX_ROUGHNESS = 9.5  # boundary px / sqrt(area); clean garments score 4-8


# --------------------------------------------------------------------------
# segmenters
# --------------------------------------------------------------------------


class PlainSegmenter:
    """Background removal for photos shot on a flat backdrop."""

    name = "plain"

    def masks(self, img: Image.Image, department=None) -> dict:
        a = np.asarray(img.convert("RGB")).astype(np.int16)
        border = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])
        bg = np.median(border, axis=0)
        dist = np.abs(a - bg).sum(axis=2)
        return {"all": np.clip((dist - 24) / 40.0, 0, 1)}


class ClothSegmenter:
    """rembg u2net_cloth_seg: masks for upper / lower / full-body clothing.

    Shoes, belts, sunglasses and other accessories are not clothing classes,
    so they use rembg's general salient-object model (u2net) instead.
    """

    name = "cloth"

    def __init__(self):
        from rembg import new_session  # optional heavy dependency
        self._new_session = new_session
        self.session = new_session("u2net_cloth_seg")
        self._generic = None

    def masks(self, img: Image.Image, department=None) -> dict:
        if department in ("footwear", "accessories"):
            if self._generic is None:
                self._generic = self._new_session("u2net")
            (m,) = self._generic.predict(img.convert("RGB"))
            return {"all": np.asarray(m, dtype=np.float32) / 255.0}
        upper, lower, full = self.session.predict(img.convert("RGB"))
        return {k: np.asarray(m, dtype=np.float32) / 255.0
                for k, m in (("upper", upper), ("lower", lower), ("full", full))}


def make_segmenter(name: str = "cloth"):
    if name == "plain":
        return PlainSegmenter()
    try:
        return ClothSegmenter()
    except ImportError as e:
        raise SystemExit("the 'cloth' segmenter needs rembg: pip install \"rembg[cpu]\" "
                         "(or use --segmenter plain)") from e


def garment_mask(masks: dict, department: str) -> np.ndarray:
    """Pick the clothing region that matches the item's department
    (topwear / bottomwear / fullbody, or "coord_set")."""
    if "all" in masks:
        return masks["all"]
    two_piece = np.maximum(masks["upper"], masks["lower"])
    union = np.maximum(two_piece, masks["full"])
    # co-ord sets are a separate top + bottom: leave out the "full" class,
    # which tends to include exposed skin between the two pieces
    pick = {"topwear": masks["upper"], "bottomwear": masks["lower"],
            "coord_set": two_piece}.get(department, union)
    if (pick > 0.5).mean() < MIN_AREA:  # model put it in another class
        pick = union
    return pick


# --------------------------------------------------------------------------
# mask cleanup + quality gate
# --------------------------------------------------------------------------


def clean_mask(m: np.ndarray):
    """Return (alpha 0..1, bbox) or (None, reason)."""
    binm = m > 0.5
    area = binm.mean()
    if area < MIN_AREA:
        return None, "no garment found"
    if area > MAX_AREA:
        return None, "close-up (fills frame)"
    keep = binm
    if ndimage is not None:
        # drop hair strands / thin slivers, then judge the pieces that remain
        opened = ndimage.binary_opening(binm, iterations=2)
        lab, n = ndimage.label(opened)
        if n == 0:
            return None, "no garment found"
        sizes = np.asarray(ndimage.sum(opened, lab, range(1, n + 1)))
        main = int(np.argmax(sizes)) + 1
        if sizes.max() / sizes.sum() < MIN_LARGEST_SHARE:
            return None, "fragmented mask"
        mx = np.flatnonzero((lab == main).any(axis=0))
        x_lo, x_hi = mx.min(), mx.max()
        keep_ids = [main]
        for k in range(1, n + 1):  # extra pieces (the top of a co-ord set) must
            if k == main or sizes[k - 1] < 0.12 * sizes.max():  # sit above/below
                continue  # the main piece, not off to the side
            xs = np.flatnonzero((lab == k).any(axis=0))
            if x_lo <= (xs.min() + xs.max()) / 2 <= x_hi:
                keep_ids.append(k)
        keep = np.isin(lab, keep_ids)
        # unsmoothed outer outline (interior holes such as prints don't count)
        raw = ndimage.binary_fill_holes(binm & ndimage.binary_dilation(keep, iterations=3))
        edge = raw & ~ndimage.binary_erosion(raw)
        if edge.sum() / np.sqrt(raw.sum()) > MAX_ROUGHNESS:
            return None, "ragged mask"
        filled = ndimage.binary_fill_holes(keep)
    else:
        filled = keep
    ys, xs = np.nonzero(filled)
    h, w = m.shape
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    touches = (y0 <= 1) + (x0 <= 1) + (y1 >= h - 2) + (x1 >= w - 2)
    if touches >= 3:
        return None, "close-up (cut off at edges)"
    alpha = np.where(ndimage.binary_dilation(keep, iterations=2) if ndimage is not None
                     else keep, m, 0.0)  # keep soft edges around the kept pieces
    alpha[filled & ~keep] = 1.0  # holes inside the garment (prints, buttons)
    return np.clip(alpha, 0, 1), (x0, y0, x1 + 1, y1 + 1)


def render_flat(img: Image.Image, alpha: np.ndarray, bbox, size=512) -> Image.Image:
    """Garment only, centred on a transparent square canvas."""
    rgba = img.convert("RGBA")
    rgba.putalpha(Image.fromarray((alpha * 255).astype(np.uint8)))
    crop = rgba.crop(bbox)
    inner = int(size * 0.9)
    scale = inner / max(crop.size)
    crop = crop.resize((max(1, round(crop.width * scale)), max(1, round(crop.height * scale))),
                       Image.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.alpha_composite(crop, ((size - crop.width) // 2, (size - crop.height) // 2))
    return canvas


def _signature(flat: Image.Image) -> np.ndarray:
    bg = Image.new("RGBA", flat.size, (255, 255, 255, 255))
    bg.alpha_composite(flat)
    return np.asarray(bg.convert("RGB").resize((24, 24)), dtype=np.float32)


# --------------------------------------------------------------------------
# colour from pixels
# --------------------------------------------------------------------------


def name_rgb(r, g, b) -> str:
    """Map an RGB value to the catalogue palette."""
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    h *= 360
    if v < 0.2:
        return "black"
    if s < 0.12 or (s < 0.2 and v < 0.35):
        return "white" if v > 0.85 else ("black" if v < 0.28 else "grey")
    if h < 15 or h >= 345:
        return "pink" if (s < 0.45 and v > 0.7) else "red"
    if h < 40:
        if v < 0.55:
            return "brown"
        return "beige" if s < 0.45 else "orange"
    if h < 65:
        if s < 0.4 and v > 0.6:
            return "beige"
        return "yellow" if v >= 0.55 else "green"
    if h < 170:
        return "green"
    if h < 200:
        return "blue"
    if h < 255:
        return "navy" if v < 0.45 else "blue"
    if h < 290:
        return "purple"
    return "pink" if v > 0.5 else "purple"


def color_breakdown(pixels: np.ndarray, top=4) -> list:
    """[{color, share, hex}] for an (N, 3) uint8 array of garment pixels."""
    if len(pixels) == 0:
        return []
    if len(pixels) > 40000:
        idx = np.random.default_rng(0).choice(len(pixels), 40000, replace=False)
        pixels = pixels[idx]
    q = Image.fromarray(pixels.reshape(-1, 1, 3)).quantize(colors=8,
                                                           method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()
    shares, rgb_of = {}, {}
    for count, i in q.getcolors():
        r, g, b = pal[3 * i: 3 * i + 3]
        name = name_rgb(r, g, b)
        shares[name] = shares.get(name, 0) + count
        if name not in rgb_of or count > rgb_of[name][0]:
            rgb_of[name] = (count, (r, g, b))
    total = sum(shares.values())
    out = [{"color": n, "share": round(c / total, 3),
            "hex": "#%02x%02x%02x" % rgb_of[n][1]}
           for n, c in sorted(shares.items(), key=lambda kv: -kv[1])]
    return out[:top]


def secondary_from_breakdown(breakdown, primary, min_share=0.10):
    for c in breakdown:
        if c["color"] != primary and c["share"] >= min_share:
            return c["color"]
    return None


# --------------------------------------------------------------------------
# per item
# --------------------------------------------------------------------------


def sized_url(url: str, width=800) -> str:
    """Ask the Shopify CDN for a smaller rendition (faster, same framing)."""
    parts = urlsplit(url)
    if "cdn.shopify.com" not in parts.netloc and "/cdn/shop/" not in parts.path:
        return url
    q = dict(parse_qsl(parts.query))
    q["width"] = str(width)
    return urlunsplit(parts._replace(query=urlencode(q)))


def process_item(item: dict, web_dir: Path, segmenter, session, max_views=4, size=512,
                 max_sources=0, delay=0.2):
    """Make flat images for one item. Returns a result dict."""
    pid = item["id"].split(":", 1)[1]
    rel_dir = Path("flat") / item["site"] / pid
    out_dir = Path(web_dir) / rel_dir
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    views, sigs, rejected, pix = [], [], {}, []
    sources = item.get("images") or []
    for src in (sources[:max_sources] if max_sources else sources):
        if max_views and len(views) >= max_views:
            break
        try:
            r = session.get(sized_url(src), timeout=30)
            r.raise_for_status()
            img = Image.open(io.BytesIO(r.content)).convert("RGB")
        except Exception as e:  # noqa: BLE001 - one bad photo must not stop the run
            log.warning("image download failed %s (%s)", src, e)
            rejected["download failed"] = rejected.get("download failed", 0) + 1
            continue
        finally:
            time.sleep(delay)
        region = "coord_set" if item.get("category") == "coord_set" else item.get("department")
        alpha, info = clean_mask(garment_mask(segmenter.masks(img, region), region))
        if alpha is None:
            rejected[info] = rejected.get(info, 0) + 1
            continue
        flat = render_flat(img, alpha, info, size=size)
        sig = _signature(flat)
        if any(np.abs(sig - s).mean() < 4 for s in sigs):
            rejected["duplicate view"] = rejected.get("duplicate view", 0) + 1
            continue
        sigs.append(sig)
        name = f"view_{len(views) + 1}.png"
        flat.save(out_dir / name, optimize=True)
        views.append((rel_dir / name).as_posix())
        a = np.asarray(img)[alpha > 0.9]
        pix.append(a)

    breakdown = color_breakdown(np.concatenate(pix)) if pix else []
    if not views:
        shutil.rmtree(out_dir, ignore_errors=True)
    return {
        "flat_images": views,
        "image_colors": breakdown,
        "secondary_color": secondary_from_breakdown(breakdown, item.get("color")),
        "rejected": rejected,
    }

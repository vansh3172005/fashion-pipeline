"""Studio product shots ("packshots") from the shops' own photos.

Usage:  .venv-gpu/Scripts/python -m pipeline.packshot [--gender men|women|both] [--limit N]
                                    [--only site,..] [--ids a,b] [--force] [--ai] [--workers 1]

For every topwear, bottomwear and footwear item the shop photos are tried in
order (at most ``MAX_TRIES``). A photo that already shows the product alone
(no model) is preferred: the product is cut out with rembg, centred on an
off-white studio background with a soft shadow, and saved as

    web/packshot/<site>/<id>.jpg          (men)
    web/packshot_women/<site>/<id>.jpg    (women)

When every photo shows a model, the garment is cut away from the person with
the clothing segmenter. With ``--ai`` (the hybrid mode) that cut-out is then
redrawn as a clean studio shot by Stable Diffusion on the local GPU
(pipeline/packshot_ai.py), cut out again and placed on the same backdrop.
Product-only photos are never redrawn: they show the exact product.

The path is stored in the item's ``packshot`` field; the page shows it instead
of the flat sketch. Nothing is uploaded. The cut-outs run on the GPU when the
GPU environment (.venv-gpu, onnxruntime-gpu) is used. Runs are resumable:
existing files are skipped unless ``--force``.
"""
import argparse
import io
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

from . import store
from .imaging import clean_mask, garment_mask, make_segmenter, sized_url
from .scrape import make_session

ROOT = Path(__file__).resolve().parent.parent
DEPTS = ("topwear", "bottomwear", "footwear")
BG = (242, 241, 237)          # off-white studio backdrop, as in the reference shots
SIZE = (800, 800)
MAX_TRIES = 4                 # photos tried per item before using the best on-model cut


def _foreground(img):
    """Plain-backdrop foreground: everything that differs from the border colour."""
    a = np.asarray(img.convert("RGB")).astype(np.int16)
    border = np.concatenate([a[:4].reshape(-1, 3), a[-4:].reshape(-1, 3),
                             a[:, :4].reshape(-1, 3), a[:, -4:].reshape(-1, 3)])
    bg = np.median(border, axis=0)
    uniform = np.abs(border - bg).sum(axis=1).mean() < 18     # a studio backdrop, not a scene
    return np.abs(a - bg).sum(axis=2) > 40, uniform


def compose(img, alpha, bbox, size=SIZE, fill=0.80):
    """Product centred on the backdrop with a soft contact shadow."""
    rgba = img.convert("RGBA")
    rgba.putalpha(Image.fromarray((alpha * 255).astype(np.uint8)))
    crop = rgba.crop(bbox)
    W, H = size
    scale = min(W * fill / crop.width, H * fill / crop.height)
    crop = crop.resize((max(1, round(crop.width * scale)), max(1, round(crop.height * scale))),
                       Image.LANCZOS)
    canvas = Image.new("RGBA", size, BG + (255,))
    x, y = (W - crop.width) // 2, (H - crop.height) // 2
    # soft shadow: the silhouette, darkened, blurred and nudged down-right
    a = crop.getchannel("A")
    shadow = Image.new("RGBA", crop.size, (60, 55, 45, 0))
    shadow.putalpha(a.point(lambda v: int(v * 0.22)))
    pad = 30
    sh = Image.new("RGBA", (crop.width + 2 * pad, crop.height + 2 * pad), (0, 0, 0, 0))
    sh.alpha_composite(shadow, (pad, pad))
    sh = sh.filter(ImageFilter.GaussianBlur(9))
    canvas.alpha_composite(sh, (x - pad + 6, y - pad + 10))
    canvas.alpha_composite(crop, (x, y))
    return canvas.convert("RGB")


def recut(img, segmenter):
    """Cut a generated studio shot out of its background (general object model)."""
    alpha, info = clean_mask(segmenter.masks(img, "footwear")["all"])
    return (alpha, info) if alpha is not None else (None, None)


def make_one(item, segmenter, session, web_dir, prefix, force=False, ai=False):
    """Returns (relative path or None, how) for one item."""
    rel = f"{prefix}/{item['site']}/{item['id'].split(':', 1)[1]}.jpg"
    out = Path(web_dir) / rel
    if out.exists() and not force:
        return rel, "exists"
    region = item.get("department")
    best = None  # (score, img, alpha, bbox, how)
    for n, src in enumerate((item.get("images") or [])[:MAX_TRIES]):
        try:
            r = session.get(sized_url(src, 900), timeout=30)
            r.raise_for_status()
            img = Image.open(io.BytesIO(r.content)).convert("RGB")
        except Exception:  # noqa: BLE001 - a bad photo must not stop the run
            continue
        alpha, info = clean_mask(garment_mask(segmenter.masks(img, region), region))
        if alpha is None:
            continue
        fg, uniform = _foreground(img)
        garment = alpha > 0.5
        # a product-only photo: the plain-backdrop foreground is (almost) all garment
        extra = (fg & ~garment).sum() / max(1, garment.sum())
        alone = uniform and extra < 0.12
        how = "product photo" if alone else "cut from model photo"
        score = (2 if alone else 1, -n)  # product-only photos first, then the earliest
        if best is None or score > best[0]:
            best = (score, img, alpha, info, how)
        if alone:
            break
    if best is None:
        return None, "no usable photo"
    _, img, alpha, bbox, how = best
    shot = compose(img, alpha, bbox)
    if ai and how == "cut from model photo":
        from .packshot_ai import studio_shot
        gen = studio_shot(shot, item)
        a2, b2 = recut(gen, segmenter)
        if a2 is not None:
            shot, how = compose(gen, a2, b2), "AI studio shot (GPU)"
    out.parent.mkdir(parents=True, exist_ok=True)
    shot.save(out, quality=88, optimize=True)
    return rel, how


def run(gender, limit=0, only=None, force=False, workers=1, ids=None, ai=False):
    db = ROOT / "data" / ("catalogue_women.db" if gender == "women" else "catalogue.db")
    out_json = ROOT / "web" / ("catalogue_women.json" if gender == "women" else "catalogue.json")
    prefix = "packshot_women" if gender == "women" else "packshot"
    con = store.connect(db)  # adds the packshot column on first use
    try:
        items = [store.decode(r) for r in con.execute("SELECT * FROM items")]
        todo = [i for i in items if i.get("department") in DEPTS
                and (not only or i["site"] in only) and (not ids or i["id"] in ids)]
        if limit:
            todo = todo[:limit]
        seg = make_segmenter("cloth")
        session = make_session()
        session.headers["Accept"] = "image/*"
        t0, done, hows = time.time(), [], {}

        def work(it):
            return it, *make_one(it, seg, session, ROOT / "web", prefix, force, ai)

        with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            for k, (it, rel, how) in enumerate(pool.map(work, todo), 1):
                hows[how] = hows.get(how, 0) + 1
                if rel:
                    done.append((rel, it["id"]))
                if k % 50 == 0 or k == len(todo):
                    with con:
                        con.executemany("UPDATE items SET packshot = ? WHERE id = ?", done)
                    done = []
                    rate = (time.time() - t0) / k
                    print(f"  {gender}: {k}/{len(todo)}  ~{rate * (len(todo) - k) / 60:.0f} min left  "
                          + ", ".join(f"{h} {n}" for h, n in hows.items()), flush=True)
        n = store.export_json(con, out_json)
        print(f"{gender}: packshots {hows}; exported {n} items -> {out_json.name}", flush=True)
    finally:
        con.close()


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pipeline.packshot")
    ap.add_argument("--gender", choices=["men", "women", "both"], default="both")
    ap.add_argument("--limit", type=int, default=0, help="at most N items per catalogue")
    ap.add_argument("--only", help="comma-separated site names")
    ap.add_argument("--ids", help="comma-separated item ids")
    ap.add_argument("--force", action="store_true", help="redo items that already have a packshot")
    ap.add_argument("--workers", type=int, default=1, help="parallel items (1 for the GPU)")
    ap.add_argument("--ai", action="store_true",
                    help="hybrid: redraw on-model cut-outs with Stable Diffusion on the GPU")
    a = ap.parse_args(argv)
    only = set(a.only.split(",")) if a.only else None
    ids = set(a.ids.split(",")) if a.ids else None
    for g in (("men", "women") if a.gender == "both" else (a.gender,)):
        run(g, a.limit, only, a.force, a.workers, ids, a.ai)


if __name__ == "__main__":
    main()

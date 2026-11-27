"""Technical flat sketches for the women's catalogue (front + back).

Same look as the men's flats in sketch.py (solid fill in the item's colour,
dark outline, dashed stitching, front view left and back view right) and the
same parametric idea, with women's silhouettes:

  dress / gown       bodice + skirt: length (mini, knee, midi, maxi), skirt
                     shape (bodycon, A-line, flared, tiered, wrap, shift), a
                     train on gowns
  kurta              straight, A-line, anarkali (waist seam + kalis), kaftan,
                     short kurti; side slits, placket
  kurta set          kurta over palazzo / pants / salwar / churidar / sharara,
                     dupatta over the shoulder
  saree              blouse, pleated skirt with border, pallu over the shoulder
  lehenga            choli + flared skirt with kalis and border (+ dupatta)
  blouse / choli     cropped bodice, deep back with tie
  tops               cami, tube, corset, peplum, crop, halter, off-shoulder,
                     sports bra, tank
  jumpsuit, co-ord sets, skirts, sharara, leggings, cape / shrug
  footwear           heels (stiletto, block, kitten, wedge), ballerinas, mules
                     (side + top view); sneakers, sandals and juttis reuse the
                     men's drawings
  accessories        handbag, clutch, potli, earrings / jhumkas, necklace,
                     bangles, maang tikka, anklet, hair accessories; belts,
                     scarves, sunglasses, watches, caps reuse the men's drawings

Shared shapes (tees, shirts, hoodies, jackets, jeans, joggers, shorts ...) are
drawn by sketch.py. Files go to web/sketch_women/<site>/<id>.svg so they never
overwrite a men's sketch.
"""
import math
import re
from pathlib import Path

from . import sketch as S
from .sketch import (CELL_H, CELL_W, GOLD, STYLE, WHITE, Canvas, P, Spec, _f, _rect, _rr,
                     luminance, poly_d, shade, sleeve_pts)

# women's pattern values -> the closest men's value for the shared drawing code
PRINT_MAP = {"printed": "floral", "ethnic print": "floral", "animal print": "floral",
             "polka dot": "floral", "embellished": "embroidered"}


class WSpec(Spec):
    def __init__(self, item):
        super().__init__(item)
        self.wpattern = self.pattern
        self.pattern = PRINT_MAP.get(self.pattern, self.pattern)
        self.embellished = self.wpattern in ("embellished", "embroidered") or self.has(
            "sequin", "sequins", "sequinned", "embellished", "zari", "mirror", "gota",
            "zardozi", "stone", "beaded", "embroidered", "embroidery")
        self.trim = GOLD if self.embellished else self.accent

    def w(self, *names):
        return any(n in self.wear for n in names)


def pattern_defs_w(spec: WSpec) -> str:
    a, b, p = spec.accent, spec.base, spec.wpattern
    if p == "polka dot":
        return ('<pattern id="pt" width="18" height="18" patternUnits="userSpaceOnUse">'
                f'<circle cx="5" cy="5" r="2.6" fill="{a}"/><circle cx="14" cy="14" r="2.6" '
                f'fill="{a}"/></pattern>')
    if p == "animal print":
        return ('<pattern id="pt" width="40" height="40" patternUnits="userSpaceOnUse">'
                f'<path d="M6 8 q6 -5 10 1 q-2 7 -9 5z M24 22 q7 -3 9 3 q-3 6 -10 3z '
                f'M8 30 q5 -2 7 3 q-3 4 -7 1z" fill="none" stroke="{shade(a, .7)}" '
                f'stroke-width="2.2"/><circle cx="11" cy="10" r="1.8" fill="{a}"/>'
                f'<circle cx="28" cy="25" r="1.8" fill="{a}"/></pattern>')
    if p == "ethnic print":  # small booti / paisley motif
        return ('<pattern id="pt" width="26" height="26" patternUnits="userSpaceOnUse">'
                f'<path d="M8 4 c5 0 7 5 4 9 c-2 3 -6 2 -6 -1 c0 -2 2 -3 3 -2" fill="none" '
                f'stroke="{a}" stroke-width="1.6"/><circle cx="20" cy="20" r="2" fill="{a}"/>'
                f'<circle cx="20" cy="15.5" r="1" fill="{a}"/><circle cx="24.5" cy="20" r="1" '
                f'fill="{a}"/><circle cx="15.5" cy="20" r="1" fill="{a}"/>'
                f'<circle cx="20" cy="24.5" r="1" fill="{a}"/></pattern>')
    if p == "embellished":
        return ('<pattern id="pt" width="16" height="16" patternUnits="userSpaceOnUse">'
                f'<circle cx="4" cy="4" r="1.5" fill="{GOLD}"/><circle cx="12" cy="12" r="1.2" '
                f'fill="{shade(GOLD, 1.35)}"/><path d="M12 2 l1.2 2 l-1.2 2 l-1.2 -2z" '
                f'fill="{GOLD}"/></pattern>')
    return S.pattern_defs(spec, "front")


def ov(spec: WSpec):
    """Overlay fill for a women's shape, or None."""
    if spec.wpattern in ("solid", "colour block", "graphic", "embroidered", None):
        return None
    return "url(#pt)"


def _over(cv, spec, d):
    f = ov(spec)
    if f:
        cv.raw(f'<path d="{d}" fill="{f}" stroke="none"/>')


def _trim(cv, d, colour, width=2.4, dash="3 3"):
    cv.raw(f'<path d="{d}" fill="none" stroke="{colour}" stroke-width="{width}" '
           f'stroke-dasharray="{dash}" vector-effect="non-scaling-stroke"/>')


def _side(p0, segs):
    """Right-hand side path from p0 through segs, plus the mirrored left side
    walked upwards (for symmetric garments)."""
    d = "".join(f" {c}{P(*ps)}" for c, ps in segs)
    nodes = [p0] + [ps[-1] for _, ps in segs]
    m = lambda q: (-q[0], q[1])  # noqa: E731
    rd = ""
    for i in range(len(segs) - 1, -1, -1):
        c, ps = segs[i]
        rd += f" {c}{P(*[m(q) for q in ps[:-1][::-1]], m(nodes[i]))}"
    pts = [p0] + [q for _, ps in segs for q in ps]
    return d, rd, pts + [m(q) for q in pts]


# ---------------------------------------------------------------------------
# bodice + skirt (dresses, gowns, kurtas, tops, blouses)
# ---------------------------------------------------------------------------

def neckline(spec, view, kind="round", nw=26, nd=24):
    """Top edge from (-nw, 0) to (nw, 0) as a path fragment starting with M."""
    if view != "front":
        if kind == "deep back":
            return f"M{P((-nw, 0))} C{P((-nw, 50), (-nw * .5, 74), (0, 74))} " \
                   f"C{P((nw * .5, 74), (nw, 50), (nw, 0))}"
        return f"M{P((-nw, 0))} C{P((-nw * .6, 7), (nw * .6, 7), (nw, 0))}"
    if kind == "v neck":
        return f"M{P((-nw, 0))} L{P((0, nd + 40))} L{P((nw, 0))}"
    if kind == "sweetheart":
        return f"M{P((-nw, 0))} C{P((-nw, 26), (-10, 40), (0, 30))} C{P((10, 40), (nw, 26), (nw, 0))}"
    if kind == "square neck":
        return f"M{P((-nw, 0))} L{P((-nw + 2, 34))} L{P((nw - 2, 34))} L{P((nw, 0))}"
    if kind == "boat neck":
        return f"M{P((-nw - 10, 0))} C{P((-nw, 10), (nw, 10), (nw + 10, 0))}"
    if kind == "high neck":
        return f"M{P((-nw + 6, 0))} C{P((-nw + 6, 6), (nw - 6, 6), (nw - 6, 0))}"
    return f"M{P((-nw, 0))} C{P((-nw, nd * .85), (-nw * .5, nd), (0, nd))} " \
           f"C{P((nw * .5, nd), (nw, nd * .85), (nw, 0))}"


def _neck_kind(spec, cat):
    n = spec.neck or ""
    if spec.has("sweetheart"):
        return "sweetheart"
    if n in ("v neck", "sweetheart", "square neck", "boat neck", "high neck"):
        return n
    if spec.has("v neck", "vneck", "angrakha", "wrap", "overlap"):
        return "v neck"
    if spec.has("square"):
        return "square neck"
    return "round"


def draw_sleeves(cv, spec, g, fill, view):
    """Sleeves behind the body; puff and bell variants."""
    puff = spec.w("puff sleeve") or spec.has("puff", "puffed", "balloon")
    bell = spec.has("bell", "flared sleeves", "flared sleeve", "bishop")
    for side in (-1, 1):
        Sx, E1, E2, A = sleeve_pts(g, side)
        if E1 is None:
            continue
        if bell:
            dx, dy = E2[0] - E1[0], E2[1] - E1[1]
            E1 = (E1[0] - dx * .35, E1[1] - dy * .35)
            E2 = (E2[0] + dx * .45, E2[1] + dy * .45)
        if puff and g["sleeve"] == "short":
            mid = ((Sx[0] + E1[0]) / 2 + side * 22, (Sx[1] + E1[1]) / 2 - 10)
            mid2 = ((A[0] + E2[0]) / 2 + side * 6, (A[1] + E2[1]) / 2 + 14)
            d = f"M{P(Sx)} Q{P(mid, E1)} L{P(E2)} Q{P(mid2, A)} Z"
            pts = [Sx, E1, E2, A, mid]
        else:
            d = poly_d([Sx, E1, E2, A])
            pts = [Sx, E1, E2, A]
        cv.shape(d, pts, fill)
        _over(cv, spec, d)
        k = .12 if g["sleeve"] != "long" else .07
        f1 = (E1[0] + (Sx[0] - E1[0]) * k, E1[1] + (Sx[1] - E1[1]) * k)
        f2 = (E2[0] + (A[0] - E2[0]) * k, E2[1] + (A[1] - E2[1]) * k)
        if spec.embellished:
            _trim(cv, f"M{P(f1)} L{P(f2)}", spec.trim)
        else:
            cv.line(f"M{P(f1)} L{P(f2)}", "s")
        if puff and g["sleeve"] == "short":
            for t in (.3, .5, .7):  # gathers
                x = E1[0] + (E2[0] - E1[0]) * t
                y = E1[1] + (E2[1] - E1[1]) * t
                cv.line(f"M{P((x, y))} L{P((x - side * 8, y - 12))}", "r")


def dress_body(cv, spec, view, *, L, waist=None, ww=50, hem=None, flare=0.0, sw=64,
               top="sleeved", neck=None, fill=None, curve_hem=None, train=0, sleeve=None,
               straight_hw=None):
    """Draw sleeves + body for any bodice-based garment. Returns geometry."""
    fill = fill or spec.base
    front = view == "front"
    over = spec.fit in ("oversized", "boxy", "relaxed") or spec.w("oversized", "kaftan")
    sd, ay, nw, nd = 12, 88 if not over else 98, 26, 24
    sleeve = sleeve or spec.sleeve or "short"
    if top != "sleeved":
        sleeve = "sleeveless"
    g = dict(sw=sw, sd=sd, ay=ay, over=over, sleeve=sleeve, L=250, nw=nw)
    if sleeve != "sleeveless" and top == "sleeved":
        draw_sleeves(cv, spec, g, fill, view)
    nk = neck or _neck_kind(spec, spec.cat)
    # ---- top edge
    if top in ("tube", "strap", "corset", "halter"):
        bw = sw - 8
        yt = 40
        if top == "corset" or (top == "tube" and spec.has("sweetheart")) or (
                front and nk == "sweetheart" and top != "halter"):
            top_d = (f"M{P((-bw, yt))} C{P((-bw + 6, yt - 14), (-14, yt - 14), (0, yt + 2))} "
                     f"C{P((14, yt - 14), (bw - 6, yt - 14), (bw, yt))}") if front else \
                f"M{P((-bw, yt))} L{P((bw, yt))}"
        elif top == "strap" and front and nk == "v neck":
            top_d = f"M{P((-bw, yt))} L{P((0, yt + 30))} L{P((bw, yt))}"
        else:
            top_d = f"M{P((-bw, yt))} C{P((-bw * .5, yt + (6 if front else 2)), (bw * .5, yt + (6 if front else 2)), (bw, yt))}"
        start = (bw, yt)
        arm = (bw + 2, ay)
        first = [("Q", [(bw + 4, (yt + ay) / 2), arm])]
    elif top == "tank":
        top_d = neckline(spec, view, nk, nw + 6, nd + 6)
        start = (nw + 6, 0)
        arm = (sw - 6, ay)
        first = [("L", [(nw + 18, 0)]), ("Q", [(sw - 8, ay * .75), arm])]
    else:
        top_d = neckline(spec, view, nk if front else ("deep back" if spec.cat in (
            "blouse",) or (spec.cat in ("saree", "lehenga") and top == "blouse") else "round"),
                         nw, nd)
        start = (nw, 0)
        arm = (sw - 6, ay)
        first = [("L", [(sw, sd)]), ("L", [arm])]
    # ---- sides down to the hem
    segs = list(first)
    if waist:
        segs.append(("Q", [(ww + 4, (ay + waist) / 2 + 10), (ww, waist)]))
        hw = hem if hem is not None else ww + flare * (L - waist)
        if hw > ww + 30:
            segs.append(("Q", [(ww + (hw - ww) * .25, waist + (L - waist) * .35), (hw, L)]))
        elif hw < ww + 12:  # bodycon: over the hip then in
            segs.append(("Q", [(ww + 20, waist + (L - waist) * .35), (hw, L)]))
        else:
            segs.append(("L", [(hw, L)]))
    else:
        hw = straight_hw or (hem if hem is not None else arm[0] + flare * (L - ay))
        segs.append(("L", [(hw, L)]))
    right, left, pts = _side(start, segs)
    ch = curve_hem if curve_hem is not None else (min(26, (hw - 40) * .12) if hw > 80 else 0)
    if not front and train:
        ch += train
    hem_d = (f" Q{P((0, L + ch * 2), (-hw, L))}" if ch > 1 else f" L{P((-hw, L))}")
    d = f"{top_d}{right}{hem_d}{left} Z"
    pts += [(0, L + ch)]
    # inner back neck through the front opening
    if front and top == "sleeved":
        cv.fill_only(f"M{P((-nw, 0))} C{P((-nw * .6, -8), (nw * .6, -8), (nw, 0))} L{P((-nw, 0))} Z",
                     spec.inner)
    cv.shape(d, pts, fill)
    _over(cv, spec, d)
    if spec.wpattern == "colour block":
        y0 = (waist or L * .55)
        cv.raw(f'<path d="M{P((-hw, L))} L{P((hw, L))} L{P((ww if waist else hw, y0))} '
               f'L{P((-(ww if waist else hw), y0))} Z" fill="{spec.accent}" class="o"/>')
    # neckline finish
    if top == "sleeved":
        if front:
            inner = neckline(spec, view, nk, nw + 5, nd + 6)
            cv.line(inner.replace(f"M{P((-nw - 5, 0))}", f"M{P((-nw - 5, 2))}"), "s")
        else:
            cv.line(f"M{P((-nw - 5, 3))} C{P((-nw * .6, 13), (nw * .6, 13), (nw + 5, 3))}", "s")
    # straps
    if top in ("strap", "halter"):
        bw = sw - 8
        for s_ in (-1, 1):
            if top == "halter":
                cv.shape(f"M{P((s_ * 6, -10))} L{P((s_ * 16, -12))} L{P((s_ * (bw - 6), 40))} "
                         f"L{P((s_ * (bw - 22), 40))} Z", [(s_ * 16, -12)], fill)
            else:
                x0 = s_ * (bw - 16)
                cv.line(f"M{P((x0, 41))} L{P((s_ * (nw + 4), -6))}")
                cv.line(f"M{P((x0 + s_ * 5, 41))} L{P((s_ * (nw + 9), -6))}")
    if top in ("tube", "corset", "strap", "halter"):
        cv.line(f"M{P((-(sw - 10), 48))} C{P((-(sw - 14) * .5, 54), ((sw - 14) * .5, 54), ((sw - 10), 48))}", "s")
    # waist seam
    if waist:
        cv.line(f"M{P((-ww, waist))} L{P((ww, waist))}")
    # hem stitch
    if ch > 1:
        cv.line(f"M{P((-hw + 4, L - 8))} Q{P((0, L + ch * 2 - 8), (hw - 4, L - 8))}", "s")
    else:
        cv.line(f"M{P((-hw + 3, L - 8))} L{P((hw - 3, L - 8))}", "s")
    return dict(L=L, hw=hw, ww=ww, waist=waist, sw=sw, nw=nw, nd=nd, ay=ay, ch=ch,
                sleeve=sleeve, neck=nk, d=d)


def hem_border(cv, spec, geo, width=16, colour=None):
    """Embroidered / zari border along the hem."""
    L, hw, ch = geo["L"], geo["hw"], geo["ch"]
    c = colour or spec.trim
    k = width
    if ch > 1:
        band = (f"M{P((-hw, L))} Q{P((0, L + ch * 2), (hw, L))} "
                f"L{P((hw * .97, L - k))} Q{P((0, L + ch * 2 - k), (-hw * .97, L - k))} Z")
    else:
        band = f"M{P((-hw, L))} L{P((hw, L))} L{P((hw - 2, L - k))} L{P((-hw + 2, L - k))} Z"
    cv.raw(f'<path d="{band}" fill="{c}" fill-opacity=".85" class="o"/>')
    if spec.embellished:
        mid = L - k / 2
        _trim(cv, f"M{P((-hw * .95, mid))} Q{P((0, mid + ch * 2), (hw * .95, mid))}",
              shade(c, .6) if c == GOLD else GOLD, 1.6, "1.5 3")


def kalis(cv, geo, n=10):
    """Panel seams radiating from the waist (anarkali, lehenga, gown)."""
    w0, L, hw, waist, ch = geo["ww"], geo["L"], geo["hw"], geo["waist"], geo["ch"]
    for i in range(1, n):
        t = i / n
        x0 = -w0 + 2 * w0 * t
        x1 = -hw + 2 * hw * t
        y1 = L + ch * 2 * (1 - (2 * t - 1) ** 2) * .5 - 2
        cv.line(f"M{P((x0, waist + 2))} L{P((x1, y1))}", "s")


def gathers(cv, geo, n=12):
    w0, waist = geo["ww"], geo["waist"]
    for i in range(n + 1):
        x = -w0 + 2 * w0 * i / n
        cv.line(f"M{P((x, waist + 2))} L{P((x * 1.06, waist + 18))}", "r")


def _length(spec, default):
    if spec.w("maxi") or spec.has("maxi", "floor length", "ankle length", "long dress"):
        return 540
    if spec.w("midi") or spec.has("midi", "calf length"):
        return 440
    if spec.w("mini") or spec.has("mini", "short dress"):
        return 300
    if spec.has("knee length"):
        return 370
    return default


def draw_dress(cv, spec, view):
    front = view == "front"
    bodycon = spec.w("bodycon", "pencil") or spec.has("bodycon", "sheath", "fitted dress")
    slip = spec.w("slip dress", "cami") or spec.has("slip", "strappy", "spaghetti")
    shirtd = spec.w("shirt dress") or spec.has("shirt dress", "shirtdress")
    kaftan = spec.w("kaftan")
    tube = spec.w("tube") or spec.has("strapless", "tube", "bandeau")
    halter = spec.w("halter")
    corset = spec.w("corset")
    tiered = spec.w("tiered")
    flared = spec.w("flared", "skater", "anarkali") or spec.has("fit and flare", "fit flare",
                                                                  "skater", "flared", "flowy",
                                                                  "umbrella", "circle")
    aline = spec.w("a line") or spec.has("a line", "aline")
    shift = spec.has("shift", "straight", "tunic dress", "t shirt dress", "tshirt dress",
                     "sweatshirt dress", "boxy")
    L = _length(spec, 370)
    top = "corset" if corset else "tube" if tube else "halter" if halter else \
        "strap" if slip else "tank" if spec.sleeve == "sleeveless" else "sleeved"
    if kaftan:
        return draw_kaftan(cv, spec, view, L if L != 370 else 470)
    if shirtd or shift:
        geo = dress_body(cv, spec, view, L=L, top=top, sw=68,
                         straight_hw=74 if not spec.w("oversized") else 90,
                         neck="round" if shirtd else None)
        if shirtd:
            _shirt_front(cv, spec, view, geo)
    else:
        waist = 150 if not spec.has("empire", "babydoll") else 112
        if bodycon:
            geo = dress_body(cv, spec, view, L=L, waist=waist, ww=46, hem=50, top=top)
        elif tiered or flared:
            geo = dress_body(cv, spec, view, L=L, waist=waist, ww=48,
                             flare=.62 if flared else .5, top=top, train=0)
        else:
            geo = dress_body(cv, spec, view, L=L, waist=waist, ww=48,
                             flare=.34 if (aline or True) else .2, top=top)
        if tiered:
            n = 3 if L > 380 else 2
            for k in range(1, n):
                t = k / n
                y = waist + (L - waist) * t
                x = geo["ww"] + (geo["hw"] - geo["ww"]) * t
                cv.line(f"M{P((-x, y))} Q{P((0, y + geo['ch'] * t * 2), (x, y))}")
                for i in range(9):
                    xi = -x + 2 * x * (i + .5) / 9
                    cv.line(f"M{P((xi, y + 2))} L{P((xi * 1.05, y + 14))}", "r")
            gathers(cv, geo)
        elif flared and not bodycon:
            gathers(cv, geo, 14)
        if (spec.w("wrap") or spec.has("wrap", "overlap")) and front:
            cv.line(f"M{P((-26, 0))} L{P((30, waist))}")
            cv.line(f"M{P((30, waist))} Q{P((44, waist + 60), (geo['hw'] * .5, L))}", "s")
            cv.line(f"M{P((geo['ww'], waist))} L{P((geo['ww'] + 30, waist + 70))} "
                    f"M{P((geo['ww'], waist + 4))} L{P((geo['ww'] + 14, waist + 80))}")
        if corset:
            _boning(cv, geo, view)
        if bodycon and not front:
            cv.line(f"M{P((0, L - 70))} L{P((0, L))}")  # back vent
    if not front and not corset:
        cv.line(f"M{P((0, 10 if geo['sleeve'] != 'sleeveless' else 44))} L{P((0, (geo['waist'] or 180) + 30))}", "z")
    if spec.has("cut out", "cutout", "cut outs", "cutouts") and front:
        y = (geo["waist"] or 150) - 6
        cv.raw(f'<path d="M{P((-30, y - 14))} Q{P((-44, y), (-30, y + 14))} Q{P((-16, y), (-30, y - 14))} Z '
               f'M{P((30, y - 14))} Q{P((44, y), (30, y + 14))} Q{P((16, y), (30, y - 14))} Z" '
               f'fill="#fbfaf7" class="o"/>')
    if spec.has("slit", "thigh slit", "side slit") and front:
        cv.line(f"M{P((geo['hw'] * .55, L))} L{P((geo['hw'] * .32, L - 160))}")
    if spec.has("belt", "belted", "tie up", "waist tie", "sash") and geo["waist"]:
        _belt(cv, spec, geo["ww"], geo["waist"], front)
    if spec.has("ruffle", "ruffled", "frill", "frills") and front:
        _ruffle(cv, spec, geo["hw"], geo["L"], geo["ch"])
    if spec.embellished and spec.wpattern not in ("embellished",):
        hem_border(cv, spec, geo, 12)
    return geo


def _boning(cv, geo, view):
    w = geo["ww"]
    y0, y1 = 52, geo["waist"] or 150
    for x in (-w * .6, -w * .2, w * .2, w * .6):
        cv.line(f"M{P((x * 1.1, y0))} Q{P((x * .9, (y0 + y1) / 2), (x, y1))}", "s")
    if view != "front":  # lace-up back
        for k in range(6):
            y = y0 + 8 + k * (y1 - y0 - 16) / 5
            cv.line(f"M{P((-8, y))} L{P((8, y + 14))} M{P((8, y))} L{P((-8, y + 14))}")


def _belt(cv, spec, ww, y, front):
    cv.shape(f"M{P((-ww - 1, y - 7))} L{P((ww + 1, y - 7))} L{P((ww + 2, y + 7))} L{P((-ww - 2, y + 7))} Z",
             [], shade(spec.base, .85))
    if front:
        cv.raw(f'<path d="M{P((6, y))} q22 -16 26 0 q-4 16 -26 0z M{P((-6, y))} q-22 -16 -26 0 '
               f'q4 16 26 0z" fill="{shade(spec.base, .85)}" class="o"/>')
        cv.line(f"M{P((4, y + 4))} Q{P((10, y + 50), (2, y + 80))} M{P((-4, y + 4))} "
                f"Q{P((-12, y + 46), (-6, y + 74))}")


def _ruffle(cv, spec, hw, L, ch):
    d = f"M{P((-hw, L))}"
    n = max(6, int(hw / 14))
    for i in range(n):
        x0 = -hw + 2 * hw * i / n
        x1 = -hw + 2 * hw * (i + 1) / n
        yb = L + ch * 2 * (1 - ((x0 + x1) / 2 / max(hw, 1)) ** 2) * .5
        d += f" Q{P(((x0 + x1) / 2, yb + 16), (x1, yb))}"
    cv.raw(f'<path d="{d}" fill="none" class="o"/>')


def _shirt_front(cv, spec, view, geo):
    nw = geo["nw"]
    if view == "front":
        for s_ in (-1, 1):
            pts = [(s_ * (nw + 2), -10), (s_ * (nw + 22), 28), (s_ * 4, 34), (s_ * 1, 22)]
            cv.shape(poly_d(pts), pts, shade(spec.base, .95))
        cv.line(f"M{P((-8, 30))} L{P((-8, geo['L'] - 4))} M{P((8, 30))} L{P((8, geo['L'] - 4))}", "s")
        y = 46
        while y < geo["L"] - 20:
            cv.circle(0, y, 2.6, WHITE)
            y += 38
    else:
        cv.shape(f"M{P((-nw - 8, 8))} Q{P((0, -6), (nw + 8, 8))} L{P((nw + 4, -10))} "
                 f"Q{P((0, -24), (-nw - 4, -10))} Z", [(-nw - 8, -22)], spec.base)


def draw_kaftan(cv, spec, view, L=470):
    """Batwing kaftan: sleeves cut in one with the body."""
    front = view == "front"
    nw, wing = 26, 170
    d = (f"{neckline(spec, view, _neck_kind(spec, 'kaftan'), nw, 30)} "
         f"L{P((wing * .55, 14))} L{P((wing, 70))} L{P((wing - 10, 200))} "
         f"Q{P((96, 196), (92, 230))} L{P((96, L))} Q{P((0, L + 10), (-96, L))} "
         f"L{P((-92, 230))} Q{P((-96, 196), (-(wing - 10), 200))} L{P((-wing, 70))} "
         f"L{P((-wing * .55, 14))} Z")
    pts = [(-wing, 0), (wing, 0), (0, L + 10), (-96, L), (96, L)]
    cv.shape(d, pts, spec.base)
    _over(cv, spec, d)
    for s_ in (-1, 1):
        cv.line(f"M{P((s_ * (wing - 18), 196))} L{P((s_ * (wing - 8), 74))}", "s")
    if front:
        cv.line(f"M{P((0, 30))} L{P((0, 110))}", "s")
        _trim(cv, f"M{P((-nw - 6, 4))} C{P((-nw - 6, 34), (-10, 40), (0, 40))} "
              f"C{P((10, 40), (nw + 6, 34), (nw + 6, 4))}", spec.trim)
        for s_ in (-1, 1):  # drawstring waist
            cv.line(f"M{P((s_ * 92, 236))} Q{P((s_ * 40, 244), (0, 240))}", "s")
    cv.line(f"M{P((-92, L - 10))} Q{P((0, L))} {P((92, L - 10))}".replace("Q(", "Q"), "s")
    return dict(L=L, hw=96, ww=92, waist=None, sw=wing, nw=nw, nd=30, ay=70, ch=5,
                sleeve="short", neck="round", d=d)


def draw_kurta(cv, spec, view, fill=None, short=None):
    front = view == "front"
    anarkali = spec.w("anarkali")
    aline = spec.w("a line", "flared") or spec.has("a line", "aline", "flared", "umbrella")
    short = short if short is not None else (spec.w("crop top") or spec.has(
        "short kurti", "short kurta", "kurti top", "tunic") or spec.cat == "top")
    sl = spec.sleeve or "three quarter"
    if spec.w("kaftan"):
        return draw_kaftan(cv, spec, view, 420)
    if anarkali:
        L = 500 if not short else 360
        geo = dress_body(cv, spec, view, L=L, waist=128, ww=48, flare=.62, fill=fill,
                         sleeve=sl)
        kalis(cv, geo, 12)
    else:
        L = 300 if short else (430 if spec.has("long", "calf length", "ankle length") else 390)
        hw = 108 if aline else 72
        geo = dress_body(cv, spec, view, L=L, sleeve=sl, fill=fill, straight_hw=hw, sw=66)
        for s_ in (-1, 1):  # side slits
            cv.line(f"M{P((s_ * (hw - 1), L - 90))} L{P((s_ * (hw - 12), L - 90))}")
    if front and geo["neck"] in ("round",) and not spec.has("angrakha"):
        nd = geo["nd"]
        cv.line(f"M{P((0, nd + 2))} L{P((0, nd + 56))}")
        for y in (nd + 16, nd + 34):
            cv.circle(-6, y, 2.4, GOLD if spec.embellished else WHITE)
    if front and spec.has("angrakha"):
        cv.line(f"M{P((-24, 0))} Q{P((10, 60), (54, 120))}")
        cv.raw(f'<path d="M{P((54, 120))} l14 30 m-14 -30 l4 40" fill="none" class="o"/>')
    if spec.embellished:
        _trim(cv, f"M{P((-32, 6))} C{P((-32, 40), (-12, 48), (0, 48))} C{P((12, 48), (32, 40), (32, 6))}",
              spec.trim)
        if front:
            for x, y in ((-30, 110), (28, 140), (-20, 180), (34, 90), (0, 150)):
                cv.circle(x, y, 4.2, spec.trim, "s")
        hem_border(cv, spec, geo, 12)
    return geo


def draw_blouse(cv, spec, view, fill=None, L=132, sleeve=None, top="sleeved"):
    """Choli / saree blouse: cropped fitted bodice, deep back with a tie."""
    sl = sleeve or (spec.sleeve if spec.sleeve not in (None, "long") else "short")
    if spec.cat == "blouse" and spec.sleeve:
        sl = spec.sleeve
    geo = dress_body(cv, spec, view, L=L, sleeve=sl, sw=62, straight_hw=50, fill=fill,
                     top=top, neck=None if view == "front" else "deep back")
    if view != "front" and top == "sleeved":
        for s_ in (-1, 1):  # dori tie with tassels
            cv.line(f"M{P((s_ * 14, 70))} Q{P((s_ * 20, 96), (s_ * 12, 118))}")
            cv.circle(s_ * 12, 122, 4, GOLD, "o")
    if view == "front":
        cv.line(f"M{P((-44, 60))} Q{P((-30, 92), (-22, 120))} M{P((44, 60))} Q{P((30, 92), (22, 120))}", "s")
    if spec.embellished or spec.cat in ("saree", "lehenga"):
        _trim(cv, f"M{P((-50, L - 6))} L{P((50, L - 6))}", spec.trim)
    return geo


# ---------------------------------------------------------------------------
# skirts and bottoms
# ---------------------------------------------------------------------------

def draw_skirt(cv, spec, view, y0=0, L=None, ww=56, kind=None, fill=None, border=False):
    """Skirt from a waistband at y0. kind: pencil, aline, flared, tiered, lehenga."""
    fill = fill or spec.base
    front = view == "front"
    kind = kind or ("tiered" if spec.w("tiered") else
                    "pleated" if spec.w("pleated") else
                    "pencil" if spec.w("pencil", "bodycon") or spec.has("pencil", "bodycon")
                    else "flared" if spec.w("flared", "skater") or spec.has("flared", "skater",
                                                                             "circle", "flowy")
                    else "aline")
    if L is None:
        L = 200 if spec.w("mini") or spec.has("mini") else (
            420 if spec.w("maxi") or spec.has("maxi", "long skirt") else
            330 if spec.w("midi") or spec.has("midi") else 280)
    wb = 16
    hw = {"pencil": ww + 4, "aline": ww + L * .32, "pleated": ww + L * .36,
          "flared": ww + L * .58, "tiered": ww + L * .5, "lehenga": ww + L * .62}[kind]
    ch = min(26, max(0, (hw - 60) * .14))
    y1 = y0 + wb
    Ly = y0 + L
    if kind == "pencil":
        d = (f"M{P((-ww, y1))} Q{P((-ww - 22, y1 + 70), (-hw, Ly))} L{P((hw, Ly))} "
             f"Q{P((ww + 22, y1 + 70), (ww, y1))} Z")
    else:
        d = (f"M{P((-ww, y1))} Q{P((-ww - (hw - ww) * .25, y1 + L * .35), (-hw, Ly))} "
             f"Q{P((0, Ly + ch * 2), (hw, Ly))} Q{P((ww + (hw - ww) * .25, y1 + L * .35), (ww, y1))} Z")
    cv.shape(d, [(-hw, y0), (hw, Ly + ch)], fill)
    _over(cv, spec, d)
    band = f"M{P((-ww, y0))} L{P((ww, y0))} L{P((ww, y1))} L{P((-ww, y1))} Z"
    cv.shape(band, [(-ww, y0), (ww, y0)], shade(fill, .93))
    geo = dict(L=Ly, hw=hw, ww=ww, waist=y1, ch=ch)
    if kind in ("flared", "tiered", "lehenga", "aline") and kind != "aline":
        gathers(cv, geo, 14)
    if kind == "pleated":
        for i in range(1, 12):
            t = i / 12
            cv.line(f"M{P((-ww + 2 * ww * t, y1))} L{P((-hw + 2 * hw * t, Ly + ch * 2 * (1 - (2 * t - 1) ** 2) * .5))}", "s")
    if kind == "tiered":
        for k in (1, 2):
            t = k / 3
            y = y1 + L * t
            x = ww + (hw - ww) * t
            cv.line(f"M{P((-x, y))} Q{P((0, y + ch * t * 2), (x, y))}")
    if kind == "lehenga":
        kalis(cv, geo, 14)
    if kind == "pencil":
        cv.line(f"M{P((-ww + 10, y1))} L{P((-ww + 12, y1 + 60))} M{P((ww - 10, y1))} L{P((ww - 12, y1 + 60))}", "s")
        if not front:
            cv.line(f"M{P((0, Ly - 60))} L{P((0, Ly))}")
    if not front:
        cv.line(f"M{P((0, y0 + 2))} L{P((0, y0 + 90))}", "z")
    if spec.has("wrap", "overlap", "sarong") and front:
        cv.line(f"M{P((ww * .4, y1))} Q{P((hw * .3, y1 + L * .5), (hw * .8, Ly))}")
    if border or (spec.embellished and kind != "pencil"):
        hem_border(cv, spec, geo, 18 if kind == "lehenga" else 12)
    hem = f"M{P((-hw + 4, Ly - 8))} Q{P((0, Ly + ch * 2 - 8), (hw - 4, Ly - 8))}"
    cv.line(hem, "s")
    return geo


def draw_sharara(cv, spec, view, fill=None):
    """Fitted to the knee, then a gathered flare; gharara has a knee band."""
    fill = fill or spec.base
    ww, wb, knee, L = 66, 16, 170, 300
    for s_ in (-1, 1):
        leg = (f"M{P((0, wb))} L{P((s_ * ww, wb))} L{P((s_ * 76, 80))} L{P((s_ * 72, knee))} "
               f"Q{P((s_ * 110, 240), (s_ * 132, L))} Q{P((s_ * 76, L + 10), (s_ * 8, L))} "
               f"Q{P((s_ * 10, 240), (s_ * 12, knee))} L{P((0, 96))} Z")
        cv.shape(leg, [(s_ * 132, L), (s_ * ww, 0)], fill)
        _over(cv, spec, leg)
        cv.line(f"M{P((s_ * 72, knee))} L{P((s_ * 12, knee))}",
                "o" if spec.has("gharara") else "s")
        for i in range(7):
            x = s_ * (14 + i * 9)
            cv.line(f"M{P((x, knee + 2))} L{P((x * 1.1, knee + 16))}", "r")
        if spec.embellished:
            _trim(cv, f"M{P((s_ * 128, L - 8))} Q{P((s_ * 76, L + 2), (s_ * 10, L - 8))}", spec.trim)
    cv.shape(f"M{P((-ww, 0))} L{P((ww, 0))} L{P((ww, wb))} L{P((-ww, wb))} Z",
             [(-ww, 0), (ww, 0)], shade(fill, .93))
    for x in range(-ww + 6, ww, 8):
        cv.line(f"M{P((x, 2))} L{P((x, wb - 2))}", "r")
    return dict(L=L, hw=132)


def draw_bottom_w(cv, spec, view, cat=None):
    """Women's bottoms: leggings, palazzos, salwar / churidar, sharara, or the
    men's trouser drawing with the right width."""
    cat = cat or spec.cat
    if spec.has("sharara", "shararas", "gharara", "ghararas") or spec.w("sharara", "gharara"):
        return draw_sharara(cv, spec, view)
    b = WSpec(spec.item)
    if cat == "leggings" or spec.w("leggings", "jeggings"):
        b.fit, b.title = "skinny", b.title + " elastic "
        return S.draw_bottom(cv, b, view, "trousers")
    if cat == "ethnic_bottom" or spec.has("salwar", "patiala", "churidar", "dhoti", "afghani"):
        return S.draw_bottom(cv, b, view, "dhoti")
    if spec.w("palazzo", "wide leg", "culottes") or spec.has("palazzo", "palazzos", "culottes"):
        b.fit, b.title = "wide leg", b.title + " elastic "
        return S.draw_bottom(cv, b, view, "trousers")
    if spec.w("bootcut") or spec.has("flared", "flare", "bell bottom", "bootcut"):
        b.fit = "flared"
    return S.draw_bottom(cv, b, view, cat if cat in ("jeans", "joggers", "shorts") else "trousers")


# ---------------------------------------------------------------------------
# tops
# ---------------------------------------------------------------------------

def draw_top_w(cv, spec, view, fill=None, L=None):
    """Women's top variants; plain tees / shirts use the men's drawing."""
    cat = spec.cat
    crop = spec.w("crop top") or spec.has("crop", "cropped")
    L0 = L or (150 if crop else 215)
    if spec.w("sports bra") or spec.has("sports bra"):
        geo = dress_body(cv, spec, view, L=112, top="tank", sw=58, straight_hw=50, fill=fill)
        cv.shape(f"M{P((-50, 112))} L{P((50, 112))} L{P((50, 94))} L{P((-50, 94))} Z", [], shade(spec.base, .9))
        for x in range(-46, 50, 8):
            cv.line(f"M{P((x, 96))} L{P((x, 110))}", "r")
        if view != "front":
            cv.raw(f'<path d="M{P((-14, 40))} L{P((0, 80))} L{P((14, 40))}" fill="#fbfaf7" class="o"/>')
        return geo
    if spec.w("corset") or spec.has("bustier"):
        geo = dress_body(cv, spec, view, L=170, waist=None, top="corset", sw=60,
                         straight_hw=50, fill=fill, curve_hem=0)
        _boning(cv, dict(geo, ww=50, waist=165), view)
        return geo
    if spec.w("tube") or spec.has("strapless", "bandeau"):
        return dress_body(cv, spec, view, L=L0 - 20, top="tube", sw=60, straight_hw=54, fill=fill)
    if spec.w("halter"):
        return dress_body(cv, spec, view, L=L0, top="halter", sw=62, straight_hw=56, fill=fill)
    if spec.w("cami") or spec.has("cami", "camisole", "strappy", "spaghetti"):
        return dress_body(cv, spec, view, L=L0, top="strap", sw=62, straight_hw=56, fill=fill)
    if spec.w("off shoulder"):
        geo = dress_body(cv, spec, view, L=L0, top="tube", sw=64, straight_hw=56, fill=fill)
        band = f"M{P((-80, 28))} Q{P((0, 40), (80, 28))} L{P((84, 52))} Q{P((0, 66), (-84, 52))} Z"
        cv.shape(band, [(-84, 28), (84, 60)], shade(fill or spec.base, .96))
        _over(cv, spec, band)
        for s_ in (-1, 1):
            cv.shape(f"M{P((s_ * 66, 40))} Q{P((s_ * 104, 50), (s_ * 98, 92))} L{P((s_ * 68, 96))} Z",
                     [(s_ * 104, 50)], fill or spec.base)
        return geo
    if spec.w("peplum") or spec.has("peplum"):
        geo = dress_body(cv, spec, view, L=230, waist=150, ww=46, flare=.9, fill=fill,
                         sleeve=spec.sleeve or "short")
        gathers(cv, geo, 10)
        return geo
    if spec.w("tank") or spec.sleeve == "sleeveless":
        return dress_body(cv, spec, view, L=L0, top="tank", sw=62, straight_hw=58, fill=fill)
    if spec.w("bodysuit"):
        geo = dress_body(cv, spec, view, L=230, sw=62, straight_hw=48, fill=fill,
                         sleeve=spec.sleeve or "long")
        cv.raw(f'<path d="M{P((-48, 230))} Q{P((-20, 200), (-10, 236))} L{P((10, 236))} '
               f'Q{P((20, 200), (48, 230))}" fill="#fbfaf7" class="o"/>')
        return geo
    if cat == "kurta":
        return draw_kurta(cv, spec, view, fill=fill, short=True)
    # blouse / tunic / generic top
    puffy = spec.w("puff sleeve") or spec.has("puff", "ruffle", "frill", "blouse")
    if cat in ("tshirt", "shirt") and not puffy:
        return S.draw_top(cv, spec, view, cat, fill=fill)
    return dress_body(cv, spec, view, L=L0, sw=64, straight_hw=62, fill=fill,
                      sleeve=spec.sleeve or "short")


def draw_cape(cv, spec, view, fill=None):
    fill = fill or spec.base
    nw, L = 26, 250
    d = (f"{neckline(spec, view, 'round', nw, 22)} C{P((60, 10), (130, 90), (150, L - 20))} "
         f"Q{P((0, L + 40), (-150, L - 20))} C{P((-130, 90), (-60, 10), (-nw, 0))} Z")
    cv.shape(d, [(-150, 0), (150, L + 20)], fill)
    _over(cv, spec, d)
    if view == "front":
        cv.line(f"M{P((0, 26))} L{P((0, L + 18))}")
    if spec.embellished:
        _trim(cv, f"M{P((-146, L - 26))} Q{P((0, L + 28), (146, L - 26))}", spec.trim)
    return dict(L=L, hw=150)


def draw_shrug(cv, spec, view, fill=None):
    fill = fill or spec.base
    geo = dress_body(cv, spec, view, L=200 if not spec.has("long") else 360, sw=68,
                     straight_hw=74, fill=fill, sleeve=spec.sleeve or "long")
    if view == "front":  # open front
        L = geo["L"]
        cv.raw(f'<path d="M{P((-22, 2))} C{P((-14, 60), (-30, L - 40), (-44, L))} '
               f'L{P((44, L))} C{P((30, L - 40), (14, 60), (22, 2))} Z" fill="#fbfaf7" class="o"/>')
    return geo


# ---------------------------------------------------------------------------
# Indian outfits
# ---------------------------------------------------------------------------

def dupatta(cv, spec, view, top_y=0, length=380, side=-1):
    """Dupatta over one shoulder, hanging down (semi-sheer, bordered)."""
    c = spec.accent if not spec.has("dupatta set") else spec.base
    x0 = side * 60
    w = 46
    d = (f"M{P((x0 - side * 6, top_y + 2))} Q{P((x0 + side * 22, top_y - 8), (x0 + side * 40, top_y + 10))} "
         f"L{P((x0 + side * 36, top_y + length))} L{P((x0 + side * (36 - w), top_y + length))} "
         f"L{P((x0 - side * 6, top_y + 2))} Z")
    cv.raw(f'<path d="{d}" fill="{c}" fill-opacity=".72" class="o"/>')
    cv.pts += [(x0 + side * 44, top_y - 8), (x0 + side * 36, top_y + length)]
    _trim(cv, f"M{P((x0 + side * 32, top_y + 14))} L{P((x0 + side * 30, top_y + length - 8))}",
          GOLD if spec.embellished else shade(c, .6), 1.8)
    y = top_y + length
    for k in range(7):  # tassels
        x = x0 + side * (36 - w) + side * (w * k / 6)
        cv.line(f"M{P((x, y))} L{P((x, y + 12))}")
        cv.circle(x, y + 14, 2, GOLD if spec.embellished else shade(c, .6), "o")


def draw_kurta_set(cv, spec, view):
    has_dupatta = spec.w("dupatta") or spec.has("dupatta", "dupattas", "stole")
    jacket = spec.w("jacket", "cape", "shrug") or spec.has("jacket", "koti", "cape", "shrug")
    sharara = spec.has("sharara", "shararas", "gharara", "ghararas")
    skirt = spec.has("skirt", "lehenga")
    short = spec.has("short kurta", "short kurti", "kurti top") or sharara
    oy = 300 if short else 380
    if spec.w("anarkali") or spec.has("anarkali"):
        oy = 440
    if skirt:
        sub = Canvas()
        draw_skirt(sub, spec, view, 0, L=420, kind="flared")
    else:
        sub = Canvas()
        b = WSpec(spec.item)
        b.cat = "ethnic_bottom" if spec.has("salwar", "churidar", "patiala", "dhoti") else "trousers"
        if not (sharara or b.cat == "ethnic_bottom" or spec.has("palazzo", "palazzos", "straight pants",
                                                                  "trousers", "pants")):
            b.title += " palazzo "
        draw_bottom_w(sub, b, view)
    shift = oy - 150 if not skirt else oy - 170  # show a good length of the bottoms
    cv.els.append(f'<g transform="translate(0,{_f(shift)})">' + "".join(sub.els) + "</g>")
    cv.pts += [(x, y + shift) for x, y in sub.pts]
    geo = draw_kurta(cv, spec, view, short=short)
    if jacket:
        layer = WSpec(spec.item)
        layer.wpattern = "embellished" if spec.embellished else "solid"
        if spec.has("cape"):
            draw_cape(cv, layer, view, fill=spec.accent)
        else:
            g2 = dress_body(cv, layer, view, L=geo["L"] - 30, sw=70, straight_hw=80,
                            fill=spec.accent, top="tank", neck="v neck")
            if view == "front":
                cv.raw(f'<path d="M{P((-20, 2))} L{P((-18, g2["L"]))} L{P((18, g2["L"]))} '
                       f'L{P((20, 2))} Z" fill="{spec.base}" class="o"/>')
    if has_dupatta:
        dupatta(cv, spec, view, 0, min(geo["L"] + 40, 460), side=1 if view == "front" else -1)
    return geo


def draw_lehenga(cv, spec, view):
    sub = Canvas()
    draw_skirt(sub, spec, view, 0, L=430, kind="lehenga", border=True)
    oy = 150
    cv.els.append(f'<g transform="translate(0,{oy})">' + "".join(sub.els) + "</g>")
    cv.pts += [(x, y + oy) for x, y in sub.pts]
    # latkan on the drawstring
    cv.line(f"M{P((58, oy + 8))} Q{P((70, oy + 60), (64, oy + 110))}")
    cv.circle(64, oy + 116, 6, GOLD, "o")
    blouse = WSpec(spec.item)
    blouse.cat = "lehenga"
    if spec.has("crop top", "jacket", "cape"):
        draw_blouse(cv, blouse, view, L=160)
    else:
        draw_blouse(cv, blouse, view, L=134)
    if not spec.has("without dupatta", "no dupatta"):
        dupatta(cv, spec, view, 0, 420, side=1 if view == "front" else -1)
    return dict(L=oy + 430)


def draw_saree(cv, spec, view):
    """Blouse + pleated skirt column with border + pallu over the left shoulder."""
    front = view == "front"
    border_c = GOLD if spec.embellished or spec.has("zari", "banarasi", "kanjivaram",
                                                     "silk", "tissue") else spec.accent
    base = spec.base
    oy, L, ww, hw = 150, 560, 58, 92
    skirt = (f"M{P((-ww, oy))} L{P((ww, oy))} Q{P((ww + 26, oy + 90), (hw, L))} "
             f"Q{P((0, L + 14), (-hw, L))} Q{P((-ww - 26, oy + 90), (-ww, oy))} Z")
    cv.shape(skirt, [(-hw, oy), (hw, L + 8)], base)
    _over(cv, spec, skirt)
    band = (f"M{P((-hw, L))} Q{P((0, L + 14), (hw, L))} L{P((hw - 3, L - 22))} "
            f"Q{P((0, L - 8), (-hw + 3, L - 22))} Z")
    cv.raw(f'<path d="{band}" fill="{border_c}" fill-opacity=".9" class="o"/>')
    if front:  # pleats fanning from the navel
        for k in range(7):
            x0 = -10 + k * 5
            x1 = -36 + k * 12
            cv.line(f"M{P((x0, oy + 20))} L{P((x1, L - 2))}", "s" if k % 2 else "o")
    blouse = WSpec(spec.item)
    blouse.cat = "saree"
    blouse.wpattern = "solid" if spec.wpattern not in ("embellished",) else "embellished"
    draw_blouse(cv, blouse, view, fill=shade(base, .82) if not spec.has("blouse") else spec.accent,
                L=134)
    # pallu: across the bodice to the left shoulder (front), hanging down the back
    if front:
        pallu = (f"M{P((ww + 6, oy + 40))} L{P((ww + 24, oy + 4))} L{P((-50, -4))} "
                 f"L{P((-74, 12))} L{P((-4, oy + 70))} Z")
        cv.raw(f'<path d="{pallu}" fill="{base}" class="o"/>')
        _over(cv, spec, pallu)
        _trim(cv, f"M{P((ww + 20, oy + 10))} L{P((-52, 2))}", border_c, 3, "4 2")
        cv.line(f"M{P((ww + 2, oy + 30))} L{P((-60, 6))}", "s")
        cv.pts += [(-74, -4), (ww + 24, oy + 70)]
    else:
        pallu = (f"M{P((-74, 6))} L{P((-34, -4))} L{P((-8, 420))} L{P((-70, 430))} Z")
        cv.raw(f'<path d="{pallu}" fill="{base}" class="o"/>')
        _over(cv, spec, pallu)
        cv.raw(f'<path d="M{P((-14, 360))} L{P((-8, 420))} L{P((-70, 430))} L{P((-72, 368))} Z" '
               f'fill="{border_c}" fill-opacity=".9" class="o"/>')
        for k in range(8):
            x = -70 + k * 8.6
            cv.line(f"M{P((x, 430 - k * 1.2))} L{P((x, 444 - k * 1.2))}")
        cv.pts += [(-74, -4), (-8, 444)]
    return dict(L=L)


# ---------------------------------------------------------------------------
# jumpsuits and co-ord sets
# ---------------------------------------------------------------------------

def draw_jumpsuit(cv, spec, view):
    waist = 150
    sub = Canvas()
    b = WSpec(spec.item)
    b.fit = "wide leg" if not spec.has("skinny", "slim") else "slim"
    b.title += " elastic "
    if spec.has("romper", "playsuit") or spec.w("biker shorts"):
        S.draw_bottom(sub, b, view, "shorts")
    else:
        S.draw_bottom(sub, b, view, "trousers")
    oy = waist - 14
    cv.els.append(f'<g transform="translate(0,{oy})">' + "".join(sub.els) + "</g>")
    cv.pts += [(x, y + oy) for x, y in sub.pts]
    if spec.w("dungaree"):
        bib = f"M{P((-50, 60))} L{P((50, 60))} L{P((56, waist + 4))} L{P((-56, waist + 4))} Z"
        cv.shape(bib, [(-56, 60), (56, waist)], spec.base)
        for s_ in (-1, 1):
            cv.shape(f"M{P((s_ * 40, 60))} L{P((s_ * 52, 0))} L{P((s_ * 64, 2))} L{P((s_ * 52, 62))} Z",
                     [(s_ * 64, 0)], spec.base)
            cv.circle(s_ * 40, 70, 4, "#b8b2a4")
        return dict(L=oy + 300)
    top = "strap" if spec.has("strappy", "cami", "spaghetti") else \
        "halter" if spec.w("halter") else "tube" if spec.w("tube") else \
        "tank" if spec.sleeve == "sleeveless" else "sleeved"
    geo = dress_body(cv, spec, view, L=waist + 6, waist=None, top=top, sw=64,
                     straight_hw=70, curve_hem=0)
    if spec.has("belt", "belted", "tie", "waist tie") or True:
        _belt(cv, spec, 70, waist, view == "front") if spec.has("belt", "belted", "tie") else \
            cv.line(f"M{P((-70, waist))} L{P((70, waist))}")
    return dict(L=oy + 300, hw=geo["hw"])


def draw_coord(cv, spec, view):
    t = spec.title
    if spec.has("skirt", "skort"):
        bottom = "skirt"
    elif spec.has("shorts", "short"):
        bottom = "shorts"
    elif spec.has("sharara", "gharara"):
        bottom = "sharara"
    elif spec.has("jogger", "joggers", "track", "tracksuit") or spec.occasion == "activewear":
        bottom = "joggers"
    elif spec.has("leggings", "legging"):
        bottom = "leggings"
    else:
        bottom = "palazzo" if spec.has("palazzo", "wide leg", "flared") else "trousers"
    del t
    sub = Canvas()
    b = WSpec(spec.item)
    if bottom == "skirt":
        draw_skirt(sub, b, view, 0, L=300 if not spec.has("mini") else 200)
        oy = 150
    elif bottom == "sharara":
        draw_sharara(sub, b, view)
        oy = 170
    else:
        b.cat = {"palazzo": "trousers", "leggings": "leggings"}.get(bottom, bottom)
        if bottom == "palazzo":
            b.title += " palazzo "
        draw_bottom_w(sub, b, view, b.cat)
        oy = 180
    cv.els.append(f'<g transform="translate(0,{oy})">' + "".join(sub.els) + "</g>")
    cv.pts += [(x, y + oy) for x, y in sub.pts]
    top = WSpec(spec.item)
    if spec.has("blazer"):
        top.cat = "blazer"
        return S.draw_top(cv, top, view, "blazer")
    if spec.has("shirt", "shirts") and not spec.has("t shirt", "tshirt"):
        top.cat = "shirt"
        if top.neck in (None, "round neck"):
            top.neck = "collar"
        return S.draw_top(cv, top, view, "shirt")
    if spec.has("hoodie", "sweatshirt", "jacket") or bottom == "joggers":
        c = "hoodie" if spec.has("hoodie") else "jacket" if spec.has("jacket") else "sweatshirt"
        top.cat = c
        return S.draw_top(cv, top, view, c)
    if spec.has("kurta", "kurti", "tunic"):
        top.cat = "kurta"
        return draw_kurta(cv, top, view, short=True)
    top.cat = "top"
    if bottom in ("skirt", "sharara") and not spec.has("shirt", "tee"):
        top.wear = set(top.wear) | {"crop top"}
    return draw_top_w(cv, top, view)


# ---------------------------------------------------------------------------
# footwear and accessories
# ---------------------------------------------------------------------------

def _heel_kind(spec):
    w = spec.wear
    if "wedges" in w or spec.has("wedge", "wedges"):
        return "wedge"
    if "block heels" in w or spec.has("block", "chunky heel"):
        return "block"
    if "kitten heels" in w or spec.has("kitten"):
        return "kitten"
    if "platform" in w:
        return "platform"
    return "stiletto"


def draw_heels(cv, spec, view):
    kind = _heel_kind(spec)
    base, front = spec.base, view == "front"
    strappy = spec.has("sandal", "sandals", "strappy", "strap", "straps", "ankle strap",
                       "open toe", "peep toe")
    mule = spec.has("mule", "mules", "slip on")
    sole_c = shade(base, .55) if luminance(base) > .35 else "#2a2522"
    h = {"stiletto": 96, "block": 80, "kitten": 44, "wedge": 86, "platform": 100}[kind]
    if front:  # side profile, toe right
        yb = 60  # ground
        heel_top = yb - h
        # insole line from heel seat (high, left) to toe (ground, right)
        sole = (f"M{P((-110, heel_top))} C{P((-60, heel_top + 4), (-10, yb - 26), (40, yb - 6))} "
                f"L{P((120, yb - 4))} Q{P((132, yb), (122, yb + 6))} L{P((40, yb + 6))} "
                f"C{P((-10, yb - 14), (-60, heel_top + 12), (-104, heel_top + 12))} Z")
        cv.shape(sole, [(-110, heel_top), (132, yb + 6)], sole_c)
        if kind == "wedge":
            cv.shape(f"M{P((-108, heel_top + 10))} C{P((-60, heel_top + 14), (-10, yb - 12), (40, yb + 4))} "
                     f"L{P((-100, yb + 6))} Z", [(-108, yb + 6)], shade(base, .8) if not spec.has("jute", "cork") else "#c9a46a")
        else:
            x0 = -104
            wtop, wbot = (22, 6) if kind == "stiletto" else ((26, 22) if kind == "block" else (16, 6))
            cv.shape(f"M{P((x0, heel_top + 10))} L{P((x0 + wtop, heel_top + 12))} "
                     f"L{P((x0 + wtop - 4 if kind != 'block' else x0 + wbot, yb + 6))} "
                     f"L{P((x0 + (0 if kind == 'block' else wtop - 4 - wbot), yb + 6))} Z",
                     [(x0, yb + 6)], sole_c)
        if kind == "platform":
            cv.shape(f"M{P((20, yb - 10))} L{P((126, yb - 10))} Q{P((134, yb), (124, yb + 8))} L{P((24, yb + 8))} Z",
                     [], sole_c)
        if strappy:
            for x0, y0 in ((60, yb - 6), (90, yb - 4)):
                cv.shape(f"M{P((x0 - 8, y0))} C{P((x0 - 4, y0 - 34), (x0 + 16, y0 - 34), (x0 + 20, y0))} Z",
                         [(x0, y0 - 34)], base)
            cv.shape(f"M{P((-112, heel_top - 4))} Q{P((-90, heel_top - 40), (-60, heel_top - 34))} "
                     f"L{P((-56, heel_top - 26))} Q{P((-88, heel_top - 30), (-104, heel_top + 4))} Z",
                     [(-112, heel_top - 40)], base)
            cv.circle(-60, heel_top - 30, 3, GOLD)
        else:
            up = (f"M{P((-108 if not mule else -40, heel_top + 2))} "
                  + (f"C{P((-112, heel_top - 26), (-86, heel_top - 30), (-70, heel_top - 22))} "
                     f"Q{P((-40, heel_top - 10), (-20, yb - 52))} " if not mule else
                     f"Q{P((-30, yb - 66), (-10, yb - 52))} ")
                  + f"C{P((30, yb - 46), (100, yb - 34), (122, yb - 4))} L{P((40, yb - 6))} "
                  f"C{P((-10, yb - 26), (-60, heel_top + 4), (-108 if not mule else -40, heel_top + 2))} Z")
            cv.shape(up, [(-112, heel_top - 30), (122, yb)], base)
            _over(cv, spec, up)
            cv.line(f"M{P((-30, yb - 58))} Q{P((10, yb - 40), (20, yb - 48))}", "s")
            if spec.has("bow"):
                cv.raw(f'<path d="M{P((40, yb - 44))} l-12 -10 l0 20z M{P((40, yb - 44))} l12 -10 l0 20z" '
                       f'fill="{spec.accent}" class="o"/>')
        if spec.embellished:
            for x in (60, 76, 92):
                cv.circle(x, yb - 22, 3, GOLD, "s")
        return
    # top view (toe right, pointed or rounded)
    pointed = kind in ("stiletto", "kitten") and not spec.has("round toe", "square toe")
    w = 34
    toe = (f"C{P((60, -w - 2), (110, -14))} {P((142, 0))} C{P((110, 14), (60, w + 2))} {P((0, w))}"
           if pointed else
           f"C{P((60, -w - 4), (118, -w + 4))} {P((126, 0))} C{P((118, w - 4), (60, w + 4))} {P((0, w))}")
    out = (f"M{P((-116, 0))} C{P((-116, -w + 6), (-80, -w + 2), (0, -w))} {toe} "
           f"C{P((-80, w - 2), (-116, w - 6), (-116, 0))} Z")
    cv.shape(out, [(-116, -w - 4), (142, w + 4)], sole_c if strappy or mule else base)
    if not strappy:
        _over(cv, spec, out)
        if not mule:
            cv.raw(f'<path d="M{P((-104, 0))} C{P((-104, -w + 12), (-70, -w + 10), (-20, -w + 10))} '
                   f'C{P((20, -14), (20, 14), (-20, w - 10))} C{P((-70, w - 10), (-104, w - 12), (-104, 0))} Z" '
                   f'fill="{spec.inner}" class="o"/>')
        else:
            cv.raw(f'<path d="M{P((-116, 0))} C{P((-116, -w + 6), (-80, -w + 2), (-20, -w + 2))} '
                   f'L{P((-20, w - 2))} C{P((-80, w - 2), (-116, w - 6), (-116, 0))} Z" fill="{spec.inner}" class="o"/>')
    else:
        for x0 in (20, 60):
            cv.shape(_rr(x0, -w - 2, x0 + 14, w + 2, 5), [], base)
        cv.shape(_rr(-96, -w + 2, -82, w - 2, 5), [], base)


def draw_flats(cv, spec, view):
    base, front = spec.base, view == "front"
    if "loafers" in spec.wear or spec.has("loafer", "loafers", "moccasin"):
        s2 = WSpec(spec.item)
        s2.wear = set(s2.wear) | {"loafers"}
        s2.cat = "shoes"
        return S.draw_footwear(cv, s2, view)
    mule = spec.has("mule", "mules")
    sole_c = shade(base, .55) if luminance(base) > .35 else "#2a2522"
    if front:
        yb = 60
        cv.shape(f"M{P((-118, yb - 6))} L{P((124, yb - 6))} Q{P((134, yb), (124, yb + 6))} "
                 f"L{P((-114, yb + 6))} Q{P((-124, yb), (-118, yb - 6))} Z", [(-124, yb + 6)], sole_c)
        up = (f"M{P((-116 if not mule else -30, yb - 6))} "
              + (f"C{P((-120, yb - 40), (-100, yb - 46), (-80, yb - 40))} Q{P((-40, yb - 30), (-10, yb - 42))} "
                 if not mule else f"Q{P((-24, yb - 50), (-6, yb - 46))} ")
              + f"C{P((40, yb - 52), (110, yb - 40), (124, yb - 6))} Z")
        cv.shape(up, [(-120, yb - 52), (124, yb)], base)
        _over(cv, spec, up)
        if spec.has("bow") or "ballerinas" in spec.wear:
            cv.raw(f'<path d="M{P((10, yb - 44))} l-14 -10 l0 20z M{P((10, yb - 44))} l14 -10 l0 20z" '
                   f'fill="{spec.accent}" class="o"/>')
            cv.circle(10, yb - 44, 3, spec.accent)
        if spec.has("mary jane", "mary janes", "strap"):
            cv.line(f"M{P((-40, yb - 36))} Q{P((-20, yb - 60), (6, yb - 44))}")
        cv.line(f"M{P((-110, yb - 12))} L{P((118, yb - 12))}", "s")
        return
    w = 36
    out = (f"M{P((-118, 0))} C{P((-118, -w + 6), (-80, -w), (0, -w))} C{P((60, -w - 4), (118, -w + 6))} "
           f"{P((126, 0))} C{P((118, w - 6), (60, w + 4))} {P((0, w))} C{P((-80, w), (-118, w - 6))} {P((-118, 0))} Z")
    cv.shape(out, [(-118, -w - 4), (126, w + 4)], base)
    _over(cv, spec, out)
    open_to = 10 if not mule else 30
    cv.raw(f'<path d="M{P((-106, 0))} C{P((-106, -w + 10), (-60, -w + 8), (-20, -w + 10))} '
           f'C{P((open_to, -14), (open_to, 14), (-20, w - 10))} C{P((-60, w - 8), (-106, w - 10), (-106, 0))} Z" '
           f'fill="{spec.inner}" class="o"/>')


def draw_clutch(cv, spec, view):
    base, front = spec.base, view == "front"
    if "potli" in spec.wear or spec.has("potli", "batua"):
        body = (f"M{P((-40, -40))} Q{P((-110, 10), (-80, 80))} Q{P((0, 110), (80, 80))} "
                f"Q{P((110, 10), (40, -40))} Z")
        cv.shape(body, [(-110, -40), (110, 100)], base)
        _over(cv, spec, body)
        cv.shape(f"M{P((-44, -60))} Q{P((0, -70), (44, -60))} L{P((40, -40))} Q{P((0, -48), (-40, -40))} Z",
                 [(-44, -70)], shade(base, .9))
        for x in range(-38, 40, 8):
            cv.line(f"M{P((x, -56))} L{P((x * 1.05, -40))}", "r")
        cv.line(f"M{P((-30, -60))} C{P((-40, -130), (40, -130), (30, -60))}")
        for s_ in (-1, 1):  # tassels on the drawstring
            cv.line(f"M{P((s_ * 44, -46))} L{P((s_ * 60, 0))}")
            cv.circle(s_ * 60, 6, 6, GOLD, "o")
        _trim(cv, f"M{P((-92, 50))} Q{P((0, 84), (92, 50))}", GOLD if spec.embellished else spec.accent)
        return
    _rect(cv, -110, -50, 110, 60, 12, base)
    _over(cv, spec, _rr(-110, -50, 110, 60, 12))
    if front:
        cv.shape(f"M{P((-110, -40))} Q{P((-110, -50), (-100, -50))} L{P((100, -50))} Q{P((110, -50), (110, -40))} "
                 f"L{P((0, 18))} Z", [], shade(base, .92))
        cv.shape(_rr(-10, 8, 10, 26, 4), [], GOLD)
        if spec.embellished:
            for x in range(-90, 100, 18):
                cv.circle(x, 46, 3, GOLD, "s")
    else:
        cv.line(f"M{P((-100, 0))} L{P((100, 0))}", "s")
        cv.line(f"M{P((-80, -50))} C{P((-80, -120), (80, -120), (80, -50))}", "z")
        cv.pts += [(0, -110)]


def draw_handbag(cv, spec, view):
    base, front = spec.base, view == "front"
    body = f"M{P((-100, -40))} L{P((100, -40))} L{P((116, 90))} Q{P((116, 100), (104, 100))} " \
           f"L{P((-104, 100))} Q{P((-116, 100), (-116, 90))} Z"
    cv.shape(body, [(-116, -40), (116, 100)], base)
    _over(cv, spec, body)
    for s_ in (-1, 1):
        cv.line(f"M{P((s_ * 64, -40))} C{P((s_ * 64, -110), (s_ * 18, -110), (s_ * 18, -40))}")
        cv.shape(_rr(s_ * 64 - 7, -46, s_ * 64 + 7, -32, 3), [], "#b8b2a4" if not spec.has("gold") else GOLD)
        cv.shape(_rr(s_ * 18 - 7, -46, s_ * 18 + 7, -32, 3), [], "#b8b2a4" if not spec.has("gold") else GOLD)
    if front:
        cv.shape(f"M{P((-100, -40))} L{P((100, -40))} L{P((104, 14))} Q{P((0, 34), (-104, 14))} Z", [], shade(base, .92))
        cv.shape(_rr(-12, 14, 12, 32, 4), [], "#b8b2a4" if not spec.has("gold") else GOLD)
    else:
        cv.line(_rr(-70, 10, 70, 70, 8), "s")
    cv.line(f"M{P((-96, 88))} L{P((96, 88))}", "s")
    cv.pts += [(0, -100)]


def draw_jewellery(cv, spec, view):
    base = GOLD if not spec.has("silver", "oxidised", "oxidized", "german silver", "white") else "#a9abae"
    if spec.has("oxidised", "oxidized", "german silver"):
        base = "#7f8287"
    stone = spec.base if spec.item.get("color") not in (None, "yellow", "grey", "white") else "#b33b3b"
    w, front = spec.wear, view == "front"
    if w & {"jhumka", "earrings"} or spec.has("earring", "earrings", "jhumka", "jhumkas", "studs",
                                              "hoops", "danglers", "chandbali"):
        for s_ in (-1, 1):
            x = s_ * 70
            if "jhumka" in w or spec.has("jhumka", "jhumkas", "jhumki"):
                cv.circle(x, -40, 16, base)
                cv.circle(x, -40, 7, stone)
                cv.line(f"M{P((x, -24))} L{P((x, -4))}")
                bell = f"M{P((x - 30, 60))} C{P((x - 26, 0), (x + 26, 0), (x + 30, 60))} Z"
                cv.shape(bell, [(x - 30, 0), (x + 30, 60)], base)
                cv.line(f"M{P((x - 24, 40))} Q{P((x, 30), (x + 24, 40))}", "s")
                for k in range(7):
                    xx = x - 27 + k * 9
                    cv.line(f"M{P((xx, 60))} L{P((xx, 72))}")
                    cv.circle(xx, 76, 3.4, WHITE if not spec.has("ruby", "red") else "#b33b3b")
            elif "hoop" in spec.title or spec.has("hoops", "hoop", "bali", "balis"):
                cv.raw(f'<ellipse cx="{x}" cy="20" rx="40" ry="44" fill="none" stroke="{base}" '
                       f'stroke-width="9"/>')
                cv.raw(f'<ellipse cx="{x}" cy="20" rx="40" ry="44" fill="none" class="o"/>')
                cv.pts += [(x - 44, -28), (x + 44, 68)]
            else:  # stud + drop
                cv.circle(x, -40, 12, base)
                cv.circle(x, -40, 5, stone)
                cv.line(f"M{P((x, -28))} L{P((x, 0))}")
                drop = f"M{P((x, 0))} C{P((x - 26, 30), (x - 18, 70), (x, 76))} C{P((x + 18, 70), (x + 26, 30), (x, 0))} Z"
                cv.shape(drop, [(x - 26, 0), (x + 26, 76)], base)
                cv.circle(x, 46, 9, stone)
        return
    if w & {"bangles", "bracelet"} or spec.has("bangle", "bangles", "kada", "kangan", "bracelet"):
        n = 4 if spec.has("set", "pair", "bangles") else 1
        for k in range(n):
            y = -30 + k * 22 if front else 0
            cv.raw(f'<ellipse cx="0" cy="{y}" rx="90" ry="{30 if front else 90}" fill="none" '
                   f'stroke="{base}" stroke-width="12"/>')
            cv.raw(f'<ellipse cx="0" cy="{y}" rx="90" ry="{30 if front else 90}" fill="none" class="o"/>')
            if spec.embellished or spec.has("kundan", "stone", "studded"):
                for a in range(0, 360, 30):
                    cv.circle(90 * math.cos(math.radians(a)), y + (30 if front else 90) * math.sin(math.radians(a)),
                              3.2, stone, "o")
            if not front:
                break
        cv.pts += [(-96, -60), (96, 100)]
        return
    if "maang tikka" in w:
        cv.line(f"M{P((0, -120))} L{P((0, 10))}")
        for y in range(-110, 10, 14):
            cv.circle(0, y, 3, base, "o")
        pend = f"M{P((0, 10))} C{P((-40, 30), (-30, 80), (0, 96))} C{P((30, 80), (40, 30), (0, 10))} Z"
        cv.shape(pend, [(-40, 10), (40, 96)], base)
        cv.circle(0, 52, 12, stone)
        for k in range(5):
            cv.circle(-20 + k * 10, 104, 3.4, WHITE)
        cv.circle(0, -126, 8, base)
        return
    if "anklet" in w:
        cv.raw(f'<ellipse cx="0" cy="0" rx="100" ry="{40 if front else 100}" fill="none" '
               f'stroke="{base}" stroke-width="5" stroke-dasharray="6 3"/>')
        for a in range(10, 180, 20):
            x, y = 100 * math.cos(math.radians(a)), (40 if front else 100) * math.sin(math.radians(a))
            cv.line(f"M{P((x, y))} L{P((x, y + 12))}")
            cv.circle(x, y + 16, 4, base)
        cv.pts += [(-104, -44), (104, 120)]
        return
    if "necklace" in w or "choker" in w or spec.has("necklace", "choker", "haar", "mangalsutra",
                                                       "pendant", "chain"):
        r = 80 if "choker" in w else 110
        cv.raw(f'<path d="M{P((-r, -60))} C{P((-r, 40), (r, 40), (r, -60))}" fill="none" '
               f'stroke="{base}" stroke-width="{10 if "choker" in w else 4}"/>')
        cv.line(f"M{P((-r, -60))} C{P((-r, 40), (r, 40), (r, -60))}", "s")
        if front:
            pend = f"M{P((0, 18))} C{P((-30, 34), (-24, 70), (0, 84))} C{P((24, 70), (30, 34), (0, 18))} Z"
            cv.shape(pend, [(-30, 18), (30, 84)], base)
            cv.circle(0, 50, 10, stone)
            if spec.has("kundan", "polki", "temple", "set") or spec.embellished:
                for k in range(-4, 5):
                    if k:
                        x = k * r / 5
                        y = -60 + 100 * (1 - (x / r) ** 2) * .75
                        cv.circle(x, y, 6, stone, "o")
        cv.pts += [(-r, -64), (r, 90)]
        return
    if "nose pin" in w:
        cv.raw(f'<ellipse cx="0" cy="0" rx="60" ry="62" fill="none" stroke="{base}" stroke-width="5"/>')
        cv.circle(-42, -44, 10, stone)
        cv.pts += [(-64, -66), (64, 66)]
        return
    if "ring" in w:
        cv.raw(f'<ellipse cx="0" cy="20" rx="56" ry="{20 if front else 56}" fill="none" stroke="{base}" '
               f'stroke-width="10"/>')
        cv.circle(0, -20 if front else 20, 20, stone)
        cv.pts += [(-62, -44), (62, 80)]
        return
    return S.draw_accessory(cv, spec, view)


def draw_hair(cv, spec, view):
    base = spec.base
    if "scrunchie" in spec.wear:
        d = ""
        for k in range(16):
            a0, a1 = k * 22.5, (k + 1) * 22.5
            r0, r1 = 70, 70
            p0 = (r0 * math.cos(math.radians(a0)), r0 * math.sin(math.radians(a0)))
            p1 = (r1 * math.cos(math.radians(a1)), r1 * math.sin(math.radians(a1)))
            mid = (96 * math.cos(math.radians((a0 + a1) / 2)), 96 * math.sin(math.radians((a0 + a1) / 2)))
            d += (f"M{P(p0)} " if k == 0 else "") + f"Q{P(mid, p1)} "
        cv.shape(d + "Z", [(-100, -100), (100, 100)], base)
        _over(cv, spec, d + "Z")
        cv.circle(0, 0, 44, "#fbfaf7")
        return
    if "hairband" in spec.wear:
        cv.raw(f'<path d="M{P((-100, 60))} C{P((-110, -90), (110, -90), (100, 60))}" fill="none" '
               f'stroke="{base}" stroke-width="18" stroke-linecap="round"/>')
        cv.line(f"M{P((-100, 60))} C{P((-110, -90), (110, -90), (100, 60))}", "s")
        cv.pts += [(-110, -90), (110, 66)]
        return
    # clips / claw clips / pins
    if spec.has("claw"):
        for k in range(6):
            x = -60 + k * 24
            cv.shape(f"M{P((x - 8, 0))} Q{P((x, -70), (x + 8, 0))} Z", [(x, -70)], base)
        _rect(cv, -80, -6, 80, 18, 8, shade(base, .9))
        return
    _rect(cv, -110, -16, 110, 16, 16, base)
    _over(cv, spec, _rr(-110, -16, 110, 16, 16))
    if spec.embellished or spec.has("pearl", "pearls", "stone"):
        for x in range(-90, 100, 20):
            cv.circle(x, 0, 6, WHITE if spec.has("pearl", "pearls") else GOLD, "o")


# ---------------------------------------------------------------------------
# dispatch + file output
# ---------------------------------------------------------------------------

SHARED_TOPS = ("tshirt", "shirt", "sweatshirt", "hoodie", "sweater", "jacket", "blazer",
               "ethnic_jacket")


def _render_view(spec, view):
    cv = Canvas()
    cat = spec.cat
    dept = spec.item.get("department")
    if dept == "footwear":
        if cat == "heels":
            draw_heels(cv, spec, view)
        elif cat == "flats":
            draw_flats(cv, spec, view)
        else:
            s2 = WSpec(spec.item)
            if "kolhapuri" in spec.wear:
                s2.cat = "sandals"
            S.draw_footwear(cv, s2, view)
        return cv
    if dept == "accessories":
        if cat == "clutch" or "potli" in spec.wear:
            draw_clutch(cv, spec, view)
        elif cat == "bag" and (spec.wear & {"handbag"} or not spec.wear & {"tote", "sling",
                                                                             "backpack"}):
            draw_handbag(cv, spec, view)
        elif cat == "jewellery":
            draw_jewellery(cv, spec, view)
        elif cat == "hair_accessory":
            draw_hair(cv, spec, view)
        else:
            S.draw_accessory(cv, spec, view)
        return cv
    if cat == "dress":
        draw_dress(cv, spec, view)
    elif cat == "gown":
        L = 560
        geo = dress_body(cv, spec, view, L=L, waist=150, ww=46, flare=.6,
                         top="strap" if spec.has("strappy", "spaghetti") else
                         "tube" if spec.has("strapless", "off shoulder", "tube") else
                         "sleeved", train=50, sleeve=spec.sleeve or "sleeveless"
                         if spec.has("sleeveless") else spec.sleeve)
        kalis(cv, geo, 10)
        if spec.embellished:
            hem_border(cv, spec, geo, 14)
        if spec.has("cape"):
            layer = WSpec(spec.item)
            layer.wpattern = "solid"
            draw_cape(cv, layer, view, fill=spec.accent)
    elif cat == "kurta":
        draw_kurta(cv, spec, view)
    elif cat == "kurta_set":
        draw_kurta_set(cv, spec, view)
    elif cat == "saree":
        draw_saree(cv, spec, view)
    elif cat == "lehenga":
        draw_lehenga(cv, spec, view)
    elif cat == "blouse":
        draw_blouse(cv, spec, view)
    elif cat == "jumpsuit":
        draw_jumpsuit(cv, spec, view)
    elif cat == "coord_set":
        draw_coord(cv, spec, view)
    elif cat == "skirt":
        draw_skirt(cv, spec, view)
    elif cat == "shrug":
        if spec.has("cape", "poncho"):
            draw_cape(cv, spec, view)
        else:
            draw_shrug(cv, spec, view)
    elif cat == "top":
        draw_top_w(cv, spec, view)
    elif cat in ("leggings", "ethnic_bottom", "trousers", "jeans", "joggers", "shorts"):
        draw_bottom_w(cv, spec, view, cat)
    elif cat in SHARED_TOPS:
        if cat in ("tshirt", "shirt") and (spec.w("crop top", "peplum", "puff sleeve", "off shoulder",
                                                  "tube", "corset")):
            draw_top_w(cv, spec, view)
        else:
            S.draw_top(cv, spec, view, cat)
    else:
        S.draw_top(cv, spec, view, "tshirt")
    return cv


def render_svg(item: dict) -> str:
    """Front + back technical flat for one women's catalogue item."""
    spec = WSpec(item)
    views = [_render_view(spec, v) for v in ("front", "back")]
    boxes = [v.bbox() for v in views]
    w = max(b[2] - b[0] for b in boxes)
    h = max(b[3] - b[1] for b in boxes)
    s = min((CELL_W - 24) / w, (CELL_H - 28) / h, 1.25)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CELL_W * 2} {CELL_H}" '
           f'width="{CELL_W * 2}" height="{CELL_H}">', STYLE,
           f"<defs>{pattern_defs_w(spec)}</defs>"]
    for i, (v, b) in enumerate(zip(views, boxes)):
        cx = CELL_W * i + CELL_W / 2 - s * (b[0] + b[2]) / 2
        cy = CELL_H / 2 - s * (b[1] + b[3]) / 2
        out.append(f'<g transform="translate({_f(cx)},{_f(cy)}) scale({s:.3f})">'
                   + "".join(v.els) + "</g>")
    out.append("</svg>")
    return "".join(out)


def sketch_path(item) -> str:
    site, pid = item["id"].split(":", 1)
    return f"sketch_women/{site}/{re.sub(r'[^A-Za-z0-9_-]', '_', pid)}.svg"


def write_sketches(items, web_dir, force=False) -> int:
    """Write one SVG per item under web/sketch_women/<site>/<id>.svg."""
    n = 0
    for it in items:
        rel = sketch_path(it)
        p = Path(web_dir) / rel
        if p.exists() and not force:
            it["sketch"] = rel
            continue
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(render_svg(it), encoding="utf-8")
        it["sketch"] = rel
        n += 1
    return n

"""Technical flat sketches (front + back) drawn from an item's attributes.

Every catalogue item gets one SVG in the style of a fashion tech-pack flat:
the garment alone, solid fill in its colour, dark outline, stitch lines, front
view on the left and back view on the right. The drawing is parametric, so it
follows what the scraper extracted:

  category       silhouette template (tee, shirt, polo, hoodie, kurta, nehru
                 jacket, sherwani, trousers, joggers, dhoti, sets ...)
  fit            body / leg width, drop shoulders, cropped length
  sleeve_length  sleeveless, short, three quarter, long
  neckline       round, v, polo, shirt collar, mandarin, hooded, high neck, henley
  color          fill (site colour name first, e.g. "olive", "maroon")
  secondary      stripes / checks / prints / embroidery colour
  pattern        striped, checked, graphic, floral, embroidered, tie dye, camo,
                 colour block, washed, textured
  wear_types     cargo pockets, bomber ribs, jeans 5-pocket, jacket over kurta ...

Nothing here touches the network; ~13k sketches render in well under a minute.
"""
import math
import re
from pathlib import Path

from .classify import norm

CELL_W, CELL_H = 300, 340

# ---------------------------------------------------------------------------
# colour
# ---------------------------------------------------------------------------

BASE_HEX = {
    "black": "#3b3b3d", "white": "#f4f2ec", "grey": "#9c9c9c", "navy": "#2f3b5e",
    "blue": "#5a86c4", "red": "#b33b3b", "green": "#5b8a5a", "beige": "#d9c8a6",
    "brown": "#7a5638", "yellow": "#e3c250", "orange": "#e08b3d", "pink": "#e8a4b6",
    "purple": "#7d5a9c", "multi": "#b9a98f",
}
NAMED_HEX = {
    "olive": "#6f6e3c", "maroon": "#6e2230", "burgundy": "#74243a", "wine": "#6a2238",
    "mustard": "#c9a03a", "khaki": "#b9a77a", "cream": "#efe6cf", "ivory": "#f3eedd",
    "off white": "#f1ede2", "charcoal": "#4b4b4d", "sky blue": "#9cc3e6",
    "light blue": "#a9c8e8", "teal": "#2f7a7a", "mint": "#a8d8bf", "sage": "#a3b597",
    "lavender": "#b8a6d6", "peach": "#f2b99a", "rust": "#a8532e", "coral": "#e9806e",
    "rose": "#d58a98", "lilac": "#c3a6d0", "emerald": "#2f7d5b", "bottle green": "#2d5a41",
    "forest": "#2f4f36", "sand": "#d6c4a1", "tan": "#c09a6b", "camel": "#c19a62",
    "coffee": "#5b3d2b", "chocolate": "#4e3324", "stone": "#c8c0b0", "indigo": "#3b4a8a",
    "royal blue": "#2f55a4", "cobalt": "#2e4fa0", "powder blue": "#b0c8e0",
    "magenta": "#b03a7a", "fuchsia": "#c2407e", "mauve": "#a07a8e", "plum": "#5e3550",
    "lemon": "#f0e27a", "gold": "#c8a24a", "golden": "#c8a24a", "silver": "#c4c4c4",
    "copper": "#b56b3c", "ecru": "#e9e1cc", "taupe": "#9c8b7a", "lime": "#a8c84a",
    "pista": "#b7cf8e", "turquoise": "#3fb0b0", "aqua": "#7fd0d0", "melange": "#a6a6a6",
    "heather": "#a2a2a2", "onion": "#c79aa0", "rani": "#d1307a", "peacock": "#1f6f7a",
    "beetroot": "#7a2040", "midnight": "#262f4a", "ink": "#283048", "denim": "#4d6a92",
    "dark blue": "#2d3f6b", "light grey": "#c3c3c3", "dark grey": "#5b5b5d",
    "jet black": "#2f2f31", "dark green": "#2f4f3a", "light green": "#a6cf9a",
    "dark brown": "#4b3324", "light brown": "#a07a55", "cherry": "#9b2335",
    "brick": "#9b4a35", "salmon": "#ec9a86", "blush": "#efc2c2", "biscuit": "#d8b98c",
    "oatmeal": "#ddd2bc", "latte": "#c8ab8a", "terracotta": "#c0623f", "ochre": "#c58b2c",
    "saffron": "#ee9a2e", "sea green": "#3c9a7a", "steel": "#7d8a99", "slate": "#6f7d8a",
}
_NAMED = sorted(NAMED_HEX, key=len, reverse=True)
GOLD = "#c8a24a"


def color_hex(item) -> str:
    text = norm(f"{item.get('color_name') or ''} {item.get('title') or ''}")
    for name in _NAMED:
        if f" {name} " in text:
            return NAMED_HEX[name]
    return BASE_HEX.get(item.get("color") or "", "#b7b2a8")


def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def shade(h, f):
    """f < 1 darkens, f > 1 lightens towards white."""
    r, g, b = _rgb(h)
    if f <= 1:
        r, g, b = (int(c * f) for c in (r, g, b))
    else:
        t = min(1.0, f - 1)
        r, g, b = (int(c + (255 - c) * t) for c in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


def luminance(h):
    r, g, b = _rgb(h)
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255


def accent_hex(item, base):
    sec = item.get("secondary_color")
    if sec and sec != item.get("color") and sec in BASE_HEX and sec != "multi":
        return BASE_HEX[sec]
    return shade(base, 0.62) if luminance(base) > 0.45 else shade(base, 1.45)


# ---------------------------------------------------------------------------
# geometry helpers
# ---------------------------------------------------------------------------


def _f(v):
    return f"{v:.1f}".rstrip("0").rstrip(".")


def P(*pts):
    return " ".join(f"{_f(x)},{_f(y)}" for x, y in pts)


class Canvas:
    """Collects SVG elements for one view and the outline points for fitting."""

    def __init__(self):
        self.els, self.pts = [], []

    def shape(self, d, pts, fill, extra=""):
        self.pts += pts
        self.els.append(f'<path d="{d}" fill="{fill}" class="o"{extra}/>')

    def fill_only(self, d, fill):
        self.els.append(f'<path d="{d}" fill="{fill}" stroke="none"/>')

    def line(self, d, cls="o"):
        self.els.append(f'<path d="{d}" class="{cls}"/>')

    def raw(self, s):
        self.els.append(s)

    def circle(self, x, y, r, fill="none", cls="o"):
        self.els.append(f'<circle cx="{_f(x)}" cy="{_f(y)}" r="{_f(r)}" fill="{fill}" '
                        f'class="{cls}"/>')

    def bbox(self):
        xs = [p[0] for p in self.pts] or [0]
        ys = [p[1] for p in self.pts] or [0]
        return min(xs), min(ys), max(xs), max(ys)


def mirror(pts):
    return [(-x, y) for x, y in pts]


def poly_d(pts, close=True):
    d = "M" + " L".join(P(p) for p in pts)
    return d + (" Z" if close else "")


# ---------------------------------------------------------------------------
# garment specs from attributes
# ---------------------------------------------------------------------------


class Spec:
    def __init__(self, item):
        self.item = item
        self.title = norm(item.get("title") or "")
        self.cat = item.get("category") or "tshirt"
        self.fit = item.get("fit") or "regular"
        self.sleeve = item.get("sleeve_length")
        self.neck = item.get("neckline")
        self.pattern = item.get("pattern") or "solid"
        self.wear = set(item.get("wear_types") or [])
        self.base = color_hex(item)
        self.accent = accent_hex(item, self.base)
        self.inner = shade(self.base, 0.72)
        self.formal = item.get("occasion") == "formal" or self.has("formal", "formals")

    def has(self, *words):
        return any(f" {w} " in self.title for w in words)


def pattern_defs(spec: Spec, view: str) -> str:
    """<pattern> definitions for the item's print (ids are local to the file)."""
    a, b, p = spec.accent, spec.base, spec.pattern
    if p == "striped":
        w = 9 if spec.has("pinstripe", "pinstriped", "pin") else 14
        return (f'<pattern id="pt" width="{w}" height="{w}" patternUnits="userSpaceOnUse">'
                f'<rect width="{w * 0.32:.1f}" height="{w}" fill="{a}" opacity=".85"/></pattern>')
    if p == "checked":
        return ('<pattern id="pt" width="22" height="22" patternUnits="userSpaceOnUse">'
                f'<rect width="8" height="22" fill="{a}" opacity=".45"/>'
                f'<rect width="22" height="8" fill="{a}" opacity=".45"/>'
                f'<rect width="22" height="1.2" y="15" fill="{shade(a, .7)}" opacity=".6"/>'
                '</pattern>')
    if p in ("floral", "graphic", "embroidered"):
        c = GOLD if p == "embroidered" else a
        return ('<pattern id="pt" width="34" height="34" patternUnits="userSpaceOnUse">'
                + "".join(f'<circle cx="{8 + 4 * math.cos(k * 1.257):.1f}" '
                          f'cy="{8 + 4 * math.sin(k * 1.257):.1f}" r="2.6" fill="{c}"/>'
                          for k in range(5))
                + f'<circle cx="8" cy="8" r="1.6" fill="{shade(c, .6)}"/>'
                + f'<path d="M22 22 q4 -6 8 0 q-4 6 -8 0z" fill="{c}" opacity=".8"/>'
                + '</pattern>')
    if p == "camouflage":
        return ('<pattern id="pt" width="60" height="60" patternUnits="userSpaceOnUse">'
                f'<path d="M5 10 q12 -8 20 4 q6 10 -6 14 q-14 2 -14 -18z" fill="{shade(b, .7)}"/>'
                f'<path d="M35 30 q14 -6 18 8 q2 12 -12 10 q-12 -2 -6 -18z" fill="{a}" '
                'opacity=".7"/>'
                f'<path d="M10 42 q10 -4 14 6 q-2 8 -12 6z" fill="{shade(b, 1.3)}"/>'
                '</pattern>')
    if p == "tie dye":
        return ('<radialGradient id="pt" cx=".5" cy=".42" r=".7">'
                f'<stop offset="0" stop-color="{shade(a, 1.3)}"/>'
                f'<stop offset=".35" stop-color="{a}" stop-opacity=".7"/>'
                f'<stop offset=".6" stop-color="{b}" stop-opacity=".2"/>'
                f'<stop offset="1" stop-color="{shade(a, .8)}" stop-opacity=".75"/>'
                '</radialGradient>')
    if p == "washed":
        return ('<linearGradient id="pt" x1="0" y1="0" x2="0" y2="1">'
                '<stop offset="0" stop-color="#fff" stop-opacity=".05"/>'
                '<stop offset=".5" stop-color="#fff" stop-opacity=".28"/>'
                '<stop offset="1" stop-color="#fff" stop-opacity=".05"/></linearGradient>')
    if p == "textured":
        return ('<pattern id="pt" width="6" height="6" patternUnits="userSpaceOnUse">'
                f'<circle cx="3" cy="3" r=".9" fill="{shade(b, .6)}" opacity=".5"/></pattern>')
    return ""


def overlay_fill(spec: Spec, chest_print: bool):
    """Fill for the pattern overlay, or None."""
    p = spec.pattern
    if p in ("striped", "checked", "camouflage", "tie dye", "washed", "textured", "floral"):
        return "url(#pt)"
    if p == "graphic" and not chest_print:
        return "url(#pt)"  # all-over print on shirts, kurtas ...
    return None


# ---------------------------------------------------------------------------
# tops
# ---------------------------------------------------------------------------

TOP_LEN = {"tshirt": 230, "polo": 228, "shirt": 248, "top": 220, "sweatshirt": 222,
           "hoodie": 228, "sweater": 222, "jacket": 232, "blazer": 262, "kurta": 335,
           "ethnic_jacket": 226, "sherwani": 375}


def top_geometry(spec: Spec, cat=None):
    cat = cat or spec.cat
    fit = spec.fit
    over = fit in ("oversized", "boxy") or "oversized" in spec.wear
    sw = {"slim": 76, "skinny": 74, "relaxed": 88}.get(fit, 98 if over else 82)
    if cat in ("blazer", "sherwani"):
        sw = 84
    L = TOP_LEN.get(cat, 230)
    if cat == "kurta" and ("short kurta" in spec.wear or spec.has("short")):
        L = 265
    if fit == "cropped" or spec.has("cropped", "crop"):
        L *= 0.8
    hw = sw * (0.98 if over else 0.92)
    if cat in ("kurta", "sherwani"):
        hw = sw * 1.08
    sd = 24 if over else 14
    ay = sd + (92 if over else 80)
    sleeve = spec.sleeve or ("long" if cat in ("shirt", "jacket", "blazer", "hoodie",
                                                "sweatshirt", "sweater", "kurta", "sherwani")
                             else "short")
    if cat == "ethnic_jacket" or (cat == "top" and spec.has("tank", "vest", "sleeveless")):
        sleeve = "sleeveless"
    if sleeve == "sleeveless" and cat != "ethnic_jacket":
        sw = min(sw, 80)
        hw = sw * 0.92
    return dict(sw=sw, L=L, hw=hw, sd=sd, ay=ay, over=over, sleeve=sleeve, nw=27, nd=22)


def sleeve_pts(g, side=-1):
    """(shoulder, cuff outer, cuff inner, armpit) for one side."""
    sw, sd, ay = g["sw"], g["sd"], g["ay"]
    S = (side * sw, sd)
    A = (side * (sw - 5), ay)
    kind = g["sleeve"]
    if kind == "sleeveless":
        return S, None, None, A
    ang, ln, cw = {"short": (30 if not g["over"] else 48, 78 if not g["over"] else 92, 0.9),
                   "three quarter": (58, 135, 0.62),
                   "long": (71, 205 if g["L"] < 300 else 225, 0.48)}.get(kind, (30, 78, 0.9))
    t = math.radians(ang)
    d = (side * math.cos(t), math.sin(t))
    n = (-side * math.sin(t), math.cos(t))
    E1 = (S[0] + d[0] * ln, S[1] + d[1] * ln)
    width = math.dist(S, A) * cw
    E2 = (E1[0] + n[0] * width, E1[1] + n[1] * width)
    return S, E1, E2, A


def draw_top(cv: Canvas, spec: Spec, view: str, cat=None, fill=None, layer=False):
    cat = cat or spec.cat
    g = top_geometry(spec, cat)
    sw, L, hw, nw, nd = g["sw"], g["L"], g["hw"], g["nw"], g["nd"]
    neck = spec.neck or "round neck"
    if cat in ("kurta", "sherwani", "ethnic_jacket") and neck not in ("v neck",):
        neck = "mandarin collar"
    if cat == "blazer":
        neck = "lapel"
    if cat == "hoodie":
        neck = "hooded"
    fill = fill or spec.base
    front = view == "front"
    shirt_hem = cat in ("shirt",) and not spec.has("cuban", "resort", "camp")
    # neck opening
    if front and neck == "v neck":
        nd_ = nd + 34
        neck_d = f"M{P((-nw, 0))} L{P((0, nd_))} L{P((nw, 0))}"
    elif front and neck in ("collar", "mandarin collar", "polo collar", "lapel"):
        neck_d = f"M{P((-nw, 0))} C{P((-nw * .7, nd * .7), (-8, nd), (0, nd))} " \
                 f"C{P((8, nd), (nw * .7, nd * .7), (nw, 0))}"
    elif front:
        neck_d = f"M{P((-nw, 0))} C{P((-nw, nd * .85), (-nw * .5, nd), (0, nd))} " \
                 f"C{P((nw * .5, nd), (nw, nd * .85), (nw, 0))}"
    else:
        neck_d = f"M{P((-nw, 0))} C{P((-nw * .6, 7), (nw * .6, 7), (nw, 0))}"
    SL, E1L, E2L, AL = sleeve_pts(g, -1)
    SR, E1R, E2R, AR = sleeve_pts(g, 1)
    tank = E1R is None and cat != "ethnic_jacket"
    if tank:
        SL, SR = (-(nw + 20), 2), (nw + 20, 2)
    right = [SR] + ([E1R, E2R] if E1R else []) + [AR]
    left = [AL] + ([E2L, E1L] if E1L else []) + [SL]
    HR, HL = (hw, L - (14 if shirt_hem else 0)), (-hw, L - (14 if shirt_hem else 0))
    if shirt_hem:
        hem_d = f"L{P(HR)} C{P((hw, L), (hw * .4, L + 12), (0, L + 12))} " \
                f"C{P((-hw * .4, L + 12), (-hw, L), HL)}"
    else:
        hem_d = f"L{P(HR)} L{P(HL)}"
    if tank:  # scooped armholes
        d = (f"{neck_d} L{P(SR)} Q{P((sw - 2, g["ay"] * .75), AR)} {hem_d} L{P(AL)} "
             f"Q{P((-sw + 2, g["ay"] * .75), SL)} Z")
    else:
        d = (neck_d + " L" + " L".join(P(p) for p in right) + " " + hem_d + " L"
             + " L".join(P(p) for p in left) + " Z")
    pts = [(-nw, 0), (nw, 0)] + right + left + [HR, HL, (0, L + 12)]
    # inner back neck visible through the front opening
    if front and not layer and neck not in ("hooded",):
        back = f"M{P((-nw, 0))} C{P((-nw * .6, -8), (nw * .6, -8), (nw, 0))}"
        if neck == "v neck":
            hole = f"{back} L{P((0, nd + 34))} Z"
        else:
            hole = f"{back} C{P((nw, nd * .85), (nw * .5, nd), (0, nd))} "                    f"C{P((-nw * .5, nd), (-nw, nd * .85), (-nw, 0))} Z"
        cv.fill_only(hole, spec.inner)
    cv.shape(d, pts, fill)
    chest_print = cat in ("tshirt", "sweatshirt", "hoodie", "top")
    ov = overlay_fill(spec, chest_print)
    if ov:
        cv.raw(f'<path d="{d}" fill="{ov}" stroke="none"/>')
    if spec.pattern == "colour block" and cat not in ("ethnic_jacket",):
        y0 = L * 0.55
        cv.raw(f'<path d="M{P((-hw, y0))} L{P((hw, y0))} L{P(HR)} L{P(HL)} Z" '
               f'fill="{spec.accent}" class="o"/>')
    # shoulder / armhole seams
    if E1R:
        for S, A in ((SL, AL), (SR, AR)):
            cv.line(f"M{P(S)} Q{P(((S[0] + A[0]) / 2 + (6 if S[0] < 0 else -6), (S[1] + A[1]) / 2), A)}")
        # cuffs
        for E1, E2, s in ((E1L, E2L, -1), (E1R, E2R, 1)):
            k = 16 if g["sleeve"] == "long" else 8
            if cat in ("sweatshirt", "hoodie", "sweater", "jacket") and g["sleeve"] == "long":
                k = 22
            # points a little way back along the sleeve from both cuff corners
            S = SL if s < 0 else SR
            A = AL if s < 0 else AR
            f1 = (E1[0] + (S[0] - E1[0]) * k / math.dist(S, E1), E1[1] + (S[1] - E1[1]) * k / math.dist(S, E1))
            f2 = (E2[0] + (A[0] - E2[0]) * k / math.dist(A, E2), E2[1] + (A[1] - E2[1]) * k / math.dist(A, E2))
            cv.line(f"M{P(f1)} L{P(f2)}", "o" if k > 10 else "s")
            if cat == "shirt" and g["sleeve"] == "long":
                mx, my = (f1[0] + E1[0] * 2) / 3, (f1[1] + E1[1] * 2) / 3
                cv.circle(mx + (f2[0] - f1[0]) * .6, my + (f2[1] - f1[1]) * .6, 2.2, "#f4f2ec")
    elif tank:  # armhole binding
        for s in (-1, 1):
            cv.line(f"M{P((s * (nw + 21), 9))} Q{P((s * (sw - 9), g["ay"] * .72), (s * (sw - 12), g["ay"] - 4))}", "s")
    # hem finish
    rib = cat in ("sweatshirt", "hoodie", "sweater") or "bomber" in spec.wear
    if rib:
        cv.line(f"M{P((-hw, L - 20))} L{P((hw, L - 20))}")
        for x in range(int(-hw) + 8, int(hw), 9):
            cv.line(f"M{P((x, L - 18))} L{P((x, L - 2))}", "r")
    elif not shirt_hem:
        cv.line(f"M{P((-hw + 2, L - 9))} L{P((hw - 2, L - 9))}", "s")
    else:
        cv.line(f"M{P((hw - 4, L - 18))} C{P((hw - 4, L - 6), (hw * .4, L + 4), (0, L + 4))} "
                f"C{P((-hw * .4, L + 4), (-hw + 4, L - 6), (-hw + 4, L - 18))}", "s")

    # ----- necklines / closures ------------------------------------------------
    if neck == "round neck" or neck in ("scoop neck", "boat neck", "square neck"):
        o = 7
        if front:
            cv.line(f"M{P((-nw - 5, 2))} C{P((-nw - 5, nd + o), (-nw * .5, nd + o + 2), (0, nd + o + 2))} "
                    f"C{P((nw * .5, nd + o + 2), (nw + 5, nd + o), (nw + 5, 2))}")
        else:
            cv.line(f"M{P((-nw - 5, 3))} C{P((-nw * .6, 13), (nw * .6, 13), (nw + 5, 3))}")
    elif neck == "v neck" and front:
        cv.line(f"M{P((-nw - 6, 2))} L{P((0, nd + 44))} L{P((nw + 6, 2))}")
    elif neck == "high neck":
        cv.shape(f"M{P((-nw, 2))} L{P((-nw + 2, -24))} Q{P((0, -28), (nw - 2, -24))} L{P((nw, 2))} "
                 f"Q{P((0, 6 if front else 4), (-nw, 2))} Z", [(-nw, -26), (nw, -26)], fill)
        for x in range(-nw + 6, nw - 2, 7):
            cv.line(f"M{P((x, -20))} L{P((x, 0))}", "r")
    elif neck == "henley" and front:
        cv.line(f"M{P((-nw - 5, 2))} C{P((-nw - 5, nd + 7), (-nw * .5, nd + 9), (0, nd + 9))} "
                f"C{P((nw * .5, nd + 9), (nw + 5, nd + 7), (nw + 5, 2))}")
        cv.line(poly_d([(-7, nd + 9), (-7, nd + 62), (7, nd + 62), (7, nd + 9)], False))
        for y in (nd + 22, nd + 38, nd + 54):
            cv.circle(0, y, 2.6, "#f4f2ec")
    elif neck == "hooded":
        if front:
            hood = [(-nw - 22, 6), (-nw - 18, -40), (0, -78), (nw + 18, -40), (nw + 22, 6)]
            cv.shape(f"M{P(hood[0])} C{P((-nw - 26, -30), (-nw - 14, -78), (0, -80))} "
                     f"C{P((nw + 14, -78), (nw + 26, -30), hood[-1])} "
                     f"C{P((nw + 8, nd + 10), (-nw - 8, nd + 10), hood[0])} Z", hood, fill)
            cv.raw(f'<path d="M{P((-nw + 2, nd + 2))} C{P((-nw - 4, -30), (-14, -62), (0, -64))} '
                   f'C{P((14, -62), (nw + 4, -30), (nw - 2, nd + 2))} '
                   f'C{P((nw * .4, nd + 10), (-nw * .4, nd + 10), (-nw + 2, nd + 2))} Z" '
                   f'fill="{spec.inner}" class="o"/>')
            for s in (-1, 1):
                cv.line(f"M{P((s * 12, nd + 8))} Q{P((s * 16, nd + 40), (s * 13, nd + 62))}")
                cv.circle(s * 13, nd + 64, 2.4, shade(fill, .6))
            # kangaroo pocket
            y1, y2 = L - 108, L - 30
            cv.line(f"M{P((-58, y2))} L{P((-46, y1))} L{P((46, y1))} L{P((58, y2))}")
            cv.line(f"M{P((-46, y1 + 4))} Q{P((-54, (y1 + y2) / 2), (-62, y2 - 4))}", "s")
        else:
            hood = [(-nw - 22, 8), (0, -86), (nw + 22, 8)]
            cv.shape(f"M{P(hood[0])} C{P((-nw - 34, -40), (-26, -88), (0, -88))} "
                     f"C{P((26, -88), (nw + 34, -40), hood[2])} "
                     f"C{P((nw, 18), (-nw, 18), hood[0])} Z", hood, fill)
            cv.line(f"M{P((0, -88))} L{P((0, 14))}", "s")
    elif neck == "polo collar":
        flap = [(-nw - 2, -4), (-nw - 18, 28), (-6, nd + 10)]
        for s in (-1, 1):
            pts = [(abs(x) * s, y) for x, y in flap]
            if front:
                cv.shape(f"M{P((s * (nw + 2), -6))} L{P((s * (nw + 20), 30))} L{P((s * 5, nd + 12))} "
                         f"L{P((s * 2, nd))} Z", pts, fill)
        if front:
            cv.line(poly_d([(-8, nd), (-8, nd + 64), (8, nd + 64), (8, nd)], False))
            for y in (nd + 22, nd + 46):
                cv.circle(0, y, 2.6, "#f4f2ec")
        else:
            cv.shape(f"M{P((-nw - 6, 6))} Q{P((0, -18), (nw + 6, 6))} L{P((nw + 2, -6))} "
                     f"Q{P((0, -26), (-nw - 2, -6))} Z", [(-nw - 6, -20)], fill)
    elif neck in ("collar", "cuban collar") and cat not in ("ethnic_jacket",):
        if front:
            band = f"M{P((-nw - 2, 2))} L{P((-nw + 2, -12))} Q{P((0, -18), (nw - 2, -12))} L{P((nw + 2, 2))} Z"
            cv.shape(band, [(-nw, -16)], shade(fill, .93))
            cuban = neck == "cuban collar"
            for s in (-1, 1):
                pts = [(s * (nw + 2), -12), (s * (nw + (30 if cuban else 22)), 34 if cuban else 30),
                       (s * 4, nd + (34 if cuban else 10)), (s * 1, nd - 2)]
                cv.shape(poly_d(pts), pts, fill)
            top = nd + (34 if cuban else 6)
            # placket + buttons down the front
            if cat in ("shirt", "jacket", "coord_set", "top") and not cuban:
                cv.line(f"M{P((-9, top))} L{P((-9, L + (10 if shirt_hem else -2)))}")
                cv.line(f"M{P((9, top))} L{P((9, L + (10 if shirt_hem else -2)))}", "s")
            else:
                cv.line(f"M{P((0, top))} L{P((0, L + (10 if shirt_hem else 0)))}")
            y = top + 14
            while y < L - 8:
                cv.circle(0, y, 2.7, "#f4f2ec")
                y += 36
        else:
            cv.shape(f"M{P((-nw - 8, 8))} Q{P((0, -6), (nw + 8, 8))} L{P((nw + 4, -10))} "
                     f"Q{P((0, -24), (-nw - 4, -10))} Z", [(-nw - 8, -22)], fill)
            if cat == "shirt":  # yoke + box pleat
                cv.line(f"M{P((-sw + 4, 44))} Q{P((0, 50), (sw - 4, 44))}")
                cv.line(f"M{P((-6, 48))} L{P((-6, 64))} M{P((6, 48))} L{P((6, 64))}", "s")
    elif neck == "mandarin collar":
        band_fill = fill
        cv.shape(f"M{P((-nw - 2, 2))} L{P((-nw, -14))} Q{P((0, -20), (nw, -14))} L{P((nw + 2, 2))} "
                 f"Q{P((0, 8 if front else 5), (-nw - 2, 2))} Z", [(-nw, -20), (nw, -20)], band_fill)
        if front:
            cv.line(f"M{P((0, -18))} L{P((0, 4))}", "s")
            if cat == "kurta":
                end = nd + 110
            elif cat in ("ethnic_jacket", "sherwani"):
                end = L
            elif cat in ("shirt", "jacket"):
                end = L + (10 if shirt_hem else 0)
            else:
                end = nd + 80
            cv.line(f"M{P((-8, 6))} L{P((-8, end))} L{P((8, end))} L{P((8, 6))}"
                    if cat == "kurta" else f"M{P((0, 6))} L{P((0, end))}")
            y, step = 18, (26 if cat in ("ethnic_jacket", "sherwani") else 30)
            while y < end - 8:
                cv.circle(0, y, 2.8, GOLD if cat in ("sherwani", "ethnic_jacket") else "#f4f2ec")
                y += step
        elif cat == "shirt":
            cv.line(f"M{P((-sw + 4, 44))} Q{P((0, 50), (sw - 4, 44))}")
    elif neck == "lapel" and front:
        bt = L * 0.56
        for s in (-1, 1):
            lap = [(s * nw, -2), (s * (nw + 6), 34), (s * (nw + 20), 52), (s * (nw + 14), 70),
                   (s * 2, bt)]
            cv.shape(poly_d(lap), lap, shade(fill, .94))
            cv.line(f"M{P((s * (nw + 6), 34))} L{P((s * (nw - 4), 30))}", "s")
        cv.line(f"M{P((0, bt))} L{P((0, L - 40))} Q{P((4, L - 8), (34, L))}")
        cv.line(f"M{P((0, L - 40))} Q{P((-4, L - 8), (-34, L))}", "s")
        for y in (bt + 6, bt + 44):
            cv.circle(0, y, 3.4, shade(fill, .55))
        for s in (-1, 1):
            y0 = L * 0.72
            cv.line(poly_d([(s * 30, y0), (s * (hw - 10), y0 - 3), (s * (hw - 10), y0 + 14),
                            (s * 30, y0 + 16)]))
        cv.line(f"M{P((-hw + 18, L * .36))} L{P((-hw + 46, L * .35))}", "o")
    elif neck == "lapel":
        cv.shape(f"M{P((-nw - 8, 8))} Q{P((0, -6), (nw + 8, 8))} L{P((nw + 4, -10))} "
                 f"Q{P((0, -24), (-nw - 4, -10))} Z", [(-nw - 8, -22)], fill)
        cv.line(f"M{P((0, 10))} L{P((0, L))}", "s")
        cv.line(f"M{P((0, L - 70))} L{P((0, L))}")

    # ----- category details -------------------------------------------------
    if front and cat == "jacket" and neck not in ("collar", "cuban collar", "mandarin collar"):
        cv.line(f"M{P((0, nd))} L{P((0, L))}")
        cv.line(f"M{P((-3, nd + 4))} L{P((-3, L - 4))}", "z")
    if front and cat in ("jacket",) and ("shacket" in spec.wear or spec.has("denim", "trucker")):
        for s in (-1, 1):
            x0, x1 = s * 22, s * 62
            cv.line(poly_d([(x0, 62), (x1, 62), (x1, 108), (x0, 108)]))
            cv.line(f"M{P((x0, 74))} L{P((x1, 74))}")
    elif front and cat == "jacket":
        for s in (-1, 1):
            cv.line(f"M{P((s * 40, L - 96))} L{P((s * 54, L - 50))}")
    if front and cat == "ethnic_jacket":
        cv.line(f"M{P((-hw + 16, 86))} L{P((-hw + 46, 84))}")
        for s in (-1, 1):
            cv.line(f"M{P((s * 22, L - 70))} L{P((s * (hw - 14), L - 72))}")
        cv.line(f"M{P((-2, L - 2))} L{P((-10, L - 14))} M{P((2, L - 2))} L{P((10, L - 14))}", "s")
    if cat in ("kurta", "sherwani"):
        for s in (-1, 1):  # side slits
            cv.line(f"M{P((s * (hw - 1), L - 78))} L{P((s * (hw - 9), L - 78))}")
    if front and cat == "shirt" and (spec.has("pocket") or spec.has("utility")):
        cv.line(poly_d([(-62, 70), (-26, 70), (-26, 110), (-44, 116), (-62, 110)]))
    if spec.pattern == "embroidered" or (cat == "sherwani" and spec.pattern != "solid"):
        c = GOLD
        cv.raw(f'<path d="M{P((-nw - 4, 8))} C{P((-nw, nd + 14), (-12, nd + 22), (-8, nd + 40))} '
               f'M{P((nw + 4, 8))} C{P((nw, nd + 14), (12, nd + 22), (8, nd + 40))}" '
               f'fill="none" stroke="{c}" stroke-width="2.4" stroke-dasharray="2 3" '
               'vector-effect="non-scaling-stroke"/>')
        if front:
            for x, y in ((-40, 90), (38, 120), (-30, 150), (44, 70)):
                cv.circle(x, y, 4.5, c, "s")
        cv.raw(f'<path d="M{P((-hw + 4, L - 14))} L{P((hw - 4, L - 14))}" stroke="{c}" '
               'stroke-width="2.4" stroke-dasharray="3 3" fill="none" '
               'vector-effect="non-scaling-stroke"/>')
    if spec.pattern == "graphic" and chest_print:
        back_print = spec.has("back")
        if (front and not back_print) or (not front and back_print) or (front and back_print):
            big = (not front) or g["over"]
            w, h = (54, 70) if big and not front else (40, 44)
            y0 = 52 if front else 46
            if front and back_print:
                w, h, y0 = 14, 14, 48
                cv.raw(f'<rect x="{_f(-w - 46)}" y="{y0}" width="{2 * w}" height="{h}" rx="3" '
                       f'fill="{spec.accent}" class="o"/>')
            else:
                cv.raw(f'<rect x="{-w}" y="{y0}" width="{2 * w}" height="{h}" rx="6" '
                       f'fill="{spec.accent}" class="o"/>')
                ink = shade(spec.accent, .45) if luminance(spec.accent) > .4 else shade(spec.accent, 1.6)
                cv.circle(0, y0 + h * .38, h * .2, ink, "s")
                for k in range(2):
                    cv.raw(f'<rect x="{_f(-w * .7)}" y="{_f(y0 + h * (.7 + .14 * k))}" '
                           f'width="{_f(w * 1.4 * (1 - .3 * k))}" height="{_f(h * .07)}" '
                           f'fill="{ink}"/>')


# ---------------------------------------------------------------------------
# bottoms
# ---------------------------------------------------------------------------


def bottom_geometry(spec: Spec, cat):
    fit = spec.fit
    L = 300
    if cat == "shorts":
        L = 140 if not spec.has("bermuda", "long") else 165
    ww, hip, rise = 70, 80, 96
    widths = {"skinny": 32, "slim": 40, "tapered": 40, "straight": 50, "regular": 50,
              "relaxed": 60, "wide leg": 76, "flared": 52, "cropped": 46, "oversized": 70,
              "boxy": 64}
    wh = widths.get(fit, 50)
    if "baggy" in spec.wear or spec.has("baggy", "loose"):
        wh = 72
    if "parachute" in spec.wear:
        wh = 70
    c = 42
    if cat == "shorts":
        wh, c = max(wh, 58) + 6, 46
    if cat == "joggers":
        wh = min(wh, 44)
    if cat == "pyjama":
        wh, c = 58, 44
    if cat == "dhoti":
        churidar = spec.has("churidar", "churidars", "aligarh")
        wh, c, rise = (30, 38, 100) if churidar else (66, 46, 165)
        if spec.has("salwar", "patiala"):
            wh, c, rise = 40, 44, 150
    if wh / 2 > c - 4:
        c = wh / 2 + 6
    return dict(L=L, ww=ww, hip=hip, rise=rise, wh=wh, c=c)


def draw_bottom(cv: Canvas, spec: Spec, view: str, cat=None):
    cat = cat or spec.cat
    g = bottom_geometry(spec, cat)
    L, ww, hip, rise, wh, c = g["L"], g["ww"], g["hip"], g["rise"], g["wh"], g["c"]
    front = view == "front"
    wb = 16
    outer, inner = c + wh / 2, c - wh / 2
    flare = spec.fit == "flared"
    baggy = wh >= 66 and cat not in ("dhoti", "shorts")
    pts = [(-ww, wb), (-hip, wb + 50), (-outer - (14 if flare else 0), L), (-inner, L), (0, rise),
           (inner, L), (outer + (14 if flare else 0), L), (hip, wb + 50), (ww, wb)]
    if baggy or cat == "dhoti":
        bulge = hip + (24 if cat == "dhoti" else 14)
        d = (f"M{P((-ww, wb))} C{P((-bulge, wb + 40), (-bulge - 4, L * .6), (-outer, L))} "
             f"L{P((-inner, L))} L{P((0, rise))} L{P((inner, L))} L{P((outer, L))} "
             f"C{P((bulge + 4, L * .6), (bulge, wb + 40), (ww, wb))} Z")
        pts += [(-bulge - 4, L * .6), (bulge + 4, L * .6)]
    else:
        d = poly_d(pts)
    cv.shape(d, pts, spec.base)
    ov = overlay_fill(spec, spec.pattern == "graphic")
    if ov:
        cv.raw(f'<path d="{d}" fill="{ov}" stroke="none"/>')
    # waistband
    elastic = cat in ("joggers", "pyjama", "dhoti") or spec.has("elastic", "drawstring")
    wbd = poly_d([(-ww, 0), (ww, 0), (ww, wb), (-ww, wb)])
    cv.shape(wbd, [(-ww, 0), (ww, 0)], shade(spec.base, .95))
    if elastic:
        for x in range(-ww + 6, ww, 8):
            cv.line(f"M{P((x, 2))} L{P((x, wb - 2))}", "r")
        if front:
            for s in (-1, 1):
                cv.line(f"M{P((s * 6, wb - 4))} Q{P((s * 10, wb + 30), (s * 18, wb + 46))}")
                cv.circle(s * 18, wb + 48, 2.2, shade(spec.base, .6))
    else:
        if front:
            cv.circle(0, wb / 2, 3, shade(spec.base, .55))
        for x in (-ww + 10, -32, 32, ww - 10) if front else (-ww + 10, -24, 0, 24, ww - 10):
            cv.line(poly_d([(x - 3, -2), (x + 3, -2), (x + 3, wb + 6), (x - 3, wb + 6)]))
    # crotch / fly
    if front and not elastic:
        cv.line(f"M{P((12, wb))} L{P((12, rise - 26))} Q{P((12, rise - 10), (0, rise - 6))}", "s")
        cv.line(f"M{P((0, wb))} L{P((0, rise - 6))}")
    elif front:
        cv.line(f"M{P((0, wb))} L{P((0, rise))}", "s")
    else:
        cv.line(f"M{P((0, wb))} L{P((0, rise))}")
    jeans = cat == "jeans" or "jeans" in spec.wear
    if front and not elastic:  # front pockets
        for s in (-1, 1):
            if jeans:
                cv.line(f"M{P((s * (ww - 30), wb))} Q{P((s * (ww - 26), wb + 30), (s * (hip - 1), wb + 34))}")
                if s < 0:
                    cv.line(poly_d([(-ww + 8, wb + 6), (-ww + 26, wb + 6), (-ww + 26, wb + 24),
                                    (-ww + 8, wb + 24)]), "s")
            else:
                cv.line(f"M{P((s * (ww - 26), wb))} L{P((s * (hip - 1), wb + 52))}")
    if not front and not elastic:
        if jeans:
            cv.line(f"M{P((-hip + 2, wb + 30))} L{P((0, wb + 46))} L{P((hip - 2, wb + 30))}")
            for s in (-1, 1):
                pk = [(s * 18, wb + 48), (s * 58, wb + 40), (s * 60, wb + 86), (s * 40, wb + 98),
                      (s * 22, wb + 90)]
                cv.line(poly_d(pk))
        else:
            for s in (-1, 1):
                cv.line(f"M{P((s * 22, wb + 32))} L{P((s * 56, wb + 32))}")
                cv.line(f"M{P((s * 22, wb + 36))} L{P((s * 56, wb + 36))}", "s")
    # cargo pockets
    if "cargo" in spec.wear or spec.has("cargo", "utility"):
        for s in (-1, 1):
            y0, y1 = (110, 190) if cat != "shorts" else (60, 110)
            xo = hip + (outer - hip) * (y0 - 60) / (L - 60) + (10 if baggy else 0)
            pk = [(s * (xo - 2), y0), (s * (xo - 44), y0), (s * (xo - 44), y1), (s * (xo - 2), y1)]
            cv.shape(poly_d(pk), [], spec.base)
            cv.line(f"M{P((s * (xo - 2), y0 + 14))} L{P((s * (xo - 44), y0 + 14))}")
    # hem / cuffs
    if cat == "joggers" or (spec.has("jogger") and cat not in ("jeans",)):
        for s in (-1, 1):
            cv.shape(poly_d([(s * outer, L - 22), (s * inner, L - 22), (s * inner, L),
                             (s * outer, L)]), [], shade(spec.base, .92))
            for x in range(int(inner) + 5, int(outer), 6):
                cv.line(f"M{P((s * x, L - 20))} L{P((s * x, L - 2))}", "r")
    elif cat == "dhoti" and spec.has("churidar", "churidars", "aligarh"):
        for k in range(5):
            y = L - 70 + k * 12
            for s in (-1, 1):
                cv.line(f"M{P((s * inner, y))} q{P((s * wh / 2 * .5, 6), (s * wh, 0))}", "s")
    else:
        for s in (-1, 1):
            cv.line(f"M{P((s * (outer - 1), L - 10))} L{P((s * (inner + 1), L - 10))}", "s")
    if cat == "dhoti" and not spec.has("churidar", "churidars", "aligarh"):
        for s in (-1, 1):  # drape folds
            cv.line(f"M{P((s * 20, wb + 4))} Q{P((s * 6, rise * .7), (s * 30, rise + 40))}", "s")
            cv.line(f"M{P((s * 46, wb + 4))} Q{P((s * 38, rise * .8), (s * 62, rise + 70))}", "s")
    # pressed crease on formal trousers
    if cat == "trousers" and (spec.formal or spec.has("pleated", "formal")):
        for s in (-1, 1):
            cv.line(f"M{P((s * c, rise + 10))} L{P((s * c, L - 14))}", "s")
            if front and spec.has("pleated"):
                cv.line(f"M{P((s * 30, wb))} L{P((s * 30, wb + 30))}", "s")
    if jeans and front:
        cv.line(f"M{P((-hip + 6, wb + 56))} L{P((-outer + 4, L - 14))}", "z")


# ---------------------------------------------------------------------------
# composition
# ---------------------------------------------------------------------------

SET_PARTS = {"tracksuit": ("sweatshirt", "joggers")}


def parts_for(spec: Spec):
    cat = spec.cat
    if cat in ("tshirt", "polo", "shirt", "top", "sweatshirt", "hoodie", "sweater", "jacket",
               "blazer", "kurta", "ethnic_jacket", "sherwani", "dress"):
        return [("top", "sherwani" if cat == "sherwani" else ("tshirt" if cat == "dress" else cat))]
    if cat in ("jeans", "trousers", "joggers", "shorts", "pyjama", "dhoti", "skirt"):
        return [("bottom", "trousers" if cat == "skirt" else cat)]
    jacket = spec.has("jacket", "nehru", "bundi", "bandi", "waistcoat", "koti", "jodhpuri",
                      "bandhgala")
    if cat == "kurta_set":
        bottom = "dhoti" if spec.has("dhoti", "churidar", "churidars", "salwar", "patiala") else \
            ("trousers" if spec.has("trouser", "trousers", "pant", "pants") else "pyjama")
        if spec.has("jodhpuri", "bandhgala") and not spec.has("kurta"):
            return [("bottom", "trousers"), ("top", "blazer_band")]
        out = [("bottom", bottom), ("top", "kurta")]
        if jacket:
            out.append(("layer", "ethnic_jacket"))
        return out
    if cat == "sherwani":
        return [("bottom", "dhoti"), ("top", "sherwani")]
    # coord sets
    if spec.has("tracksuit", "track suit") or spec.occasion == "activewear":
        return [("bottom", "joggers"), ("top", "jacket" if spec.has("jacket") else "sweatshirt")]
    bottom = "shorts" if spec.has("shorts", "short") else (
        "joggers" if spec.has("jogger", "joggers") else "trousers")
    top = "jacket" if spec.has("jacket", "shacket") else (
        "tshirt" if spec.has("tee", "t shirt", "tshirt") else (
            "hoodie" if spec.has("hoodie") else (
                "sweatshirt" if spec.has("sweatshirt") else "shirt")))
    return [("bottom", bottom), ("top", top)]


def _render_view(spec: Spec, view: str):
    cv = Canvas()
    dept = spec.item.get("department")
    if dept in ("footwear", "accessories"):
        (draw_footwear if dept == "footwear" else draw_accessory)(cv, spec, view)
        return cv
    parts = parts_for(spec)
    if len(parts) == 1:
        kind, cat = parts[0]
        if kind == "top":
            draw_top(cv, spec, view, cat)
        else:
            draw_bottom(cv, spec, view, cat)
        return cv
    # sets: bottom drawn first, top overlaps the waistband
    offset = {"kurta": 150, "sherwani": 210, "shirt": 196, "tshirt": 186, "jacket": 190,
              "sweatshirt": 182, "hoodie": 186, "blazer_band": 200}
    top_cat = next(c for k, c in parts if k == "top")
    oy = offset.get(top_cat, 190)
    for kind, cat in parts:
        if kind == "bottom":
            sub = Canvas()
            bspec = Spec(spec.item)
            bspec.cat = cat
            bspec.fit = "slim" if cat == "trousers" and top_cat in ("blazer_band",) else bspec.fit
            draw_bottom(sub, bspec, view, cat)
            cv.els.append(f'<g transform="translate(0,{oy})">' + "".join(sub.els) + "</g>")
            cv.pts += [(x, y + oy) for x, y in sub.pts]
        elif kind == "top":
            if cat == "blazer_band":
                t = Spec(spec.item)
                t.neck = "mandarin collar"
                t.sleeve = "long"
                draw_top(cv, t, view, "sherwani")
                continue
            t = Spec(spec.item)
            t.cat = cat
            if cat in ("kurta",):
                t.sleeve = spec.sleeve or "long"
            draw_top(cv, t, view, cat)
        else:  # layered jacket over the kurta, in the accent colour
            t = Spec(spec.item)
            t.cat = cat
            t.pattern = "embroidered" if spec.pattern == "embroidered" else "solid"
            draw_top(cv, t, view, cat, fill=spec.accent, layer=True)
    return cv


Spec.occasion = property(lambda self: self.item.get("occasion"))

STYLE = ("<style>.o{fill-opacity:1;stroke:#1f1f22;stroke-width:2.1;stroke-linejoin:round;"
         "stroke-linecap:round;vector-effect:non-scaling-stroke}"
         "path.o:not([fill]),.o[fill=none]{fill:none}"
         ".s{fill:none;stroke:#1f1f22;stroke-width:1.1;stroke-dasharray:4 3;opacity:.75;"
         "vector-effect:non-scaling-stroke}"
         ".r{fill:none;stroke:#1f1f22;stroke-width:.9;opacity:.45;"
         "vector-effect:non-scaling-stroke}"
         ".z{fill:none;stroke:#1f1f22;stroke-width:1.6;stroke-dasharray:1.5 2;opacity:.7;"
         "vector-effect:non-scaling-stroke}</style>")


def render_svg(item: dict) -> str:
    """Front + back technical flat for one catalogue item, as an SVG string."""
    spec = Spec(item)
    views = [_render_view(spec, v) for v in ("front", "back")]
    # one scale for both views so they match
    boxes = [v.bbox() for v in views]
    w = max(b[2] - b[0] for b in boxes)
    h = max(b[3] - b[1] for b in boxes)
    s = min((CELL_W - 24) / w, (CELL_H - 28) / h, 1.25)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CELL_W * 2} {CELL_H}" '
           f'width="{CELL_W * 2}" height="{CELL_H}">', STYLE,
           f"<defs>{pattern_defs(spec, 'front')}</defs>"]
    for i, (v, b) in enumerate(zip(views, boxes)):
        cx = CELL_W * i + CELL_W / 2 - s * (b[0] + b[2]) / 2
        cy = CELL_H / 2 - s * (b[1] + b[3]) / 2
        out.append(f'<g transform="translate({_f(cx)},{_f(cy)}) scale({s:.3f})">'
                   + "".join(v.els) + "</g>")
    out.append("</svg>")
    return "".join(out)


def sketch_path(item) -> str:
    site, pid = item["id"].split(":", 1)
    return f"sketch/{site}/{re.sub(r'[^A-Za-z0-9_-]', '_', pid)}.svg"


def write_sketches(items, web_dir, force=False) -> int:
    """Write one SVG per item under web/sketch/<site>/<id>.svg; returns count."""
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


# ---------------------------------------------------------------------------
# footwear (side + top view) and accessories (front + back)
# ---------------------------------------------------------------------------

WHITE = "#f4f2ec"


def _rr(x0, y0, x1, y1, r):
    """Rounded-rectangle path."""
    return (f"M{P((x0 + r, y0))} L{P((x1 - r, y0))} Q{P((x1, y0), (x1, y0 + r))} "
            f"L{P((x1, y1 - r))} Q{P((x1, y1), (x1 - r, y1))} L{P((x0 + r, y1))} "
            f"Q{P((x0, y1), (x0, y1 - r))} L{P((x0, y0 + r))} Q{P((x0, y0), (x0 + r, y0))} Z")


def _rect(cv, x0, y0, x1, y1, r, fill):
    cv.shape(_rr(x0, y0, x1, y1, r), [(x0, y0), (x1, y1)], fill)


def _overlay(cv, spec, d):
    ov = overlay_fill(spec, False)
    if ov:
        cv.raw(f'<path d="{d}" fill="{ov}" stroke="none"/>')


def _shoe_kind(spec):
    w = spec.wear
    if spec.cat == "ethnic_footwear":
        return "mojari"
    if spec.cat == "sandals":
        return "slide" if "slides" in w or spec.has("slides", "sliders", "slippers", "clogs") \
            else ("flipflop" if spec.has("flip", "flipflop", "flops") else "sandal")
    if "boots" in w:
        return "boot"
    if "loafers" in w:
        return "loafer"
    if "formal shoes" in w or spec.formal:
        return "formal"
    return "sneaker"


def draw_footwear(cv, spec, view):
    kind = _shoe_kind(spec)
    base = spec.base
    dark = luminance(base) < .35
    sole_col = WHITE if kind in ("sneaker",) else (shade(base, .55) if not dark else "#2a2522")
    if view == "front":  # side profile, toe to the right
        if kind in ("slide", "sandal", "flipflop"):
            sole = f"M{P((-118, 58))} C{P((-126, 46), (-110, 40), (-80, 40))} L{P((96, 40))} " \
                   f"C{P((124, 40), (130, 52), (120, 60))} L{P((-110, 64))} Z"
            cv.shape(sole, [(-126, 40), (130, 64)], sole_col if kind != "flipflop" else base)
            cv.line(f"M{P((-112, 50))} L{P((116, 48))}", "s")
            if kind == "slide":
                band = f"M{P((-10, 41))} C{P((0, -8), (70, -10), (88, 41))} Z"
                cv.shape(band, [(-10, -10), (88, 41)], base)
                _overlay(cv, spec, band)
                cv.line(f"M{P((4, 30))} C{P((14, 4), (64, 2), (76, 30))}", "s")
            elif kind == "flipflop":
                cv.line(f"M{P((70, 41))} L{P((40, 6))} L{P((-20, 41))}")
            else:
                for x0 in (-20, 30, 70):
                    cv.shape(f"M{P((x0 - 6, 41))} C{P((x0 - 2, 4), (x0 + 22, 4), (x0 + 28, 41))} Z",
                             [(x0, 4)], base)
                cv.line(f"M{P((-100, 40))} C{P((-110, 10), (-80, 2), (-60, 40))}")
            return
        if kind == "mojari":
            up = f"M{P((-112, 50))} C{P((-118, 20), (-104, 6), (-84, 8))} L{P((-40, 16))} " \
                 f"C{P((20, 0), (80, 18), (118, 34))} C{P((134, 30), (140, 18), (132, 10))} " \
                 f"C{P((140, 26), (132, 50), (112, 52))} Z"
            cv.shape(up, [(-118, 6), (140, 52)], base)
            _overlay(cv, spec, up)
            cv.shape(f"M{P((-114, 50))} L{P((112, 50))} L{P((110, 58))} L{P((-112, 58))} Z",
                     [(-114, 58)], sole_col)
            cv.raw(f'<path d="M{P((-30, 22))} C{P((10, 10), (60, 22), (100, 36))}" fill="none" '
                   f'stroke="{GOLD}" stroke-width="2.4" stroke-dasharray="2 3" '
                   'vector-effect="non-scaling-stroke"/>')
            for x, y in ((0, 28), (30, 30), (60, 34)):
                cv.circle(x, y, 4, GOLD, "s")
            return
        top = {"boot": -110, "sneaker": -30, "formal": -18, "loafer": -12}[kind]
        sole_h = 20 if kind == "sneaker" else 9
        y_s = 60
        up = (f"M{P((-118, y_s))} C{P((-122, 30), (-118, top + 20), (-108, top + 4))} "
              f"Q{P((-96, top - 8), (-80, top - 2))} L{P((-56, top + 10))} ")
        if kind == "sneaker":
            up += f"L{P((-44, -44))} Q{P((-34, -50), (-26, -40))} "
        elif kind == "boot":
            up += f"L{P((-40, top + 10))} L{P((-36, -24))} "
        up += f"L{P((36, 16))} C{P((80, 22), (118, 30), (124, 50))} L{P((125, y_s))} Z"
        cv.shape(up, [(-122, top - 10), (125, y_s)], base)
        _overlay(cv, spec, up)
        sole = (f"M{P((-121, y_s))} L{P((128, y_s))} C{P((132, y_s + sole_h * .6), (124, y_s + sole_h), (110, y_s + sole_h))} "
                f"L{P((-112, y_s + sole_h))} C{P((-122, y_s + sole_h), (-124, y_s + 4), (-121, y_s))} Z")
        cv.shape(sole, [(-124, y_s + sole_h)], sole_col)
        if kind in ("formal", "loafer", "boot"):  # heel block
            cv.shape(f"M{P((-118, y_s + sole_h))} L{P((-78, y_s + sole_h))} L{P((-80, y_s + sole_h + 10))} "
                     f"L{P((-116, y_s + sole_h + 10))} Z", [(-118, y_s + sole_h + 10)], sole_col)
        if kind == "sneaker":
            cv.line(f"M{P((-112, y_s + 8))} L{P((122, y_s + 8))}", "s")
            for k in range(5):  # laces
                x, y = -30 + k * 13, -32 + k * 9.5
                cv.line(f"M{P((x - 7, y - 8))} L{P((x + 7, y + 8))}")
            cv.line(f"M{P((-100, top + 16))} Q{P((-76, 20), (-40, 40))} L{P((60, 40))}", "s")
            cv.line(f"M{P((70, 28))} C{P((92, 30), (110, 36), (118, 46))}", "s")
        elif kind == "formal":
            for k in range(3):
                x, y = -42 + k * 14, -8 + k * 6
                cv.line(f"M{P((x - 6, y - 5))} L{P((x + 6, y + 5))}")
            cv.line(f"M{P((-52, -4))} C{P((-30, 20), (10, 34), (40, 22))}", "s")
            if spec.has("brogue", "brogues", "wingtip"):
                for x in range(66, 118, 8):
                    cv.circle(x, 36 - (x - 66) * .1, 1.6, shade(base, .5), "s")
            cv.line(f"M{P((70, 24))} C{P((90, 28), (104, 40), (106, 56))}")
        elif kind == "loafer":
            cv.line(f"M{P((-30, -2))} C{P((0, 20), (40, 26), (64, 22))}")
            cv.shape(_rr(-12, 4, 30, 18, 4), [], shade(base, .85))
            if spec.has("tassel", "tassels"):
                cv.circle(-18, 22, 4, shade(base, .6), "o")
            if spec.has("penny"):
                cv.line(f"M{P((0, 10))} L{P((20, 10))}", "s")
        elif kind == "boot":
            for k in range(6):
                x, y = -48 + k * 9, -84 + k * 18
                cv.line(f"M{P((x - 7, y))} L{P((x + 7, y))}")
            cv.line(f"M{P((-112, -40))} L{P((-104, 40))}", "s")
        return
    # ---- top view ---------------------------------------------------------
    w = 40 if kind not in ("mojari", "formal") else 34
    out = (f"M{P((-120, 0))} C{P((-120, -w), (-80, -w - 2), (-40, -w + 2))} "
           f"C{P((20, -w - 4), (100, -w - 4), (122, -12))} "
           f"C{P((130, 0), (130, 6), (122, 12))} C{P((100, w + 4), (20, w + 4), (-40, w - 2))} "
           f"C{P((-80, w + 2), (-120, w), (-120, 0))} Z")
    if kind == "mojari":
        out = (f"M{P((-118, 0))} C{P((-118, -w), (-60, -w), (0, -w + 4))} "
               f"C{P((70, -w + 8), (120, -10), (140, 0))} C{P((120, 10), (70, w - 8), (0, w - 4))} "
               f"C{P((-60, w), (-118, w), (-118, 0))} Z")
    if kind in ("slide", "sandal", "flipflop"):
        cv.shape(out, [(-122, -w - 4), (132, w + 4)], sole_col if kind != "flipflop" else shade(base, 1.2))
        if kind == "slide":
            band = _rr(0, -w - 2, 66, w + 2, 10)
            cv.shape(band, [], base)
            _overlay(cv, spec, band)
        elif kind == "flipflop":
            cv.line(f"M{P((66, 0))} L{P((10, -w + 6))} M{P((66, 0))} L{P((10, w - 6))}")
            cv.circle(66, 0, 3, base)
        else:
            for x0 in (-10, 40, 80):
                cv.shape(_rr(x0, -w - 1, x0 + 16, w + 1, 5), [], base)
        return
    cv.shape(out, [(-122, -w - 4), (140, w + 4)], base)
    _overlay(cv, spec, out)
    open_end = -10 if kind in ("loafer", "mojari") else (-30 if kind == "formal" else -40)
    cv.raw(f'<path d="M{P((-108, 0))} C{P((-108, -w + 10), (-70, -w + 8), (-50, -w + 10))} '
           f'L{P((open_end, -8))} L{P((open_end, 8))} L{P((-50, w - 10))} '
           f'C{P((-70, w - 8), (-108, w - 10), (-108, 0))} Z" fill="{spec.inner}" class="o"/>')
    if kind == "sneaker":
        cv.shape(_rr(-50, -11, 30, 11, 6), [], shade(base, .92))
        for x in range(-42, 30, 12):
            cv.line(f"M{P((x, -16))} L{P((x + 8, 16))} M{P((x, 16))} L{P((x + 8, -16))}", "s")
    elif kind in ("formal", "boot"):
        for x in range(-24, 20, 11):
            cv.line(f"M{P((x, -12))} L{P((x, 12))}", "s")
        cv.line(f"M{P((-26, -14))} L{P((22, -14))} M{P((-26, 14))} L{P((22, 14))}")
    elif kind == "mojari":
        cv.raw(f'<path d="M{P((0, -18))} C{P((40, -14), (80, -6), (110, 0))} C{P((80, 6), (40, 14), (0, 18))}" '
               f'fill="none" stroke="{GOLD}" stroke-width="2.4" stroke-dasharray="2 3" '
               'vector-effect="non-scaling-stroke"/>')
    cv.line(f"M{P((-112, 0))} C{P((-112, -w + 6), (-80, -w + 4), (-40, -w + 7))}", "s")


def draw_accessory(cv, spec, view):
    cat, base, front = spec.cat, spec.base, view == "front"
    w = spec.wear
    if cat == "belt":
        if front:
            strap = f"M{P((-140, -14))} L{P((96, -14))} L{P((96, 14))} L{P((-140, 14))} Q{P((-156, 0), (-140, -14))} Z"
            cv.shape(strap, [(-156, -14), (96, 14)], base)
            _overlay(cv, spec, strap)
            cv.line(f"M{P((-138, -9))} L{P((96, -9))} M{P((-138, 9))} L{P((96, 9))}", "s")
            for x in range(-120, -60, 14):
                cv.circle(x, 0, 2.6, shade(base, .4), "o")
            metal = "#b8b2a4" if not spec.has("gold", "brass") else GOLD
            cv.shape(_rr(96, -24, 140, 24, 6), [(96, -24), (140, 24)], metal)
            cv.shape(_rr(104, -16, 132, 16, 4), [], shade(base, .9))
            cv.line(f"M{P((96, 0))} L{P((126, 0))}")
            cv.shape(_rr(70, -18, 84, 18, 2), [], base)
        else:
            cv.shape(f"M{P((-140, -14))} L{P((140, -14))} L{P((140, 14))} L{P((-140, 14))} Z",
                     [(-140, -14), (140, 14)], shade(base, .85) if not spec.has("reversible") else spec.accent)
            cv.line(f"M{P((-138, -9))} L{P((138, -9))} M{P((-138, 9))} L{P((138, 9))}", "s")
            cv.line(f"M{P((110, -14))} L{P((110, 14))}")
        return
    if cat == "wallet":
        if front:
            _rect(cv, -90, -60, 90, 60, 10, base)
            _overlay(cv, spec, _rr(-90, -60, 90, 60, 10))
            cv.line(_rr(-82, -52, 82, 52, 7), "s")
            cv.circle(60, 30, 5, shade(base, .6), "s")
        else:
            for x0 in (-170, 0):
                _rect(cv, x0, -60, x0 + 170, 60, 8, base)
                for y in (-36, -10, 16):
                    cv.shape(_rr(x0 + 14, y, x0 + 156, y + 30, 4), [], shade(base, .88))
            cv.line(f"M{P((0, -60))} L{P((0, 60))}")
        return
    if cat == "bag":
        if "backpack" in w or spec.has("backpack", "rucksack", "school bag"):
            body = _rr(-72, -90, 72, 110, 30)
            cv.shape(body, [(-72, -90), (72, 110)], base)
            _overlay(cv, spec, body)
            cv.line(f"M{P((-20, -90))} C{P((-20, -116), (20, -116), (20, -90))}")
            if front:
                cv.shape(_rr(-50, 20, 50, 96, 14), [], shade(base, .9))
                cv.line(f"M{P((-60, -64))} C{P((-20, -84), (20, -84), (60, -64))}", "z")
                cv.line(f"M{P((-46, 30))} L{P((46, 30))}", "z")
            else:
                for s in (-1, 1):
                    cv.shape(f"M{P((s * 26, -84))} C{P((s * 56, -40), (s * 30, 40), (s * 52, 104))} "
                             f"L{P((s * 36, 104))} C{P((s * 14, 40), (s * 40, -40), (s * 12, -84))} Z",
                             [], shade(base, .8))
            return
        if "duffle" in w:
            body = f"M{P((-130, -40))} C{P((-150, -40), (-150, 60), (-130, 60))} L{P((130, 60))} " \
                   f"C{P((150, 60), (150, -40), (130, -40))} Z"
            cv.shape(body, [(-150, -40), (150, 60)], base)
            _overlay(cv, spec, body)
            cv.line(f"M{P((-40, -40))} C{P((-40, -90), (40, -90), (40, -40))}")
            cv.line(f"M{P((-120, -30))} L{P((120, -30))}", "z")
            if front:
                cv.line(_rr(-60, 0, 60, 46, 6), "s")
            return
        if "trolley" in w:
            _rect(cv, -70, -100, 70, 120, 14, base)
            _overlay(cv, spec, _rr(-70, -100, 70, 120, 14))
            cv.line(f"M{P((-30, -100))} L{P((-30, -150))} L{P((30, -150))} L{P((30, -100))}")
            for x in (-50, 50):
                cv.circle(x, 128, 9, "#3b3b3d")
            for x in (-35, 0, 35):
                cv.line(f"M{P((x, -88))} L{P((x, 108))}", "s")
            return
        if "tote" in w or spec.has("tote", "shopper", "jhola"):
            body = f"M{P((-80, -50))} L{P((80, -50))} L{P((96, 110))} L{P((-96, 110))} Z"
            cv.shape(body, [(-96, -50), (96, 110)], base)
            _overlay(cv, spec, body)
            for s in (-1, 1):
                cv.line(f"M{P((s * 50, -50))} C{P((s * 50, -120), (s * 10, -120), (s * 12, -50))}")
            if front and spec.pattern == "graphic":
                cv.raw(f'<rect x="-40" y="0" width="80" height="60" rx="6" fill="{spec.accent}" class="o"/>')
            return
        # sling / crossbody / laptop / pouch / messenger
        wide = "laptop bag" in w
        x1, y1 = (130, 80) if wide else (90, 60)
        body = _rr(-x1, -y1, x1, y1, 14)
        cv.shape(body, [(-x1, -y1), (x1, y1)], base)
        _overlay(cv, spec, body)
        if front:
            cv.shape(f"M{P((-x1, -y1 + 10))} Q{P((-x1, -y1), (-x1 + 10, -y1))} L{P((x1 - 10, -y1))} "
                     f"Q{P((x1, -y1), (x1, -y1 + 10))} L{P((x1, 4))} L{P((-x1, 4))} Z", [], shade(base, .9))
            cv.shape(_rr(-10, -6, 10, 14, 3), [], "#b8b2a4")
        cv.line(f"M{P((-x1 + 6, -y1 + 6))} C{P((-x1, -y1 - 110), (x1, -y1 - 110), (x1 - 6, -y1 + 6))}")
        cv.pts += [(0, -y1 - 90)]
        return
    if cat == "cap":
        if "beanie" in w:
            dome = f"M{P((-80, 20))} C{P((-84, -80), (84, -80), (80, 20))} Z"
            cv.shape(dome, [(-84, -80), (84, 20)], base)
            _overlay(cv, spec, dome)
            cv.shape(_rr(-84, 10, 84, 54, 6), [], shade(base, .9))
            for x in range(-76, 80, 8):
                cv.line(f"M{P((x, 14))} L{P((x, 50))}", "r")
            return
        if "bucket hat" in w:
            crown = f"M{P((-62, 20))} L{P((-52, -50))} Q{P((0, -64), (52, -50))} L{P((62, 20))} Z"
            cv.shape(f"M{P((-110, 52))} C{P((-90, 14), (90, 14), (110, 52))} "
                     f"C{P((60, 64), (-60, 64), (-110, 52))} Z", [(-110, 14), (110, 64)], base)
            cv.shape(crown, [(-62, -60), (62, 20)], base)
            _overlay(cv, spec, crown)
            cv.line(f"M{P((-60, 10))} Q{P((0, 18), (60, 10))}", "s")
            return
        dome = f"M{P((-86, 24))} C{P((-90, -84), (90, -84), (86, 24))} Z"
        cv.shape(dome, [(-90, -84), (90, 24)], base)
        _overlay(cv, spec, dome)
        cv.circle(0, -59, 5, base)
        if front:
            for x in (-40, 40):
                cv.line(f"M{P((0, -58))} Q{P((x * .9, -40), (x, 22))}", "s")
            cv.shape(f"M{P((-92, 22))} C{P((-70, 60), (70, 60), (92, 22))} C{P((60, 34), (-60, 34), (-92, 22))} Z",
                     [(-92, 22), (92, 60)], shade(base, .9))
            if spec.pattern == "graphic" or spec.has("logo", "embroidered"):
                cv.raw(f'<rect x="-28" y="-30" width="56" height="26" rx="4" fill="{spec.accent}" class="o"/>')
        else:
            cv.line(f"M{P((0, -58))} L{P((0, 0))}", "s")
            cv.raw(f'<path d="M{P((-30, 24))} C{P((-30, -10), (30, -10), (30, 24))} Z" fill="{spec.inner}" class="o"/>')
            cv.shape(_rr(-34, 12, 34, 24, 3), [], shade(base, .7))
        return
    if cat == "sunglasses":
        lens = "#2f3136" if luminance(base) > .3 else shade(base, .7)
        frame = base if luminance(base) < .6 else "#3b3b3d"
        if front:
            for s in (-1, 1):
                if "aviator" in w:
                    d = f"M{P((s * 12, -24))} L{P((s * 96, -26))} C{P((s * 104, 10), (s * 80, 40), (s * 52, 40))} " \
                        f"C{P((s * 20, 40), (s * 10, 10), (s * 12, -24))} Z"
                elif "round frames" in w:
                    d = (f"M{P((s * 12, 0))} A42,42 0 1 1 {P((s * 96, 0))} A42,42 0 1 1 {P((s * 12, 0))} Z")
                else:
                    d = f"M{P((s * 10, -30))} L{P((s * 100, -34))} L{P((s * 92, 26))} " \
                        f"Q{P((s * 60, 38), (s * 22, 26))} Z"
                cv.shape(d, [(s * 104, -42), (s * 10, 42)], lens)
                cv.raw(f'<path d="{d}" fill="none" stroke="{frame}" stroke-width="4" vector-effect="non-scaling-stroke"/>')
            cv.line(f"M{P((-12, -18))} Q{P((0, -28), (12, -18))}")
            cv.line(f"M{P((-100, -30))} L{P((-118, -28))} M{P((100, -30))} L{P((118, -28))}")
        else:
            cv.shape(f"M{P((-120, -6))} L{P((90, -10))} Q{P((120, -10), (124, 30))} L{P((116, 32))} "
                     f"Q{P((110, 4), (88, 2))} L{P((-120, 6))} Z", [(-120, -10), (124, 32)], frame)
            cv.shape(f"M{P((-130, -36))} L{P((-120, -36))} L{P((-116, 36))} L{P((-126, 36))} Z",
                     [(-130, -36)], lens)
        return
    if cat == "tie":
        if "bow tie" in w or spec.has("bow"):
            bow = f"M{P((-12, -10))} L{P((-90, -44))} Q{P((-104, 0), (-90, 44))} L{P((-12, 10))} " \
                  f"L{P((12, 10))} L{P((90, 44))} Q{P((104, 0), (90, -44))} L{P((12, -10))} Z"
            cv.shape(bow, [(-104, -44), (104, 44)], base)
            _overlay(cv, spec, bow)
            cv.shape(_rr(-14, -16, 14, 16, 4), [], shade(base, .85))
            if not front:
                cv.line(f"M{P((-150, 0))} L{P((-104, 0))} M{P((104, 0))} L{P((150, 0))}")
                cv.pts += [(-150, 0), (150, 0)]
            return
        if "pocket square" in w:
            sq = f"M{P((-70, -20))} L{P((-40, -70))} L{P((-10, -24))} L{P((20, -80))} L{P((50, -22))} " \
                 f"L{P((70, -20))} L{P((70, 60))} L{P((-70, 60))} Z"
            cv.shape(sq, [(-70, -80), (70, 60)], base)
            _overlay(cv, spec, sq)
            cv.line(_rr(-62, -12, 62, 52, 2), "s")
            return
        knot = f"M{P((-16, -150))} L{P((16, -150))} L{P((10, -118))} L{P((-10, -118))} Z"
        blade = f"M{P((-10, -118))} L{P((10, -118))} L{P((30, 110))} L{P((0, 140))} L{P((-30, 110))} Z"
        if front:
            cv.shape(blade, [(-30, -118), (30, 140)], base)
            _overlay(cv, spec, blade)
            cv.shape(knot, [(-16, -150), (16, -118)], shade(base, .9))
            _overlay(cv, spec, knot)
        else:
            cv.shape(blade, [(-30, -150), (30, 140)], shade(base, .9))
            cv.line(f"M{P((0, -118))} L{P((0, 110))}", "s")
            cv.shape(_rr(-24, 40, 24, 54, 2), [], shade(base, .8))
            cv.shape(f"M{P((-8, 54))} L{P((8, 54))} L{P((14, 100))} L{P((0, 112))} L{P((-14, 100))} Z", [], base)
        return
    if cat == "socks":
        tall = not spec.has("ankle", "no show", "loafer", "low")
        h = 120 if tall else 50
        for s, dx in ((-1, -40), (1, 60)):
            d = (f"M{P((dx - 30, -h))} L{P((dx + 10, -h))} L{P((dx + 12, 30))} "
                 f"C{P((dx + 14, 50), (dx + 40, 50), (dx + 70, 52))} C{P((dx + 92, 54), (dx + 92, 86), (dx + 70, 88))} "
                 f"L{P((dx - 10, 88))} C{P((dx - 40, 88), (dx - 34, 50), (dx - 30, 30))} Z")
            cv.shape(d, [(dx - 40, -h), (dx + 92, 88)], base if s < 0 or front else shade(base, .92))
            _overlay(cv, spec, d)
            cv.shape(_rr(dx - 31, -h, dx + 11, -h + 18, 2), [], shade(base, .88))
            for x in range(int(dx - 26), int(dx + 8), 6):
                cv.line(f"M{P((x, -h + 2))} L{P((x, -h + 16))}", "r")
            cv.shape(f"M{P((dx + 62, 52))} C{P((dx + 92, 54), (dx + 92, 86), (dx + 66, 88))} Z", [], spec.accent)
        return
    if cat == "watch":
        strap = shade(base, .8)
        cv.shape(_rr(-28, -150, 28, 150, 10), [(-28, -150), (28, 150)], strap)
        if front:
            cv.circle(0, 0, 62, "#c9c4b8")
            cv.circle(0, 0, 52, WHITE if luminance(base) > .3 else "#2c2c2e")
            for k in range(12):
                a = k * math.pi / 6
                cv.line(f"M{P((46 * math.sin(a), -46 * math.cos(a)))} L{P((40 * math.sin(a), -40 * math.cos(a)))}")
            cv.line(f"M{P((0, 0))} L{P((0, -36))} M{P((0, 0))} L{P((24, 8))}")
            cv.shape(_rr(60, -8, 72, 8, 2), [], "#c9c4b8")
        else:
            cv.circle(0, 0, 60, "#c9c4b8")
            cv.circle(0, 0, 44, "#d8d3c8", "s")
            for k in range(4):
                a = k * math.pi / 2 + .6
                cv.circle(50 * math.cos(a), 50 * math.sin(a), 3, "#9a958a")
        cv.pts += [(-62, -62), (62, 62)]
        for y in (-110, -90, 90, 110):
            cv.line(f"M{P((-28, y))} L{P((28, y))}", "s")
        return
    if cat == "jewellery":
        metal = GOLD if spec.has("gold", "golden", "brass") or spec.item.get("color") == "yellow" else "#bfc0c2"
        if "chain" in w:
            if front:
                for k in range(30):
                    t = math.pi * k / 29
                    x, y = -100 * math.cos(t), 120 * math.sin(t) - 60
                    cv.raw(f'<ellipse cx="{_f(x)}" cy="{_f(y)}" rx="7" ry="4.5" fill="none" stroke="{metal}" '
                           f'stroke-width="3" transform="rotate({_f(math.degrees(t) + 90)} {_f(x)} {_f(y)})"/>')
                    cv.pts.append((x, y))
                if spec.has("pendant", "locket"):
                    cv.shape(f"M{P((0, 60))} L{P((16, 84))} L{P((0, 110))} L{P((-16, 84))} Z", [(0, 110)], metal)
            else:
                cv.shape("M-110,0 A110,24 0 1 0 110,0 A110,24 0 1 0 -110,0 Z", [(-110, -24), (110, 24)], "none")
                cv.raw(f'<ellipse cx="0" cy="0" rx="104" ry="20" fill="none" stroke="{metal}" stroke-width="5" '
                       'stroke-dasharray="6 3"/>')
            return
        if "ring" in w:
            cv.raw(f'<ellipse cx="0" cy="20" rx="60" ry="{60 if front else 18}" fill="none" stroke="{metal}" '
                   'stroke-width="12"/>')
            cv.pts += [(-66, -46), (66, 86)]
            if front:
                cv.shape(f"M{P((-20, -40))} L{P((20, -40))} L{P((26, -56))} L{P((0, -70))} L{P((-26, -56))} Z",
                         [(0, -70)], spec.accent)
            return
        if "brooch" in w or "cufflinks" in w:
            for dx in ((-60, 60) if "cufflinks" in w else (0,)):
                pts = [(dx + 50 * math.cos(k * math.pi / 5 - math.pi / 2) * (1 if k % 2 == 0 else .45),
                        50 * math.sin(k * math.pi / 5 - math.pi / 2) * (1 if k % 2 == 0 else .45)) for k in range(10)]
                if "cufflinks" in w:
                    cv.circle(dx, 0, 36, metal)
                    cv.circle(dx, 0, 22, spec.accent, "s")
                    cv.pts += [(dx - 36, -36), (dx + 36, 36)]
                else:
                    cv.shape(poly_d(pts), pts, metal)
                    cv.circle(dx, 0, 12, spec.accent)
            return
        # bracelet / kada
        cv.raw(f'<ellipse cx="0" cy="0" rx="90" ry="{90 if front else 26}" fill="none" stroke="{metal}" '
               f'stroke-width="{16 if spec.has("kada") else 10}"/>')
        if front and not spec.has("kada"):
            for k in range(16):
                a = k * math.pi / 8
                cv.circle(90 * math.cos(a), 90 * math.sin(a), 6, spec.accent if spec.has("bead", "beads", "beaded", "rudraksha") else metal)
        cv.pts += [(-100, -100), (100, 100)]
        return
    if cat == "scarf":
        if front:
            d = f"M{P((-40, -150))} L{P((40, -150))} L{P((46, 130))} L{P((-46, 130))} Z"
            cv.shape(d, [(-46, -150), (46, 150)], base)
            _overlay(cv, spec, d)
            cv.line(f"M{P((-30, -150))} Q{P((-6, -20), (-36, 130))}", "s")
            if spec.pattern == "embroidered" or spec.has("zari", "border"):
                cv.raw(f'<path d="M{P((-44, 112))} L{P((44, 112))}" stroke="{GOLD}" stroke-width="3" '
                       'stroke-dasharray="3 2" fill="none" vector-effect="non-scaling-stroke"/>')
            for x in range(-44, 46, 7):
                cv.line(f"M{P((x, 130))} L{P((x, 148))}")
        else:
            d = _rr(-110, -70, 110, 70, 4)
            cv.shape(d, [(-110, -70), (110, 70)], base)
            _overlay(cv, spec, d)
            cv.line(f"M{P((-110, 0))} L{P((110, 0))} M{P((0, -70))} L{P((0, 70))}", "s")
            for y in range(-66, 70, 7):
                cv.line(f"M{P((110, y))} L{P((126, y))}")
            cv.pts += [(126, 0)]
        return
    if cat == "ethnic_accessory":
        if "kalangi" in w and "safa" not in w:
            cv.shape(f"M{P((0, 80))} C{P((-40, 20), (-30, -80), (10, -130))} C{P((20, -60), (30, 20), (0, 80))} Z",
                     [(-40, -130), (30, 80)], spec.accent)
            cv.circle(0, 70, 22, GOLD)
            for k in range(8):
                a = k * math.pi / 4
                cv.circle(22 * math.cos(a), 70 + 22 * math.sin(a), 4, WHITE, "s")
            return
        dome = f"M{P((-100, 40))} C{P((-110, -60), (-40, -100), (0, -96))} C{P((40, -100), (110, -60), (100, 40))} " \
               f"C{P((60, 60), (-60, 60), (-100, 40))} Z"
        cv.shape(dome, [(-110, -100), (110, 60)], base)
        _overlay(cv, spec, dome)
        for k in range(5):
            y = -70 + k * 22
            cv.line(f"M{P((-96, y + 40))} C{P((-40, y - 10), (40, y + 20), (96, y - 20))}", "s")
        if front:
            if "kalangi" in w:
                cv.shape(f"M{P((30, -60))} C{P((10, -110), (30, -150), (60, -170))} C{P((60, -120), (56, -90), (40, -56))} Z",
                         [(60, -170)], spec.accent)
                cv.circle(36, -56, 10, GOLD)
        else:
            cv.shape(f"M{P((-20, 40))} L{P((20, 40))} L{P((50, 170))} L{P((-50, 170))} Z", [(-50, 170), (50, 170)], base)
            _overlay(cv, spec, f"M{P((-20, 40))} L{P((20, 40))} L{P((50, 170))} L{P((-50, 170))} Z")
        return
    # unknown accessory: a simple tag shape
    _rect(cv, -80, -60, 80, 60, 12, base)

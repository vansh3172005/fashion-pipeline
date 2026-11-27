"""Outfit recommender: implements outfit_styling_rules.md.

A line-for-line Python port of web/recommend.js (the browser version), so the
API returns exactly the outfits the page shows.

  section 1     outfit templates (Western, One-piece, Indian, Co-ord)
  section 2     hard rules: gender, occasion family, compatible styles, size in stock
  sections 3-7  soft rules, +1 each: colour (two checks), pattern, fit, fabric, price
  section 8     keep passing outfits, rank by score, vary the items, give one reason
"""
import re

# ---------------------------------------------------------------- section 1: pieces
# tuples (not sets) keep the same order as the JavaScript Sets
TOP = ("tshirt", "shirt", "polo", "top", "sweatshirt", "hoodie", "sweater")
BOTTOM = ("jeans", "trousers", "joggers", "shorts", "skirt", "leggings")
LAYER = ("jacket", "blazer", "shrug")
ONE_PIECE = ("dress", "gown", "jumpsuit")
COORD = ("coord_set",)
INDIAN_TOP = ("kurta",)
INDIAN_BOTTOM = ("pyjama", "dhoti", "ethnic_bottom", "trousers", "leggings")
INDIAN_FULL = ("kurta_set", "sherwani", "saree", "lehenga")
INDIAN_LAYER = ("ethnic_jacket", "shrug")
FOOTWEAR = ("shoes", "sandals", "heels", "flats", "ethnic_footwear")
ETHNIC_FOOTWEAR = ("ethnic_footwear", "sandals", "flats", "heels")
ACCESSORY = ("belt", "bag", "cap", "sunglasses", "watch", "jewellery", "wallet",
             "hair_accessory", "clutch", "tie", "scarf")
ETHNIC_ACCESSORY = ("scarf", "jewellery", "clutch", "ethnic_accessory", "bag")


def template_of(it):
    c = it.get("category")
    if c in ONE_PIECE:
        return "onepiece"
    if c in COORD:
        return "coord"
    if c in INDIAN_FULL or c in INDIAN_TOP or c in ("ethnic_bottom", "pyjama", "dhoti", "blouse",
                                                    "ethnic_jacket"):
        return "indian"
    if c in TOP or c in BOTTOM or c in LAYER:
        return "western"
    if it.get("department") in ("footwear", "accessories"):
        return "accessory"
    return None


SLOTS = {
    "western": [("top", TOP), ("bottom", BOTTOM), ("footwear", FOOTWEAR), ("accessory", ACCESSORY),
                ("layer", LAYER)],
    "onepiece": [("main", ONE_PIECE), ("footwear", FOOTWEAR), ("accessory", ACCESSORY)],
    "coord": [("main", COORD), ("footwear", FOOTWEAR), ("accessory", ACCESSORY)],
    "indian_full": [("main", INDIAN_FULL), ("footwear", ETHNIC_FOOTWEAR),
                    ("accessory", ETHNIC_ACCESSORY), ("layer", INDIAN_LAYER)],
    "indian_kurta": [("top", INDIAN_TOP), ("bottom", INDIAN_BOTTOM), ("footwear", ETHNIC_FOOTWEAR),
                     ("accessory", ETHNIC_ACCESSORY), ("layer", INDIAN_LAYER)],
}
OPTIONAL = ("accessory", "layer")

# ---------------------------------------------------------------- section 2: hard rules
OCCASION_FAMILY = {
    "casual": "casual", "street": "casual", "college": "casual", "vacation": "casual",
    "lounge": "casual", "formal": "formal", "smart casual": "formal", "party": "party",
    "festive": "festive", "activewear": "active",
}


def occasion_family(it):
    # an occasion the pipeline only defaulted ("casual" with no evidence) fits any outfit
    if (it.get("attr_source") or {}).get("occasion") == "default":
        return None
    return OCCASION_FAMILY.get(it.get("occasion"))


STYLE_PAIRS = {
    "minimalist": ["classic", "streetwear", "sporty"],
    "classic": ["minimalist", "glam"],
    "streetwear": ["minimalist", "sporty", "edgy"],
    "boho": ["ethnic_fusion", "minimalist"],
    "sporty": ["streetwear", "minimalist"],
    "glam": ["classic", "traditional", "edgy"],
    "ethnic_fusion": ["traditional", "boho", "glam"],
    "traditional": ["ethnic_fusion", "glam"],
    "edgy": ["streetwear", "glam"],
}


def styles_ok(a, b):
    sa, sb = a.get("primary_style"), b.get("primary_style")
    if not sa or not sb or sa == "unclassified" or sb == "unclassified" or sa == sb:
        return True
    return sb in STYLE_PAIRS.get(sa, []) or sa in STYLE_PAIRS.get(sb, [])


def gender_ok(a, b):
    return a.get("gender") == b.get("gender") or "unisex" in (a.get("gender"), b.get("gender"))


def occasion_ok(a, b):
    fa, fb = occasion_family(a), occasion_family(b)
    return not fa or not fb or fa == fb


WAIST = {"XS": ["26", "28"], "S": ["28", "30"], "M": ["32"], "L": ["34"], "XL": ["36"],
         "XXL": ["38"], "2XL": ["38"]}


def size_ok(it, size):
    if not size or it.get("department") in ("footwear", "accessories"):
        return True
    s = [str(x).upper() for x in it.get("sizes_available") or []]
    if not s:
        return True  # free size / one size
    want = str(size).upper()
    # bottoms are often sold by waist: S 28-30, M 32, L 34, XL 36, XXL 38
    waist = WAIST.get(want, [])
    for x in s:
        parts = re.split(r"[^A-Z0-9]+", x)
        if x == want or want in parts or any(w in parts for w in waist):
            return True
    return False


# an item with no real occasion tag suits the occasions its style is worn for
STYLE_OCCASIONS = {
    "casual": None,  # every style
    "formal": ["classic", "minimalist", "glam"],
    "party": ["glam", "edgy", "classic", "minimalist", "streetwear", "ethnic_fusion"],
    "festive": ["traditional", "ethnic_fusion", "glam", "boho"],
    "active": ["sporty", "streetwear"],
}


def suits_occasion(it, occ):
    if not occ:
        return True
    fam = occasion_family(it)
    if fam:
        return fam == occ
    ok = STYLE_OCCASIONS.get(occ)
    return not ok or it.get("primary_style") in ok


def pair_ok(a, b):
    return gender_ok(a, b) and occasion_ok(a, b) and styles_ok(a, b)


# a footwear, accessory or layer pick whose title names another kind of item is a
# catalogue mis-label ("Cotton Handkerchief" filed as shoes): never suggest it
NOT_FOR = {
    "footwear": re.compile(r"\b(handkerchief|socks?|pocket square|polish|laces?|insoles?|t-?shirts?|"
                           r"shirts?|kurtas?)\b", re.I),
    "accessory": re.compile(r"\b(jeans|denim pants|trousers?|t-?shirts?|shirts?|kurtas?|dress|shorts|"
                            r"joggers?)\b", re.I),
    "layer": re.compile(r"\b(t-?shirts?|tees?|polos?|kurtas?|dress)\b", re.I),
}
LAYER_WORD = re.compile(r"\b(jacket|shacket|overshirt|blazer|shrug|cardigan|koti|bundi)\b", re.I)


def title_ok(slot, it):
    rx = NOT_FOR.get(slot)
    if not rx or not rx.search(it.get("title") or ""):
        return True
    return slot == "layer" and bool(LAYER_WORD.search(it.get("title") or ""))


# ---------------------------------------------------------------- sections 3-7: soft rules
NEUTRAL = ("black", "white", "grey", "navy", "beige")
SAFE_PAIRS = [("navy", "white"), ("black", "white"), ("beige", "white"), ("green", "beige"),
              ("blue", "white"), ("red", "beige"), ("black", "red"), ("pink", "white")]
CLASH = [("red", "green"), ("orange", "pink"), ("purple", "yellow")]
PATTERNED = ("printed", "graphic", "floral", "striped", "checked", "embroidered", "embellished",
             "ethnic print", "animal print", "polka dot", "tie dye", "camouflage", "colour block")
LOOSE = ("oversized", "relaxed", "boxy", "wide leg", "flared")
LIGHT = ("cotton", "linen", "muslin", "chiffon", "georgette")
HEAVY = ("wool", "fleece", "velvet", "corduroy", "cashmere")
FESTIVE_FABRIC = ("silk", "velvet", "brocade", "tissue", "organza")
BANDS = ["cheap", "affordable", "luxury"]


def _has(pairs, x, y):
    return any((p == x and q == y) or (p == y and q == x) for p, q in pairs)


def _uniq(values):
    return list(dict.fromkeys(v for v in values if v))


def _garments(items):
    return [i for i in items if i.get("department") not in ("footwear", "accessories")]


def _band(b):
    return BANDS.index(b) if b in BANDS else -1


def score(items):
    g = _garments(items)
    cols = _uniq(i.get("color") for i in items)
    bright = [c for c in cols if c not in NEUTRAL and c != "multi"]
    checks, why = [], []
    # 3. colour: at most two non-neutral colours, no clash; a safe pair or one colour family
    no_clash = not any(_has(CLASH, x, y) for k, x in enumerate(bright) for y in bright[k + 1:])
    checks.append(len(bright) <= 2 and no_clash)
    gc = _uniq(i.get("color") for i in g)
    pair_found = any(_has(SAFE_PAIRS, x, y) for k, x in enumerate(gc) for y in gc[k + 1:])
    tonal = (len(gc) == 1 and gc[0] != "multi") or (len(gc) > 0 and all(c in NEUTRAL for c in gc))
    checks.append(pair_found or tonal)
    if pair_found:
        p = next(pq for pq in SAFE_PAIRS if pq[0] in gc and pq[1] in gc)
        why.append(f"{p[0]} + {p[1]}")
    elif tonal:
        why.append(f"all {gc[0]}" if len(gc) == 1 else "all neutrals")
    # 4. pattern: one patterned garment at most
    pat = sum(1 for i in g if i.get("pattern") in PATTERNED)
    checks.append(pat <= 1)
    if pat == 1:
        why.append("one patterned piece")
    elif not pat:
        why.append("all solid")
    # 5. fit: balance a loose piece with a slim one; no oversized on oversized (unless streetwear)
    top = next((i for i in g if i.get("category") in TOP or i.get("category") in INDIAN_TOP), None)
    bot = next((i for i in g if i.get("category") in BOTTOM or i.get("category") in INDIAN_BOTTOM),
               None)
    fit_ok = True
    if top and bot and top.get("fit") and bot.get("fit"):
        both = top["fit"] in LOOSE and bot["fit"] in LOOSE
        fit_ok = not both or (top.get("primary_style") == "streetwear"
                              and bot.get("primary_style") == "streetwear")
        if fit_ok and (top["fit"] in LOOSE) != (bot["fit"] in LOOSE):
            why.append("balanced fit")
    checks.append(fit_ok)
    # 6. fabric and season: light with light, heavy with heavy; no festive fabric with gym wear
    fab = set()
    for i in g:
        fab.update(i.get("fabrics") or ([i["fabric"]] if i.get("fabric") else []))
    mixed = any(f in LIGHT for f in fab) and any(f in HEAVY for f in fab)
    gym = any(occasion_family(i) == "active" for i in items)
    checks.append(not mixed and not (gym and any(f in FESTIVE_FABRIC for f in fab)))
    # 7. price: same or neighbouring band
    bands = [b for b in (_band(i.get("price_band")) for i in items) if b >= 0]
    checks.append(not bands or max(bands) - min(bands) <= 1)
    fam = next((f for f in map(occasion_family, items) if f), None)
    if fam:
        why.append("activewear" if fam == "active" else fam)
    return {"score": sum(1 for c in checks if c), "max": len(checks), "why": ", ".join(why[:3])}


# ---------------------------------------------------------------- section 8: build and rank
def slots_for(anchor):
    t = template_of(anchor)
    if t == "indian":
        return SLOTS["indian_full"] if anchor.get("category") in INDIAN_FULL else SLOTS["indian_kurta"]
    return SLOTS.get(t)


def slot_of(slots, it):
    return next((name for name, cats in slots if it.get("category") in cats), None)


_INDEX = {}


def index_of(catalogue):
    key = id(catalogue)
    m = _INDEX.get(key)
    if m is None or m[0] is not catalogue:
        by = {}
        for it in catalogue:
            by.setdefault(it.get("category"), []).append(it)
        m = (catalogue, by)
        _INDEX[key] = m
    return m[1]


def fnv(s):
    """Same 32-bit FNV-1a hash as recommend.js (so seeds give the same order)."""
    h = 2166136261
    for ch in s:
        h = ((h ^ ord(ch)) * 16777619) & 0xFFFFFFFF
    return h


def complete_look(anchor, catalogue, size=None, n=3, seed=0, beam=14, exclude=None):
    """Up to ``n`` outfits built around ``anchor`` from ``catalogue``."""
    slots = slots_for(anchor)
    if not slots:
        return []
    my_slot = slot_of(slots, anchor)
    if not my_slot:
        return []
    # candidates per slot: pass the hard rules against the anchor, ranked by the soft
    # score of the pair, with a seeded tie-break so another seed gives other suggestions
    cand, by_cat = {}, index_of(catalogue)
    for name, cats in slots:
        if name == my_slot:
            continue
        lst = []
        for c in cats:
            for it in by_cat.get(c, []):
                if (it["id"] == anchor["id"] or (exclude and (it["id"] in exclude
                                                              or "^" + it["id"] in exclude))
                        or not pair_ok(anchor, it) or not size_ok(it, size)):
                    continue
                if (name == "bottom" and template_of(anchor) == "indian"
                        and it.get("category") == "trousers" and anchor.get("gender") != "women"):
                    continue  # men: kurta with pyjama / dhoti, not trousers
                if not title_ok(name, it):
                    continue
                ps = it.get("primary_style")
                same = 2 if ps == anchor.get("primary_style") else (1 if ps and ps != "unclassified" else 0)
                conf = {"high": 2, "medium": 1}.get(it.get("style_confidence"), 0)
                lst.append((score([anchor, it])["score"], same + conf, fnv(f"{it['id']}{seed}"), it))
        lst.sort(key=lambda x: (-x[0], -x[1], x[2]))
        cand[name] = [x[3] for x in lst[:beam]]
    need = [s for s, _ in slots if s != my_slot and s not in OPTIONAL]
    if any(not cand.get(s) for s in need):
        return []
    # combine required slots, then add the best optional pieces that still pass the rules
    outfits = [[anchor]]
    for s in need:
        nxt = [o + [it] for o in outfits for it in cand[s] if all(pair_ok(x, it) for x in o)]
        nxt.sort(key=lambda o: -score(o)["score"])
        outfits = nxt[:60]
    out, used = [], set()
    for o in outfits:
        if any(i["id"] in used for i in o[1:]):
            continue  # vary the items across suggestions
        full = list(o)
        for s in ("layer", "accessory"):
            if s not in cand or s == my_slot:
                continue
            base = score(full)["score"]
            add = next((it for it in cand[s] if it["id"] not in used
                        and all(pair_ok(x, it) for x in full)
                        and score(full + [it])["score"] >= base), None)
            if add and (s == "accessory" or anchor.get("occasion") == "formal"
                        or fnv(f"{anchor['id']}{s}{seed}") % 3 == 0):
                full.append(add)
        sc = score(full)
        out.append({"items": full, "score": sc["score"], "max": sc["max"], "why": sc["why"]})
        used.update(i["id"] for i in full[1:])
        if len(out) >= n:
            break
    out.sort(key=lambda o: -o["score"])
    return out


KINDS = ("western", "onepiece", "indian", "coord")


def outfit_stream(catalogue, f=None, seed=0):
    """Every outfit the catalogue can make for the filters, one at a time (no cap).
    f: {kind, style, occasion, band, size}"""
    f = f or {}

    def anchor_ok(it):
        t = template_of(it)
        if not t or t == "accessory":
            return False
        if t == "western" and it.get("category") not in TOP:
            return False  # anchor on the top
        if t == "indian" and not (it.get("category") in INDIAN_FULL or it.get("category") in INDIAN_TOP):
            return False
        if f.get("kind") in KINDS and t != f["kind"]:
            return False
        if f.get("style") and it.get("primary_style") != f["style"]:
            return False
        if not suits_occasion(it, f.get("occasion")):
            return False
        if f.get("band") and it.get("price_band") != f["band"]:
            return False
        return size_ok(it, f.get("size"))

    anchors = sorted((it for it in catalogue if anchor_ok(it)), key=lambda a: fnv(f"{a['id']}{seed}"))
    # spread anchors across category x colour, round-robin, so the first outfits are varied
    groups = {}
    for a in anchors:
        groups.setdefault(f"{a.get('category')}|{a.get('color')}", []).append(a)
    lists = list(groups.values())
    order = [g[r] for r in range(max((len(g) for g in lists), default=0)) for g in lists if r < len(g)]
    if f.get("band"):
        want = _band(f["band"])
        pool = [i for i in catalogue if not i.get("price_band") or abs(_band(i["price_band"]) - want) <= 1]
    else:
        pool = catalogue
    used, uses = set(), {}
    for a in order:
        if a["id"] in used:
            continue
        o = complete_look(a, pool, size=f.get("size"), n=1, seed=seed, exclude=used)
        if o:
            for i in o[0]["items"]:
                if i.get("department") not in ("footwear", "accessories"):
                    used.add(i["id"])
                    continue
                uses[i["id"]] = uses.get(i["id"], 0) + 1
                if uses[i["id"]] >= 3:
                    used.add("^" + i["id"])  # footwear / accessory used 3 times
            yield o[0]

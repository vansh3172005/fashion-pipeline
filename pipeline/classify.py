"""Attribute extraction for garment products.

The extractor reads the site's own data first and only falls back to
inference from free text:

  1. ``field``       an explicit labelled field on the site: a spec line in the
                     product description ("Fit: Oversized Fit"), or a variant
                     option ("Size", "Color")
  2. ``tags``        the store's own product tags
  3. ``title``       the product title
  4. ``description`` free description text
  5. ``image``       pixels of the product photo (set later by imaging.py)
  6. ``default``     a category default ("hoodie" -> hooded neckline)

Every attribute records which of these it came from in ``attr_source`` so the
UI and reports can tell site-provided values from inferred ones.

Everything here is pure functions over text, so it is cheap to unit test.
"""
import html
import re

# The nine parameters the scraper extracts for every garment.
PARAMETERS = ("color", "secondary_color", "pattern", "fit", "fabric",
              "sleeve_length", "neckline", "occasion", "size")

CATEGORIES = ("tshirt", "polo", "shirt", "top", "sweatshirt", "hoodie", "sweater",
              "jacket", "blazer", "jeans", "trousers", "joggers", "shorts", "skirt", "dress",
              "coord_set", "kurta", "kurta_set", "sherwani", "ethnic_jacket", "pyjama", "dhoti")
# only collected when a site sets "include_accessories": true
ACCESSORY_CATEGORIES = ("shoes", "sandals", "ethnic_footwear", "belt", "sunglasses", "bag",
                        "wallet", "tie", "cap", "socks", "watch", "jewellery", "scarf",
                        "ethnic_accessory")
FOOTWEAR = ("shoes", "sandals", "ethnic_footwear")
ALL_CATEGORIES = CATEGORIES + ACCESSORY_CATEGORIES
DEPARTMENT = {
    "tshirt": "topwear", "polo": "topwear", "shirt": "topwear", "top": "topwear",
    "sweatshirt": "topwear", "hoodie": "topwear", "sweater": "topwear",
    "jacket": "topwear", "blazer": "topwear", "jeans": "bottomwear", "trousers": "bottomwear",
    "joggers": "bottomwear", "shorts": "bottomwear", "skirt": "bottomwear",
    "dress": "fullbody", "coord_set": "fullbody",
    "kurta": "topwear", "ethnic_jacket": "topwear", "kurta_set": "fullbody",
    "sherwani": "fullbody", "pyjama": "bottomwear", "dhoti": "bottomwear",
    "shoes": "footwear", "belt": "accessories", "sunglasses": "accessories",
    "bag": "accessories", "wallet": "accessories", "tie": "accessories", "cap": "accessories",
    "socks": "accessories", "sandals": "footwear", "ethnic_footwear": "footwear",
    "watch": "accessories", "jewellery": "accessories", "scarf": "accessories",
    "ethnic_accessory": "accessories",
}

# --------------------------------------------------------------------------
# text helpers
# --------------------------------------------------------------------------


def norm(text: str) -> str:
    """Lowercase, strip html + apostrophes, collapse punctuation to spaces."""
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.lower().replace("'", "").replace("’", "")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return f" {text.strip()} "


def _has(pattern: str, text: str) -> bool:
    return re.search(pattern, text) is not None


def _tag_text(tags) -> str:
    return tags if isinstance(tags, str) else " | ".join(tags or ())


def split_tags(raw) -> list:
    if isinstance(raw, str):
        return [t.strip() for t in raw.split(",") if t.strip()]
    return [str(t).strip() for t in (raw or [])]


def _first(rules, sources):
    """First rule matching the first source that has a match.

    ``sources`` is a sequence of (source_name, text, rules_override_or_None).
    Returns (value, source_name) or (None, None).
    """
    for name, text, override in sources:
        if not text:
            continue
        t = norm(text)
        for value, pat in (override or rules):
            if _has(pat, t):
                return value, name
    return None, None


# --------------------------------------------------------------------------
# site spec block ("Composition: 100% Cotton<br>Fit: Oversized Fit ...")
# --------------------------------------------------------------------------

_SPEC_KEYS = {
    "composition": "fabric", "material": "fabric", "fabric": "fabric",
    "upper material": "fabric", "frame material": "fabric",
    "color": "color", "colour": "color",
    "fit": "fit",
    "sleeve length": "sleeve_length", "sleeves": "sleeve_length",
    "sleeve": "sleeve_length",
    "neckline": "neckline", "neck": "neckline", "collar": "neckline",
    "pattern": "pattern", "print": "pattern",
    "occasion": "occasion",
    "gsm": "gsm", "mrp": "mrp",
}


def description_text(body_html: str) -> str:
    """HTML description -> plain text with one line per block/<br>."""
    t = re.sub(r"(?is)<(style|script)[^>]*>.*?</\1>", " ", body_html or "")
    t = re.sub(r"(?i)<\s*(br|/p|p|li|/li|/div|/h\d)\b[^>]*>", "\n", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t).replace("\xa0", " ")
    return "\n".join(re.sub(r"[ \t]+", " ", ln).strip() for ln in t.splitlines())


def parse_specs(body_html: str) -> dict:
    """Labelled spec lines from a product description, keyed by parameter.

    Only known labels are kept (see _SPEC_KEYS), first occurrence wins, so a
    later marketing sentence such as "Fabric: our signature cotton ..." never
    overrides the composition line.
    """
    specs = {}
    for line in description_text(body_html).splitlines():
        m = re.match(r"([A-Za-z][A-Za-z ]{1,24}?)\s*(?::|\s-\s)\s*(\S.*)$", line)
        if not m:
            continue
        key = _SPEC_KEYS.get(m.group(1).strip().lower())
        if key and key not in specs:
            specs[key] = m.group(2).strip()[:160]
    return specs


def _clean_description(body_html: str) -> str:
    """Description without care/sizing boilerplate (avoids "wash with similar
    colours"-style false positives)."""
    keep = []
    for ln in description_text(body_html).splitlines():
        if re.search(r"(?i)wash|tumble|iron|bleach|chlorine|dry clean|screen brightness|"
                     r"size chart|model .*wearing|mrp|processing time|country of", ln):
            continue
        keep.append(ln)
    return " ".join(keep)


# --------------------------------------------------------------------------
# category
# --------------------------------------------------------------------------

_EXCLUDE = (
    r" (socks?|bags?|tote|totes|backpacks?|(?<!no )caps?(?! sleeves?)|hats?|beanies?|snapbacks?|"
    r"scarf|scarves|belts?|wallets?|gift cards?|keychains?|stickers?|"
    r"underwear|boxers?|briefs?|bras?|bralettes?|lingerie|panties|trunks|"
    r"sunglasses|perfumes?|fragrance|shoes?|sneakers?|slides|sliders|flip flops?|"
    r"kids|for kids|toddlers?|infants?|bundle|combo|pack of \d+|\d+ pack|gloves?|"
    r"rugs?|cushions?|posters?|mugs?|swim\w*|bikini|"
    r"stoles?|dupattas?|mufflers?|bottles?(?! green)|earrings?|necklaces?|bracelets?|rings?|"
    r"jewell?ery|brooch(es)?|kalangi|safa|pagdi|turbans?|mojaris?|juttis?|"
    r"handkerchiefs?|towels?|bedsheets?|candles?|fabric|unstitched|running material|"
    r"perfume|deodorant|serum|soap|trimmers?|pocket squares?|cufflinks?|ties|bow ties?|"
    r"neck ?ties?|lapel pins?|brooches|gift sets?|gift box|hampers?) "
)
# order matters: the first rule that matches wins
_CATEGORY_RULES = (
    ("sherwani", r" (sherwanis?|achkans?) "),
    ("kurta_set", r" (kurta (pyjama|pajama|churidar|dhoti|pant|pants|trouser|salwar)( sets?)?|"
                  r"kurta sets?|kurta with (pyjama|pajama|churidar|pants?|trousers?|dhoti)|"
                  r"kurta jacket sets?|kurta and (pyjama|pajama|churidar|pants?)|"
                  r"pathani( suits?| sets?)?|indo ?western sets?|jodhpuri sets?|"
                  r"bandhgala sets?|ethnic sets?|kurta bundi sets?) "),
    ("ethnic_jacket", r" (nehru jackets?|bandhgalas?|bandh galas?|bandi|bundi|modi jackets?|"
                      r"jodhpuri( jacket)?|ethnic jackets?|ethnic waistcoats?|koti) "),
    ("kurta", r" (kurtas?|short kurtas?|angrakhas?|kurta shirts?) "),
    ("dhoti", r" (dhotis?|dhoti pants?|mundus?|veshtis?|lungis?|churidars?|salwars?|"
              r"patiala|aligarh pyjamas?) "),
    ("pyjama", r" (pyjamas?(?! sets?)|pajamas?(?! sets?)|lounge pants?) "),
    ("coord_set", r" (co ords?|coords?|co ord sets?|coord sets?|sets?|pyjama sets?|"
                  r"pajama sets?|night suits?|tracksuits?|track suits?|suits?) "),
    ("skirt", r" (skirts?|skorts?) "),
    ("shorts", r" (shorts|short(?! (jackets?|kurtas?|sleeves?|sleeved|length|coats?|tops?))|"
               r"jorts|cut offs?|cutoffs?|bermudas?) "),
    ("jeans", r" jeans? "),
    ("joggers", r" (joggers?|track ?pants?|sweat ?pants?|trackpants?) "),
    ("trousers", r" (trousers?|pants?|cargos?|chinos?|slacks|leggings?|flares?|"
                 r"palazzos?|parachutes?|bottoms?) "),
    ("blazer", r" (blazers?|suit jackets?|waistcoats?) "),
    ("jacket", r" (jackets?|bombers?|varsity|windcheaters?|puffers?|coats?|trench|"
               r"shackets?|gilets?|overshirts?) "),
    ("hoodie", r" (hoodies?|hooded|zip hoodies?) "),
    ("sweatshirt", r" (sweatshirts?|sweat shirts?|crewneck sweatshirts?|pullovers?) "),
    ("polo", r" (polos?|polo t ?shirts?|rugby) "),
    ("tshirt", r" (t ?shirts?|tees?|baby ?tees?|henleys?|long ?sleeves?|tshirts?|jerseys?) "),
    ("shirt", r" (shirts?|flannels?|oxfords?|button downs?|button ups?) "),
    ("sweater", r" (sweaters?|cardigans?|jumpers?|knitwear|turtlenecks?|sweater vests?) "),
    ("jeans", r" denims? "),  # bare "denim" = jeans only if no shirt/jacket word matched
    ("dress", r" (dress(es)?|shirt ?dress|jumpsuits?|rompers?|playsuits?|gowns?) "),
    ("top", r" (tops?|crop tops?|tanks?|tank tops?|camis?|camisoles?|tubes?|tube tops?|"
            r"bodysuits?|corsets?|vests?|blouses?|halters?|halternecks?|bustiers?|tunics?) "),
)


_ACCESSORY_RULES = (
    ("ethnic_footwear", r" (mojaris?|juttis?|jootis?|nagras?|khussas?|kolhapuris?|"
                        r"ethnic footwear|ethnic shoes) "),
    ("sandals", r" (sandals?|slides|sliders|flip ?flops?|chappals?|floaters?|clogs?|"
                r"slippers?) "),
    ("shoes", r" (shoes?|loafers?|sneakers?|boots?|brogues?|derbys?|monks?|mules?|"
              r"moccasins?|footwear|trainers|espadrilles?) "),
    ("watch", r" (watch|watches|chronograph|wrist ?watch) "),
    ("ethnic_accessory", r" (safas?|pagdis?|pagris?|turbans?|kalangis?|sehras?|malas?) "),
    ("jewellery", r" (bracelets?|kadas?|chains?|necklaces?|pendants?|rings?|earrings?|studs|"
                  r"brooch(es)?|lapel pins?|cufflinks?|jewell?ery|jewelry|rudraksha) "),
    ("scarf", r" (scarf|scarves|mufflers?|stoles?|shawls?|dupattas?|bandanas?) "),
    ("sunglasses", r" (sunglasses|shades|eyewear|spectacles) "),
    ("belt", r" belts? "),
    ("wallet", r" (wallets?|card holders?) "),
    ("bag", r" (bags?|backpacks?|totes?|duffels?|briefcases?|laptop sleeves?|messenger|"
            r"suitcases?|luggage|trolley) "),
    ("tie", r" (ties|tie|neck ?ties?|bow ?ties?|pocket squares?) "),
    ("cap", r" ((?<!no )caps?(?! sleeves?)|hats?|beanies?|snapbacks?|visors?|headbands?) "),
    ("socks", r" socks? "),
)


_NOT_ACCESSORY = re.compile(
    r" (gift cards?|kids|keychains?|key chains?|stickers?|posters?|mugs?|bottles?(?! green)|"
    r"perfumes?|fragrances?|deodorants?|candles?|phone cases?|masks?|towels?|cushions?|"
    r"serums?|trimmers?|hampers?|gift box|shoe (laces?|care|cleaner|polish|bags?)|"
    r"insoles?|stencils?|coasters?|notebooks?|diary|pens?|frames?|umbrellas?) ")


def _last_match(rules, text):
    """(position of the last matching keyword, category) or (-1, None)."""
    best = (-1, None)
    for cat, pattern in rules:
        ms = list(re.finditer(pattern, text))
        if ms and ms[-1].start() > best[0]:
            best = (ms[-1].start(), cat)
    return best


def _accessory_category(title, product_type):
    """Footwear / accessory category, or None. The head noun of an English
    product title comes last ("Chain Print Shirt" is a shirt, "Leather Belt"
    a belt), so the later of the apparel and accessory keywords wins."""
    for source in (title, product_type):
        text = norm(source)
        if not text.strip():
            continue
        if _NOT_ACCESSORY.search(text):
            return None
        pos_a, acc = _last_match(_ACCESSORY_RULES, text)
        if acc is None:
            continue
        if _has(_ACCESSORY_RULES[0][1], text):  # mojari / jutti wins over "shoes"
            acc = "ethnic_footwear"
        if acc != "socks" and _has(r" (pack of \d+|\d+ pack|combo|set of \d+ (?!pcs))", text) \
                and acc not in ("bag",):
            return None
        pos_c, app = _last_match(_CATEGORY_RULES, text)
        if app is not None and pos_c > pos_a and app != "coord_set":
            return False  # apparel: decided by the garment rules
        return acc
    return None


def detect_category(title: str, product_type: str = "", tags=(), include_accessories=False):
    """Return one of CATEGORIES (or ACCESSORY_CATEGORIES when allowed) or None."""
    if include_accessories:
        for source in (title, product_type):
            if _has(r" (pack of \d+|\d+ pack|combo|gift cards?|kids) ", norm(source)):
                acc = _accessory_category(title, product_type)
                return acc if acc == "socks" else None
        acc = _accessory_category(title, product_type)
        if acc:
            return acc
    if _has(_EXCLUDE, norm(title)) or _has(_EXCLUDE, norm(product_type)):
        return None  # accessories, innerwear, kids, footwear ... are out of scope
    # title is the strongest signal, then product_type, then tags
    tag_list = split_tags(tags) if isinstance(tags, str) else list(tags or ())
    for source in (title, product_type, *tag_list):
        text = norm(source)
        for cat, pattern in _CATEGORY_RULES:
            if _has(pattern, text):
                return cat
    return None


# --------------------------------------------------------------------------
# gender
# --------------------------------------------------------------------------

_WOMEN = (r" (women|womens|woman|ladies|lady|female|girls?|kurtis?|kurti sets?|sarees?|"
          r"saris?|lehengas?|lehenga sets?|blouses?|anarkalis?|salwar suits?|sharara|gharara|"
          r"palazzo sets?|dresses|gowns?|skirts?|bras?|maternity|kaftan dress|nighty) ")
_MEN = r" (men|mens|man|male) "
_UNISEX = r" (unisex|gender neutral|all gender|genderless) "


def detect_gender(title: str, product_type: str = "", tags=(), handle: str = "",
                  default=None):
    """Return (gender, source). Store tags ("Men", "Women") are the site's own
    labels; a product tagged with both is unisex."""
    tag_list = split_tags(tags) if isinstance(tags, str) else list(tags or ())
    for name, text in (("tags", " ".join(tag_list)),
                       ("title", " ".join([title, product_type, handle]))):
        t = norm(text)
        if _has(_UNISEX, t):
            return "unisex", name
        w, m = _has(_WOMEN, t), _has(_MEN, t)
        if w and m:
            return "unisex", name
        if w:
            return "women", name
        if m:
            return "men", name
    if default:
        return default, "site default"  # e.g. a menswear-only store
    return "unspecified", None


# --------------------------------------------------------------------------
# colour
# --------------------------------------------------------------------------

PALETTE = ("black", "white", "grey", "navy", "blue", "red", "green", "beige", "brown",
           "yellow", "orange", "pink", "purple", "multi")
# canonical colour -> synonyms. Longest synonym wins, so "navy blue" -> navy.
COLOR_MAP = {
    "black": ["black", "jet black", "onyx", "ebony", "noir", "carbon", "charcoal black"],
    "white": ["white", "off white", "ivory", "optic white", "snow", "ecru", "bone"],
    "grey": ["grey", "gray", "charcoal", "heather", "slate", "ash", "graphite",
             "silver", "anthracite", "melange", "marl", "smoke"],
    "navy": ["navy", "midnight", "midnight blue", "dark blue", "navy blue", "ink blue"],
    "blue": ["blue", "sky blue", "royal blue", "cobalt", "indigo", "denim blue", "teal",
             "aqua", "turquoise", "cyan", "azure", "light blue", "powder blue", "ice blue"],
    "red": ["red", "burgundy", "maroon", "wine", "crimson", "scarlet", "cherry",
            "brick", "oxblood"],
    "green": ["green", "olive", "sage", "forest green", "emerald", "mint", "lime",
              "moss", "army green", "bottle green", "khaki green", "pista"],
    "beige": ["beige", "cream", "sand", "tan", "stone", "khaki", "camel", "oatmeal",
              "taupe", "nude", "biscuit", "off beige", "latte"],
    "brown": ["brown", "chocolate", "coffee", "mocha", "chestnut", "walnut", "espresso",
              "cocoa", "pecan", "rust brown", "russet"],
    "yellow": ["yellow", "mustard", "gold", "lemon", "butter", "sunshine"],
    "orange": ["orange", "rust", "coral", "peach", "terracotta", "tangerine", "apricot"],
    "pink": ["pink", "rose", "blush", "fuchsia", "magenta", "salmon", "dusty rose",
             "baby pink", "hot pink"],
    "purple": ["purple", "lavender", "lilac", "violet", "plum", "mauve", "grape",
               "aubergine", "wine purple"],
    "multi": ["multi", "multicolor", "multicolour", "multicoloured", "multi color",
              "multi colour", "rainbow", "tie dye"],
}
_SYN_TO_COLOR = sorted(
    ((syn, canon) for canon, syns in COLOR_MAP.items() for syn in syns),
    key=lambda x: -len(x[0]),
)


def colors_in_text(text: str) -> list:
    """All palette colours named in ``text``, in order of appearance."""
    t = norm(text)
    hits = []
    for syn, canon in _SYN_TO_COLOR:  # longest first, then mask the match
        needle = f" {syn} "
        start = t.find(needle)
        while start != -1:
            hits.append((start, canon))
            t = t[:start + 1] + "#" * len(syn) + t[start + 1 + len(syn):]
            start = t.find(needle)
    out = []
    for _, c in sorted(hits):
        if c not in out:
            out.append(c)
    return out


def color_from_text(text: str):
    found = colors_in_text(text)
    return found[0] if found else None


def _option_values(product, pattern):
    for opt in product.get("options") or []:
        if re.search(pattern, (opt.get("name") or "").lower()):
            return [str(v) for v in opt.get("values") or []]
    return []


def detect_colors(product: dict, specs: dict = None):
    """Return dict(color, color_name, secondary_color, sources...).

    Primary colour: spec "Color:" field, then the "Color" variant option, then
    the title, then tags. Secondary colour: a second colour named in the same
    field (e.g. "Black & White"), then other colours in the title. The image
    step may still fill a missing secondary colour from pixels.
    """
    specs = specs if specs is not None else parse_specs(product.get("body_html", ""))
    title = product.get("title") or ""
    candidates = []
    if specs.get("color"):
        candidates.append(("field", specs["color"]))
    for v in _option_values(product, r"colou?r"):
        candidates.append(("field", v))
    candidates.append(("title", title))
    candidates.append(("tags", _tag_text(split_tags(product.get("tags")))))

    primary = primary_src = name = None
    for src, text in candidates:
        found = colors_in_text(text)
        if found:
            primary, primary_src, name = found[0], src, text.strip()
            break
    secondary = secondary_src = None
    if primary:
        for src, text in candidates[:-1]:  # tags are too noisy for a 2nd colour
            for c in colors_in_text(text):
                if c != primary and c != "multi":
                    secondary, secondary_src = c, src
                    break
            if secondary:
                break
    return {"color": primary, "color_name": name if primary_src == "field" else None,
            "secondary_color": secondary, "_src_color": primary_src,
            "_src_secondary_color": secondary_src}


# --------------------------------------------------------------------------
# fabric
# --------------------------------------------------------------------------

_FIBRES = (  # (canonical, pattern on normalised text); order = tie-break
    ("cotton", r"(supima cotton|organic cotton|combed cotton|cotton)"),
    ("polyester", r"(recycled polyester|polyester|poly)"),
    ("modal", r"(lenzing modal|modal)"),
    ("lyocell", r"(lyocell|tencel)"),
    ("viscose", r"(viscose|rayon)"),
    ("linen", r"linen"),
    ("wool", r"(merino|lambswool|wool)"),
    ("cashmere", r"cashmere"),
    ("nylon", r"(nylon|polyamide)"),
    ("elastane", r"(elastane|spandex|lycra)"),
    ("acrylic", r"acrylic"),
    ("silk", r"(raw silk|silk)"),
    ("khadi", r"khadi"),
    ("velvet", r"velvet"),
    ("satin", r"satin"),
    ("denim", r"denim"),
    ("fleece", r"fleece"),
    ("corduroy", r"corduroy"),
    ("leather", r"(faux leather|vegan leather|leather|suede)"),
)


def fabrics_in_text(text: str, fibres=_FIBRES) -> list:
    t = norm(text)
    hits = []
    for name, pat in fibres:
        m = re.search(rf" {pat} ", t)
        if m:
            hits.append((m.start(), name))
    return [n for _, n in sorted(hits)]


def parse_composition(text: str, fibres=_FIBRES) -> dict:
    """"60% Cotton 40% Polyester" -> {"cotton": 60, "polyester": 40}."""
    comp = {}
    for pct, fibre in re.findall(r"(\d+(?:\.\d+)?)\s*%\s*([A-Za-z][A-Za-z ]{1,30}?)"
                                 r"(?=\s*\d|\s*[,/&+]|\s*$|\s*\))", text or ""):
        names = fabrics_in_text(fibre, fibres)
        if names:
            comp[names[0]] = comp.get(names[0], 0) + float(pct)
    return comp


def detect_fabric(product: dict, specs: dict, title: str, tags, fibres=_FIBRES) -> dict:
    """Fabric list ordered by share (composition) or first appearance."""
    comp_text = specs.get("fabric") or ""
    comp = parse_composition(comp_text, fibres)
    if comp:
        fabrics = [k for k, _ in sorted(comp.items(), key=lambda kv: -kv[1])]
        src = "field"
    else:
        src = None
        fabrics = []
        for name, text in (("field", comp_text), ("title", title),
                           ("tags", _tag_text(tags)),
                           ("description", _clean_description(product.get("body_html", "")))):
            fabrics = fabrics_in_text(text, fibres)
            if fabrics:
                src = name
                break
    gsm = None
    m = re.search(r"\d{2,4}", specs.get("gsm") or "")
    if m:
        gsm = int(m.group(0))
    return {"fabric": fabrics[0] if fabrics else None, "fabrics": fabrics[:4],
            "composition": comp or None, "gsm": gsm, "_src_fabric": src}


# --------------------------------------------------------------------------
# pattern / fit / sleeve / neckline / occasion
# --------------------------------------------------------------------------

LICENSED = (r"marvel|disney|dc|naruto|harry potter|looney tunes|spongebob|hello ?kitty|"
            r"hellokitty|star wars|pokemon|superman|spiderman|batman|bratz|playboy|"
            r"hot ?wheels|hotwheels|red ?bull|redbull|tokidoki|nick 90s|lilo|smiley|"
            r"guns n roses|nirvana|2pac|anime|friends|f1|nba|nfl|garfield|mickey|minnie")

PATTERN_RULES = (
    ("striped", r" (stripes?|striped|pinstriped?|pin stripe) "),
    ("checked", r" (checks?|checked|checkered|plaid|gingham|tartan|windowpane) "),
    ("tie dye", r" (tie dye|tie and dye|tie dyed) "),
    ("camouflage", r" (camo|camouflage) "),
    ("floral", r" (floral|flowers?|tropical|hawaiian) "),
    ("colour block", r" (colou?r ?block(ed)?|contrast|panell?ed|two tone) "),
    ("embroidered", r" (embroidery|embroidered|embroided) "),
    ("graphic", rf" (graphic|graphics|printed|print|prints|screen print|puff print|"
                rf"typography|slogan|logo|artwork|{LICENSED}) "),
    ("washed", r" (acid wash|washed|faded|distressed|vintage wash|fade) "),
    ("textured", r" (textured|ribbed|rib|waffle|crinkle|jacquard|cable|knitted texture|"
                 r"self design|seersucker|pique|corduroy) "),
    ("solid", r" (solid|plain|basic|basics|essential|essentials) "),
)

FIT_RULES = (
    ("oversized", r" (oversized?|over sized|drop shoulder|dropped shoulder) "),
    ("boxy", r" boxy "),
    ("relaxed", r" (relaxed|loose|baggy|comfort) "),
    ("skinny", r" skinny "),
    ("slim", r" (slim|fitted|muscle|bodycon|body fit|tight) "),
    ("wide leg", r" (wide leg|wide|palazzo|parachute) "),
    ("flared", r" (flared?|flares|bootcut|boot cut|bell bottoms?) "),
    ("tapered", r" (tapered|carrot) "),
    ("straight", r" straight "),
    ("cropped", r" (cropped|crop) "),
    ("regular", r" (regular|classic fit|standard|true to size) "),
)

_SLEEVE_FIELD = (
    ("sleeveless", r" (sleeveless|no sleeves?|strapless|spaghetti|tank|cami|halter) "),
    ("three quarter", r" (3 4|three quarter|elbow) "),
    ("long", r" (long|full|longsleeves?) "),
    ("short", r" (short|half|cap) "),
)
_SLEEVE_TEXT = (  # stricter: the word must be about sleeves
    ("sleeveless", r" (sleeveless|tank|tank top|camisole|cami|tube|halter|strapless|"
                   r"spaghetti|vest) "),
    ("three quarter", r" (3 4 sleeves?|three quarter sleeves?) "),
    ("long", r" (long sleeves?|full sleeves?|longsleeves?|ls) "),
    ("short", r" (short sleeves?|half sleeves?|cap sleeves?|ss) "),
)

NECK_RULES = (
    ("hooded", r" (hood|hooded|hoodie) "),
    ("polo collar", r" polo "),
    ("v neck", r" v ?neck "),
    ("henley", r" henley "),
    ("high neck", r" (turtle ?neck|mock ?neck|high neck|roll neck|funnel neck) "),
    ("square neck", r" square( neck)? "),
    ("halter", r" (halter( neck)?|halterneck) "),
    ("off shoulder", r" (off shoulder|one shoulder|tube|strapless|bardot) "),
    ("boat neck", r" boat( neck)? "),
    ("scoop neck", r" (scoop( neck)?|u neck) "),
    ("sweetheart", r" sweetheart "),
    ("cowl neck", r" cowl "),
    ("mandarin collar", r" (mandarin|band collar|chinese collar|nehru) "),
    ("cuban collar", r" (cuban|camp collar|resort collar|revere) "),
    ("collar", r" (collar|collared|spread|button down|classic collar|shirt collar|notch) "),
    ("round neck", r" (round( neck)?|crew( neck)?|crewneck) "),
)
_NECK_TEXT = tuple(r for r in NECK_RULES if r[0] not in ("collar", "round neck")) + (
    ("collar", r" (collared|spread collar|button down|shirt collar) "),
    ("round neck", r" (round neck|crew neck|crewneck) "),
)

OCCASION_RULES = (
    ("activewear", r" (gym|gym wear|workout|training|athleisure|activewear|active|sports?|"
                   r"running|yoga|lifting|dancers?|performance) "),
    ("lounge", r" (lounge|loungewear|pyjamas?|pajamas?|sleepwear|nightwear|night suit) "),
    ("party", r" (party|party wear|cocktail|club ?wear|night out|happy hour|evening) "),
    ("formal", r" (formals?|formal wear|semi formal|office|workwear|business) "),
    ("festive", r" (festive|ethnic|wedding|celebration|diwali) "),
    ("vacation", r" (vacation|beach|resort|holiday|summer society|endless summer) "),
    ("smart casual", r" smart casuals? "),
    ("street", r" (street ?wear|street style) "),
    ("college", r" college( wear)? "),
    ("casual", r" (casual|casual wear|everyday|daily wear|streetwear|street) "),
)


def site_occasions(specs: dict, tags=()) -> list:
    """Every occasion the site itself names (Occasion field + tags), in order.

    "Formal Wear, Club Wear" -> ["formal", "party"]. Size-chart tags such as
    "Trouser Size Chart (Formal & Chinos)" are ignored.
    """
    found = []
    texts = [specs.get("occasion") or ""]
    texts += [t for t in (split_tags(tags) if isinstance(tags, str) else tags or ())
              if not re.search(r"(?i)size ?chart", t)]
    for text in texts:
        for part in re.split(r"[,/|&]", text):
            t = norm(part.replace("_", " "))
            hits = []
            for v, pat in OCCASION_RULES:
                m = re.search(pat, t)
                if m:
                    hits.append((m.start(), v))
            for _, v in sorted(hits)[:1]:
                if v not in found:
                    found.append(v)
    return found

_DEFAULT_NECK = {"hoodie": "hooded", "polo": "polo collar", "shirt": "collar",
                 "tshirt": "round neck", "sweatshirt": "round neck", "jacket": "collar",
                 "kurta": "mandarin collar", "kurta_set": "mandarin collar",
                 "sherwani": "mandarin collar", "ethnic_jacket": "mandarin collar",
                 "blazer": "collar"}
_DEFAULT_SLEEVE = {"tshirt": "short", "polo": "short", "hoodie": "long",
                   "sweatshirt": "long", "sweater": "long", "jacket": "long",
                   "kurta": "long", "kurta_set": "long", "sherwani": "long",
                   "ethnic_jacket": "sleeveless", "blazer": "long"}


# Words that are too vague to trust when they appear in marketing copy
# ("running errands", "evening looks", "a wardrobe essential", "check out").
_WEAK_IN_DESCRIPTION = re.compile(
    r" (running|evening|performance|active|sports?|street|friends|essentials?|basics?|"
    r"checks?|contrast|comfort|wide|fade|logo|prints?|rib|club|casual|everyday) ")


def _desc(desc):
    t = norm(desc)
    while True:  # overlapping matches need repeated passes
        t2 = _WEAK_IN_DESCRIPTION.sub(" ", t)
        if t2 == t:
            return t
        t = t2


def _sources(specs_value, title, tags, ptype, desc, field_rules=None, text_rules=None):
    desc = _desc(desc) if desc else desc
    return (("field", specs_value, field_rules), ("title", title, text_rules),
            ("tags", _tag_text(tags), text_rules), ("title", ptype, text_rules),
            ("description", desc, text_rules))


def detect_pattern(specs, title, tags=(), ptype="", desc="", rules=PATTERN_RULES):
    v, s = _first(rules, _sources(specs.get("pattern"), title, tags, ptype, desc))
    return (v, s) if v else ("solid", "default")


def detect_fit(category, specs, title, tags=(), ptype="", desc=""):
    if DEPARTMENT.get(category) in ("footwear", "accessories"):
        return None, "n/a"
    rules = FIT_RULES
    if DEPARTMENT.get(category) == "topwear":  # leg shapes make no sense for tops
        rules = tuple(r for r in FIT_RULES if r[0] not in ("wide leg", "flared", "tapered",
                                                            "skinny", "straight"))
    v, s = _first(rules, _sources(specs.get("fit"), title, tags, ptype, desc))
    return (v, s) if v else ("regular", "default")


_NO_UPPER = ("bottomwear", "footwear", "accessories")


def detect_sleeve(category, specs, title, tags=(), ptype="", desc="", text_rules=_SLEEVE_TEXT,
                  defaults=_DEFAULT_SLEEVE):
    if DEPARTMENT.get(category) in _NO_UPPER:
        return None, "n/a"
    v, s = _first(text_rules, _sources(specs.get("sleeve_length"), title, tags, ptype,
                                       desc, field_rules=_SLEEVE_FIELD))
    if v:
        return v, s
    if category in defaults:
        return defaults[category], "default"
    return None, None


def detect_neckline(category, specs, title, tags=(), ptype="", desc="", defaults=_DEFAULT_NECK):
    if DEPARTMENT.get(category) in _NO_UPPER:
        return None, "n/a"
    v, s = _first(_NECK_TEXT, _sources(specs.get("neckline"), title, tags, ptype, desc,
                                       field_rules=NECK_RULES))
    if v:
        return v, s
    if category in defaults:
        return defaults[category], "default"
    return None, None


def detect_occasion(specs, title, tags=(), ptype="", desc=""):
    if specs.get("occasion"):  # the site lists occasions; the first one is primary
        first = site_occasions({"occasion": specs["occasion"]})
        if first:
            return first[0], "field"
    v, s = _first(OCCASION_RULES, _sources(specs.get("occasion"), title, tags, ptype, desc))
    return (v, s) if v else ("casual", "default")


# --------------------------------------------------------------------------
# size
# --------------------------------------------------------------------------

_SIZE_ORDER = ["XXS", "XS", "S", "M", "L", "XL", "XXL", "2XL", "3XL", "XXXL", "4XL", "5XL",
               "6XL"]


def _size_key(s):
    u = s.upper().strip()
    if u in _SIZE_ORDER:
        return (0, _SIZE_ORDER.index(u), u)
    m = re.match(r"\d+", u)
    return (1, int(m.group(0)), u) if m else (2, 0, u)


def detect_sizes(product: dict):
    """(all sizes, sizes in stock) from the variant option named "Size"."""
    idx = None
    for i, opt in enumerate(product.get("options") or [], start=1):
        if re.search(r"size", (opt.get("name") or "").lower()):
            idx = i
            break
    if idx is None:
        return [], []
    all_s, avail = [], []
    for v in product.get("variants") or []:
        s = v.get(f"option{idx}")
        if not s:
            continue
        if s not in all_s:
            all_s.append(s)
        if v.get("available") and s not in avail:
            avail.append(s)
    if not all_s:  # feed without option1..3 on variants
        all_s = [str(x) for x in product["options"][idx - 1].get("values") or []]
    return sorted(all_s, key=_size_key), sorted(avail, key=_size_key)


# --------------------------------------------------------------------------
# price
# --------------------------------------------------------------------------

DEFAULT_BANDS = {"cheap": [0, 799], "affordable": [800, 1499], "luxury": [1500, None]}


def price_band(price, bands=None):
    """Band name for ``price``. Bands are {name: [low, high_or_None]}; each band
    starts at its low bound and runs until the next band's low bound."""
    if price is None:
        return None
    bands = bands or DEFAULT_BANDS
    ordered = sorted(bands.items(), key=lambda kv: kv[1][0] or 0)
    name = None
    for band, (lo, _hi) in ordered:
        if price >= (lo or 0):
            name = band
    return name or ordered[0][0]


def detect_prices(product: dict, specs: dict):
    """(price, mrp, discount_pct). Price = lowest variant price."""
    prices, mrps = [], []
    for v in product.get("variants") or []:
        try:
            prices.append(float(v.get("price")))
        except (TypeError, ValueError):
            pass
        try:
            cap = float(v.get("compare_at_price") or 0)
            if cap > 0:
                mrps.append(cap)
        except (TypeError, ValueError):
            pass
    price = min(prices) if prices else None
    mrp = max(mrps) if mrps else None
    if not mrp and specs.get("mrp"):
        m = re.search(r"(\d[\d,]*(?:\.\d+)?)", specs["mrp"].replace(" ", ""))
        if m:
            mrp = float(m.group(1).replace(",", ""))
    if mrp and price and mrp < price:
        mrp = None
    disc = round(100 * (mrp - price) / mrp) if mrp and price and mrp > price else 0
    return price, mrp or price, disc


# --------------------------------------------------------------------------
# whole product -> attributes
# --------------------------------------------------------------------------


WEAR_TYPE_RULES = (  # garment sub-type (formerly "styles"); several may apply
    ("oversized", r" (oversized?|over sized|drop shoulder) "), ("polo", r" polos? "),
    ("henley", r" henleys? "), ("hoodie", r" (hoodies?|hooded) "), ("cargo", r" cargos? "),
    ("jeans", r" (jeans?|denims?) "), ("joggers", r" (joggers?|track ?pants?) "),
    ("chinos", r" chinos? "), ("shacket", r" (shackets?|overshirts?) "),
    ("bomber", r" bombers? "), ("varsity", r" varsity "), ("co ord", r" (co ords?|coords?) "),
    ("cuban collar", r" (cuban|camp collar|resort collar) "), ("oxford", r" oxfords? "),
    ("kurta", r" kurtas? "), ("short kurta", r" short kurtas? "), ("pathani", r" pathani "),
    ("sherwani", r" sherwanis? "), ("nehru jacket", r" (nehru|bandi|bundi|modi jacket) "),
    ("bandhgala", r" (bandhgala|bandh gala|jodhpuri) "), ("indo western", r" indo ?western "),
    ("dhoti", r" dhotis? "), ("tank", r" (tanks?|vests?|sleeveless) "),
    ("tracksuit", r" (tracksuits?|track suits?) "), ("blazer", r" blazers? "),
    ("suit", r" suits? "), ("waistcoat", r" waistcoats? "),
    ("sweater", r" (sweaters?|cardigans?) "), ("shorts", r" shorts? "), ("baggy", r" baggy "),
    ("wide leg", r" wide leg "), ("parachute", r" parachute "), ("linen", r" linen "),
    ("graphic", r" graphic "),
)


ACCESSORY_TYPE_RULES = (
    ("sneakers", r" (sneakers?|trainers|high tops?|low tops?) "), ("loafers", r" (loafers?|moccasins?) "),
    ("formal shoes", r" (derbys?|oxfords?|brogues?|monks?|formal shoes?|dress shoes?) "),
    ("boots", r" (boots?|chelsea) "), ("sports shoes", r" (running|sports? shoes?|training shoes?|gym shoes?) "),
    ("slides", r" (slides|sliders|flip ?flops?|slippers?|clogs?) "), ("sandals", r" (sandals?|floaters?) "),
    ("mojari", r" (mojaris?|juttis?|jootis?|nagras?|khussas?) "), ("kolhapuri", r" kolhapuris? "),
    ("backpack", r" (backpacks?|rucksacks?) "), ("tote", r" totes? "),
    ("duffle", r" (duffle|duffel|gym bags?|travel bags?) "), ("sling", r" (sling|crossbody|messenger) "),
    ("laptop bag", r" (laptop|briefcase|office bags?) "), ("trolley", r" (trolley|suitcases?|luggage) "),
    ("pouch", r" (pouch|pouches|toiletry) "),
    ("baseball cap", r" (baseball|dad caps?|snapbacks?|trucker) "), ("bucket hat", r" bucket hats? "),
    ("beanie", r" beanies? "), ("aviator", r" aviators? "), ("wayfarer", r" wayfarers? "),
    ("round frames", r" round "), ("bow tie", r" bow ?ties? "), ("pocket square", r" pocket squares? "),
    ("cufflinks", r" cufflinks? "), ("bracelet", r" (bracelets?|kadas?) "),
    ("chain", r" (chains?|necklaces?|pendants?) "), ("ring", r" rings? "), ("brooch", r" (brooch|brooches|lapel pins?) "),
    ("stole", r" (stoles?|dupattas?|shawls?) "), ("muffler", r" (mufflers?|scarf|scarves) "),
    ("safa", r" (safas?|pagdis?|pagris?|turbans?) "), ("kalangi", r" kalangis? "),
    ("leather", r" (leather|suede) "),
)


def detect_accessory_types(title: str, ptype: str = "") -> list:
    t = norm(f"{title} {ptype}")
    return [name for name, pat in ACCESSORY_TYPE_RULES if _has(pat, t)]


def detect_wear_types(title: str, ptype: str = "") -> list:
    t = norm(f"{title} {ptype}")
    return [name for name, pat in WEAR_TYPE_RULES if _has(pat, t)]


def classify_product(product: dict, bands=None, include_accessories=False,
                     default_gender=None, site=None, catalogue="men"):
    """Shopify product dict -> attribute dict, or None if out of scope.

    ``catalogue="women"`` uses the women's categories, scope and attribute
    words (style_taxonomy_women.md); the men's path is unchanged."""
    if catalogue == "women":
        return _classify_women(product, bands, include_accessories, default_gender, site)
    title = (product.get("title") or "").strip()
    ptype = product.get("product_type") or ""
    tags = split_tags(product.get("tags"))
    category = detect_category(title, ptype, tags, include_accessories)
    if not category:
        return None
    specs = parse_specs(product.get("body_html", ""))
    desc = _clean_description(product.get("body_html", ""))
    gender, g_src = detect_gender(title, ptype, tags, product.get("handle", ""),
                                  default=default_gender)
    colors = detect_colors(product, specs)
    fabric = detect_fabric(product, specs, title, tags)
    pattern, p_src = detect_pattern(specs, title, tags, ptype, desc)
    fit, f_src = detect_fit(category, specs, title, tags, ptype, desc)
    sleeve, s_src = detect_sleeve(category, specs, title, tags, ptype, desc)
    neck, n_src = detect_neckline(category, specs, title, tags, ptype, desc)
    occasion, o_src = detect_occasion(specs, title, tags, ptype, desc)
    sizes, sizes_avail = detect_sizes(product)
    price, mrp, disc = detect_prices(product, specs)

    attr_source = {
        "gender": g_src, "color": colors.pop("_src_color"),
        "secondary_color": colors.pop("_src_secondary_color"),
        "pattern": p_src, "fit": f_src, "fabric": fabric.pop("_src_fabric"),
        "sleeve_length": s_src, "neckline": n_src, "occasion": o_src,
        "size": "field" if sizes else None,
    }
    out = {
        "category": category,
        "department": DEPARTMENT[category],
        "gender": gender,
        **colors,
        "pattern": pattern,
        "fit": fit,
        **fabric,
        "sleeve_length": sleeve,
        "neckline": neck,
        "occasion": occasion,
        "occasions": site_occasions(specs, tags) or [occasion],
        "sizes": sizes,
        "sizes_available": sizes_avail,
        "price": price,
        "mrp": mrp,
        "discount_pct": disc,
        "price_band": price_band(price, bands),
        "wear_types": (detect_accessory_types(title, ptype)
                       if DEPARTMENT[category] in ("footwear", "accessories")
                       else detect_wear_types(title, ptype)),
        "attr_source": attr_source,
    }
    from .style import classify_style  # late import: style.py imports this module
    out.update(classify_style(product, out, site))
    return out


# ==========================================================================
# women's catalogue (style_taxonomy_women.md)
#
# Separate tables so the men's catalogue is untouched. Indian women's titles
# often name a whole outfit ("Kurta with Pants and Dupatta", "Saree with
# Blouse"), so outfit words are checked first; otherwise the head noun (the
# last garment word before "with ...") decides.
# ==========================================================================

WOMEN_CATEGORIES = ("tshirt", "shirt", "top", "blouse", "sweatshirt", "hoodie", "sweater",
                    "jacket", "shrug", "blazer", "ethnic_jacket", "jeans", "trousers",
                    "leggings", "joggers", "shorts", "skirt", "ethnic_bottom", "dress", "gown",
                    "jumpsuit", "coord_set", "kurta", "kurta_set", "saree", "lehenga")
WOMEN_ACCESSORY_CATEGORIES = ("heels", "flats", "sandals", "shoes", "ethnic_footwear", "bag",
                              "clutch", "jewellery", "hair_accessory", "scarf", "belt",
                              "sunglasses", "watch", "cap", "socks", "wallet")
WOMEN_FOOTWEAR = ("heels", "flats", "sandals", "shoes", "ethnic_footwear")
for _c, _d in {"blouse": "topwear", "shrug": "topwear", "leggings": "bottomwear",
               "ethnic_bottom": "bottomwear", "gown": "fullbody", "jumpsuit": "fullbody",
               "saree": "fullbody", "lehenga": "fullbody", "heels": "footwear",
               "flats": "footwear", "clutch": "accessories", "hair_accessory": "accessories"
               }.items():
    DEPARTMENT.setdefault(_c, _d)

# not clothing, or out of scope for the women's catalogue (section 8)
_EXCLUDE_W = re.compile(
    r" (kids?|for girls|girls|boys?|baby|babies|toddlers?|infants?|newborn|teens?|"
    r"(?<!sports )bras?|bralette sets?|briefs?|panties|panty|lingerie|thongs?|boyshorts?|"
    r"hipsters?|shapewear|camisole sets?|"
    r"nightwear|night ?wear|sleepwear|sleep ?wear|night ?suits?|nightsuits?|nighty|nighties|"
    r"nightdress(es)?|night ?dress(es)?|nightgowns?|night gowns?|pyjama sets?|pajama sets?|"
    r"pj sets?|lounge sets?|loungewear|lounge ?wear|bathrobes?|robes?|"
    r"swim\w*|bikinis?|monokinis?|"
    r"dress materials?|unstitched suits?|suit pieces?|suit fabrics?|running material|"
    r"fabric|yardage|"
    r"gift cards?|gift vouchers?|e ?gift|gift sets?|gift box|hampers?|combos?|"
    r"pack of \d+|\d+ pack|set of (2|two|3|three|4|5|6) (kurtis|kurtas|tops|tees|t shirts|"
    r"leggings|dresses|shirts)|"
    r"masks?|cushions?|cushion covers?|rugs?|bedsheets?|bed ?covers?|quilts?|dohars?|towels?|"
    r"curtains?|table ?(runners?|cloths?|mats?)|napkins?|coasters?|mugs?|bottles?|candles?|"
    r"posters?|stickers?|notebooks?|diary|diaries|keychains?|key chains?|phone cases?|"
    r"perfumes?|fragrances?|deodorants?|lipsticks?|kajal|serums?|soaps?|"
    r"dolls?|toys?|stuffed|plushies?|aprons?|pets?|dogs?|"
    # men's-only garments that women-only stores sometimes list without a gender tag
    r"sherwanis?|achkans?|kurta (pyjama|pajama)s?|pathani|cufflinks?|groom|grooms) ")
# a saree's blouse piece is part of the saree, not an unstitched dress material
_EXCLUDE_UNSTITCHED_W = re.compile(r" (unstitched|semi stitched|blouse pieces?|blouse fabric) ")
_OUTFIT_W = re.compile(r" (sarees?|saris?|sari|lehengas?|lehnga|ghagras?|chaniya) ")

_PRIORITY_W = (  # outfit words: the whole title is one of these whatever comes later
    ("blouse", r" (saree blouses?|sari blouses?|readymade (saree )?blouses?|designer blouses?|"
               r"stitched blouses?|padded blouses?|ready to wear blouses?|blouse for saree) "),
    ("saree", r" (sarees?|saris?|sari|pre ?draped|pre stitched saree) "),
    ("lehenga", r" (lehengas?|lehnga|lehenga cholis?|ghagras?|ghagra cholis?|chaniya cholis?|"
                r"chaniya) "),
    ("kurta_set", r" ((kurtas?|kurtis?|anarkalis?|tunics?|kurta sets?) (and |with |)"
                  r"(pants?|palazzos?|trousers?|sharara|shararas|gharara|ghararas|salwars?|"
                  r"churidars?|dupattas?|skirts?|dhotis?|dhoti pants?|pyjamas?|leggings?|"
                  r"patiala|afghani|straight pants?|jacket|jackets|capes?|shrugs?|koti|"
                  r"bottoms?|stoles?)|"
                  r"kurta sets?|kurti sets?|kurta suits?|suit sets?|salwar suits?|"
                  r"salwar kameez|churidar suits?|anarkali (sets?|suits?)|sharara (sets?|suits?)|"
                  r"gharara (sets?|suits?)|palazzo (sets?|suits?)|patiala (sets?|suits?)|"
                  r"straight (sets?|suits?)|afghani (sets?|suits?)|ethnic sets?|"
                  r"(2|3|two|three) (piece|pc|pcs) (suits?|kurta sets?)|"
                  r"(?<!blazer )(?<!pant )(?<!track )(?<!body )(?<!jump )(?<!co ord )"
                  r"(?<!night )(?<!lounge )(?<!sweat )(?<!swim )(?<!trouser )suits?) "),
    ("jumpsuit", r" (jumpsuits?|jump suits?|rompers?|playsuits?|dungarees?|overalls?) "),
    ("gown", r" (gowns?) "),
    ("coord_set", r" ((crop )?(tops?|shirts?|blazers?|tees?|t shirts?|jackets?|cholis?|"
                  r"bralettes?|corsets?|shrugs?|capes?) (and |with |)(ethnic |printed |"
                  r"matching |flared |pleated |wide leg |)(skirts?|pants?|trousers?|shorts|"
                  r"palazzos?|joggers?|sharara|shararas|culottes?|dhoti pants?) (sets?|co ords?)|"
                  r"crop tops? (and |with )(ethnic |printed |)(skirts?|lehenga|sharara|"
                  r"dhoti pants?)|co ords?|co ord sets?|coord sets?|coords?|"
                  r"(2|3|two|three) (piece|pc|pcs) sets?|tracksuits?|track suits?) "),
    ("ethnic_bottom", r" (sharara|gharara|dhoti|salwar|patiala|afghani|churidar|harem) "
                      r"(pants?|bottoms?|pyjamas?|leggings?|trousers?) "),
)
_HEAD_W = (  # head-noun rules: the last match before "with ..." wins
    ("dress", r" (dress(es)?|shirt ?dress|maxi|midi|kaftans?|caftans?|sundress(es)?|"
              r"frocks?|bodycon) "),
    ("skirt", r" (skirts?|skorts?) "),
    ("shorts", r" (shorts|hot pants|bermudas?|jorts) "),
    ("jeans", r" (jeans?) "),
    ("leggings", r" (leggings?|jeggings?|tights|yoga pants?|treggings?) "),
    ("joggers", r" (joggers?|track ?pants?|sweat ?pants?|trackpants?) "),
    ("ethnic_bottom", r" (salwars?|churidars?|patialas?|dhoti pants?|dhotis?|"
                      r"sharara( pants?)?|shararas|gharara( pants?)?|ghararas|afghani pants?|"
                      r"harem pants?) "),
    ("trousers", r" (trousers?|pants?|palazzos?|culottes?|cargos?|chinos?|slacks|flares?|"
                 r"bottoms?|parachutes?|pantsuits?) "),
    ("blazer", r" (blazers?|waistcoats?) "),
    ("shrug", r" (shrugs?|capes?|kimonos?|ponchos?) "),
    ("ethnic_jacket", r" (nehru jackets?|kotis?|bundis?|bandis?|ethnic jackets?|"
                      r"ethnic waistcoats?) "),
    ("jacket", r" (jackets?|bombers?|varsity|windcheaters?|puffers?|coats?|trench|"
               r"shackets?|overshirts?|gilets?|overcoats?) "),
    ("hoodie", r" (hoodies?|hooded sweatshirts?) "),
    ("sweatshirt", r" (sweatshirts?|sweat shirts?|pullovers?) "),
    ("sweater", r" (sweaters?|cardigans?|jumpers?|knitwear|turtlenecks?|sweater vests?) "),
    ("kurta", r" (kurtas?|kurtis?|anarkalis?|tunics?|angrakhas?|kurta tops?) "),
    ("tshirt", r" (t ?shirts?|tees?|tshirts?|baby ?tees?|henleys?|polos?) "),
    ("shirt", r" (shirts?|button downs?|button ups?|oxfords?|flannels?) "),
    ("top", r" (tops?|crop tops?|tanks?|tank tops?|camis?|camisoles?|tube tops?|bodysuits?|"
            r"corsets?|bustiers?|bralettes?|halters?|halternecks?|peplums?|sports bras?|"
            r"vests?|cholis?|bandeaus?|blouses?) "),
    ("coord_set", r" (sets?|outfits?) "),
)
_ETHNIC_BLOUSE = (r" (sarees?|sari|readymade|padded|stitched|cholis?|ethnic|zari|brocade|"
                  r"banarasi|silk|mirror work|sequin|sequinned) ")

_ACCESSORY_RULES_W = (
    ("ethnic_footwear", r" (mojaris?|juttis?|jootis?|nagras?|khussas?|kolhapuris?|"
                        r"ethnic footwear|ethnic sandals?|ethnic flats?) "),
    ("heels", r" (heels?|high heels?|stilettos?|pumps|wedges?|block heels?|kitten heels?|"
              r"platforms?|heeled sandals?) "),
    ("flats", r" (flats|ballerinas?|ballet flats|bellies|mary janes?|loafers?|moccasins?|"
              r"mules?) "),
    ("sandals", r" (sandals?|slides|sliders|flip ?flops?|chappals?|slippers?|clogs?|"
                r"floaters?) "),
    ("shoes", r" (shoes?|sneakers?|boots?|booties|trainers|espadrilles?|footwear) "),
    ("watch", r" (watch|watches|wrist ?watch) "),
    ("hair_accessory", r" (scrunchies?|hair ?clips?|hair ?bands?|headbands?|hair ?ties?|"
                       r"claw clips?|hair ?pins?|barrettes?|hair accessor(y|ies)|hair ?bows?|"
                       r"tiaras?|hair ?chains?|juda pins?|parandis?) "),
    ("jewellery", r" (earrings?|jhumkas?|jhumkis?|studs|hoops?|danglers?|necklaces?|"
                  r"necklace sets?|chokers?|pendants?|chains?|bracelets?|bangles?|kadas?|"
                  r"kangans?|anklets?|payals?|rings?|nose ?pins?|nose ?rings?|nath|"
                  r"maang ?tikkas?|tikkas?|passa|matha ?pattis?|hath ?phools?|kamarbandh|"
                  r"waist ?chains?|brooch(es)?|jewell?ery|jewelry|mangalsutras?|charms?|"
                  r"ear ?cuffs?|haath ?phool) "),
    ("scarf", r" (scarf|scarves|stoles?|shawls?|dupattas?|bandanas?|mufflers?) "),
    ("sunglasses", r" (sunglasses|shades|eyewear) "),
    ("belt", r" belts? "),
    ("wallet", r" (wallets?|card holders?|coin purses?) "),
    ("clutch", r" (clutch(es)?|potlis?|potli bags?|batuas?|minaudieres?|evening bags?) "),
    ("bag", r" (bags?|handbags?|backpacks?|totes?|sling bags?|slings?|crossbody|purses?|"
            r"hobos?|satchels?|baguettes?|duffels?|duffles?|laptop sleeves?) "),
    ("cap", r" ((?<!no )caps?(?! sleeves?)(?! sleeved)|hats?|beanies?|visors?|berets?) "),
    ("socks", r" socks? "),
)
_NOT_ACCESSORY_W = re.compile(
    _NOT_ACCESSORY.pattern[:-2] + r"|girls|baby|toddlers?|lipsticks?|kajal|nail (paint|polish)|"
    r"makeup|cosmetics?|stockings?|gift sets?|hampers?|combos?|pack of \d+|\d+ pack|"
    r"lingerie|(?<!sports )bras?) ")
# garment / accessory words that keep a title out of the garment path when the
# accessory path is off (a "Bangles Set" is not a co-ord set)
_ACCESSORY_WORD_W = re.compile(
    r" (stoles?|dupattas?|shawls?|scarf|scarves|jewell?ery|earrings?|jhumkas?|bags?|handbags?|"
    r"heels|sandals?|footwear|shoes?|sneakers?|juttis?|bangles?|necklaces?|clutch(es)?|"
    r"potlis?|belts?|watch(es)?|sunglasses|caps?|hats?|socks?|scrunchies?|hair ?clips?|"
    r"anklets?|rings?) ")

_FIBRES_W = _FIBRES + (
    ("georgette", r"georgette"), ("chiffon", r"chiffon"), ("crepe", r"crepe"),
    ("organza", r"organza"), ("net", r"(net|tulle)"), ("chanderi", r"chanderi"),
    ("muslin", r"(muslin|mulmul)"), ("tissue", r"tissue"), ("brocade", r"brocade"),
)
_PATTERN_W = (
    PATTERN_RULES[0], PATTERN_RULES[1], PATTERN_RULES[2], PATTERN_RULES[3], PATTERN_RULES[4],
    ("polka dot", r" (polka|polka dots?|polka dotted|dotted) "),
    ("animal print", r" (leopard|zebra|cheetah|snake ?skin|snake print|animal print|"
                     r"croc print) "),
    ("ethnic print", r" (bandhani|bandhej|leheriya|lehariya|ikat|ajrakh|kalamkari|bagru|"
                     r"dabu|block print|block printed|hand block|shibori|batik|sanganeri|"
                     r"kantha|madhubani|warli|patola|ethnic print|ethnic motifs?) "),
    PATTERN_RULES[5],
    ("embellished", r" (sequins?|sequinned|sequined|embellished|embellishment|mirror work|"
                    r"stone work|zardozi|zari work|beaded|bead work|gota|gota patti|"
                    r"swarovski|crystals?|glitter|shimmer|metallic) "),
    PATTERN_RULES[6],
    ("printed", r" (printed|print|prints|all over print|aop|digital print) "),
    ("graphic", rf" (graphic|graphics|screen print|puff print|typography|slogan|logo|"
                rf"artwork|{LICENSED}) "),
    *PATTERN_RULES[8:],
)
_SLEEVE_TEXT_W = (
    ("sleeveless", r" (sleeveless|strappy|straps|strap|spaghetti|tube|strapless|off shoulder|"
                   r"corsets?|bustiers?|bandeau|halter|halterneck|cami|camisole|tank|"
                   r"tank top|sports bra|bralette|one shoulder) "),
    ("three quarter", r" (3 4 sleeves?|three quarter sleeves?|3 4th sleeves?|elbow sleeves?) "),
    ("long", r" (long sleeves?|full sleeves?|longsleeves?|bell sleeves?|bishop sleeves?) "),
    ("short", r" (short sleeves?|half sleeves?|cap sleeves?|puff sleeves?|puffed sleeves?|"
              r"flutter sleeves?|ruffle sleeves?) "),
)
_DEFAULT_SLEEVE_W = {**_DEFAULT_SLEEVE, "kurta": "three quarter",
                     "kurta_set": "three quarter", "saree": "short", "lehenga": "short",
                     "blouse": "short", "shrug": "long"}
_DEFAULT_NECK_W = {**_DEFAULT_NECK, "kurta": "round neck", "kurta_set": "round neck",
                   "saree": "round neck", "lehenga": "round neck", "blouse": "round neck"}

WEAR_TYPE_RULES_W = (  # women's garment sub-types (taxonomy section 7 notes)
    ("anarkali", r" anarkalis? "), ("a line", r" (a line|aline|a lined) "),
    ("straight", r" straight "), ("flared", r" (flared?|flowy|umbrella|godet|circular) "),
    ("kaftan", r" (kaftans?|caftans?) "), ("tiered", r" tiered "),
    ("maxi", r" maxi "), ("midi", r" midi "), ("mini", r" mini "),
    ("shirt dress", r" shirt ?dress "), ("slip dress", r" slip dress "),
    ("wrap", r" (wrap|wrapped|overlap) "), ("bodycon", r" bodycon "),
    ("skater", r" skater "), ("pencil", r" pencil "), ("pleated", r" (pleated|pleats) "),
    ("peplum", r" peplums? "), ("crop top", r" (crop tops?|cropped tops?|crop) "),
    ("corset", r" (corsets?|bustiers?) "), ("cami", r" (camis?|camisoles?|strappy|spaghetti) "),
    ("tank", r" (tanks?|tank tops?|vests?) "), ("tube", r" (tube|bandeau|strapless) "),
    ("off shoulder", r" (off shoulder|one shoulder|cold shoulder) "),
    ("halter", r" (halter|halterneck) "), ("sports bra", r" sports bras? "),
    ("bodysuit", r" bodysuits? "), ("puff sleeve", r" (puff|puffed) sleeves? "),
    ("palazzo", r" palazzos? "), ("culottes", r" culottes? "), ("sharara", r" shararas? "),
    ("gharara", r" ghararas? "), ("salwar", r" (salwars?|patiala|afghani) "),
    ("churidar", r" churidars? "), ("dhoti", r" (dhotis?|dhoti pants?) "),
    ("dupatta", r" (dupattas?|stoles?) "), ("jacket", r" (jackets?|koti|shrugs?|capes?) "),
    ("cape", r" capes? "), ("shrug", r" shrugs? "),
    ("pre draped", r" (pre ?draped|ready to wear saree|pre stitched) "),
    ("leggings", r" leggings? "), ("jeggings", r" jeggings? "),
    ("wide leg", r" (wide leg|wide legged|palazzo) "), ("mom jeans", r" mom (fit )?jeans? "),
    ("bootcut", r" (bootcut|boot cut|bell bottoms?) "), ("cargo", r" cargos? "),
    ("parachute", r" parachute "), ("oversized", r" (oversized?|over sized|drop shoulder) "),
    ("baggy", r" baggy "), ("hoodie", r" (hoodies?|hooded) "), ("blazer", r" blazers? "),
    ("co ord", r" (co ords?|coords?) "), ("jumpsuit", r" jumpsuits? "),
    ("dungaree", r" (dungarees?|overalls?) "), ("gown", r" gowns? "),
    ("lehenga choli", r" (lehenga cholis?|cholis?) "), ("saree", r" (sarees?|saris?) "),
    ("blouse", r" blouses? "), ("skort", r" skorts? "),
    ("biker shorts", r" (biker|cycling) shorts "), ("linen", r" linen "),
    ("graphic", r" graphic "),
)
ACCESSORY_TYPE_RULES_W = (
    ("stilettos", r" stilettos? "), ("block heels", r" block heels? "),
    ("kitten heels", r" kitten heels? "), ("wedges", r" wedges? "), ("platform", r" platforms? "),
    ("pumps", r" pumps "), ("ballerinas", r" (ballerinas?|ballet flats|bellies|mary janes?) "),
    ("mules", r" mules? "), ("loafers", r" (loafers?|moccasins?) "),
    ("juttis", r" (juttis?|jootis?|mojaris?|nagras?|khussas?) "), ("kolhapuri", r" kolhapuris? "),
    ("sneakers", r" (sneakers?|trainers) "), ("boots", r" (boots?|booties) "),
    ("sports shoes", r" (running|sports? shoes?|training shoes?|gym shoes?) "),
    ("slides", r" (slides|sliders|flip ?flops?|slippers?|clogs?) "),
    ("sandals", r" (sandals?|floaters?) "),
    ("handbag", r" (handbags?|shoulder bags?|hobos?|satchels?|baguettes?) "),
    ("tote", r" totes? "), ("sling", r" (slings?|sling bags?|crossbody) "),
    ("backpack", r" backpacks? "), ("potli", r" (potlis?|batuas?) "), ("clutch", r" clutch(es)? "),
    ("earrings", r" (earrings?|studs|hoops?|danglers?|ear ?cuffs?) "),
    ("jhumka", r" (jhumkas?|jhumkis?) "),
    ("necklace", r" (necklaces?|necklace sets?|pendants?|chains?|mangalsutras?) "),
    ("choker", r" chokers? "), ("bangles", r" (bangles?|kadas?|kangans?) "),
    ("bracelet", r" bracelets? "), ("ring", r" rings? "), ("anklet", r" (anklets?|payals?) "),
    ("maang tikka", r" (maang ?tikkas?|tikkas?|matha ?pattis?|passa) "),
    ("nose pin", r" (nose ?pins?|nose ?rings?|nath) "),
    ("hair clip", r" (hair ?clips?|claw clips?|barrettes?|hair ?pins?|juda pins?) "),
    ("scrunchie", r" scrunchies? "), ("hairband", r" (hair ?bands?|headbands?|tiaras?) "),
    ("dupatta", r" dupattas? "), ("stole", r" (stoles?|shawls?) "),
    ("scarf", r" (scarf|scarves|bandanas?) "),
    ("oxidised", r" (oxidi[sz]ed|german silver) "), ("kundan", r" (kundan|polki) "),
    ("temple", r" temple "), ("pearl", r" pearls? "), ("leather", r" (leather|suede) "),
)


_WITH_W = r" (?:with|w|wth|paired with|featuring|along with|comes with) "


def _last_end(rules, text):
    """(end of the last matching keyword, category): "T-Shirt" ends after "shirt"
    too, but the longer "t shirt" match wins the tie."""
    best = (-1, 0, None)
    for cat, pattern in rules:
        for m in re.finditer(pattern, text):
            key = (m.end(), m.end() - m.start())
            if key > best[:2]:
                best = (*key, cat)
    return best[0], best[2]


def _head_category(text, rules):
    """(position, category) of the last rule match in the part before "with"."""
    head = re.split(_WITH_W, text)[0] + " "
    pos, cat = _last_end(rules, head)
    if cat is None and head.strip() != text.strip():
        pos, cat = _last_end(rules, text)
    return pos, cat


def _garment_category_w(text):
    for cat, pat in _PRIORITY_W:
        if _has(pat, text):
            return cat
    _, cat = _head_category(text, _HEAD_W)
    if cat is None and _has(r" denims? ", text):
        cat = "jeans"
    if cat == "top" and _has(r" blouses? ", text) and _has(_ETHNIC_BLOUSE, text):
        cat = "blouse"
    return cat


def _accessory_category_w(title, product_type):
    """Women's footwear / accessory category, None, or False (= a garment)."""
    for source in (title, product_type):
        text = norm(source)
        if not text.strip():
            continue
        if _NOT_ACCESSORY_W.search(text):
            return None
        head = re.split(_WITH_W, text)[0] + " "
        pos_a, acc = _last_end(_ACCESSORY_RULES_W, head)
        if acc is None:
            if _last_end(_HEAD_W, head)[1] is not None or any(
                    _has(p, head) for _, p in _PRIORITY_W):
                return False  # "Top with Chain Detail", "Dress with Belt"
            pos_a, acc = _last_end(_ACCESSORY_RULES_W, text)
            if acc is None:
                continue
        if _has(_ACCESSORY_RULES_W[0][1], text):  # juttis / kolhapuris win over "sandals"
            acc = "ethnic_footwear"
        elif acc == "bag" and _has(r" (potlis?|batuas?|clutch(es)?) ", text):
            acc = "clutch"
        elif acc in ("sandals", "flats", "shoes") and _has(
                r" (heels?|heeled|stilettos?|wedges?|block heels?|kitten heels?) ", text):
            acc = "heels"  # "Block Heel Sandals", "Wedge Mules"
        if any(_has(p, text) for _, p in _PRIORITY_W[:4]):
            return False  # "Kurta Set with Dupatta", "Saree with Blouse": clothing
        if acc == "scarf" and _has(r" (kurtas?|kurtis?|suits?|sets?|lehengas?|sarees?|"
                                   r"anarkalis?|gowns?) ", text):
            return False
        pos_c, app = _head_category(text, _HEAD_W)
        if app is not None and pos_c > pos_a and app != "coord_set":
            return False
        return acc
    return None


def detect_category_women(title, product_type="", tags=(), include_accessories=False):
    """One of WOMEN_CATEGORIES (or WOMEN_ACCESSORY_CATEGORIES when allowed) or None."""
    t, pt = norm(title), norm(product_type)
    if _EXCLUDE_W.search(t) or _EXCLUDE_W.search(pt):
        return None
    for text in (t, pt):
        if _EXCLUDE_UNSTITCHED_W.search(text) and not _OUTFIT_W.search(text):
            return None  # unstitched dress material / blouse piece sold alone
    acc = _accessory_category_w(title, product_type)
    if acc:
        return acc if include_accessories else None
    if acc is None and _ACCESSORY_WORD_W.search(t) and not any(
            _has(p, t) for _, p in _PRIORITY_W):
        _, app = _head_category(t, _HEAD_W)
        if app is None or app == "coord_set":
            return None
    tag_list = split_tags(tags) if isinstance(tags, str) else list(tags or ())
    for source in (title, product_type, *tag_list):
        cat = _garment_category_w(norm(source))
        if cat:
            return cat
    return None


def detect_wear_types_women(title, ptype=""):
    t = norm(f"{title} {ptype}")
    return [name for name, pat in WEAR_TYPE_RULES_W if _has(pat, t)]


def detect_accessory_types_women(title, ptype=""):
    t = norm(f"{title} {ptype}")
    return [name for name, pat in ACCESSORY_TYPE_RULES_W if _has(pat, t)]


def _classify_women(product, bands, include_accessories, default_gender, site):
    title = (product.get("title") or "").strip()
    ptype = product.get("product_type") or ""
    tags = split_tags(product.get("tags"))
    category = detect_category_women(title, ptype, tags, include_accessories)
    if not category:
        return None
    specs = parse_specs(product.get("body_html", ""))
    desc = _clean_description(product.get("body_html", ""))
    gender, g_src = detect_gender(title, ptype, tags, product.get("handle", ""),
                                  default=default_gender)
    colors = detect_colors(product, specs)
    fabric = detect_fabric(product, specs, title, tags, _FIBRES_W)
    pattern, p_src = detect_pattern(specs, title, tags, ptype, desc, _PATTERN_W)
    fit, f_src = detect_fit(category, specs, title, tags, ptype, desc)
    sleeve, s_src = detect_sleeve(category, specs, title, tags, ptype, desc, _SLEEVE_TEXT_W,
                                  _DEFAULT_SLEEVE_W)
    neck, n_src = detect_neckline(category, specs, title, tags, ptype, desc, _DEFAULT_NECK_W)
    occasion, o_src = detect_occasion(specs, title, tags, ptype, desc)
    sizes, sizes_avail = detect_sizes(product)
    price, mrp, disc = detect_prices(product, specs)
    dept = DEPARTMENT[category]
    attr_source = {
        "gender": g_src, "color": colors.pop("_src_color"),
        "secondary_color": colors.pop("_src_secondary_color"), "pattern": p_src,
        "fit": f_src, "fabric": fabric.pop("_src_fabric"), "sleeve_length": s_src,
        "neckline": n_src, "occasion": o_src, "size": "field" if sizes else None,
    }
    out = {
        "category": category, "department": dept, "gender": gender, **colors,
        "pattern": pattern, "fit": fit, **fabric, "sleeve_length": sleeve, "neckline": neck,
        "occasion": occasion, "occasions": site_occasions(specs, tags) or [occasion],
        "sizes": sizes, "sizes_available": sizes_avail, "price": price, "mrp": mrp,
        "discount_pct": disc, "price_band": price_band(price, bands),
        "wear_types": (detect_accessory_types_women(title, ptype)
                       if dept in ("footwear", "accessories")
                       else detect_wear_types_women(title, ptype)),
        "attr_source": attr_source,
    }
    from .style import classify_style
    out.update(classify_style(product, out, site, catalogue="women"))
    return out

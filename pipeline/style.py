"""Fashion-style classification (style_taxonomy.md).

Every item gets one primary style out of eight (minimalist, classic,
streetwear, boho, sporty, glam, ethnic_fusion, traditional) or
``unclassified``, up to two secondary styles, per-style scores and a
confidence. The method is deterministic keyword scoring:

  * keyword hits in title / product type / tags / the site's labelled
    pattern-fit-occasion fields at full weight (strong 3, medium 2, weak 1),
    hits only in the description at half weight (rounded down, capped +3),
    each distinct phrase once;
  * negative phrases -2 each (title / type / tags only);
  * brand prior +2 for the site or vendor;
  * palette and fabric signals +1 each;
  * then the conflict rules of section 3 and the fallbacks of section 5.4.

Rule data lives in style_rules.yaml so keywords can be tuned without code
changes.
"""
import re
from functools import lru_cache
from pathlib import Path

import yaml

from .classify import _clean_description, norm, parse_specs, split_tags

RULES_PATH = Path(__file__).with_name("style_rules.yaml")            # men's catalogue
RULES_PATH_WOMEN = Path(__file__).with_name("style_rules_women.yaml")  # women's catalogue
STYLES = ("minimalist", "classic", "streetwear", "boho", "sporty", "glam", "ethnic_fusion",
          "traditional")
UNCLASSIFIED = "unclassified"
STYLE_LABELS = {"minimalist": "Minimalist", "classic": "Classic", "streetwear": "Streetwear",
                "boho": "Boho", "sporty": "Sporty", "glam": "Glam",
                "ethnic_fusion": "Ethnic fusion", "traditional": "Traditional",
                "edgy": "Edgy", "unclassified": "Unclassified"}
# the women's taxonomy adds a ninth style
STYLES_WOMEN = STYLES + ("edgy",)


def styles_for(catalogue="men"):
    return STYLES_WOMEN if catalogue == "women" else STYLES


def rules_for(catalogue="men"):
    return load_rules(str(RULES_PATH_WOMEN)) if catalogue == "women" else load_rules()

INDIAN = {"kurta", "kurta_set", "sherwani", "ethnic_jacket", "dhoti"}
TAILORED = {"shirt", "trousers", "blazer", "polo"}


@lru_cache(maxsize=None)
def load_rules(path: str = str(RULES_PATH)) -> dict:
    with open(path, encoding="utf-8") as f:
        rules = yaml.safe_load(f)
    # pre-normalise every phrase once
    for block in ("styles", "accessory_styles"):
        for name, sty in (rules.get(block) or {}).items():
            for level in ("strong", "medium", "weak", "negative"):
                sty[level] = list(dict.fromkeys(norm(p).strip() for p in sty.get(level) or []))
            if block == "accessory_styles":  # shared palette / fabric signals
                sty.setdefault("palette", rules["styles"][name].get("palette") or [])
                sty.setdefault("fabrics", rules["styles"][name].get("fabrics") or [])
    rules["cues"] = {k: [norm(p).strip() for p in v] for k, v in rules["cues"].items()}
    rules["description_ignore"] = {norm(p).strip() for p in rules.get("description_ignore") or []}
    rules["brand_priors"] = {_key(k): v for k, v in (rules.get("brand_priors") or {}).items()}
    return rules


def _key(name) -> str:
    return re.sub(r"[^a-z0-9]", "", (name or "").lower())


def _hit(phrase: str, text: str) -> bool:
    return f" {phrase} " in text


def _any(phrases, text) -> bool:
    return any(_hit(p, text) for p in phrases)


def brand_prior(site_name, vendor, rules=None) -> list:
    rules = rules or load_rules()
    pri = rules["brand_priors"]
    return list(dict.fromkeys(pri.get(_key(site_name), []) + pri.get(_key(vendor), [])))


def score_styles(full: str, desc: str, prior, color, color_name, fabrics, rules=None,
                 block="styles"):
    """Return (scores, hits) where hits = [(style, phrase, where), ...].
    ``block`` picks the keyword lists: "styles" (garments) or "accessory_styles"."""
    rules = rules or load_rules()
    w = rules["weights"]
    scores, hits = {}, []
    cname = norm(color_name or "")
    for s in rules.get("style_ids") or STYLES:
        r = rules[block][s]
        total, from_desc, evidence = 0, 0, False
        for level in ("strong", "medium", "weak"):
            for p in r[level]:
                if _hit(p, full):
                    total += w[level]
                    hits.append((s, p, "text"))
                    evidence = evidence or level != "weak"
                elif desc and p not in rules["description_ignore"] and _hit(p, desc):
                    add = min(w[level] // 2, w["description_cap"] - from_desc)
                    if add > 0:
                        evidence = evidence or level != "weak"
                        total += add
                        from_desc += add
                        hits.append((s, p, "description"))
        for p in r["negative"]:
            if _hit(p, full):
                total += w["negative"]
                hits.append((s, "-" + p, "text"))
        if s in prior:
            total += w["prior"]
            hits.append((s, "brand prior", "site"))
        pal = r.get("palette") or []
        if pal and (color in pal or _any(pal, cname)):
            total += w["palette"]
            hits.append((s, "palette", "colour"))
        if set(r.get("fabrics") or []) & set(fabrics or ()):
            total += w["fabric"]
            hits.append((s, "fabric", "fabric"))
        if not evidence:
            total = min(total, rules.get("no_evidence_cap", 2))
        scores[s] = total
    return scores, hits


def classify_style(product: dict, attrs: dict, site: dict = None, catalogue="men") -> dict:
    """Section 6 fields for one product: primary_style, style_tags,
    style_scores, style_confidence, style_source (+ style_hits for audit).
    ``catalogue="women"`` uses style_rules_women.yaml and the women's rules."""
    if catalogue == "women":
        return classify_style_women(product, attrs, site or {})
    rules = load_rules()
    site = site or {}
    title = product.get("title") or ""
    tags = split_tags(product.get("tags"))
    specs = parse_specs(product.get("body_html", ""))
    labelled = " ".join(specs.get(k) or "" for k in ("pattern", "fit", "occasion"))
    full = norm(" | ".join([title, product.get("product_type") or "", " | ".join(tags),
                            labelled]))
    title_n = norm(title)
    desc = norm(_clean_description(product.get("body_html", "")))
    prior = brand_prior(site.get("name"), product.get("vendor"), rules)
    if attrs.get("department") in ("footwear", "accessories"):
        return _accessory_style(attrs, rules, full, norm(title), desc, prior)
    scores, hits = score_styles(full, desc, prior, attrs.get("color"),
                                attrs.get("color_name"), attrs.get("fabrics"), rules)

    cue = rules["cues"]
    cat = attrs.get("category")
    printed = _any(cue["print"], full) or attrs.get("pattern") in (
        "graphic", "floral", "camouflage", "tie dye")
    embellished = _any(cue["embellishment"], full) or attrs.get("pattern") == "embroidered"
    neutral = attrs.get("color") in (None, *rules["neutral_colors"])
    fusion = _any(cue["fusion"], title_n)

    # "Not minimalist: anything printed, graphic, embroidered or embellished"
    if _any(cue["print"], title_n) or _any(cue["embellishment"], title_n):
        scores["minimalist"] = min(scores["minimalist"], 0)
    indian_word = _any(("kurta", "kurtas", "sherwani", "dhoti", "pathani", "nehru", "bandi",
                        "bundi", "bandhgala", "jodhpuri", "churidar", "pyjama", "angrakha",
                        "lungi", "mundu", "veshti"), title_n)
    forced, adds, removes = None, [], set()

    def best(cands):
        return sorted(cands, key=lambda s: (-scores[s], rules["tie_order"].index(s)))[0]

    # --- section 3 conflict rules, most specific first -------------------
    if cat == "sherwani" or _hit("sherwani", title_n):
        adds += ["traditional", "glam"]
        forced = "glam" if embellished else "traditional"
        if fusion:
            adds.append("ethnic_fusion")
    elif cat == "kurta_set" and _any(("jacket", "bundi", "bandi", "waistcoat", "koti", "nehru",
                                       "jodhpuri", "bandhgala", "3 piece", "three piece"),
                                      title_n):
        # kurta + jacket sets and jodhpuri / bandhgala suits are the taxonomy's
        # typical Indo-western garments
        forced = "ethnic_fusion"
        adds.append("traditional")
    elif cat == "ethnic_jacket" or _any(("nehru jacket", "bandhgala", "bandi", "modi jacket",
                                         "jodhpuri"), title_n):
        adds += ["traditional", "ethnic_fusion"]
        forced = "ethnic_fusion" if fusion else "glam" if embellished else "traditional"
    elif fusion:
        forced = "ethnic_fusion"
        removes.add("traditional")
    elif cat in INDIAN:
        if cat in ("kurta", "kurta_set") and _any(cue["western_garment"], title_n):
            adds.append("ethnic_fusion")
        # an Indian garment is always primarily traditional, fusion or glam
        forced = best(("traditional", "ethnic_fusion", "glam"))
        if scores[forced] < 3 and forced != "traditional":
            forced = "traditional"
        if not printed and not embellished and "minimalist" in prior:
            adds.append("minimalist")
    elif _any(cue["boho_signature"], title_n) or (
            cat == "shirt" and printed and "linen" in (attrs.get("fabrics") or ())
            and scores["boho"] >= 3):
        forced = "boho"
    elif ("sporty" in prior and "streetwear" not in prior
          and (attrs.get("fit") == "oversized" or attrs.get("pattern") == "graphic"
               or _any(("oversized", "graphic"), full) or _any(cue["street_bottom"], title_n))):
        forced = "streetwear"
        adds.append("sporty")
    elif cat == "joggers":
        forced = "sporty"
        if _any(cue["street_bottom"], full):
            adds.append("streetwear")
    elif cat in ("hoodie", "sweatshirt") and not printed:
        if _any(cue["sport"], full):
            forced = "sporty"
        elif "minimalist" in prior and (_any(("plain", "solid", "basic", "essential"), full)
                                        or "streetwear" not in prior):
            forced = "minimalist"
        else:
            forced = "streetwear"
    if (forced is None and cat not in INDIAN and not indian_word and scores["traditional"] >= 3
            and max(STYLES, key=lambda s: (scores[s], -rules["tie_order"].index(s)))
            == "traditional"):
        # a Western cut that the store files under ethnic wear = Indo-western
        forced = "ethnic_fusion"
        adds.append("traditional")
    if embellished and "glam" not in adds:
        adds.append("glam")
    plain = not printed and not embellished
    if (plain and neutral and cat in TAILORED and forced is None
            and not _any(("oversized", "baggy", "cargo", "boxy"), full)):
        adds.append("classic")

    # --- section 5.3 selection ---------------------------------------------
    t = rules["thresholds"]
    top = max(scores.values())
    ranked = sorted(STYLES, key=lambda s: (-scores[s], rules["tie_order"].index(s)))
    keep = [s for s in ranked if top >= t["min_score"]
            and scores[s] >= max(t["min_score"], t["relative"] * top) and s not in removes]
    fallback = False
    if forced:
        primary = forced
    elif keep:
        primary = keep[0]
    else:  # 5.4 fallbacks
        fallback = True
        if plain and neutral and cat in TAILORED:
            primary = "classic"
        elif plain and neutral and cat not in INDIAN:
            primary = "minimalist"
        elif cat in INDIAN:
            primary = "traditional"
        elif adds:
            primary = adds[0]
        else:
            primary = UNCLASSIFIED
    tags_out = [primary]
    for s in adds + keep:
        if s not in tags_out and s not in removes and primary != UNCLASSIFIED:
            tags_out.append(s)
    tags_out = tags_out[: t["max_tags"]]

    gap = scores.get(primary, 0) - max(v for k, v in scores.items() if k != primary)
    if fallback or primary == UNCLASSIFIED:
        conf = "low"
    elif scores.get(primary, 0) >= 6 and gap >= 2:
        conf = "high"
    elif scores.get(primary, 0) >= 3:
        conf = "medium"
    else:
        conf = "low"
    return {
        "primary_style": primary,
        "style_tags": tags_out,
        "style_scores": scores,
        "style_confidence": conf,
        "style_source": "rules",
        "style_hits": sorted({p for s, p, _ in hits if s == primary and p[0] != "-"}),
    }


ACC_CLASSIC_DEFAULT = {"belt", "wallet", "tie", "watch", "sunglasses"}


def _select(scores, rules, forced=None, adds=(), fallback=None):
    """Section 5.3 selection for the accessory path."""
    t = rules["thresholds"]
    top = max(scores.values())
    ranked = sorted(rules.get("style_ids") or STYLES,
                    key=lambda s: (-scores[s], rules["tie_order"].index(s)))
    keep = [s for s in ranked if top >= t["min_score"]
            and scores[s] >= max(t["min_score"], t["relative"] * top)]
    is_fallback = False
    if forced:
        primary = forced
    elif keep:
        primary = keep[0]
    else:
        is_fallback, primary = True, fallback or UNCLASSIFIED
    tags = [primary]
    for s in list(adds) + keep:
        if s not in tags and primary != UNCLASSIFIED:
            tags.append(s)
    gap = scores.get(primary, 0) - max(v for k, v in scores.items() if k != primary)
    if is_fallback or primary == UNCLASSIFIED:
        conf = "low"
    elif scores.get(primary, 0) >= 6 and gap >= 2:
        conf = "high"
    elif scores.get(primary, 0) >= 3:
        conf = "medium"
    else:
        conf = "low"
    return primary, tags[: t["max_tags"]], conf


def _accessory_style(attrs, rules, full, title_n, desc, prior):
    """Styles for footwear and accessories: their own keyword lists, the same
    priors and thresholds, plus category rules (ethnic footwear, safas and
    stoles are traditional, sports shoes sporty, formal shoes classic; plain
    neutral belts / wallets / ties / watches fall back to classic)."""
    scores, hits = score_styles(full, desc, prior, attrs.get("color"), attrs.get("color_name"),
                                attrs.get("fabrics"), rules, block="accessory_styles")
    cat = attrs.get("category")
    types = set(attrs.get("wear_types") or [])
    cue = rules["cues"]
    embellished = _any(cue["embellishment"], full)
    printed = _any(cue["print"], title_n)
    neutral = attrs.get("color") in (None, *rules["neutral_colors"], "brown")
    # mojaris and stoles are usually embroidered: only heavy work makes them glam
    heavy = _any(("sequin", "sequinned", "zari", "zardozi", "stone work", "velvet", "beaded",
                  "mirror work", "kalangi", "groom", "wedding", "diamante"), full)
    if not (embellished or heavy or _any(("metallic", "gold", "gold plated", "velvet", "patent",
                                          "rhinestone", "crystal", "pearl"), title_n)):
        scores["glam"] = min(scores["glam"], 2)  # store "wedding" tags alone are not glam
    forced, adds = None, []
    if cat in ("ethnic_footwear", "ethnic_accessory") or "stole" in types:
        forced = "glam" if heavy or "kalangi" in types else "traditional"
        adds.append("traditional")
        if _any(cue["fusion"], title_n):
            forced = "ethnic_fusion"
    elif "sports shoes" in types or (cat == "shoes" and _any(cue["sport"], full)):
        forced = "sporty"
    elif "formal shoes" in types or "loafers" in types:
        forced = "glam" if embellished else "classic"
    if embellished and forced != "glam":
        adds.append("glam")
    fallback = None
    if not printed and not embellished and neutral:
        fallback = "classic" if cat in ACC_CLASSIC_DEFAULT or "leather" in types else "minimalist"
    primary, tags, conf = _select(scores, rules, forced, adds, fallback)
    return {
        "primary_style": primary, "style_tags": tags, "style_scores": scores,
        "style_confidence": conf, "style_source": "rules",
        "style_hits": sorted({p for s, p, _ in hits if s == primary and p[0] != "-"}),
    }


# ==========================================================================
# women's catalogue (style_taxonomy_women.md): same scoring engine and
# selection, the women's rule file, nine styles (adds edgy) and the
# women's section 3 conflict rules
# ==========================================================================

W_INDIAN = {"kurta", "kurta_set", "saree", "lehenga", "ethnic_bottom", "ethnic_jacket", "blouse"}
W_TAILORED = {"blazer", "trousers", "shirt"}
W_WESTERN = {"tshirt", "shirt", "top", "sweatshirt", "hoodie", "sweater", "jacket", "shrug",
             "blazer", "jeans", "trousers", "leggings", "joggers", "shorts", "skirt", "dress",
             "gown", "jumpsuit", "coord_set"}
W_PRINTED_PATTERNS = ("graphic", "printed", "floral", "ethnic print", "animal print",
                      "polka dot", "tie dye", "camouflage", "striped", "checked")


def _confidence(scores, primary, fallback):
    gap = scores.get(primary, 0) - max(v for k, v in scores.items() if k != primary)
    if fallback or primary == UNCLASSIFIED:
        return "low"
    if scores.get(primary, 0) >= 6 and gap >= 2:
        return "high"
    if scores.get(primary, 0) >= 3:
        return "medium"
    return "low"


def classify_style_women(product: dict, attrs: dict, site: dict) -> dict:
    rules = rules_for("women")
    styles = rules["style_ids"]
    title = product.get("title") or ""
    ptype = product.get("product_type") or ""
    tags = split_tags(product.get("tags"))
    specs = parse_specs(product.get("body_html", ""))
    labelled = " ".join(specs.get(k) or "" for k in ("pattern", "fit", "occasion"))
    full = norm(" | ".join([title, ptype, " | ".join(tags), labelled]))
    title_n = norm(title)
    tt = norm(f"{title} | {ptype}")  # title + product type: no store-wide tags
    desc = norm(_clean_description(product.get("body_html", "")))
    prior = brand_prior(site.get("name"), product.get("vendor"), rules)
    if attrs.get("department") in ("footwear", "accessories"):
        return _accessory_style_women(attrs, rules, full, tt, desc, prior)
    scores, hits = score_styles(full, desc, prior, attrs.get("color"),
                                attrs.get("color_name"), attrs.get("fabrics"), rules)
    # edgy needs a hard cue: one strong keyword or two medium ones in the
    # title / type / tags ("dark pink" or one "chain" alone is not edgy)
    e = rules["styles"]["edgy"]
    e_hits = {p for s_, p, w in hits if s_ == "edgy" and w == "text"}
    if not (e_hits & set(e["strong"])) and len(e_hits & set(e["medium"])) < 2:
        scores["edgy"] = min(scores["edgy"], 2)
    cue = rules["cues"]
    cat = attrs.get("category")
    wear = set(attrs.get("wear_types") or ())
    pattern = attrs.get("pattern")
    printed = _any(cue["print"], tt) or pattern in W_PRINTED_PATTERNS
    embellished = _any(cue["embellishment"], tt) or pattern in ("embroidered", "embellished")
    neutral = attrs.get("color") in (None, *rules["neutral_colors"])
    fusion = _any(cue["fusion"], tt)
    glam_cue = _any(cue["glam_strong"], tt)

    # "Not minimalist: anything printed, graphic, embroidered or embellished"
    if _any(cue["print"], title_n) or _any(cue["embellishment"], title_n):
        scores["minimalist"] = min(scores["minimalist"], 0)
    forced, adds, removes = None, [], set()

    def best(cands):
        return sorted(cands, key=lambda s: (-scores[s], rules["tie_order"].index(s)))[0]

    def indian_primary():
        f = best(("traditional", "ethnic_fusion", "glam"))
        return f if scores[f] >= 3 or f == "traditional" else "traditional"

    sharara = _any(("sharara", "shararas", "gharara", "ghararas"), tt)
    # --- section 3 conflict rules, most specific first -------------------------
    if cat == "saree":
        if _any(cue["saree_fusion"], tt) or fusion:
            forced = "ethnic_fusion"
            adds.append("traditional")
        elif glam_cue:  # "Embellished Sequin Saree" (taxonomy test 8)
            forced = "glam"
            adds.append("traditional")
        else:
            forced = "traditional"
            if embellished:
                adds.append("glam")
    elif cat == "lehenga" or (sharara and cat in ("kurta_set", "coord_set", "ethnic_bottom")):
        adds += ["traditional", "glam"]
        forced = "glam" if glam_cue else "traditional"
        if _any(cue["lehenga_fusion"], tt):
            adds.append("ethnic_fusion")
        if fusion:
            forced = "ethnic_fusion"
    elif fusion:
        forced = "ethnic_fusion"
        if cat in W_INDIAN:
            adds.append("traditional")
        else:
            removes.add("traditional")
    elif cat == "gown" and _any(cue["indian_gown"], tt):
        forced = "glam"
        adds.append("ethnic_fusion")
    elif cat in ("kurta", "kurta_set"):
        western = _any(cue["western_garment"], tt)
        if western:
            adds.append("ethnic_fusion")
            forced = indian_primary()
        elif cat == "kurta_set" and _any(cue["set_bottom"], tt):
            forced = "traditional"
        else:
            forced = indian_primary()
        if not printed and not embellished and "minimalist" in prior:
            adds.append("minimalist")
    elif cat in W_INDIAN:
        forced = indian_primary()
    elif cat == "leggings" and "traditional" in prior and not (
            _any(cue["sport"], full) or "sporty" in prior):
        # plain cotton leggings from an ethnic-wear store are churidar leggings worn
        # under kurtas, not activewear
        scores["sporty"] = min(scores["sporty"], 2)
        forced = "traditional"
    elif (cat == "leggings"
          or "sports bra" in wear or _any(("yoga", "gym", "sports bra", "workout"), tt)):
        # (plain cotton leggings from an ethnic-wear store go under kurtas: not sporty)
        forced = "sporty"
        if _any(("oversized", "baggy", "graphic"), tt):
            adds.append("streetwear")
    elif cat == "joggers" or _any(("track pants", "trackpants", "jogger", "joggers"), tt):
        forced = "sporty"
        if _any(cue["street_bottom"], tt):
            adds.append("streetwear")
    elif cat in ("hoodie", "sweatshirt") and not (printed or pattern == "graphic"):
        if _any(cue["sport"], full):
            forced = "sporty"
        elif "minimalist" in prior and (_any(("plain", "solid", "basic", "essential"), tt)
                                        or "streetwear" not in prior):
            forced = "minimalist"
        else:
            forced = "streetwear"
    if forced is None and cat in W_WESTERN:
        shine, hard = _any(cue["shine"], tt), _any(cue["hard"], tt)
        streety = (_any(("oversized", "graphic", "hoodie", "baggy"), tt) or cat == "hoodie"
                   or pattern == "graphic")
        if shine and hard:
            adds += ["glam", "edgy"]
            forced = "edgy" if scores["edgy"] > scores["glam"] else "glam"
        elif streety and _any(cue["edgy_street"], tt):
            forced = "streetwear"
            adds.append("edgy")
        elif attrs.get("color") == "black" and hard:
            forced = "edgy"
        elif (cat in ("dress", "skirt", "jumpsuit", "coord_set", "top", "shirt")
              and _any(cue["boho_western_indian"], tt)):
            forced = "boho"  # block-print / ikat in a Western cut: boho, not traditional
        elif (cat in ("dress", "skirt") or "kaftan" in wear) and not glam_cue and not (
                _any(cue["party_silhouette"], tt)) and (
                _any(cue["boho_dress"], tt) and (
                    not _any(("printed", "print"), tt) or _any(("maxi", "flowy", "tiered",
                                                                  "midi", "wrap", "kaftan"), tt)
                    or _any([c for c in cue["boho_dress"] if c not in ("printed",)], tt))):
            forced = "boho"
        if (cat in ("dress", "gown", "jumpsuit") or _any(("corset", "bustier"), tt)) and \
                _any(cue["party_silhouette"], tt) and "glam" not in adds:
            adds.append("glam")  # corset / cut-out / bodycon party silhouettes
    if (forced is None and cat in W_WESTERN and scores["traditional"] >= 3
            and max(styles, key=lambda s: (scores[s], -rules["tie_order"].index(s)))
            == "traditional"):
        # a Western cut in an Indian craft textile = Indo-western
        forced = "ethnic_fusion"
        adds.append("traditional")
    if embellished and "glam" not in adds and forced != "glam":
        adds.append("glam")
    plain = not printed and not embellished
    tailored = cat in W_TAILORED or "shirt dress" in wear
    if (plain and neutral and tailored and forced is None
            and not _any(("oversized", "baggy", "cargo", "boxy", "cropped", "crop"), tt)):
        adds.append("classic")

    # --- section 5.3 selection -----------------------------------------------
    t = rules["thresholds"]
    top = max(scores.values())
    ranked = sorted(styles, key=lambda s: (-scores[s], rules["tie_order"].index(s)))
    keep = [s for s in ranked if top >= t["min_score"]
            and scores[s] >= max(t["min_score"], t["relative"] * top) and s not in removes]
    fallback = False
    if forced:
        primary = forced
    elif keep:
        primary = keep[0]
    else:  # 5.4 fallbacks
        fallback = True
        if plain and neutral and tailored:
            primary = "classic"
        elif plain and neutral and cat not in W_INDIAN:
            primary = "minimalist"
        elif cat in W_INDIAN:
            primary = "traditional"
        elif adds:
            primary = adds[0]
        else:
            primary = UNCLASSIFIED
    tags_out = [primary]
    for s in adds + keep:
        if s not in tags_out and s not in removes and primary != UNCLASSIFIED:
            tags_out.append(s)
    tags_out = tags_out[: t["max_tags"]]
    return {
        "primary_style": primary, "style_tags": tags_out, "style_scores": scores,
        "style_confidence": _confidence(scores, primary, fallback), "style_source": "rules",
        "style_hits": sorted({p for s, p, _ in hits if s == primary and p[0] != "-"}),
    }


W_ACC_CLASSIC_DEFAULT = {"belt", "wallet", "watch", "sunglasses", "bag", "heels", "flats"}


def _accessory_style_women(attrs, rules, full, tt, desc, prior):
    """Women's footwear and accessories: own keyword lists plus category rules
    (juttis, kolhapuris, dupattas, jhumkas and potlis are traditional, kundan /
    bridal pieces glam, sports shoes sporty; plain neutral bags, belts, watches
    and heels fall back to classic)."""
    scores, hits = score_styles(full, desc, prior, attrs.get("color"), attrs.get("color_name"),
                                attrs.get("fabrics"), rules, block="accessory_styles")
    cat = attrs.get("category")
    types = set(attrs.get("wear_types") or [])
    cue = rules["cues"]
    embellished = _any(cue["embellishment"], tt)
    printed = _any(cue["print"], tt)
    neutral = attrs.get("color") in (None, *rules["neutral_colors"], "brown")
    heavy = _any(("sequin", "sequins", "sequinned", "zari", "zardozi", "stone work", "velvet",
                  "beaded", "mirror work", "kundan", "polki", "bridal", "wedding", "diamante",
                  "rhinestone", "rhinestones", "crystal", "crystals", "american diamond",
                  "cz", "swarovski", "embellished", "jadau", "glitter"), tt)
    if not (embellished or heavy or _any(("metallic", "gold plated", "velvet", "patent",
                                          "pearl", "pearls", "satin", "stiletto", "stilettos",
                                          "clutch", "potli", "party", "partywear",
                                          "cocktail", "statement", "shimmer"), tt)):
        scores["glam"] = min(scores["glam"], 2)  # store "wedding" tags alone are not glam
    forced, adds = None, []
    trad_jewel = types & {"jhumka", "maang tikka", "nose pin", "temple", "kundan", "oxidised"} \
        or _any(("jhumka", "jhumkas", "chandbali", "chandbalis", "kada", "payal", "payals",
                 "mangalsutra", "meenakari", "kamarbandh", "passa", "haath phool"), tt)
    if _any(cue["fusion"], tt):
        forced = "ethnic_fusion"
    elif cat == "ethnic_footwear" or "potli" in types or types & {"dupatta", "stole"}:
        forced = "glam" if heavy else "traditional"
        adds.append("traditional")
    elif cat == "jewellery" and trad_jewel:
        if heavy or "kundan" in types:
            forced = "glam"
            adds.append("traditional")
        else:
            forced = "traditional"
            if "oxidised" in types:
                adds.append("boho")
    elif "sports shoes" in types or (cat in ("shoes", "socks", "bag") and _any(
            ("running", "gym", "training", "sports", "yoga"), full)):
        forced = "sporty"
    elif cat == "clutch" or "stilettos" in types:
        forced = "glam" if (heavy or embellished or scores["glam"] >= 3) else None
    if embellished and forced != "glam":
        adds.append("glam")
    fallback = None
    if not printed and not embellished and neutral:
        fallback = "classic" if cat in W_ACC_CLASSIC_DEFAULT or "leather" in types \
            else "minimalist"
    primary, tags, conf = _select(scores, rules, forced, adds, fallback)
    return {
        "primary_style": primary, "style_tags": tags, "style_scores": scores,
        "style_confidence": conf, "style_source": "rules",
        "style_hits": sorted({p for s, p, _ in hits if s == primary and p[0] != "-"}),
    }

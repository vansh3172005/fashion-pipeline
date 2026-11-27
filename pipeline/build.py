"""Offline catalogue build: cached raw feeds -> balanced men's style catalogue.

Steps (style_taxonomy.md sections 8 and 11):
  1. classify every cached product (attributes + style);
  2. men's scope: keep gender "men"; keep unisex / unlabelled products only if
     the store is men-only or the product sits in one of the site's men's
     collections; everything dropped is counted by reason;
  3. remove exact duplicates (same title + same photo file across sites) and
     near-duplicates (same title + same colour within one site);
  4. balance: about ``per_style`` items per primary style, no site above
     ``site_cap`` of the catalogue, unclassified items left out (they are
     reported, not hidden).
"""
import re
from collections import Counter, defaultdict

from .classify import classify_product, norm
from .scrape import ShopifyAdapter, load_raw, to_item
from .style import STYLES, UNCLASSIFIED

CONF_RANK = {"high": 0, "medium": 1, "low": 2}
KIDS_SIZE = re.compile(r"(?i)\b(\d+\s*-\s*\d+\s*(yrs?|years?|y|months?|m)\b|\d+\s*(yrs?|years?|months?)\b|"
                       r"\bkids?\b|\bboys?\b|\binfant)")


# women's footwear / accessories that carry no gender word
WOMEN_ACCESSORY = re.compile(
    r" (heels|high heel|wedges|pumps|stilettos?|ballerinas?|bellies|mary janes|kitten|handbags?|"
    r"clutch(es)?|bangles?|anklets?|payals?|nose ?pins?|maang|tikka|jhumkas?|bindis?|"
    r"scrunchies?|hair (clips?|bands?|ties?)|hairbands?|kurtis?|sarees?|lehengas?|"
    r"mangalsutra|chokers?|potli|bra) ")


GARMENT_SET = re.compile(r" (kurtas?|sherwanis?|pants?|pyjamas?|pajamas?|jackets?|dhotis?|"
                         r"churidars?|trousers?|lungis?|sets?|bandi|bundi) ")


def site_pool(site: dict, raw: dict, accessories=False, catalogue="men"):
    """(items, dropped Counter) for one site's cached feed.

    ``accessories=False`` builds the garment pool (taxonomy section 8);
    ``accessories=True`` returns only footwear and accessories, with the same
    men's scope plus the site's men's accessory collections.
    ``catalogue="women"`` applies the women's taxonomy and scope instead."""
    if catalogue == "women":
        return _site_pool_women(site, raw, accessories)
    men_ids = set()
    for ids in (raw.get("men_collection_ids") or {}).values():
        men_ids.update(ids)
    if accessories:
        for ids in (raw.get("men_accessory_ids") or {}).values():
            men_ids.update(ids)
    men_only = site.get("default_gender") == "men"
    adapter = ShopifyAdapter(None)
    items, dropped = [], Counter()
    for p in raw["products"]:
        a = classify_product(p, site.get("price_bands"), default_gender=site.get("default_gender"),
                             site=site, include_accessories=accessories)
        if accessories and a and a["department"] not in ("footwear", "accessories"):
            continue  # garments are handled by the apparel pool
        if accessories and a and a["category"] in ("scarf", "ethnic_accessory") and GARMENT_SET.search(
                norm(p.get("title") or "")):
            dropped["garment set sold with a dupatta / safa (clothing, not an accessory)"] += 1
            continue
        if not a:
            if not accessories:
                dropped["not apparel / out of scope"] += 1
            continue
        g = a["gender"]
        explicit_men = g == "men" and a["attr_source"].get("gender") not in (None, "site default")
        if accessories and not explicit_men and WOMEN_ACCESSORY.search(
                norm(f"{p.get('title')} {p.get('product_type')}")):
            g = "women"
        if g == "women":
            dropped["women"] += 1
            continue
        if g != "men":
            in_men = p.get("id") in men_ids
            if not (in_men or men_only):
                dropped[f"{g} not in a men's collection"] += 1
                continue
            if g == "unspecified":
                a["gender"] = "men"
                a["attr_source"]["gender"] = "men's collection"
        if not a.get("price"):
            dropped["no price"] += 1
            continue
        if a["sizes"] and all(KIDS_SIZE.search(s) for s in a["sizes"]):
            dropped["kids (sold only in age sizes)"] += 1
            continue
        if a["sizes"] and any(KIDS_SIZE.search(s) for s in a["sizes"]):
            # father-and-son listings: keep the product, drop the kids' sizes
            a["sizes"] = [s for s in a["sizes"] if not KIDS_SIZE.search(s)]
            a["sizes_available"] = [s for s in a["sizes_available"] if not KIDS_SIZE.search(s)]
        it = to_item(site, adapter, p, a)
        if it is None:
            dropped["no image"] += 1
            continue
        items.append(it)
    return items, dropped


def _site_pool_women(site, raw, accessories):
    """Women's scope (style_taxonomy_women.md section 8): keep gender "women";
    unisex / unlabelled items only from a women-only store or one of the site's
    women's collections; men's, kids', lingerie and sleepwear are dropped."""
    women_ids = set()
    for ids in (raw.get("women_collection_ids") or {}).values():
        women_ids.update(ids)
    if accessories:
        for ids in (raw.get("women_accessory_ids") or {}).values():
            women_ids.update(ids)
    women_only = site.get("default_gender") == "women"
    adapter = ShopifyAdapter(None)
    items, dropped = [], Counter()
    for p in raw["products"]:
        a = classify_product(p, site.get("price_bands"), default_gender=site.get("default_gender"),
                             site=site, include_accessories=accessories, catalogue="women")
        if accessories and a and a["department"] not in ("footwear", "accessories"):
            continue  # garments are handled by the apparel pool
        if not a:
            if not accessories:
                dropped["not women's clothing / out of scope"] += 1
            continue
        g = a["gender"]
        if g == "men":
            dropped["men"] += 1
            continue
        if g != "women":
            if not (p.get("id") in women_ids or women_only):
                dropped[f"{g} not in a women's collection"] += 1
                continue
            a["attr_source"]["gender"] = ("women's collection" if p.get("id") in women_ids
                                          else "site default")
            a["gender"] = "women" if g == "unspecified" else g
        if not a.get("price"):
            dropped["no price"] += 1
            continue
        if a["sizes"] and all(KIDS_SIZE.search(s) for s in a["sizes"]):
            dropped["kids (sold only in age sizes)"] += 1
            continue
        if a["sizes"] and any(KIDS_SIZE.search(s) for s in a["sizes"]):
            # mother-and-daughter listings: keep the product, drop the kids' sizes
            a["sizes"] = [s for s in a["sizes"] if not KIDS_SIZE.search(s)]
            a["sizes_available"] = [s for s in a["sizes_available"] if not KIDS_SIZE.search(s)]
        it = to_item(site, adapter, p, a)
        if it is None:
            dropped["no image"] += 1
            continue
        it["catalogue_gender"] = "women"
        items.append(it)
    return items, dropped


def _photo_key(url: str) -> str:
    """Photo file name without CDN size suffix / version query."""
    name = (url or "").split("?")[0].rsplit("/", 1)[-1].lower()
    name = re.sub(r"_(\d+x\d*|\d*x\d+)(?=\.)", "", name)
    return re.sub(r"_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "", name)


def dedupe(items):
    """Return (kept, Counter of reasons)."""
    seen_exact, seen_colour, kept, why = set(), set(), [], Counter()
    for it in items:
        t = norm(it["title"]).strip()
        k1 = (t, _photo_key(it["image"]))
        k2 = (it["site"], t, it.get("color_name") or it.get("color"))
        if k1 in seen_exact:
            why["exact duplicate (title + photo)"] += 1
            continue
        if k2 in seen_colour:
            why["same title + colour on one site"] += 1
            continue
        seen_exact.add(k1)
        seen_colour.add(k2)
        kept.append(it)
    return kept, why


def balance(items, per_style=1875, site_cap=0.12, total=(13000, 15000), max_style=2400,
            styles=STYLES):
    """Pick the catalogue. Thin styles are filled first so the site cap does
    not starve them; within a style items are taken round-robin over sites and
    categories, high-confidence first. If the catalogue is below ``total[0]``
    the large styles are topped up (never past ``max_style``) - items are never
    relabelled to fill a thin style."""
    by_style = defaultdict(list)
    for it in items:
        by_style[it["primary_style"]].append(it)
    cap = int(site_cap * total[1])
    site_n, picked, chosen = Counter(), defaultdict(list), set()

    def queue(style):
        groups = defaultdict(list)
        for it in sorted(by_style[style], key=lambda i: (CONF_RANK[i["style_confidence"]],
                                                         -max(i["style_scores"].values()),
                                                         i["id"])):
            groups[(it["site"], it["category"])].append(it)
        # round-robin across sites, and across each site's categories
        sites = defaultdict(list)
        for (s, _c), g in groups.items():
            sites[s].append(g)
        tiers, rnd = {"high": [], "medium": [], "low": []}, 0
        while any(any(g) for gs in sites.values() for g in gs):
            for s in sorted(sites):
                gs = [g for g in sites[s] if g]
                if gs:
                    it = gs[rnd % len(gs)].pop(0)
                    tiers[it["style_confidence"]].append(it)
            rnd += 1
        # clearest examples first (still spread over sites within a tier);
        # medium and low confidence only when a style needs them
        return tiers["high"] + tiers["medium"] + tiers["low"]

    queues = {s: queue(s) for s in styles}

    def fill(style, limit):
        for it in queues[style]:
            if len(picked[style]) >= limit:
                return
            if it["id"] in chosen or site_n[it["site"]] >= cap:
                continue
            picked[style].append(it)
            chosen.add(it["id"])
            site_n[it["site"]] += 1

    for s in sorted(styles, key=lambda s: len(queues[s])):  # thin styles first
        fill(s, per_style)
    n = sum(len(v) for v in picked.values())
    if n < total[0]:  # top up evenly from the styles that still have stock
        lim = per_style
        while n < total[0] and lim < max_style:
            lim += 25
            for s in styles:
                fill(s, lim)
            n = sum(len(v) for v in picked.values())
    out = [it for s in styles for it in picked[s]]
    return out, {"per_style": {s: len(picked[s]) for s in styles},
                 "pool_per_style": {s: len(by_style[s]) for s in (*styles, UNCLASSIFIED)},
                 "per_site": dict(site_n.most_common()), "site_cap": cap}

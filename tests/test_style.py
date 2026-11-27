"""Style taxonomy tests (style_taxonomy.md section 9) plus scope, dedupe,
balance and sketch tests for the multi-site men's catalogue."""
import re

import pytest

from pipeline.build import balance, dedupe, site_pool
from pipeline.classify import classify_product
from pipeline.sketch import render_svg, sketch_path
from pipeline.style import STYLES, classify_style, load_rules


def style_of(title, site=None, tags=(), body="", vendor=None):
    p = {"id": 1, "title": title, "tags": list(tags), "body_html": body, "vendor": vendor,
         "variants": [{"price": "999", "available": True}],
         "images": [{"src": "https://x.example/a.jpg"}]}
    return classify_product(p, site={"name": site} if site else None)


# section 9 table: (title, site, expected primary, expected also-contains)
CASES = [
    ("Men's Oversized Graphic Tee", "snitch", "streetwear", []),
    ("Plain Black Cotton T-Shirt", None, "minimalist", []),
    ("Oxford Button Down Shirt - Blue", None, "classic", []),
    ("Slim Fit Chinos - Khaki", None, "classic", []),
    ("Black Dry Fit Training Joggers", None, "sporty", []),
    ("Oversized Cargo Joggers", None, "sporty", ["streetwear"]),
    ("Embroidered Silk Sherwani with Churidar", None, "glam", ["traditional"]),
    ("Cotton Kurta Pyjama Set - White", None, "traditional", []),
    ("Indo Western Jacket Kurta Set", None, "ethnic_fusion", []),
    ("Block Print Linen Camp Collar Shirt", None, "boho", []),
    ("Linen Kaftan Shirt - Mint", None, "boho", []),
    ("Nehru Jacket - Navy", None, "traditional", ["ethnic_fusion"]),
    ("Velvet Bandhgala Jacket", None, "glam", ["traditional"]),
    ("Hand Block Printed Cotton Kurta", None, "traditional", ["boho"]),
    ("Pullover Hoodie, Heather Grey, Fleece", None, "streetwear", []),
    ("Pullover Hoodie, Plain", "saphed", "minimalist", []),
    ("Tie Dye Oversized T-Shirt", None, "boho", ["streetwear"]),
    ("Chikankari Kurta - Ivory", None, "traditional", []),
    ("Men's Solid Band Collar Linen Shirt", "saphed", "minimalist", ["classic"]),
]


@pytest.mark.parametrize("title,site,primary,also", CASES)
def test_taxonomy_cases(title, site, primary, also):
    a = style_of(title, site)
    assert a["primary_style"] == primary, (a["style_scores"], a["style_tags"])
    assert set(also) <= set(a["style_tags"])
    assert a["style_tags"][0] == primary
    assert a["style_source"] == "rules"


@pytest.mark.parametrize("title", ["Water Bottle", "Gift Card", "Batik Pocket Squares (Set of 3)",
                                   "Women's Anarkali Kurta Set"])
def test_out_of_scope_not_classified(title):
    a = style_of(title)
    assert a is None or a["gender"] == "women"


def test_deterministic_and_max_three_tags():
    a = style_of("Embroidered Velvet Indo Western Sherwani Set", "kisah")
    b = style_of("Embroidered Velvet Indo Western Sherwani Set", "kisah")
    assert a["style_tags"] == b["style_tags"] and a["style_scores"] == b["style_scores"]
    assert 1 <= len(a["style_tags"]) <= 3
    assert set(a["style_scores"]) == set(STYLES)
    assert a["style_confidence"] in ("high", "medium", "low")


def test_description_hits_half_weight_and_capped():
    rules = load_rules()
    many_boho = "<p>" + " ".join(rules["styles"]["boho"]["strong"]) + "</p>"
    a = style_of("Shirt", body=many_boho)
    # every strong boho phrase is only in the description: 3 // 2 = 1 each, capped at +3
    assert a["style_scores"]["boho"] == 3


def test_description_pairing_advice_ignored():
    # "pair it with chinos and a blazer" must not make a tee classic
    a = style_of("Regular Fit T-Shirt", body="<p>Pair it with chinos, trousers and a blazer.</p>")
    assert a["style_scores"]["classic"] <= 2


def test_weak_signals_alone_capped():
    # linen + earthy colour + "relaxed" are weak boho signals: no boho without a real cue
    a = style_of("Rust Relaxed Linen Shirt")
    assert a["style_scores"]["boho"] <= 2 and a["primary_style"] != "boho"


def test_minimalist_never_printed():
    a = style_of("Plain Essential Printed Shirt - Black")
    assert a["primary_style"] != "minimalist"


def test_conflict_fusion_removes_traditional():
    a = style_of("Indo Western Kurta Set with Churidar")
    assert a["primary_style"] == "ethnic_fusion" and "traditional" not in a["style_tags"]


def test_conflict_kurta_with_western_word_adds_fusion():
    a = style_of("Denim Kurta")
    assert a["primary_style"] == "traditional" and "ethnic_fusion" in a["style_tags"]


def test_conflict_embellished_adds_glam():
    a = style_of("Sequin Embroidered Oversized Shirt", "snitch")
    assert "glam" in a["style_tags"]


def test_conflict_activewear_brand_oversized_is_streetwear():
    a = style_of("Oversized Gym T-Shirt", "fuaark")
    assert a["primary_style"] == "streetwear" and "sporty" in a["style_tags"]


def test_conflict_kurta_jacket_set_is_fusion():
    a = style_of("Kurta Pyjama Set with Nehru Jacket")
    assert a["primary_style"] == "ethnic_fusion" and "traditional" in a["style_tags"]


def test_store_ethnic_label_on_western_shirt_is_fusion():
    a = style_of("Cotton Printed Cuban Shirt", tags=["Men's Ethnic Shirt", "Men Ethnic Wear"])
    assert a["primary_style"] == "ethnic_fusion"


def test_fallbacks():
    assert style_of("Regular Shirt - White")["primary_style"] == "classic"
    assert style_of("Crew Neck T-Shirt - Grey")["primary_style"] == "minimalist"
    assert style_of("Kurta - Maroon")["primary_style"] == "traditional"
    assert style_of("Zebra Shirt - Pink Yellow")["style_confidence"] == "low"


def test_brand_prior_by_vendor():
    a = style_of("Heavy Hoodie", vendor="Pleasures")
    assert a["style_scores"]["streetwear"] >= 4


def test_wear_types():
    a = style_of("Oversized Cargo Joggers")
    assert {"oversized", "cargo", "joggers"} <= set(a["wear_types"])


def test_ethnic_categories():
    assert style_of("Cotton Kurta Pyjama Set")["category"] == "kurta_set"
    assert style_of("Silk Sherwani")["category"] == "sherwani"
    assert style_of("Nehru Jacket")["category"] == "ethnic_jacket"
    assert style_of("Short Kurta")["category"] == "kurta"
    assert style_of("Benarasi Short Jacket")["category"] == "jacket"
    assert style_of("Short Sleeve Linen Shirt")["category"] == "shirt"
    assert style_of("Dress Cuff Oxford Shirt")["category"] == "shirt"
    assert style_of("Art Silk Dhoti")["category"] == "dhoti"


# ---------------------------------------------------------------------------
# men's scope (section 8), dedupe and balancing (section 11)
# ---------------------------------------------------------------------------


def _p(pid, title, tags=()):
    return {"id": pid, "title": title, "tags": list(tags), "handle": f"h{pid}",
            "variants": [{"price": "1299", "available": True}],
            "images": [{"src": f"https://cdn.example/files/p{pid}.jpg?v=1"}]}


def test_mens_scope():
    raw = {"products": [_p(1, "Oxford Shirt", ["Men"]), _p(2, "Oxford Shirt Blue", ["Women"]),
                        _p(3, "Linen Shirt"), _p(4, "Linen Shirt Green"),
                        _p(5, "Unisex Hoodie", ["Unisex"])],
           "men_collection_ids": {"men": [4, 5]}}
    site = {"name": "mixed", "base_url": "https://m.example"}
    items, dropped = site_pool(site, raw)
    assert sorted(int(i["id"].split(":")[1]) for i in items) == [1, 4, 5]
    assert dropped["women"] == 1 and dropped["unspecified not in a men's collection"] == 1
    four = next(i for i in items if i["id"].endswith(":4"))
    assert four["gender"] == "men" and four["attr_source"]["gender"] == "men's collection"
    # a men-only store keeps unlabelled products
    items2, _ = site_pool({**site, "default_gender": "men"}, {"products": [_p(3, "Linen Shirt")]})
    assert len(items2) == 1


def test_dedupe():
    a = {"site": "a", "title": "Black Tee", "image": "https://c/x/p1_600x.jpg", "color": "black"}
    b = {"site": "b", "title": "Black Tee", "image": "https://d/y/p1.jpg?v=2", "color": "black"}
    c = {"site": "a", "title": "Black Tee", "image": "https://c/x/p9.jpg", "color": "black"}
    d = {"site": "a", "title": "Black Tee", "image": "https://c/x/p8.jpg", "color": "white"}
    kept, why = dedupe([a, b, c, d])
    assert kept == [a, d] and sum(why.values()) == 2


def _item(i, style, site, conf="high"):
    return {"id": f"{site}:{i}", "site": site, "category": "shirt", "primary_style": style,
            "style_confidence": conf, "style_scores": {s: 0 for s in STYLES} | {style: 6}}


def test_balance_caps_and_order():
    items = [_item(i, "classic", f"s{i % 3}") for i in range(300)]
    items += [_item(1000 + i, "boho", "s0", "low" if i % 2 else "high") for i in range(20)]
    cat, rep = balance(items, per_style=50, site_cap=0.5, total=(10, 100), max_style=60)
    assert rep["per_style"]["classic"] == 50 and rep["per_style"]["boho"] == 20
    assert max(rep["per_site"].values()) <= 50
    # classic is spread over the three sites
    assert len({i["site"] for i in cat if i["primary_style"] == "classic"}) == 3
    boho = [i for i in cat if i["primary_style"] == "boho"]
    assert [i["style_confidence"] for i in boho][:10] == ["high"] * 10  # low confidence last


# ---------------------------------------------------------------------------
# flat sketches
# ---------------------------------------------------------------------------

SKETCH_CASES = ["Oversized Graphic Tee - Black", "Striped Oxford Shirt", "Cargo Joggers",
                "Kurta Pyjama Set with Nehru Jacket", "Embroidered Sherwani", "Zip Hoodie",
                "Slim Fit Jeans", "Checked Shorts", "Linen Co-ord Set", "Gym Tank Top",
                "Velvet Blazer", "Art Silk Dhoti", "Polo T-Shirt"]


@pytest.mark.parametrize("title", SKETCH_CASES)
def test_sketch_renders_front_and_back(title):
    it = style_of(title)
    it.update(id="site:123", title=title)
    svg = render_svg(it)
    assert svg.startswith("<svg") and svg.endswith("</svg>")
    assert svg.count(') scale(') == 2  # front + back views
    assert "nan" not in svg and "<script" not in svg
    assert re.search(r'fill="#[0-9a-f]{6}"', svg)


def test_sketch_follows_colour_and_path():
    it = style_of("Olive Overshirt")
    it.update(id="snitch:9/9", title="Olive Overshirt", color_name="Olive")
    assert "#6f6e3c" in render_svg(it)
    assert sketch_path(it) == "sketch/snitch/9_9.svg"


def test_classify_style_without_site():
    a = classify_style({"title": "Plain Tee"}, {"category": "tshirt", "color": "white"}, None)
    assert a["primary_style"] in STYLES


# ---------------------------------------------------------------------------
# end to end: fetch -> build against the offline mock stores
# ---------------------------------------------------------------------------


def test_end_to_end_fetch_build(tmp_path):
    import json

    from pipeline import run, store
    from tests import mock_shops

    servers = mock_shops.start()
    saved = (run.DB, run.WEB, run.OUT, run.RAW, run.REPORT)
    try:
        cfg = tmp_path / "sites.json"
        cfg.write_text(json.dumps(mock_shops.sites_config()))
        run.DB, run.WEB = tmp_path / "c.db", tmp_path / "web"
        run.OUT, run.RAW, run.REPORT = run.WEB / "catalogue.json", tmp_path / "raw", \
            tmp_path / "report.md"
        run.main(["scrape", "--sites", str(cfg), "--delay", "0", "--per-style", "40",
                  "--min-total", "10", "--max-total", "400"])
        # shop02 answers 403 and shop03 is robots-blocked: no cache, nothing stored
        assert sorted(p.name for p in run.RAW.iterdir()) == ["shop01.json.gz", "shop04.json.gz"]
        data = json.loads(run.OUT.read_text(encoding="utf-8"))
        assert data and all(d["gender"] in ("men", "unisex") for d in data)
        assert all(d["primary_style"] != "unclassified" for d in data)
        for d in data:
            assert (run.WEB / d["sketch"]).read_text(encoding="utf-8").startswith("<svg")
        report = run.REPORT.read_text(encoding="utf-8")
        assert "Items per style" in report and "shop01" in report
        con = store.connect(run.DB)
        runs = {r["site"]: r["status"] for r in con.execute("SELECT * FROM scrape_runs")}
        con.close()
        assert runs["shop02"] == "error" and runs["shop01"] == "ok"
    finally:
        run.DB, run.WEB, run.OUT, run.RAW, run.REPORT = saved
        for s in servers:
            s.shutdown()


# ---------------------------------------------------------------------------
# footwear and accessories
# ---------------------------------------------------------------------------

ACC_CASES = [
    ("Black Leather Derby Shoes", "shoes", "classic"),
    ("White Chunky Sneakers", "shoes", "streetwear"),
    ("Running Shoes Mesh", "shoes", "sporty"),
    ("Embroidered Mojari", "ethnic_footwear", "traditional"),
    ("Velvet Zari Embellished Mojari", "ethnic_footwear", "glam"),
    ("Brown Kolhapuri Chappal", "ethnic_footwear", "traditional"),
    ("Grey Sliders", "sandals", None),
    ("Black Leather Belt", "belt", "classic"),
    ("Graphic Snapback Cap", "cap", "streetwear"),
    ("Macrame Jute Tote Bag", "bag", "boho"),
    ("Pack of 3 Ankle Socks", "socks", "sporty"),
    ("Navy Silk Tie", "tie", "classic"),
    ("Aviator Sunglasses", "sunglasses", "classic"),
    ("Printed Silk Stole", "scarf", "traditional"),
    ("Groom Safa with Kalangi", "ethnic_accessory", "glam"),
    ("Chronograph Watch", "watch", None),
    ("Silver Cuban Chain", "jewellery", None),
]


@pytest.mark.parametrize("title,cat,style", ACC_CASES)
def test_accessory_category_and_style(title, cat, style):
    a = classify_product({"title": title, "variants": [{"price": "999"}]},
                         include_accessories=True)
    assert a["category"] == cat
    assert a["department"] in ("footwear", "accessories")
    assert a["fit"] is None and a["sleeve_length"] is None and a["neckline"] is None
    if style:
        assert a["primary_style"] == style, a["style_scores"]


@pytest.mark.parametrize("title", ["Chain Print Shirt", "Oxford Button Down Shirt",
                                   "Cap Sleeve Top"])
def test_garment_head_noun_beats_accessory_word(title):
    a = classify_product({"title": title, "variants": [{"price": "999"}]},
                         include_accessories=True)
    assert a["department"] not in ("footwear", "accessories")


def test_not_accessories():
    for t in ("Shoe Cleaner Kit", "Perfume 100ml", "Gift Card", "Leather Keychain"):
        assert classify_product({"title": t, "variants": [{"price": "99"}]},
                                include_accessories=True) is None


def test_accessory_pool_scope_and_separation():
    raw = {"products": [_p(1, "Leather Belt", ["Men"]), _p(2, "Oxford Shirt", ["Men"]),
                        _p(3, "Block Heels Sandals", []), _p(4, "Canvas Sneakers"),
                        _p(5, "Snapback Cap")],
           "men_collection_ids": {}, "men_accessory_ids": {"caps": [5]}}
    site = {"name": "mixed", "base_url": "https://m.example"}
    acc, dropped = site_pool(site, raw, accessories=True)
    assert sorted(int(i["id"].split(":")[1]) for i in acc) == [1, 5]   # no shirt, no heels
    garments, _ = site_pool(site, raw)
    assert [int(i["id"].split(":")[1]) for i in garments] == [2]       # garments unchanged
    # a men-only store keeps unlabelled footwear but still drops women's words
    acc2, d2 = site_pool({**site, "default_gender": "men"}, raw, accessories=True)
    assert sorted(int(i["id"].split(":")[1]) for i in acc2) == [1, 4, 5] and d2["women"] == 1


@pytest.mark.parametrize("title", [t for t, _, _ in ACC_CASES] + [
    "Canvas Backpack", "Leather Duffle Bag", "Cabin Trolley Suitcase", "Leather Sling Bag",
    "Wool Beanie", "Bucket Hat", "Bow Tie", "Pocket Square", "Leather Wallet", "Gold Kada",
    "Silver Ring", "Lapel Pin Brooch", "Chelsea Boots", "Tassel Loafers", "Flip Flops"])
def test_accessory_sketches(title):
    it = classify_product({"title": title, "variants": [{"price": "999"}]},
                          include_accessories=True)
    it.update(id="site:7", title=title)
    svg = render_svg(it)
    assert svg.startswith("<svg") and svg.count(") scale(") == 2 and "nan" not in svg

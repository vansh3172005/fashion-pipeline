import json
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import imaging, run, store  # noqa: E402
from pipeline.classify import (classify_product, colors_in_text,  # noqa: E402
                               detect_category, detect_colors, detect_fabric,
                               detect_gender, detect_occasion, detect_sizes,
                               parse_composition, parse_specs, price_band)
from pipeline.scrape import (ADAPTERS, SiteAdapter, register_adapter,  # noqa: E402
                             scrape_site)
from tests import mock_shops  # noqa: E402

BONKERS_BODY = (
    '<p>PRODUCT DETAILS<br><br><strong>Composition:</strong> <span><span>60% Cotton 40% '
    'Polyester</span></span><br><strong>GSM:</strong> 380<br><strong>Color: </strong>'
    '<span data-sheets-root="1">Teal Blue</span><br><strong>Wash care:</strong> Machine wash '
    'cold with similar colors.<br><strong>Fit:</strong> Oversized Fit<br><strong>Sleeve '
    'length:</strong> Full Sleeves<br><strong>Neck:</strong> Round neck<br><strong>Please '
    'Note:</strong><br></p><ul><li>MRP: Rs.<span>1899</span>/- incl. of all taxes.</li></ul>'
    '<p>Fabric: our signature cotton for everyday outfits and evening looks.</p>')
SNITCH_BODY = (
    '<p style="text-transform: capitalize;">Fit - Regular Fit<br> Size - Model Is Wearing '
    'Size M</p><p><b>Occasion</b>: Smart Casuals <br><b>Pattern</b>: Plain<br><b>Collar'
    '</b>: Spread<br><b>Material</b>: 87% Nylon 13% Spandex<br><b>Sleeves</b>: Full '
    'Sleeve</p>')


# ------------------------------------------------------------------ site fields

def test_parse_specs_bonkers_and_snitch_layouts():
    s = parse_specs(BONKERS_BODY)
    assert s["fabric"] == "60% Cotton 40% Polyester"   # first "Fabric:"-like line wins
    assert s["color"] == "Teal Blue" and s["fit"] == "Oversized Fit"
    assert s["sleeve_length"] == "Full Sleeves" and s["neckline"] == "Round neck"
    assert s["gsm"] == "380" and "1899" in s["mrp"]
    s2 = parse_specs(SNITCH_BODY)
    assert s2["fit"] == "Regular Fit" and s2["occasion"] == "Smart Casuals"
    assert s2["pattern"] == "Plain" and s2["neckline"] == "Spread"
    assert s2["fabric"].startswith("87% Nylon")


def test_classify_product_reads_site_fields_and_records_source():
    p = {"title": "Wear A Hug Oversized Hoodie", "tags": ["Men", "Hoodie"],
         "body_html": BONKERS_BODY,
         "options": [{"name": "Size", "values": ["S", "M", "L"]}],
         "variants": [{"option1": s, "price": "1799.00", "compare_at_price": "1899.00",
                       "available": s != "L"} for s in ("L", "S", "M")]}
    a = classify_product(p)
    assert a["category"] == "hoodie" and a["department"] == "topwear"
    assert a["gender"] == "men" and a["attr_source"]["gender"] == "tags"
    assert a["color"] == "blue" and a["color_name"] == "Teal Blue"
    assert a["fabrics"] == ["cotton", "polyester"] and a["composition"] == {"cotton": 60,
                                                                          "polyester": 40}
    assert a["gsm"] == 380
    assert (a["fit"], a["attr_source"]["fit"]) == ("oversized", "field")
    assert (a["sleeve_length"], a["neckline"]) == ("long", "round neck")
    # "evening looks" in marketing copy must not make it party wear
    assert (a["occasion"], a["attr_source"]["occasion"]) == ("casual", "default")
    assert a["sizes"] == ["S", "M", "L"] and a["sizes_available"] == ["S", "M"]
    assert (a["price"], a["mrp"], a["discount_pct"]) == (1799.0, 1899.0, 5)
    assert a["price_band"] == "luxury"
    for param in ("color", "fabric", "fit", "sleeve_length", "neckline", "size"):
        assert a["attr_source"][param] == "field", param


def test_snitch_style_specs_classify():
    a = classify_product({"title": "Regular Fit Technical Stretch Shirt", "tags": ["Shirts"],
                          "body_html": SNITCH_BODY, "options": [{"name": "Color",
                                                                 "values": ["Brown"]}],
                          "variants": [{"price": "1999.00"}]})
    assert a["category"] == "shirt" and a["fit"] == "regular" and a["pattern"] == "solid"
    assert a["occasion"] == "smart casual" and a["neckline"] == "collar"
    assert a["fabrics"] == ["nylon", "elastane"] and a["color"] == "brown"
    assert a["attr_source"]["pattern"] == "field"


# ------------------------------------------------------------------ category rules

def test_category():
    assert detect_category("Freedom Oversized T-shirt") == "tshirt"
    assert detect_category("Icon Baby Tee") == "tshirt"
    assert detect_category("Classic Polo T-Shirt") == "polo"
    assert detect_category("Oxford Button Down Shirt") == "shirt"
    assert detect_category("Night Fade Black Relaxed Fit Jeans") == "jeans"
    assert detect_category("Olive Tape Wide Leg Joggers") == "joggers"
    assert detect_category("Sporty Straight Fit Pants") == "trousers"
    assert detect_category("Rock On Hoodie") == "hoodie"
    assert detect_category("Delilah Square Neck Crop Top") == "top"
    assert detect_category("Yellow Ribbed Halterneck") == "top"
    assert detect_category("Fuchsia Fever Co-ord Set") == "coord_set"
    assert detect_category("Moon Grey Pyjama Set") == "coord_set"
    assert detect_category("Twill Viscose Printed Taylor Shirtdress") == "dress"
    assert detect_category("Double Knee Cut Offs") == "shorts"
    assert detect_category("Hokage Home Run Jersey") == "tshirt"


def test_category_exclusions_and_false_exclusions():
    for t in ("Coffee Club Cap", "Bonkers Socks - Pack of 3", "Canvas Tote", "Bucket Hat",
              "Lace Trimmed Boxer Shorts", "Corduroy Snapback", "Gift Card", "Ribbed Gloves",
              "Kids Tee"):
        assert detect_category(t) is None, t
    # colour names and slang must not exclude real garments
    assert detect_category("Bottle Green Everyday Joggers") == "joggers"
    assert detect_category("No Cap Story Tank") == "top"
    assert detect_category("Cap Sleeve Tee") == "tshirt"
    assert detect_category("Backstreet Boys Oversized T-shirt") == "tshirt"
    assert detect_category("Venomized Mask Oversized T-shirt") == "tshirt"


def test_gender():
    assert detect_gender("Tee", tags=["Women", "New In"]) == ("women", "tags")
    assert detect_gender("Tee", tags=["Men", "Women"])[0] == "unisex"
    assert detect_gender("Men's Tee") == ("men", "title")
    assert detect_gender("Unisex Tee")[0] == "unisex"
    assert detect_gender("A Tee She Will Love, Gift For Her")[0] == "unspecified"


# ------------------------------------------------------------------ colour / fabric

def test_colors():
    assert colors_in_text("Off White") == ["white"]
    assert colors_in_text("Navy Blue and Olive Green") == ["navy", "green"]
    c = detect_colors({"title": "Tee", "body_html": "<b>Color:</b> Black & White"})
    assert (c["color"], c["secondary_color"]) == ("black", "white")
    c = detect_colors({"title": "Soft Blue Contrast Halter Top",
                       "options": [{"name": "Colour", "values": ["Blue"]}]})
    assert c["color"] == "blue" and c["secondary_color"] is None
    c = detect_colors({"title": "Rust Brown Track Pants"})
    assert c["color"] == "brown"   # "rust brown" is one colour, not orange + brown


def test_fabric():
    assert parse_composition("88% Lenzing Modal 12% Spandex") == {"modal": 88, "elastane": 12}
    assert parse_composition("Shell: 98% Polyester 2% Elastane") == {"polyester": 98,
                                                                    "elastane": 2}
    f = detect_fabric({"body_html": "<p>Wash with similar colours. Not cotton.</p>"},
                      {}, "Linen Shirt", [])
    assert f["fabric"] == "linen" and f["_src_fabric"] == "title"


def test_occasion_ignores_weak_description_words():
    assert detect_occasion({}, "Tee", desc="great for running errands and evening looks") == \
        ("casual", "default")
    assert detect_occasion({}, "Tee", tags=["GYM Wear"]) == ("activewear", "tags")
    assert detect_occasion({"occasion": "Party Wear"}, "Tee") == ("party", "field")


def test_bottomwear_has_no_sleeve_or_neckline():
    a = classify_product({"title": "Black Relaxed Fit Jeans", "tags": ["Men"],
                          "variants": [{"price": "1799"}]})
    assert a["sleeve_length"] is None and a["neckline"] is None
    assert a["attr_source"]["sleeve_length"] == "n/a"


def test_sizes_sorted_and_price_bands():
    sizes, avail = detect_sizes({"options": [{"name": "Size"}],
                                 "variants": [{"option1": s, "available": s in ("M", "XXL")}
                                              for s in ("XXL", "M", "XS", "L")]})
    assert sizes == ["XS", "M", "L", "XXL"] and avail == ["M", "XXL"]
    assert [price_band(p) for p in (0, 799, 800, 1499, 1500, 9999)] == \
        ["cheap", "cheap", "affordable", "affordable", "luxury", "luxury"]
    assert price_band(None) is None


# ------------------------------------------------------------------ imaging

def _photo(fill_frame=False):
    im = Image.new("RGB", (200, 260), (238, 238, 236))
    d = ImageDraw.Draw(im)
    if fill_frame:
        d.rectangle([0, 0, 199, 259], fill=(20, 30, 80))
    else:
        d.rectangle([60, 50, 140, 220], fill=(20, 30, 80))
        d.rectangle([75, 90, 125, 150], fill=(230, 200, 30))  # print on the garment
    return im


def test_flat_image_cutout_and_colours():
    im = _photo()
    alpha, bbox = imaging.clean_mask(imaging.garment_mask(imaging.PlainSegmenter().masks(im),
                                                          "topwear"))
    assert alpha is not None
    x0, y0, x1, y1 = bbox
    assert abs(x0 - 60) <= 3 and abs(y1 - 221) <= 3
    assert alpha[10, 10] == 0 and alpha[150, 100] > 0.9        # background gone
    assert alpha[120, 100] == 1.0                               # print kept (holes filled)
    flat = imaging.render_flat(im, alpha, bbox, size=128)
    assert flat.size == (128, 128) and flat.mode == "RGBA" and flat.getpixel((0, 0))[3] == 0
    pixels = np.asarray(im)[alpha > 0.9]
    bd = imaging.color_breakdown(pixels)
    assert bd[0]["color"] == "navy"
    assert imaging.secondary_from_breakdown(bd, "navy") == "yellow"


def test_flat_image_rejects_closeups():
    alpha, why = imaging.clean_mask(imaging.PlainSegmenter().masks(_photo(True))["all"])
    assert alpha is None, why
    m = np.zeros((100, 100))
    m[:, 5:95] = 1                                   # cut off at top, bottom, left/right
    assert imaging.clean_mask(m)[0] is None


def test_name_rgb():
    assert imaging.name_rgb(10, 10, 10) == "black"
    assert imaging.name_rgb(250, 250, 250) == "white"
    assert imaging.name_rgb(128, 128, 128) == "grey"
    assert imaging.name_rgb(30, 40, 90) == "navy"
    assert imaging.name_rgb(200, 30, 30) == "red"
    assert imaging.name_rgb(120, 70, 40) == "brown"


def test_cloth_segmenter_region_choice():
    up, low, full = (np.zeros((10, 10)) for _ in range(3))
    up[:5] = 1
    low[5:] = 1
    full[:] = 1
    m = {"upper": up, "lower": low, "full": full}
    assert imaging.garment_mask(m, "topwear").sum() == 50
    assert imaging.garment_mask(m, "bottomwear").sum() == 50
    assert imaging.garment_mask(m, "coord_set").sum() == 100   # top + bottom, no "full"


# ------------------------------------------------------------------ adapters

def test_custom_adapter_plugs_in_without_touching_classification():
    class FakeAdapter(SiteAdapter):
        def iter_products(self, site):
            self.pages = 1
            for i in range(30):
                yield {"id": i, "title": f"Black Oversized T-shirt {i}", "tags": ["Women"],
                       "handle": f"t{i}", "variants": [{"price": "599"}],
                       "images": [{"src": f"https://img.example/{i}.jpg"}]}

    register_adapter("fake", FakeAdapter)
    try:
        class NoNet:
            def get(self, *a, **k):
                raise __import__("requests").RequestException("offline")
        items, rep = scrape_site({"name": "fake", "base_url": "https://fake.example",
                                  "platform": "fake"}, per_cell=10, session=NoNet(),
                                 bands=["cheap"], categories=["tshirt"])
        assert rep["status"] == "ok" and len(items) == 10
        assert items[0]["gender"] == "women" and items[0]["price_band"] == "cheap"
    finally:
        ADAPTERS.pop("fake")


# ------------------------------------------------------------------ end to end

def test_end_to_end_bands_quota_images():
    servers = mock_shops.start()
    try:
        with tempfile.TemporaryDirectory() as d:
            cfg = Path(d) / "sites.json"
            cfg.write_text(json.dumps(mock_shops.sites_config()))
            run.DB, run.WEB = Path(d) / "c.db", Path(d) / "web"
            run.OUT = run.WEB / "catalogue.json"
            run.main(["scrape-quota", "--sites", str(cfg), "--delay", "0", "--workers", "4",
                      "--per-cell", "5"])
            con = store.connect(run.DB)
            try:
                per = {}
                for r in con.execute("SELECT site, price_band, category, COUNT(*) n FROM items "
                                     "GROUP BY 1, 2, 3"):
                    per.setdefault(r["site"], {})[(r["price_band"], r["category"])] = r["n"]
                cats = list(mock_shops.TEMPLATES)
                assert per["shop01"] == {(b, c): 5 for b in ("cheap", "affordable", "luxury")
                                         for c in cats}
                assert set(b for b, _ in per["shop04"]) == {"cheap", "affordable"}
                assert "shop02" not in per and "shop03" not in per
                status = {r["site"]: r["status"] for r in con.execute(
                    "SELECT site, status FROM scrape_runs")}
                assert status == {"shop01": "ok", "shop02": "error", "shop03": "blocked",
                                  "shop04": "short"}
                assert con.execute("SELECT COUNT(*) FROM items WHERE image IS NULL OR "
                                   "image = ''").fetchone()[0] == 0
                assert con.execute("SELECT COUNT(*) FROM items WHERE title LIKE '%Cap%' OR "
                                   "title LIKE '%Socks%'").fetchone()[0] == 0
                it = store.decode(con.execute("SELECT * FROM items WHERE site='shop01' "
                                              "LIMIT 1").fetchone())
                assert it["attr_source"]["fabric"] == "field" and it["currency"] == "INR"
                assert it["sizes_available"] and "XS" not in it["sizes_available"]
            finally:
                con.close()

            # flat images with the offline segmenter
            run.main(["images", "--segmenter", "plain", "--only", "shop01", "--limit", "4",
                      "--size", "96"])
            data = json.loads(run.OUT.read_text(encoding="utf-8"))
            done = [x for x in data if x.get("flat_images")]
            assert len(done) == 4
            for x in done:
                assert len(x["flat_images"]) == 2          # view 3 is a close-up -> rejected
                for f in x["flat_images"]:
                    assert (run.WEB / f).exists()
                assert x["image_colors"]

            # rerun: no duplicates, flat images survive a rescrape
            run.main(["scrape-quota", "--sites", str(cfg), "--delay", "0", "--only", "shop01",
                      "--per-cell", "5"])
            con2 = store.connect(run.DB)
            try:
                assert con2.execute("SELECT COUNT(*) FROM items WHERE site='shop01'"
                                    ).fetchone()[0] == 5 * 3 * len(cats)
                assert con2.execute("SELECT COUNT(*) FROM items WHERE flat_images != '[]'"
                                    ).fetchone()[0] == 4
            finally:
                con2.close()
    finally:
        for s in servers:
            s.shutdown()


# ------------------------------------------------------------------ formal-only / accessories (Snitch)

SNITCH_SHOE = ("<p>Specifications</p><p>Occasion : Formal Wear, Club Wear<br>Pattern : Solid<br>"
               "Upper Material : Vegan Leather<br>Closure Type : Slip-On</p>")


def test_accessories_only_when_enabled():
    from pipeline.classify import detect_category as dc
    assert dc("Beige Tassel Loafers") is None                    # excluded by default
    assert dc("Beige Tassel Loafers", include_accessories=True) == "shoes"
    assert dc("Black Oxford Shoes", include_accessories=True) == "shoes"
    assert dc("Oxford Button Down Shirt", include_accessories=True) == "shirt"
    assert dc("Vegan Reversible Formal Belt", include_accessories=True) == "belt"
    assert dc("Bold Square Black Sunglasses", include_accessories=True) == "sunglasses"
    assert dc("VITTO Black Suitcase- Set of 3", include_accessories=True) == "bag"
    assert dc("Pack Of 3 Regular Fit T-Shirt", include_accessories=True) is None
    assert dc("Yacht Club Luxe Linen Blazer") == "blazer"
    assert dc("Blue Denim Regular Fit Plus Size Shirt") == "shirt"
    assert dc("Leather Inlay Denim") == "jeans"


def test_site_occasions_and_formal_shoe():
    from pipeline.classify import site_occasions
    assert site_occasions({"occasion": "Formal Wear, Club Wear"}) == ["formal", "party"]
    assert site_occasions({}, ["FIXED_FORMALS", "Casual Wear",
                               "Trouser Size Chart (Formal & Chinos)"]) == ["formal", "casual"]
    assert site_occasions({}, ["Trouser Size Chart (Formal & Chinos)"]) == []
    a = classify_product({"title": "Beige Tassel Loafers", "tags": ["Shoes"],
                          "body_html": SNITCH_SHOE,
                          "options": [{"name": "Color", "values": ["Beige"]},
                                      {"name": "Size", "values": ["7", "8", "10"]}],
                          "variants": [{"option2": s, "price": "1999", "available": True}
                                       for s in ("10", "7", "8")]},
                         include_accessories=True, default_gender="men")
    assert a["category"] == "shoes" and a["department"] == "footwear"
    assert (a["occasion"], a["occasions"]) == ("formal", ["formal", "party"])
    assert a["fabric"] == "leather" and a["attr_source"]["fabric"] == "field"
    assert a["fit"] is None and a["neckline"] is None and a["sleeve_length"] is None
    assert a["sizes"] == ["7", "8", "10"]
    assert (a["gender"], a["attr_source"]["gender"]) == ("men", "site default")


def test_occasion_filter_keeps_only_formal():
    def prod(i, occ):
        return {"id": i, "title": f"Slim Fit Shirt {i}", "handle": f"s{i}",
                "body_html": f"<b>Occasion</b>: {occ}", "variants": [{"price": "1299"}],
                "images": [{"src": f"https://img.example/{i}.jpg"}]}

    class Feed(SiteAdapter):
        def iter_products(self, site):
            self.pages = 1
            yield from [prod(1, "Formal Wear"), prod(2, "Casual Wear"),
                        prod(3, "Casual Wear, Formal Wear"), prod(4, "Street Wear")]

    class NoNet:
        def get(self, *a, **k):
            raise __import__("requests").RequestException("offline")

    register_adapter("feed", Feed)
    try:
        items, rep = scrape_site({"name": "f", "base_url": "https://f.example",
                                  "platform": "feed", "occasion_filter": ["formal"],
                                  "default_gender": "men"}, per_cell=0, session=NoNet())
        assert sorted(i["id"] for i in items) == ["f:1", "f:3"]
        assert rep["off_occasion"] == 2 and all(i["gender"] == "men" for i in items)
    finally:
        ADAPTERS.pop("feed")


def test_image_sample_spreads_across_categories_and_bands():
    rows = [{"category": c, "price_band": b, "id": f"{c}{b}{i}"}
            for c, n in (("shirt", 50), ("trousers", 20), ("shoes", 3))
            for b in ("cheap", "luxury") for i in range(n)]
    picked = run._spread(rows, 6)
    assert len(picked) == 6
    assert {(r["category"], r["price_band"]) for r in picked} == {
        (c, b) for c in ("shirt", "trousers", "shoes") for b in ("cheap", "luxury")}

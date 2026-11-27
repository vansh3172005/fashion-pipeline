"""Women's catalogue: style_taxonomy_women.md sections 3, 5, 8 and 9."""
import pytest

from pipeline.build import site_pool
from pipeline.classify import classify_product, detect_category_women
from pipeline.style import STYLES, STYLES_WOMEN, classify_style, rules_for
from pipeline import sketch_women


def product(title, tags=(), body="", ptype="", price="1500", vendor=None, pid=1, options=None,
            variants=None):
    return {"id": pid, "title": title, "tags": list(tags), "body_html": body,
            "product_type": ptype, "vendor": vendor, "handle": "x",
            "options": options or [],
            "variants": variants or [{"price": price, "available": True}],
            "images": [{"src": "https://cdn.example/p.jpg"}]}


def classify(title, site=None, **kw):
    s = {"name": site} if site else {}
    return classify_product(product(title, **kw), site=s, catalogue="women",
                            default_gender="women")


# --------------------------------------------------------------------------
# section 9: the taxonomy's own test table
# --------------------------------------------------------------------------

SECTION_9 = [
    ("Oversized Graphic Tee", "jaywalking", "streetwear", []),
    ("Plain Black Slip Dress", None, "minimalist", []),
    ("Tailored Blazer - Camel", None, "classic", []),
    ("Pencil Skirt with Pleats", None, "classic", []),
    ("High Waist Gym Leggings with Pockets", "blissclub", "sporty", []),
    ("Cotton Printed Kurta Set with Palazzo and Dupatta", None, "traditional", []),
    ("Banarasi Silk Saree with Blouse", None, "traditional", []),
    ("Embellished Sequin Saree", None, "glam", ["traditional"]),
    ("Pre-Draped Saree Gown", None, "ethnic_fusion", []),
    ("Indo Western Kurta with Cape - Jacket Set", None, "ethnic_fusion", ["traditional"]),
    ("Party Wear Sequin Lehenga Choli", None, "glam", ["traditional"]),
    ("Tiered Floral Maxi Dress", None, "boho", []),
    ("Broderie Eyelet Midi Dress", None, "boho", []),
    ("Faux Leather Studded Biker Jacket", None, "edgy", []),
    ("Black Cut-Out Corset Mini Dress", None, "edgy", ["glam"]),
    ("Mesh Layered Top with Chain Detail", None, "edgy", []),
    ("Oversized Hoodie with Punk Graphic", None, "streetwear", ["edgy"]),
    ("Sequin Evening Gown - Wine", None, "glam", []),
    ("Crop Top with Ethnic Skirt", None, "ethnic_fusion", []),
    ("Chikankari Anarkali Kurta - Ivory", None, "traditional", []),
    ("Plain Solid Linen Shirt", "anavila", "minimalist", []),
]


@pytest.mark.parametrize("title,site,primary,also", SECTION_9)
def test_section_9(title, site, primary, also):
    a = classify(title, site)
    assert a is not None, title
    assert a["primary_style"] == primary, (title, a["style_tags"], a["style_scores"])
    for s in also:
        assert s in a["style_tags"], (title, a["style_tags"])


@pytest.mark.parametrize("title", ["Dupatta Stole", "Gift Card"])
def test_section_9_out_of_scope(title):
    assert classify(title) is None


def test_nine_styles_and_men_untouched():
    assert STYLES_WOMEN == STYLES + ("edgy",)
    assert "edgy" not in rules_for("men")["styles"]
    assert set(rules_for("women")["styles"]) == set(STYLES_WOMEN)
    # the default (men's) path never returns edgy and still uses the men's rules
    a = classify_product(product("Black Faux Leather Studded Biker Jacket"),
                         default_gender="men")
    assert "edgy" not in a["style_scores"]


# --------------------------------------------------------------------------
# section 5: scoring and selection
# --------------------------------------------------------------------------

def test_deterministic():
    a = classify("Floral Tiered Maxi Dress", "bohemiandream")
    b = classify("Floral Tiered Maxi Dress", "bohemiandream")
    assert a == b


def test_at_most_three_tags():
    a = classify("Indo Western Sequin Embellished Lehenga with Cape Jacket")
    assert len(a["style_tags"]) <= 3


def test_description_half_weight_and_cap():
    body = "<p>Bohemian tiered crochet fringe tassel macrame kaftan look.</p>"
    with_desc = classify("Cotton Top", body=body)
    without = classify("Cotton Top")
    gained = with_desc["style_scores"]["boho"] - without["style_scores"]["boho"]
    assert 0 < gained <= 3


def test_brand_prior_alone_is_not_a_style():
    a = classify("Cotton Top", "blissclub")
    assert a["style_scores"]["sporty"] <= 2


# --------------------------------------------------------------------------
# section 3: conflict rules
# --------------------------------------------------------------------------

def tags(title, site=None):
    a = classify(title, site)
    return a["primary_style"], a["style_tags"]


def test_saree_rules():
    assert tags("Kanjivaram Silk Saree")[0] == "traditional"
    p, t = tags("Zari Woven Banarasi Saree")
    assert p == "traditional" and "glam" in t
    assert tags("Ready to Wear Pre Stitched Saree")[0] == "ethnic_fusion"
    assert tags("Belted Dhoti Saree")[0] == "ethnic_fusion"


def test_lehenga_and_sharara_rules():
    p, t = tags("Chanderi Lehenga Choli Set")
    assert p == "traditional" and "glam" in t
    p, t = tags("Bridal Embroidered Lehenga")
    assert p == "glam" and "traditional" in t
    p, t = tags("Lehenga with Cape Jacket")
    assert "ethnic_fusion" in t
    p, t = tags("Cotton Kurta with Sharara and Dupatta")
    assert p == "traditional" and "glam" in t


def test_fusion_word_rules():
    p, t = tags("Indo Western Printed Dress")
    assert p == "ethnic_fusion" and "traditional" not in t
    p, t = tags("Fusion Kurta with Dhoti Pants")
    assert p == "ethnic_fusion"


def test_kurta_rules():
    assert tags("Cotton Kurta Set with Churidar and Dupatta")[0] == "traditional"
    assert "ethnic_fusion" in tags("Printed Kurta with Denim Jacket")[1]
    p, t = tags("Solid Cotton Kurta", "suta")
    assert p == "traditional" and "minimalist" in t


def test_boho_dress_rules():
    assert tags("Floral Printed Flowy Midi Dress")[0] == "boho"
    assert tags("Hand Block Printed Wrap Dress")[0] == "boho"
    assert tags("Ikat Shirt Dress")[0] == "boho"


def test_indian_gown_rule():
    p, t = tags("Anarkali Gown with Dupatta")
    assert p == "glam" and "ethnic_fusion" in t


def test_glam_edgy_rules():
    p, t = tags("Sequin Mini Dress with Chain Straps")
    assert p in ("glam", "edgy") and {"glam", "edgy"} <= set(t)
    assert tags("Black Leather Look Mini Skirt")[0] == "edgy"
    p, t = tags("Oversized Distressed Graphic Tee")
    assert p == "streetwear" and "edgy" in t


def test_sport_rules():
    assert tags("Flare Leggings")[0] == "sporty"
    p, t = tags("Oversized Graphic Yoga Tee")
    assert p == "sporty" and "streetwear" in t
    p, t = tags("Cargo Joggers")
    assert p == "sporty" and "streetwear" in t
    assert tags("Training Zip Hoodie")[0] == "sporty"
    assert tags("Fleece Hoodie")[0] == "streetwear"


def test_embellished_adds_glam_and_plain_defaults():
    assert "glam" in tags("Mirror Work Cotton Kurta")[1]
    assert tags("Black Top")[0] == "minimalist"
    assert tags("Navy Trousers")[0] == "classic"


# --------------------------------------------------------------------------
# section 8: scope
# --------------------------------------------------------------------------

@pytest.mark.parametrize("title,cat", [
    ("Saree with Unstitched Blouse Piece", "saree"),
    ("Sports Bra", "top"),
    ("Embroidered Readymade Blouse", "blouse"),
    ("Pink Chanderi Suit", "kurta_set"),
    ("Sharara Pants", "ethnic_bottom"),
    ("Shirt with Pants Co-ord Set", "coord_set"),
    ("Dress with Belt", "dress"),
    ("Mesh Layered Top with Chain Detail", "top"),
    ("Floral Jumpsuit", "jumpsuit"),
    ("Flare Leggings", "leggings"),
])
def test_women_categories(title, cat):
    assert detect_category_women(title) == cat


@pytest.mark.parametrize("title", [
    "Padded Bra", "Lace Bralette Set", "Floral Night Suit", "Cotton Nighty", "Kids Frock",
    "Girls Lehenga", "Unstitched Suit Material", "Cotton Dress Material", "Bikini Set",
    "Pack of 3 Leggings", "Lounge Set", "Gift Card", "Cushion Cover",
    "Off-White Pure Raw Silk Sherwani", "Flight Cufflinks - Gold", "Kurta Pyjama Set",
])
def test_out_of_scope(title):
    assert detect_category_women(title, include_accessories=True) is None


@pytest.mark.parametrize("title,cat", [
    ("Block Heels", "heels"), ("Kolhapuri Flats", "ethnic_footwear"),
    ("Embroidered Juttis", "ethnic_footwear"), ("Ballerina Flats", "flats"),
    ("Women Potli Bag", "clutch"), ("Oxidised Jhumka Earrings", "jewellery"),
    ("Embroidered Dupatta", "scarf"), ("Satin Scrunchie", "hair_accessory"),
    ("Leather Tote Bag", "bag"),
])
def test_women_accessories(title, cat):
    assert detect_category_women(title) is None  # not a garment
    assert detect_category_women(title, include_accessories=True) == cat


def test_accessory_styles():
    a = classify_product(product("Oxidised Silver Jhumka Earrings"), catalogue="women",
                         include_accessories=True, default_gender="women")
    assert a["primary_style"] == "traditional"
    a = classify_product(product("Kundan Bridal Necklace Set"), catalogue="women",
                         include_accessories=True, default_gender="women")
    assert a["primary_style"] == "glam"
    a = classify_product(product("Running Shoes"), catalogue="women",
                         include_accessories=True, default_gender="women")
    assert a["primary_style"] == "sporty"


def _raw(products, **ids):
    return {"products": products, **ids}


def test_site_pool_gender_rules():
    site = {"name": "mixed", "base_url": "https://x.example"}
    ps = [product("Women Floral Dress", pid=1), product("Men Cotton Kurta", pid=2),
          product("Cotton Dress", pid=3), product("Cotton Kurta", pid=4)]
    items, dropped = site_pool(site, _raw(ps, women_collection_ids={"women": [4]}),
                               catalogue="women")
    assert sorted(i["id"] for i in items) == ["mixed:1", "mixed:4"]
    assert dropped["men"] == 1 and dropped["unspecified not in a women's collection"] == 1
    women_only = dict(site, default_gender="women")
    items, _ = site_pool(women_only, _raw(ps), catalogue="women")
    assert sorted(i["id"] for i in items) == ["mixed:1", "mixed:3", "mixed:4"]


def test_site_pool_drops_age_sizes():
    site = {"name": "s", "base_url": "https://x.example", "default_gender": "women"}
    kid = product("Cotton Dress", options=[{"name": "Size", "values": ["2-3 Yrs", "4-5 Yrs"]}],
                  variants=[{"price": "500", "option1": "2-3 Yrs", "available": True}])
    items, dropped = site_pool(site, _raw([kid]), catalogue="women")
    assert not items and dropped["kids (sold only in age sizes)"] == 1


# --------------------------------------------------------------------------
# sketches
# --------------------------------------------------------------------------

SKETCH_TITLES = [
    "Floral Tiered Maxi Dress", "Black Bodycon Mini Dress", "Satin Slip Dress",
    "Linen Shirt Dress", "Sequin Evening Gown", "Anarkali Kurta", "Straight Cotton Kurta",
    "Kurta Set with Palazzo and Dupatta", "Kurta with Sharara and Dupatta",
    "Banarasi Silk Saree", "Bridal Lehenga Choli", "Embroidered Readymade Blouse",
    "Corset Top", "Cami Top", "Sports Bra", "Peplum Top", "Off Shoulder Top",
    "Pleated Midi Skirt", "Wide Leg Jumpsuit", "Shirt and Skirt Co-ord Set",
    "Flare Leggings", "Cotton Salwar", "Printed Kaftan Dress", "Cotton Cape",
    "Oversized Graphic Tee", "Denim Jacket", "Mom Jeans",
]
ACC_TITLES = ["Stiletto Heels", "Block Heel Sandals", "Ballerina Flats", "Embroidered Juttis",
              "Potli Bag", "Leather Handbag", "Jhumka Earrings", "Gold Bangles Set",
              "Maang Tikka", "Satin Scrunchie", "Leather Belt", "Chunky Sneakers"]


@pytest.mark.parametrize("title", SKETCH_TITLES + ACC_TITLES)
def test_sketch_renders(title):
    a = classify_product(product(title, pid=7), catalogue="women", include_accessories=True,
                         default_gender="women")
    assert a is not None, title
    it = {"id": "s:7", "title": title, **a}
    svg = sketch_women.render_svg(it)
    assert svg.startswith("<svg") and svg.endswith("</svg>")
    assert svg.count("<g transform") >= 2  # front + back
    assert "nan" not in svg


def test_sketch_path_is_separate_from_mens():
    assert sketch_women.sketch_path({"id": "bluorng:1"}) == "sketch_women/bluorng/1.svg"

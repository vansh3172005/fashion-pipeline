# Style Taxonomy for the Indian Men's Fashion Catalogue

| Field | Value |
| --- | --- |
| Document | style_taxonomy.md |
| Version | 1.0 |
| Date | 2026-11-20 |
| Companion to | `SRS.md` (Fashion Catalogue Scraping Pipeline) |
| Audience | Claude Code (implementing agent) and human reviewers |
| Scope | Men's clothing from Indian websites only |

---

## 0. Instructions for Claude Code

1. This document defines a **style** attribute: the *look* a garment belongs to (for example streetwear or traditional). It is separate from the garment type (t-shirt, kurta, pants), which the pipeline already extracts.
2. Websites almost never label products with these styles, so the pipeline must **infer** them. Implement the rules in Section 5 as deterministic code in a new module `pipeline/style.py`, with the rule data in `pipeline/style_rules.yaml` (Section 7).
3. The pipeline's existing field `styles` (polo, oversized, hoodie, cargo and so on) describes the **garment sub-type**. To avoid confusion, rename it to `wear_types` everywhere (code, database column, JSON export, frontend). The new fields in Section 6 hold the fashion style.
4. Keep all matching consistent with `classify.norm()`: text is lowercased, HTML stripped, apostrophes removed, punctuation collapsed to single spaces, and padded with a space on both sides. Match whole words or phrases only.
5. Every keyword you add or change needs a test in `tests/test_style.py` (see Section 9).
6. Do not scrape or label women's, kids', innerwear, footwear or accessory products. Men's apparel only.
7. The keyword lists below are a **starting point**. Tune them against real scraped titles and the audit in Section 10; do not treat them as final.

---

## 1. Purpose

The catalogue (target 13,000 to 15,000 men's items) must be browsable and analysable by fashion style. Indian men's fashion splits across specialist brands, so the same eight styles appear on different kinds of sites: streetwear D2C labels, linen and minimal labels, ethnic wear labels, and activewear labels. A single, shared taxonomy lets all of them be filtered together.

---

## 2. The eight styles

Each item receives **one primary style** and up to **two secondary styles**.

| ID | Label | One-line definition |
| --- | --- | --- |
| `minimalist` | Minimalist | Clean lines, solid colours, neutral palette, little or no branding or print |
| `classic` | Classic | Timeless tailored or smart-casual pieces that do not follow trends |
| `streetwear` | Streetwear | Urban, relaxed or oversized, graphic-led, youth-culture pieces |
| `boho` | Boho | Relaxed, artisanal, printed or textured pieces with earthy or free-spirited character |
| `sporty` | Sporty | Performance or athleisure pieces designed for movement or gym-to-street wear |
| `glam` | Glam | Embellished, occasion-led, party and wedding pieces meant to stand out |
| `ethnic_fusion` | Ethnic fusion | Indian garments blended with Western cuts, or Western garments with Indian motifs |
| `traditional` | Traditional | Established Indian garments in classic Indian cuts and craft textiles |
| `unclassified` | Unclassified | Fallback when no style reaches the threshold (target: 10% of items or fewer) |

### 2.1 Detailed definitions

**Minimalist**
- Look: solid colour, no logo, no graphic, no embellishment, clean silhouette.
- Typical garments: plain t-shirt, band-collar shirt, straight trousers, plain overshirt, knit pullover, simple linen shirt.
- Palette: black, white, grey, navy, beige, olive, off-white, stone.
- Fabrics: cotton, linen, wool, merino.
- Not minimalist: anything printed, graphic, embroidered or embellished.

**Classic**
- Look: tailored or smart-casual, timeless, office-ready or weekend-smart.
- Typical garments: oxford shirt, formal shirt, chinos, tailored trousers, polo, straight jeans, blazer-style jacket if in scope, checked or striped shirt.
- Palette: white, blue, navy, grey, brown, khaki.
- Not classic: oversized, graphic, cropped, distressed items.

**Streetwear**
- Look: urban, oversized or baggy fits, bold graphics, utility details, drop shoulders.
- Typical garments: oversized graphic tee, hoodie, cargo pants, baggy jeans, varsity jacket, puffer, co-ord tracksuit.
- Cues: graphic, print, logo, slogan, anime, distressed, acid wash, patchwork, utility pockets.
- Not streetwear: plain slim-fit basics from tailoring-led brands.

**Boho**
- Look: relaxed, artisanal and free-spirited; prints and handcraft textures.
- Typical garments: kaftan shirt, printed linen shirt, block-print shirt, tie-dye tee, camp-collar printed shirt, shacket with prints, crochet or fringe details.
- Cues: kaftan, tie dye, block print, paisley, floral, tribal, ikat, tassel, fringe, crochet, earthy colours (rust, terracotta, mustard, sage, indigo).
- Note: boho is thin in Indian men's wear. Expect the smallest counts here and report them honestly.

**Sporty**
- Look: performance fabrics and athletic cuts.
- Typical garments: joggers, track pants, track jacket, dry-fit tee, gym vest or tank, running shorts if shorts are in scope, compression wear, sweatshirts with sport branding.
- Cues: active, activewear, athleisure, gym, training, running, dry fit, quick dry, moisture wicking, performance, jersey, track.

**Glam**
- Look: embellished, shiny or rich fabrics worn for occasions.
- Typical garments: embroidered sherwani, bandhgala, velvet or brocade jacket, satin or sequin shirt, tuxedo-style jacket, party-wear kurta set.
- Cues: embellished, embroidered, sequin, zari, velvet, satin, silk, brocade, jacquard, metallic, party wear, wedding, reception, festive, groom.
- Palette: black, gold, maroon, emerald, wine, ivory with gold.

**Ethnic fusion**
- Look: Indian and Western styling combined.
- Typical garments: Indo-western sherwani with trousers, kurta jacket set, Nehru jacket worn over a Western shirt, dhoti pants, asymmetric or cape kurta, kurta-style shirt, ethnic-print bomber, co-ord set with a kurta top and tailored trousers.
- Cues: indo western, indowestern, fusion, jacket set, kurta jacket, dhoti pants, asymmetric kurta, cape, kurta shirt, shacket kurta.

**Traditional**
- Look: established Indian garments with classic silhouettes and craft textiles.
- Typical garments: kurta, kurta pyjama set, pathani suit, sherwani, dhoti, mundu or veshti, lungi, angrakha, bandi (waistcoat), Nehru jacket in classic cut.
- Cues: kurta, pyjama, pathani, sherwani, dhoti, mundu, veshti, lungi, angrakha, bandi, chikankari, bandhani, ajrakh, kalamkari, banarasi, khadi, handloom, lucknowi, phulkari.

---

## 3. Overlap and conflict rules

These rules take priority over raw scores (Section 5).

| Situation | Rule |
| --- | --- |
| Sherwani | Add `traditional` and `glam`; primary is `glam` if the title contains an embellishment cue, otherwise `traditional` |
| Nehru jacket or bandhgala | Add `traditional` and `ethnic_fusion`; primary `traditional` unless the title says "indo western" or "fusion" |
| Title contains "indo western" or "fusion" | Primary is `ethnic_fusion`; remove `traditional` from the secondary list unless the garment is a sherwani |
| Kurta with a Western garment word (jeans, denim, jacket, bomber, shirt collar) | Add `ethnic_fusion` |
| Printed or block-print linen shirt in a Western cut | `boho` (not `traditional`) |
| Plain kurta with no embellishment | `traditional`, plus `minimalist` if the brand prior is minimalist |
| Oversized or graphic item from an activewear brand | `streetwear` primary, `sporty` secondary |
| Joggers, track pants | `sporty` primary; add `streetwear` if the title says oversized, baggy, cargo or graphic |
| Hoodie or sweatshirt with no graphic | `streetwear` unless the title has sport cues, then `sporty`; if plain and from a minimalist brand, `minimalist` |
| Embellished item from any brand | Always add `glam` as a secondary at least |
| Plain, solid, unprinted basic (tee, shirt, trousers) in a neutral colour | Default to `minimalist`, or `classic` if tailored (formal shirt, chinos, trousers) |

---

## 4. Brand priors (starting points, verify before use)

A brand prior adds a small score to the styles a brand is known for. It helps when a title carries no cue. The list below comes from the candidate sites discussed during planning. Confirm each site is reachable with `python -m pipeline.run check` before relying on it, and edit the list as the real site list changes.

| Brand | Prior styles (each +2) |
| --- | --- |
| Snitch | streetwear, classic |
| The Souled Store | streetwear, sporty |
| Bewakoof | streetwear, sporty |
| SIX5SIX | streetwear, sporty, minimalist |
| Bluorng, Almost Gods, Jaywalking, House of Men | streetwear |
| DaMENSCH | sporty, classic |
| XYXX, HRX, Chkokko | sporty |
| Saphed | minimalist, classic, traditional |
| Manan | boho, minimalist |
| Minizmo, Seven, Andamen | minimalist, classic |
| Bombay Shirt Company | classic |
| Jaypore | boho, traditional |
| Kisah | traditional, ethnic_fusion, glam |
| Sojanya, HeSpoke, Sachin's | traditional, ethnic_fusion |
| Ethnix by Raymond | glam, ethnic_fusion, traditional |
| House of Indya | ethnic_fusion, glam |
| Tasva | minimalist, traditional |
| Manyavar | traditional, glam |
| House of Masaba, Pernia's Pop-Up Shop | glam, boho |
| Fabindia | traditional |

Multi-brand sites (for example Pernia's) get no prior for brands they only resell; set a prior per `vendor` field instead where the feed provides it.

### 4.1 Candidate websites by style

These are the Indian men's-fashion sites identified during planning from public articles and store pages. **None has been checked for a usable product feed yet**; run `python -m pipeline.run check` first, drop sites that fail, and add replacements. A domain is given only where it appeared in the research; for the others, confirm the domain before adding it to `sites.json`.

| Site | Styles it covers | Domain | What the research said |
| --- | --- | --- | --- |
| Snitch | streetwear, classic | confirm | Men's fast fashion: shirts, t-shirts, jeans, trousers |
| The Souled Store | streetwear, sporty | confirm | Pop-culture streetwear, expanding into activewear |
| Bewakoof | streetwear, sporty | confirm | Quirky graphics, loungewear, athleisure |
| SIX5SIX | streetwear, sporty, minimalist | confirm | Streetwear and sportswear, minimal and athleisure-inspired |
| Bluorng | streetwear | confirm | Known name in Indian streetwear culture |
| Almost Gods | streetwear | confirm | Edgy, colourful streetwear designs |
| Jaywalking | streetwear | confirm | Delhi streetwear label (gender-fluid and men's) |
| Underrated Club | streetwear | underratedclub.com | Streetwear brand with oversized fits, cargos, joggers |
| Capsul | streetwear | confirm | Multi-brand streetwear store; resold brands need per-vendor priors |
| House of Men | streetwear, minimalist | houseofmen.in | Winterwear, streetwear and minimalist apparel; newly launched, probably small |
| DaMENSCH | sporty, classic | confirm | Polo t-shirts, hoodies, joggers |
| XYXX | sporty | confirm | Innerwear and loungewear, moving into athleisure (exclude innerwear) |
| HRX | sporty | confirm | One of India's first homegrown activewear brands |
| Chkokko | sporty | confirm | Athleisure for men and women (keep men's only) |
| Saphed (Saphed Man) | minimalist, classic, traditional | saphed.com | Linen shirts, kurtas, Nehru jackets; only about 155 men's products |
| Manan | boho, minimalist | manandesign.com (also canvasandweaves.com) | Linen shirts, kaftan shirts, block-printed and embroidered styles, kurtas |
| Minizmo | minimalist, classic | confirm | "Minimal is more" menswear: work shirts, blazers |
| Seven | minimalist, classic | confirm | Minimal design philosophy across shirts and kurtas |
| Andamen | classic, minimalist | confirm | "Contemporary heritage" men's shirts |
| Bombay Shirt Company | classic | confirm | Bespoke and made-to-measure shirts |
| Jaypore | boho, traditional | jaypore.com | Craft textiles (Kalamkari, Ajrakh, Chikankari, block print) in shirts and kurtas |
| Kisah | traditional, ethnic_fusion, glam | confirm | Kolkata-based D2C men's ethnic brand; sherwanis, kurta sets |
| Sojanya | traditional, ethnic_fusion | confirm | Sherwani jackets and ethnic range |
| HeSpoke | traditional, ethnic_fusion | confirm | Festive and family-occasion kurtas |
| Sachin's | traditional, ethnic_fusion | confirm | Kurta suits, pathani suits, Indo-western sets, sherwanis |
| Ethnix by Raymond | glam, ethnic_fusion, traditional | stores.myraymond.com (store page; confirm the online store) | Sherwanis, kurtas, short kurtas, Indo-western outfits |
| House of Indya | ethnic_fusion, glam | houseofindya.com | Kurta sets, sherwani sets, Nehru jackets, Indo-western; prices shown in USD, confirm INR storefront |
| Tasva | minimalist, traditional | confirm | Modern Indian menswear with a minimalist vibe |
| Manyavar | traditional, glam | confirm | Ornate, statement-making traditional wear |
| House of Masaba | glam, boho | houseofmasaba.com | Designer kurta sets, wedding outfits, printed shirts |
| Pernia's Pop-Up Shop | glam, boho | perniaspopupshop.com | Multi-brand designer store (for example Abraham & Thakore, printed linen shacket sets); needs per-vendor priors |
| Fabindia | traditional | confirm | Kurtas and Indian wear |
| Nykaa Fashion (marketplace) | traditional, ethnic_fusion, glam | nykaafashion.com | Its men's ethnicwear page lists 31,495 items. Large multi-brand marketplace: check terms of use and bot protection before attempting; do not bypass blocks |

**Coverage by style** (which sites to rely on for each):

| Style | Main sites |
| --- | --- |
| minimalist | Saphed, Manan, Minizmo, Seven, Tasva, SIX5SIX, House of Men |
| classic | Snitch, DaMENSCH, Bombay Shirt Company, Andamen, Minizmo, Saphed |
| streetwear | The Souled Store, Bewakoof, Snitch, SIX5SIX, Bluorng, Almost Gods, Jaywalking, Underrated Club, Capsul, House of Men |
| boho | Manan, Jaypore, House of Masaba, Pernia's (smallest style; expect low counts) |
| sporty | HRX, Chkokko, XYXX, DaMENSCH, SIX5SIX, The Souled Store |
| glam | Kisah, Ethnix by Raymond, House of Indya, House of Masaba, Pernia's, Manyavar |
| ethnic_fusion | Ethnix by Raymond, House of Indya, Kisah, Sachin's, Sojanya, HeSpoke |
| traditional | Fabindia, Manyavar, Kisah, Sojanya, HeSpoke, Jaypore, Saphed, Tasva |

**Sites deliberately left out:** large general marketplaces such as Myntra, Ajio and Flipkart. They sell every style, but they typically have heavy bot protection and strict terms, so they are not recommended unless the operator has confirmed that scraping is permitted.

Catalogue size note: only two sizes were found in the research (Saphed about 155 men's products, Nykaa Fashion 31,495 men's ethnicwear items). All other counts are unknown until `check --count` reports them (see the checklist in Section 12). Most single D2C brands are expected to hold hundreds to low thousands of men's items, so 13,000 to 15,000 total will likely need 20 to 25 working sites.

---

## 5. Classification algorithm

### 5.1 Inputs

For each product: `title`, `product_type`, `tags`, `handle`, `vendor`, `body_html`, variant `options` (colour), the site `name`, and the already-detected garment `category`, `colors` and `fabrics`.

### 5.2 Scoring

For every style, compute a numeric score:

1. **Keyword hits.** Each keyword rule in `style_rules.yaml` has a weight: `strong` = 3, `medium` = 2, `weak` = 1.
   - A hit in `title`, `product_type` or `tags` counts at full weight.
   - A hit in `body_html` counts at half weight, rounded down, and each style is capped at +3 from the description.
   - Each distinct rule counts once per product, however many times it appears.
2. **Negative keywords.** A style's `negative` list subtracts 2 per distinct hit (for example `graphic` is negative for minimalist and classic).
3. **Brand prior.** Add +2 if the site or vendor has that style in its prior (Section 4).
4. **Palette signals** (weak, +1 each, at most +1 per style): neutral colours for minimalist, earthy colours for boho, jewel tones with gold for glam.
5. **Fabric signals** (weak, +1 each, at most +1 per style): linen or cotton for minimalist and boho, silk, velvet or satin for glam, polyester performance blends for sporty, khadi or handloom for traditional.

### 5.3 Selecting labels

1. Apply the conflict rules in Section 3 (they may add, remove or force styles).
2. Let `top` be the highest score. If `top < 3`, apply the fallback defaults in Section 5.4.
3. Keep every style with `score >= max(3, 0.5 * top)`.
4. Sort by score (ties broken by this order: traditional, ethnic_fusion, glam, streetwear, sporty, boho, classic, minimalist). The first is `primary_style`. Keep at most 3 styles in total in `style_tags`.

### 5.4 Fallbacks (when `top < 3`)

1. Plain, unprinted item (no print, graphic or embellishment cue) in a neutral colour: `minimalist` for casual basics, `classic` for tailored basics.
2. Kurta or other Indian garment word with no further cue: `traditional`.
3. Otherwise: `unclassified`.

### 5.5 Confidence

Store `style_confidence`: `high` if `top >= 6` and the gap to the next style is at least 2; `medium` if `top >= 3`; `low` otherwise (including all fallbacks). The frontend may hide low-confidence items from style filters by default.

### 5.6 Optional refinement (SHOULD, not required for v1)

For items that are `unclassified`, `low` confidence, or have a top-two score gap of 1 or less, call a language model (and optionally a vision model on the product image) with a fixed prompt and a JSON-only response limited to the eight style IDs. Cache every response keyed by product id. Record `style_source = "llm"`. Always keep the rule-based result and mark the field's origin so the audit can compare both.

---

## 6. Output fields

Add these to the items table, the JSON export and the frontend. Names are fixed.

| Field | Type | Description |
| --- | --- | --- |
| `primary_style` | TEXT | One of the nine IDs in Section 2 |
| `style_tags` | JSON array | Up to 3 style IDs, primary first |
| `style_scores` | JSON object | Score per style, for debugging and audit |
| `style_confidence` | TEXT | `high`, `medium` or `low` |
| `style_source` | TEXT | `rules` or `llm` |

Existing field change: rename `styles` to `wear_types` (garment sub-type: polo, oversized, cargo, hoodie, jeans and so on).

Frontend changes: add a **Style** filter (the eight labels plus Unclassified), show the primary style as a tag on each card, and show facet counts like the other filters.

---

## 7. Rule data format (`pipeline/style_rules.yaml`)

Use this structure. Phrases are written in normalised form (lowercase, no punctuation). Multi-word phrases match as whole phrases.

```yaml
version: 1
thresholds: {min_score: 3, relative: 0.5, max_tags: 3}
styles:
  minimalist:
    strong: ["minimalist", "minimal", "essential", "solid", "plain", "clean"]
    medium: ["band collar", "mandarin collar", "straight fit", "relaxed fit", "overshirt", "basic"]
    weak: ["neutral", "everyday", "classic fit"]
    negative: ["graphic", "printed", "print", "logo", "embroidered", "sequin", "tie dye", "distressed"]
    palette: ["black", "white", "grey", "navy", "beige", "olive"]
    fabrics: ["cotton", "linen", "wool"]
  classic:
    strong: ["oxford", "formal", "tailored", "chinos", "chino", "dress shirt", "blazer"]
    medium: ["polo", "striped", "checked", "check", "straight jeans", "trousers", "slim fit", "regular fit", "work shirt"]
    weak: ["smart casual", "office", "timeless", "heritage"]
    negative: ["oversized", "graphic", "baggy", "cropped", "distressed", "neon"]
    palette: ["white", "navy", "blue", "grey", "brown", "beige"]
    fabrics: ["cotton", "wool"]
  streetwear:
    strong: ["streetwear", "oversized", "graphic", "baggy", "drop shoulder", "cargo", "varsity"]
    medium: ["hoodie", "puffer", "distressed", "acid wash", "washed", "patchwork", "anime", "utility", "boxy", "wide leg", "co ord"]
    weak: ["urban", "street", "logo", "print", "printed", "slogan", "tee"]
    negative: ["formal", "tailored", "kurta", "sherwani"]
    palette: []
    fabrics: ["fleece", "denim"]
  boho:
    strong: ["boho", "bohemian", "kaftan", "tie dye", "block print", "ikat", "crochet", "macrame", "fringe", "tassel"]
    medium: ["paisley", "floral", "tribal", "hand painted", "hand block", "camp collar printed", "printed linen", "artisanal", "shacket"]
    weak: ["earthy", "relaxed", "resort", "printed", "linen"]
    negative: ["formal", "tailored", "sport", "gym", "sequin"]
    palette: ["orange", "yellow", "brown", "green"]
    fabrics: ["linen", "cotton"]
  sporty:
    strong: ["activewear", "athleisure", "gym", "training", "running", "dry fit", "quick dry", "moisture wicking", "performance", "track pants", "joggers", "jogger"]
    medium: ["track jacket", "compression", "sports", "workout", "athletic", "stretch", "jersey", "tracksuit"]
    weak: ["active", "sweat", "lounge"]
    negative: ["formal", "sherwani", "kurta", "embroidered"]
    palette: []
    fabrics: ["polyester", "nylon", "elastane"]
  glam:
    strong: ["embellished", "sequin", "zari", "velvet", "brocade", "party wear", "wedding", "reception", "groom", "tuxedo", "sherwani"]
    medium: ["embroidered", "satin", "jacquard", "metallic", "bandhgala", "festive", "occasion", "statement", "luxe", "silk"]
    weak: ["shimmer", "gold", "royal", "rich", "celebration"]
    negative: ["gym", "training", "plain tee", "basic"]
    palette: ["black", "red", "purple"]
    fabrics: ["silk", "viscose"]
  ethnic_fusion:
    strong: ["indo western", "indowestern", "fusion", "kurta jacket", "jacket set", "dhoti pants", "asymmetric kurta"]
    medium: ["nehru jacket", "cape", "kurta shirt", "co ord kurta", "kurta with jacket", "shacket kurta", "ethnic print bomber"]
    weak: ["modern ethnic", "contemporary kurta", "bandi"]
    negative: ["gym", "training"]
    palette: []
    fabrics: []
  traditional:
    strong: ["kurta", "kurta set", "pyjama", "pathani", "sherwani", "dhoti", "mundu", "veshti", "lungi", "angrakha"]
    medium: ["bandi", "nehru jacket", "chikankari", "bandhani", "ajrakh", "kalamkari", "banarasi", "khadi", "handloom", "lucknowi", "phulkari", "churidar", "bandhgala"]
    weak: ["ethnic", "festive", "puja", "diwali", "eid", "handwoven", "craft"]
    negative: ["graphic", "oversized", "gym", "baggy"]
    palette: []
    fabrics: ["khadi", "cotton", "silk"]
brand_priors: {}   # filled from Section 4, keyed by site name or vendor
```

Notes for implementation:
- `fabrics` and `palette` entries refer to the pipeline's existing normalised fabric and colour names. Add `khadi` to the fabric list in `classify.py` if you use it here.
- Words such as `solid`, `plain`, `print` and `tee` are weak and ambiguous. Prefer phrase matches and rely on the threshold rather than adding more single words.

---

## 8. Scope and filters for this catalogue

Include: men's tops, bottoms, ethnic sets and separates, knitwear and outerwear that a man would wear as clothing.

Exclude: women's and kids' clothing, innerwear and lingerie, footwear, bags, belts, wallets, hats and caps, jewellery, grooming, home goods, gift cards, bundles and combo packs.

Gender rule: keep an item only if `gender == "men"` or the item is explicitly unisex *and* sold in the site's men's collection. Items with `unspecified` gender are kept only when fetched from a men's-only collection feed. Log everything dropped by this rule.

---

## 9. Test cases (put in `tests/test_style.py`)

Each row is a unit test: input title (and site or tags where shown), expected primary style, and expected secondary styles (a subset match is enough).

| # | Input | Expected primary | Expected also contains |
| --- | --- | --- | --- |
| 1 | "Men's Oversized Graphic Tee" (site: snitch) | streetwear | |
| 2 | "Plain Black Cotton T-Shirt" (neutral palette) | minimalist | |
| 3 | "Oxford Button Down Shirt - Blue" | classic | |
| 4 | "Slim Fit Chinos - Khaki" | classic | |
| 5 | "Black Dry Fit Training Joggers" | sporty | |
| 6 | "Oversized Cargo Joggers" | sporty | streetwear |
| 7 | "Embroidered Silk Sherwani with Churidar" | glam | traditional |
| 8 | "Cotton Kurta Pyjama Set - White" | traditional | |
| 9 | "Indo Western Jacket Kurta Set" | ethnic_fusion | |
| 10 | "Block Print Linen Camp Collar Shirt" | boho | |
| 11 | "Linen Kaftan Shirt - Mint" | boho | |
| 12 | "Nehru Jacket - Navy" | traditional | ethnic_fusion |
| 13 | "Velvet Bandhgala Jacket" | glam | traditional |
| 14 | "Hand Block Printed Cotton Kurta" | traditional | boho |
| 15 | "Pullover Hoodie, Heather Grey, Fleece" (no graphic, no brand prior) | streetwear | |
| 16 | "Pullover Hoodie, Plain" (site: saphed) | minimalist | |
| 17 | "Tie Dye Oversized T-Shirt" | boho | streetwear |
| 18 | "Chikankari Kurta - Ivory" | traditional | |
| 19 | "Men's Solid Band Collar Linen Shirt" (site: saphed) | minimalist | classic |
| 20 | "Water Bottle" or "Gift Card" | not classified (out of scope, filtered earlier) | |

Also test: determinism (same input, same output), maximum three tags, description-only hits count at half weight and are capped, and each conflict rule in Section 3.

---

## 10. Quality targets and audit

1. After the first real scrape, sample **20 items per style** (160 in total, drawn across sites). A reviewer marks whether each assigned style is correct.
2. Targets: at least **80% precision** for each style, and **at most 10% of items** unclassified.
3. For any style under target, inspect its false positives and adjust keywords, negatives or conflict rules, then rerun the tests.
4. Report per style: item count, precision from the audit, and the top 10 keywords that fired. Thin styles (boho, glam) may fall short on count; report the number rather than padding with wrongly labelled items.
5. Report the share of items that are `high`, `medium` and `low` confidence.

---

## 11. Balancing the catalogue (13,000 to 15,000 items)

1. Scrape all men's items per site (do not cap at 50 per category), then classify them.
2. Use a target of roughly 1,600 to 1,900 items per style as `primary_style`, for a total of 13,000 to 15,000. If a style cannot reach its target, do not relabel items to fill it; instead take more items from sites strong in that style, or accept and report the shortfall.
3. Cap any single site at about 12% of the final catalogue so no brand dominates.
4. Remove exact duplicates (same title and image across sites) and near-duplicates (same product listed in several colours is kept once per colour only if colours differ in the feed).
5. Record the final counts per style and per site in a `catalogue_report.md` file.

---

## 12. Implementation checklist for Claude Code

- [ ] Create `pipeline/style_rules.yaml` from Section 7 and load it once at startup.
- [ ] Create `pipeline/style.py` with `classify_style(product, attrs, site) -> dict` implementing Section 5, returning the Section 6 fields.
- [ ] Call it from `classify_product` and store the results.
- [ ] Rename `styles` to `wear_types` and add the five new columns (migrate the SQLite schema, update the export and the frontend).
- [ ] Add the Style filter and the primary-style tag to `web/index.html`.
- [ ] Add `tests/test_style.py` covering Section 9.
- [ ] Apply the men's-only scope in Section 8.
- [ ] Add a `--count` option to `check` that reports how many men's items each site holds.
- [ ] Run the audit in Section 10 and tune the rules.
- [ ] Produce `catalogue_report.md` (Section 11).
- [ ] Update `SRS.md` and `README.md` to reference this document.

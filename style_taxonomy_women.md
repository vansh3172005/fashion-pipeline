# Style Taxonomy for the Indian Women's Fashion Catalogue

| Field | Value |
| --- | --- |
| Document | style_taxonomy_women.md |
| Version | 1.0 |
| Date | 2026-11-21 |
| Companion to | `style_taxonomy.md` (men's taxonomy) and `SRS.md` |
| Audience | Claude Code (implementing agent) and human reviewers |
| Scope | Women's clothing from Indian websites only |
| Difference from the men's taxonomy | Nine styles instead of eight: adds `edgy`; women's garment scope; women's brand list; women-specific rules |

---

## 0. Instructions for Claude Code

1. This document defines the **style** attribute for the **women's** catalogue: the *look* a garment belongs to (for example boho or edgy). It is separate from the garment type (kurta, dress, jeans), which the pipeline already extracts.
2. It uses the same method, field names and file layout as the men's `style_taxonomy.md`. Build **one** style engine in `pipeline/style.py` that loads a rule file by catalogue gender: `pipeline/style_rules_men.yaml` (from `style_taxonomy.md`) and `pipeline/style_rules_women.yaml` (from Section 7 of this document). Do not fork the code.
3. Websites rarely label products with these styles, so the pipeline must **infer** them with deterministic rules (Section 5).
4. The existing field `styles` (polo, cargo, anarkali and so on) describes the **garment sub-type**. Rename it to `wear_types` everywhere (code, database column, JSON export, frontend), as in the men's document. If that rename is already done, skip it.
5. Keep all matching consistent with `classify.norm()`: text is lowercased, HTML stripped, apostrophes removed, punctuation collapsed to single spaces, and padded with a space on both sides. Match whole words or phrases only.
6. Every keyword you add or change needs a test in `tests/test_style_women.py` (Section 9).
7. Do not scrape or label men's, kids', lingerie or innerwear, footwear, bag, jewellery or accessory products (Section 8).
8. The keyword lists below are a **starting point**. Tune them against real scraped titles and the audit in Section 10.
9. Never bypass access controls on any site (see `SRS.md`, NFR-LEGAL-1).

---

## 1. Purpose

The women's catalogue (target volume in Section 11) must be browsable and analysable by fashion style. Indian women's fashion is split across specialist labels: streetwear and edgy labels, minimal and workwear labels, activewear labels, boho labels, ethnic and fusion labels, and occasion-wear labels. One shared taxonomy lets all of them be filtered together and compared with the men's catalogue.

---

## 2. The nine styles

Each item receives **one primary style** and up to **two secondary styles**.

| ID | Label | One-line definition |
| --- | --- | --- |
| `minimalist` | Minimalist | Clean lines, solid colours, neutral palette, little or no print or embellishment |
| `classic` | Classic | Timeless tailored, workwear or smart-casual pieces that do not follow trends |
| `streetwear` | Streetwear | Urban, relaxed or oversized, graphic-led, youth-culture pieces |
| `boho` | Boho | Flowy, artisanal, printed or textured pieces with a free-spirited, earthy character |
| `sporty` | Sporty | Performance or athleisure pieces designed for movement or gym-to-street wear |
| `glam` | Glam | Embellished, shiny or occasion-led pieces for parties, cocktails and weddings |
| `ethnic_fusion` | Ethnic fusion | Indian garments blended with Western cuts, or Western garments with Indian motifs |
| `traditional` | Traditional | Established Indian garments in classic Indian cuts and craft textiles |
| `edgy` | Edgy | Bold, rebellious, dark or deconstructed pieces with hardware, leather or cut-out details |
| `unclassified` | Unclassified | Fallback when no style reaches the threshold (target: 10% of items or fewer) |

### 2.1 Detailed definitions

**Minimalist**
- Look: solid colour, no logo, no print, no embellishment, clean silhouette.
- Typical garments: plain tee, straight-fit shirt, wide-leg or straight trousers, slip dress, knit top, simple kurta, co-ord set in a solid colour.
- Palette: black, white, grey, navy, beige, olive, off-white, stone.
- Fabrics: cotton, linen, wool, modal, khadi.
- Not minimalist: anything printed, graphic, embroidered or embellished.

**Classic**
- Look: tailored, workwear or smart-casual, timeless and not trend-led.
- Typical garments: blazer, trench coat, tailored trousers, pencil skirt, shirt dress, wrap dress, button-down shirt, pleated trousers, striped or checked shirt.
- Palette: white, black, navy, camel, grey, blue.
- Not classic: oversized, graphic, cropped, distressed or neon items.

**Streetwear**
- Look: urban, oversized or baggy fits, bold graphics, utility details, drop shoulders.
- Typical garments: oversized graphic tee, hoodie, cargo pants, baggy jeans, parachute pants, varsity jacket, co-ord tracksuit.
- Cues: graphic, oversized, baggy, cargo, hoodie, drop shoulder, varsity, anime, patchwork, acid wash.
- Not streetwear: plain tailored basics.

**Boho**
- Look: flowy, relaxed, artisanal; prints, lace and handcraft textures.
- Typical garments: tiered maxi dress, peasant top, broderie or eyelet dress, tie-dye set, kaftan, sarong skirt, crochet top, block-print dress.
- Cues: boho, bohemian, tiered, flowy, peasant, crochet, macrame, fringe, tassel, ikat, broderie, eyelet, lace, paisley, floral, tie dye, kaftan, sarong, resort.
- Palette: earthy (rust, terracotta, mustard, sage, indigo, cream).

**Sporty**
- Look: performance fabrics and athletic cuts.
- Typical garments: leggings, tights, sports bra (treated as activewear, not lingerie), yoga pants, track pants, joggers, running tee, gym tank, biker shorts, athleisure jacket.
- Cues: activewear, athleisure, movewear, yoga, gym, training, running, workout, dry fit, quick dry, moisture wicking, performance, tights.

**Glam**
- Look: embellished, shiny or rich fabrics worn for occasions.
- Typical garments: sequin dress, evening gown, cocktail dress, party-wear lehenga, embellished saree, satin or velvet co-ord, bridal wear, sangeet and reception outfits.
- Cues: sequin, embellished, gown, cocktail, party wear, evening, wedding, bridal, sangeet, reception, zari, velvet, satin, metallic, bodycon (party), lehenga.
- Palette: black, gold, wine, emerald, silver, metallic shades, ivory with gold.

**Ethnic fusion**
- Look: Indian and Western styling combined.
- Typical garments: kurta with a jacket or cape, crop top with ethnic skirt, dhoti pants with a jacket, saree gown, pre-draped saree, lehenga with a jacket, co-ord kurta set with Western trousers, asymmetric or layered kurta, indo-western dress.
- Cues: indo western, indowestern, fusion, kurta jacket, jacket set, cape set, dhoti pants, crop top skirt, pre draped saree, saree gown, asymmetric kurta, layered kurta, shrug.

**Traditional**
- Look: established Indian garments with classic silhouettes and craft textiles.
- Typical garments: saree, kurta or kurti, kurta set with palazzo or churidar and dupatta, anarkali, salwar suit, patiala, lehenga choli, sharara, gharara.
- Cues: saree, sari, kurta, kurti, anarkali, salwar, patiala, palazzo set, churidar, dupatta set, chikankari, bandhani, ajrakh, kalamkari, banarasi, kanjivaram, chanderi, patola, phulkari, handloom, khadi, block print kurta.

**Edgy**
- Look: bold and rebellious; dark palettes, hard materials and hardware, deconstructed shapes.
- Typical garments: faux-leather jacket or pants, studded or chain-detail pieces, corset or bustier top, mesh or sheer layers, cut-out dress, asymmetric hem, distressed denim, biker or moto jacket, all-black co-ords, structured-shoulder blazers, punk or grunge graphics.
- Cues: edgy, leather, faux leather, vegan leather, studded, studs, chain, hardware, cut out, corset, bustier, mesh, sheer, asymmetric, deconstructed, distressed, ripped, biker, moto, punk, grunge, gothic, harness, lace up, spike.
- Palette: black, charcoal, oxblood, metallics (weak signal).
- Not edgy: pastel, ruffled, floral, soft romantic pieces.

---

## 3. Overlap and conflict rules

These rules take priority over raw scores (Section 5).

| Situation | Rule |
| --- | --- |
| Saree | `traditional` primary. Add `glam` if the title has an embellishment cue (sequin, zari, stone work, embellished). Make `ethnic_fusion` primary if the title says pre-draped, saree gown, belted saree, dhoti saree or ready to wear |
| Lehenga, sharara, gharara | `traditional` and `glam`. Primary is `glam` if the title has party, sequin, embellished, bridal, cocktail or sangeet; otherwise `traditional`. Add `ethnic_fusion` if the title also has jacket, cape, crop top or indo western |
| Title contains "indo western" or "fusion" | Primary is `ethnic_fusion`; remove `traditional` from the secondary list unless the garment is a saree or lehenga |
| Kurta set with palazzo, churidar, salwar or dupatta | `traditional` |
| Kurta with a Western garment (jacket, cape, jeans, denim, trousers, skirt, shrug) | Add `ethnic_fusion` |
| Plain kurta or kurta set with no print or embellishment | `traditional`, plus `minimalist` if the brand prior includes minimalist |
| Printed, flowy dress with floral, ikat, tie-dye, broderie or tiered cues | `boho` |
| Block-print or ikat dress in a Western cut | `boho` (not `traditional`) |
| Gown with an Indian cue (lehenga gown, cape gown, indo western gown) | `glam` primary, `ethnic_fusion` secondary |
| Sequin, metallic or velvet item with leather, chain, cut-out, corset or mesh cues | `glam` and `edgy` both kept; primary is the higher score, ties go to `glam` |
| Black item with any hard-material or hardware cue (leather, studs, chain, mesh, cut-out) | `edgy` primary |
| Oversized, graphic or hoodie item that also has an edgy cue (punk, grunge, distressed, studded) | `streetwear` primary, `edgy` secondary |
| Leggings, tights, sports bra, yoga or gym items | `sporty` primary. Add `streetwear` if the title says oversized, baggy or graphic |
| Joggers, track pants | `sporty`; add `streetwear` if the title says oversized, baggy, cargo or graphic |
| Hoodie or sweatshirt with no graphic | `streetwear` unless the title has sport cues, then `sporty`; if plain and from a minimalist brand, `minimalist` |
| Embellished item from any brand | Always add `glam` as a secondary at least |
| Plain, solid, unprinted basic (tee, shirt, trousers, slip dress) in a neutral colour | Default to `minimalist`, or `classic` if tailored (blazer, trousers, shirt dress) |

---

## 4. Brand priors (starting points, verify before use)

A brand prior adds a small score to the styles a brand is known for. It helps when a title carries no cue. The list comes from public articles and store pages found during research. Confirm each site is reachable with `python -m pipeline.run check` before relying on it, and edit the list as the real site list changes. Many of these brands also sell men's or kids' clothing; keep only items that pass the women's filter in Section 8.

| Brand | Prior styles (each +2) |
| --- | --- |
| Jaywalking (women's lines only) | streetwear, edgy |
| Bluorng | streetwear |
| Midnight LAW | streetwear, edgy |
| Toffle | streetwear |
| Bomaachi | streetwear |
| Smoke Wear | streetwear, edgy |
| NoughtOne | streetwear, edgy |
| Urban Suburban | boho, classic |
| Papa Don't Preach | edgy, ethnic_fusion |
| Doodlage | edgy, ethnic_fusion |
| Bungalow 8 | edgy, ethnic_fusion |
| The Wishing Tree | edgy, ethnic_fusion |
| Anomaly | minimalist |
| Meesha | minimalist, classic |
| Anavila | minimalist, traditional |
| Claraché | minimalist, classic |
| Haseena | minimalist |
| Dusk Attire | classic, minimalist |
| Qua Clothing | classic |
| Femmella | classic, minimalist |
| Vanaras | classic, minimalist |
| Ishaavi | minimalist, boho |
| trueBrowns | minimalist, ethnic_fusion |
| Two Point Two | minimalist, classic |
| BlissClub | sporty |
| HRX | sporty |
| Cultsport | sporty |
| Chkokko | sporty |
| Aastey | sporty |
| Bohemian Dream | boho |
| Saundh | boho, ethnic_fusion |
| BOHO-CHIC by Sukriti Jain | boho, glam |
| ituvana | boho |
| Biba | traditional, ethnic_fusion |
| Be Indie | ethnic_fusion, traditional |
| House of Indya | ethnic_fusion, glam |
| Westside (ethnic range) | traditional, classic |
| Libas | traditional, glam |
| Fabindia | traditional, minimalist |
| Kalki Fashion | glam, edgy, ethnic_fusion |
| Pernia's Pop-Up Shop | glam, ethnic_fusion |
| Aza Fashions | glam, ethnic_fusion |
| Mohey (Manyavar) | glam, traditional |
| Andaaz Fashion | glam, traditional |

Multi-brand sites (Pernia's, Aza Fashions, Nykaa Fashion) get no site-level prior for brands they only resell; set a prior per `vendor` field instead where the feed provides it.

### 4.1 Candidate websites by style

These are the Indian women's-fashion sites identified from public articles and store pages. **None has been checked for a usable product feed yet.** Run `python -m pipeline.run check` first, drop sites that fail, and add replacements. A domain is given only where it appeared in the research; for the others, confirm the domain before adding it to `sites.json`.

| Site | Styles it covers | Domain | What the research said |
| --- | --- | --- | --- |
| Jaywalking | streetwear, edgy | confirm | Edgy, oversized silhouettes; gender-fluid, men's and women's (keep women's only) |
| Bluorng | streetwear | confirm | Named GQ India's "Streetwear Label of the Year" for 2023 |
| Midnight LAW | streetwear, edgy | confirm | Founded 2018; vintage and retro aesthetics with punk influences; graphic tees |
| Toffle | streetwear | confirm | New Delhi; customised streetwear, tie-dye pieces |
| Smoke Wear | streetwear, edgy | confirm | Described as an edgy streetwear label with baggy, minimalistic cuts |
| NoughtOne | streetwear, edgy | confirm | Streetwear inspired by military uniforms |
| Bomaachi | streetwear | confirm | Streetwear label with a statement identity |
| Urban Suburban | boho, classic | confirm | Delhi-based women's label; comfortable, Indianised holiday wear |
| Papa Don't Preach | edgy, ethnic_fusion | confirm | Rebellious, streetwear-energy take on traditional designs |
| Doodlage | edgy, ethnic_fusion | confirm | Upcycled fabrics; eclectic fusion pieces, bold jackets |
| Bungalow 8 | edgy, ethnic_fusion | confirm | Bengaluru; luxe, edgy streetwear blending Indian textiles |
| The Wishing Tree | edgy, ethnic_fusion | confirm | Handcrafted kurtas and statement jackets with an edgy soul |
| Anomaly | minimalist | confirm | Founded 2015 by Medha Khosla; early in India's minimalist market |
| Meesha | minimalist, classic | confirm | Indian and French sensibilities; frontrunner in Indian minimalism |
| Anavila | minimalist, traditional | confirm | Minimalist label that employs rural women weavers |
| Claraché | minimalist, classic | confirm | Timeless pieces with its own aesthetic |
| Haseena | minimalist | confirm | Luxury in simplicity; indulgent, wearable staples |
| Dusk Attire | classic, minimalist | confirm | Targets metropolitan women aged 22 to 50 who want style and comfort |
| Qua Clothing | classic | confirm | Power-dressing label for women |
| Femmella | classic, minimalist | confirm | Prêt label since 2008; sold on Nykaa, Myntra and its own website |
| Vanaras | classic, minimalist | confirm | Timeless pieces: boyfriend blazers, slit pants, trench capes |
| Ishaavi | minimalist, boho | confirm | Artisanal minimal womenswear: palazzos and flowy dresses |
| trueBrowns | minimalist, ethnic_fusion | confirm | Minimal, flowy, urban ethnic silhouettes in light fabrics |
| Two Point Two | minimalist, classic | confirm | Elevates classic silhouettes; simple but powerful pieces |
| BlissClub | sporty | confirm | Women's activewear ("movewear") founded in 2020 in Bengaluru; leggings with pockets |
| HRX | sporty | confirm | One of India's first homegrown activewear brands (men's and women's; keep women's only) |
| Cultsport | sporty | confirm | Activewear competitor named alongside HRX and BlissClub |
| Chkokko | sporty | confirm | Athleisure for men and women (keep women's only) |
| Aastey | sporty | confirm | Sustainable athleisure brand |
| Bohemian Dream | boho | confirm | Homegrown label inspired by nomadic spirit; Indian tradition for modern life |
| Saundh | boho, ethnic_fusion | confirm | Boho-inspired ethnicwear with modern cuts and rich prints |
| BOHO-CHIC by Sukriti Jain | boho, glam | listed on nykaafashion.com | About 551 items on Nykaa Fashion's luxe section; lace, eyelet and sequin dresses |
| ituvana | boho | confirm | Breezy sarong-skirt styles with a laid-back lifestyle |
| Biba | traditional, ethnic_fusion | biba.in | Fusion kurta sets in sizes XS to 5XL; printed and asymmetric styles |
| Be Indie | ethnic_fusion, traditional | listed on ajio.com | Ethnic and fusion wear: layered kurtas, kurtas with jackets, palazzos |
| House of Indya | ethnic_fusion, glam | houseofindya.com | Indo-western kurta sets, anarkalis, traditional wear; prices in USD, confirm the INR storefront |
| Westside | traditional, classic | westside.com | Kurta sets from casual to heavily embroidered festive |
| Libas | traditional, glam | libas.in | Kurtas, sarees and party-wear dresses with sequins and zari lehengas |
| Fabindia | traditional, minimalist | confirm (listed on nykaafashion.com) | Sarees, kurtas, tunics, block-print dupattas; earthy, understated craft textiles |
| Kalki Fashion | glam, edgy, ethnic_fusion | kalkifashion.com | Party lehengas, cocktail collection, indo-western gowns, cape gowns |
| Pernia's Pop-Up Shop | glam, ethnic_fusion, boho | perniaspopupshop.com | Multi-brand designer store: party wear (1,327 products on its party page), lehengas, gowns, fusion dresses, boho dresses |
| Aza Fashions | glam, ethnic_fusion | azafashions.com | Designer lehengas from established and emerging designers; fusion lehengas |
| Mohey (Manyavar) | glam, traditional | manyavar.com/mohey | Party-wear and bridal lehengas |
| Andaaz Fashion | glam, traditional | andaazfashion.com | Party-wear lehenga cholis |
| Mirraw | glam, traditional | mirraw.com | Lehenga cholis, party-wear sarees and gowns |
| Nykaa Fashion (marketplace) | all ethnic styles | nykaafashion.com | Women's Indianwear page lists 244,951 items. Large multi-brand marketplace: check terms of use and bot protection before attempting; do not bypass blocks |

**Coverage by style** (which sites to rely on for each):

| Style | Main sites |
| --- | --- |
| minimalist | Anomaly, Meesha, Anavila, Claraché, Haseena, Ishaavi, trueBrowns, Two Point Two, Fabindia |
| classic | Qua Clothing, Dusk Attire, Femmella, Vanaras, Meesha, Urban Suburban, Westside |
| streetwear | Jaywalking, Bluorng, Midnight LAW, Toffle, Smoke Wear, NoughtOne, Bomaachi |
| boho | Bohemian Dream, Saundh, BOHO-CHIC by Sukriti Jain, ituvana, Ishaavi, Pernia's, Urban Suburban |
| sporty | BlissClub, HRX, Cultsport, Chkokko, Aastey |
| glam | Kalki Fashion, Libas, Pernia's, Aza Fashions, Mohey, Andaaz Fashion, Mirraw, House of Indya |
| ethnic_fusion | House of Indya, Biba, Be Indie, Kalki Fashion, Aza Fashions, Papa Don't Preach, Doodlage, Bungalow 8, The Wishing Tree |
| traditional | Fabindia, Biba, Libas, Westside, Anavila, Mohey, Andaaz Fashion, Mirraw |
| edgy | Papa Don't Preach, Doodlage, Bungalow 8, The Wishing Tree, Midnight LAW, Smoke Wear, NoughtOne, Kalki Fashion, Jaywalking |

**Sites deliberately left out:** large general marketplaces such as Myntra, Ajio and Flipkart. They sell every style, but they typically have heavy bot protection and strict terms, so they are not recommended unless the operator has confirmed that scraping is permitted. Ajio is mentioned above only because it hosts the Be Indie brand page; prefer the brand's own site.

Catalogue size note: only a few sizes appear in the research (Nykaa Fashion's women's Indianwear at 244,951 items, BOHO-CHIC at about 551, Pernia's party page at 1,327). All other counts are unknown until `check --count` reports them. Most single D2C brands are expected to hold hundreds to low thousands of women's items, so a total of 13,000 to 15,000 will likely need 20 to 30 working sites. Edgy, boho and sporty will probably be the thinnest styles.

---

## 5. Classification algorithm

Identical in method to the men's taxonomy, with one added style (`edgy`).

### 5.1 Inputs

For each product: `title`, `product_type`, `tags`, `handle`, `vendor`, `body_html`, variant `options` (colour), the site `name`, and the already-detected garment `category`, `colors` and `fabrics`.

### 5.2 Scoring

For every style, compute a numeric score:

1. **Keyword hits.** Each keyword rule in `style_rules_women.yaml` has a weight: `strong` = 3, `medium` = 2, `weak` = 1.
   - A hit in `title`, `product_type` or `tags` counts at full weight.
   - A hit in `body_html` counts at half weight, rounded down, and each style is capped at +3 from the description.
   - Each distinct rule counts once per product, however many times it appears.
2. **Negative keywords.** A style's `negative` list subtracts 2 per distinct hit.
3. **Brand prior.** Add +2 if the site or vendor has that style in its prior (Section 4).
4. **Palette signals** (weak, +1, at most +1 per style): neutrals for minimalist, earthy colours for boho, black or metallics for glam and edgy.
5. **Fabric signals** (weak, +1, at most +1 per style): linen or cotton for minimalist and boho, silk, velvet or satin for glam, faux leather for edgy, polyester or nylon blends for sporty, khadi or handloom for traditional.

### 5.3 Selecting labels

1. Apply the conflict rules in Section 3 (they may add, remove or force styles).
2. Let `top` be the highest score. If `top < 3`, apply the fallback defaults in Section 5.4.
3. Keep every style with `score >= max(3, 0.5 * top)`.
4. Sort by score (ties broken by this order: traditional, ethnic_fusion, glam, edgy, streetwear, sporty, boho, classic, minimalist). The first is `primary_style`. Keep at most 3 styles in `style_tags`.

### 5.4 Fallbacks (when `top < 3`)

1. Plain, unprinted item (no print, graphic or embellishment cue) in a neutral colour: `minimalist` for casual basics, `classic` for tailored basics.
2. Saree, kurta, anarkali, salwar or lehenga word with no further cue: `traditional`.
3. Otherwise: `unclassified`.

### 5.5 Confidence

Store `style_confidence`: `high` if `top >= 6` and the gap to the next style is at least 2; `medium` if `top >= 3`; `low` otherwise (including all fallbacks). The frontend may hide low-confidence items from style filters by default.

### 5.6 Optional refinement (SHOULD, not required for v1)

For items that are `unclassified`, `low` confidence, or have a top-two score gap of 1 or less, call a language model (and optionally a vision model on the product image) with a fixed prompt and a JSON-only response limited to the nine style IDs. Cache every response by product id. Record `style_source = "llm"`. Keep the rule-based result so the audit can compare both. `edgy` and `glam` are the styles most likely to benefit from image checks.

---

## 6. Output fields

The fields are the same as in the men's taxonomy, so a combined catalogue can use one schema.

| Field | Type | Description |
| --- | --- | --- |
| `primary_style` | TEXT | One of the ten IDs in Section 2 |
| `style_tags` | JSON array | Up to 3 style IDs, primary first |
| `style_scores` | JSON object | Score per style, for debugging and audit |
| `style_confidence` | TEXT | `high`, `medium` or `low` |
| `style_source` | TEXT | `rules` or `llm` |
| `catalogue_gender` | TEXT | `men` or `women` (add if the combined catalogue shares one table) |

Existing field change: rename `styles` to `wear_types` (garment sub-type: anarkali, cargo, maxi, leggings and so on).

Frontend changes: add a **Style** filter (the nine labels plus Unclassified) with a Men / Women switch, show the primary style as a tag on each card, and show facet counts like the other filters.

---

## 7. Rule data format (`pipeline/style_rules_women.yaml`)

Phrases are written in normalised form (lowercase, no punctuation). Multi-word phrases match as whole phrases.

```yaml
version: 1
thresholds: {min_score: 3, relative: 0.5, max_tags: 3}
styles:
  minimalist:
    strong: ["minimalist", "minimal", "essential", "solid", "plain", "clean", "capsule"]
    medium: ["slip dress", "straight fit", "wide leg trousers", "co ord", "knit top", "basic", "relaxed fit"]
    weak: ["neutral", "everyday", "effortless"]
    negative: ["graphic", "printed", "print", "embellished", "sequin", "embroidered", "ruffle", "tie dye"]
    palette: ["black", "white", "grey", "navy", "beige", "olive"]
    fabrics: ["cotton", "linen", "wool", "viscose"]
  classic:
    strong: ["tailored", "blazer", "trench", "pencil skirt", "shirt dress", "workwear", "power dressing", "formal"]
    medium: ["wrap dress", "pleated", "trousers", "button down", "striped", "checked", "houndstooth", "office"]
    weak: ["timeless", "smart casual", "structured", "midi"]
    negative: ["oversized", "graphic", "cropped", "distressed", "neon", "baggy"]
    palette: ["white", "black", "navy", "brown", "grey", "beige"]
    fabrics: ["cotton", "wool", "viscose"]
  streetwear:
    strong: ["streetwear", "oversized", "graphic", "baggy", "cargo", "drop shoulder", "varsity", "hoodie"]
    medium: ["parachute", "wide leg jeans", "puffer", "acid wash", "patchwork", "anime", "utility", "boxy", "co ord"]
    weak: ["urban", "street", "logo", "print", "printed", "slogan", "tee"]
    negative: ["formal", "tailored", "saree", "kurta", "lehenga", "bridal"]
    palette: []
    fabrics: ["fleece", "denim"]
  boho:
    strong: ["boho", "bohemian", "tiered", "peasant", "crochet", "macrame", "fringe", "tassel", "ikat", "broderie", "eyelet", "kaftan", "sarong"]
    medium: ["maxi", "flowy", "lace", "paisley", "floral", "tie dye", "block print", "resort", "hand painted", "smocked"]
    weak: ["earthy", "relaxed", "breezy", "printed"]
    negative: ["formal", "tailored", "gym", "leather", "studded"]
    palette: ["orange", "yellow", "brown", "green"]
    fabrics: ["cotton", "linen", "viscose"]
  sporty:
    strong: ["activewear", "athleisure", "movewear", "yoga", "gym", "training", "running", "workout", "leggings", "sports bra", "dry fit", "quick dry", "moisture wicking"]
    medium: ["tights", "track pants", "joggers", "jogger", "performance", "biker shorts", "compression", "athletic", "sports"]
    weak: ["active", "stretch", "lounge", "sweat"]
    negative: ["lehenga", "saree", "embroidered", "sequin", "gown"]
    palette: []
    fabrics: ["polyester", "nylon", "elastane"]
  glam:
    strong: ["sequin", "embellished", "gown", "cocktail", "party wear", "evening", "wedding", "bridal", "sangeet", "reception", "zari", "lehenga"]
    medium: ["velvet", "satin", "metallic", "bodycon", "sharara", "gharara", "stone work", "festive", "occasion", "statement", "shimmer"]
    weak: ["gold", "silver", "glitter", "luxe", "celebration"]
    negative: ["gym", "training", "plain tee", "basic"]
    palette: ["black", "red", "purple"]
    fabrics: ["silk", "viscose"]
  ethnic_fusion:
    strong: ["indo western", "indowestern", "fusion", "kurta jacket", "jacket set", "cape set", "dhoti pants", "crop top skirt", "pre draped saree", "saree gown", "dhoti saree"]
    medium: ["asymmetric kurta", "layered kurta", "kurta with jacket", "co ord kurta", "shrug", "ethnic dress", "lehenga with jacket", "belted saree", "ready to wear saree"]
    weak: ["modern ethnic", "contemporary kurta", "ethnic print"]
    negative: ["gym", "training"]
    palette: []
    fabrics: []
  traditional:
    strong: ["saree", "sari", "kurta", "kurti", "anarkali", "salwar", "patiala", "kurta set", "palazzo set", "churidar", "lehenga choli", "ghagra"]
    medium: ["chikankari", "bandhani", "ajrakh", "kalamkari", "banarasi", "kanjivaram", "chanderi", "patola", "phulkari", "handloom", "khadi", "dupatta", "sharara", "gharara"]
    weak: ["ethnic", "festive", "puja", "diwali", "eid", "handwoven", "craft", "block print"]
    negative: ["graphic", "oversized", "gym", "baggy", "studded"]
    palette: []
    fabrics: ["khadi", "cotton", "silk"]
  edgy:
    strong: ["edgy", "faux leather", "vegan leather", "leather", "studded", "studs", "corset", "bustier", "cut out", "cutout", "punk", "grunge", "gothic", "biker", "moto", "harness"]
    medium: ["chain", "hardware", "mesh", "sheer", "asymmetric", "asymmetrical", "deconstructed", "distressed", "ripped", "lace up", "spike", "all black"]
    weak: ["bold", "dark", "statement", "structured shoulder", "metallic"]
    negative: ["floral", "pastel", "ruffle", "bohemian", "peasant", "kurta", "saree"]
    palette: ["black", "grey"]
    fabrics: ["leather", "denim"]
brand_priors: {}   # filled from Section 4, keyed by site name or vendor
```

Notes for implementation:
- `fabrics` and `palette` refer to the pipeline's normalised fabric and colour names. Add `leather` and `khadi` to the fabric list in `classify.py` if they are missing.
- Words such as `solid`, `plain`, `print`, `chain`, `bold` and `dark` are ambiguous. Prefer phrase matches and rely on the threshold rather than adding more single words. Treat `lehenga`, `sharara` and `gharara` carefully: they appear in both `glam` and `traditional`, and the conflict rules in Section 3 decide the primary.
- Women's garment sub-types (`wear_types`) need their own list in `classify.py`: for example anarkali, a-line kurta, straight kurta, kurta set, saree, lehenga choli, sharara, maxi dress, midi dress, shirt dress, slip dress, jumpsuit, co-ord set, crop top, blouse, peplum, culottes, palazzo, leggings, jeggings, wide-leg jeans, mom jeans, cargo pants, blazer, shrug, cape.

---

## 8. Scope and filters for this catalogue

Include: women's tops, dresses, skirts, bottoms, co-ord sets, jumpsuits, ethnic sets (kurta sets, anarkalis, salwar suits, lehengas), sarees, gowns, knitwear, outerwear a woman would wear as clothing, and activewear (including leggings and sports tops).

Exclude: men's and kids' clothing, lingerie and innerwear (bras and briefs other than sports bras; sleepwear is out unless a later decision adds loungewear), footwear, bags, jewellery, belts, scarves, hats, standalone dupattas and stoles, unstitched dress material, blouse pieces sold alone, beauty and grooming, home goods, gift cards, bundles and combo packs.

Gender rule: keep an item only if `gender == "women"` or the item is explicitly unisex *and* sold in the site's women's collection. Items with `unspecified` gender are kept only when fetched from a women's-only collection feed. Many streetwear and activewear brands are gender-fluid; keep only their women's items. Log everything dropped by this rule.

---

## 9. Test cases (put in `tests/test_style_women.py`)

Each row is a unit test: input title (and site or tags where shown), expected primary style, and expected secondary styles (a subset match is enough).

| # | Input | Expected primary | Expected also contains |
| --- | --- | --- | --- |
| 1 | "Oversized Graphic Tee" (site: jaywalking, women's feed) | streetwear | |
| 2 | "Plain Black Slip Dress" | minimalist | |
| 3 | "Tailored Blazer - Camel" | classic | |
| 4 | "Pencil Skirt with Pleats" | classic | |
| 5 | "High Waist Gym Leggings with Pockets" (site: blissclub) | sporty | |
| 6 | "Cotton Printed Kurta Set with Palazzo and Dupatta" | traditional | |
| 7 | "Banarasi Silk Saree with Blouse" | traditional | |
| 8 | "Embellished Sequin Saree" | glam | traditional |
| 9 | "Pre-Draped Saree Gown" | ethnic_fusion | |
| 10 | "Indo Western Kurta with Cape - Jacket Set" | ethnic_fusion | traditional |
| 11 | "Party Wear Sequin Lehenga Choli" | glam | traditional |
| 12 | "Tiered Floral Maxi Dress" | boho | |
| 13 | "Broderie Eyelet Midi Dress" | boho | |
| 14 | "Faux Leather Studded Biker Jacket" | edgy | |
| 15 | "Black Cut-Out Corset Mini Dress" | edgy | glam |
| 16 | "Mesh Layered Top with Chain Detail" | edgy | |
| 17 | "Oversized Hoodie with Punk Graphic" | streetwear | edgy |
| 18 | "Sequin Evening Gown - Wine" | glam | |
| 19 | "Crop Top with Ethnic Skirt" | ethnic_fusion | |
| 20 | "Chikankari Anarkali Kurta - Ivory" | traditional | |
| 21 | "Plain Solid Linen Shirt" (site: anavila) | minimalist | |
| 22 | "Dupatta Stole" or "Gift Card" | not classified (out of scope, filtered earlier) | |

Also test: determinism (same input, same output), maximum three tags, description-only hits count at half weight and are capped, and each conflict rule in Section 3.

---

## 10. Quality targets and audit

1. After the first real scrape, sample **20 items per style** (nine styles, so 180 items in total, drawn across sites). A reviewer marks whether each assigned style is correct.
2. Targets: at least **80% precision** for each style, and **at most 10% of items** unclassified.
3. For any style under target, inspect its false positives and adjust keywords, negatives or conflict rules, then rerun the tests. `edgy` versus `streetwear` and `glam` versus `edgy` are the pairs most likely to need work.
4. Report per style: item count, precision from the audit, and the top 10 keywords that fired. Thin styles (edgy, boho, sporty) may fall short on count; report the number rather than padding with wrongly labelled items.
5. Report the share of items that are `high`, `medium` and `low` confidence.

---

## 11. Balancing the catalogue

1. Scrape all women's items per site (no per-category cap), then classify them.
2. The target total for the women's catalogue has not been fixed yet. Default to the same 13,000 to 15,000 range as the men's catalogue unless the owner decides otherwise. For nine styles that means roughly 1,450 to 1,650 items per style as `primary_style`.
3. If a style cannot reach its target, do not relabel items to fill it; instead take more items from sites strong in that style, or accept and report the shortfall.
4. Cap any single site at about 12% of the final catalogue so no brand dominates.
5. Remove duplicates and limit look-alikes (for example no more than 10 white shirts in one style) using the approach already discussed for the men's catalogue; that step is handled separately.
6. Record the final counts per style and per site in `catalogue_report_women.md`.

---

## 12. Implementation checklist for Claude Code

- [ ] Create `pipeline/style_rules_women.yaml` from Section 7 and load it by catalogue gender (one shared engine, two rule files).
- [ ] Extend `pipeline/style.py` to support the `edgy` style and the Section 3 conflict rules for women.
- [ ] Add women's garment categories and sub-types (Section 7 notes) to `classify.py`.
- [ ] Call the style engine from `classify_product` and store the Section 6 fields.
- [ ] Rename `styles` to `wear_types` if not already done; add the new columns and migrate SQLite.
- [ ] Add the Style filter (nine labels) and a Men / Women switch to `web/index.html`.
- [ ] Add `tests/test_style_women.py` covering Section 9.
- [ ] Apply the women's-only scope in Section 8.
- [ ] Add a `--count` option to `check` that reports how many women's items each site holds.
- [ ] Run the audit in Section 10 and tune the rules.
- [ ] Produce `catalogue_report_women.md` (Section 11).
- [ ] Update `SRS.md` and `README.md` to reference this document.

# Software Requirements Specification: Garment Catalogue Pipeline

| Field | Value |
| --- | --- |
| Document | SRS.md |
| Version | 3.2 (adds the size trim, diversity cap, grouping, outfit recommender and the new analytics; 3.1 added the women's catalogue) |
| Date | 2026-11-25 |
| Author | Vansh (requirements), drafted with Claude |
| Status | Implemented. Current catalogues after the trims: men 6,525 items (`catalogue_report.md`), women 11,814 items (`catalogue_report_women.md`). As built: men 13,957 garments, women 13,614 garments. |

RFC 2119 keywords apply. IDs are stable; reference them in commits and tests.

## 1. Scope

This version builds a **men's** catalogue of 13,000–15,000 garments from Indian
fashion websites. The eight fashion styles and their separation rules are
defined in `style_taxonomy_men.md`, which is part of this specification:

- minimalist, classic, streetwear, boho;
- sporty, glam, ethnic fusion, traditional.

For each garment the pipeline:

- extracts the nine parameters, reading the site's own data first;
- assigns a price band, a primary style, up to two secondary styles, and a
  confidence;
- draws a front-and-back technical flat sketch of the garment alone;
- stores everything in SQLite.

A static frontend, served on this computer only, provides a filterable
catalogue and a dynamic analytics dashboard across all sites.

**Sites (v3.0, 2026-11-20).** `sites.json` lists 41 Indian storefronts with a
public Shopify feed that robots.txt allows. Each site's men's items are found in
one of two ways:

- for men-only stores, through `default_gender`;
- for mixed stores, through their men's collections (`men_collections`).

Sites without a usable feed are recorded in the README and left out. The
Snitch-formal and Bonkers databases are kept in `data/backup_*`.

Out of scope:

- kids' clothing and innerwear (women's clothing is covered by section 2.8);
- marketplaces with bot protection (Myntra, Ajio, Flipkart, Nykaa);
- logged-in pages;
- ML training.

## 2. Functional requirements

### 2.1 Site and configuration

| ID | Priority | Requirement |
| --- | --- | --- |
| FR-SITE-1 | MUST | `sites.json` lists the site with `name`, `base_url`, `currency`, `price_bands` and optional `platform` (default `shopify`) and `collections`. |
| FR-SITE-2 | MUST | `check` tests robots.txt and the product feed and prints `OK`, `BLOCKED` or `FAIL` with a reason. |
| FR-SITE-3 | MUST | `params` samples the live site and prints which parameters the site itself publishes: field label, variant option or tags, with coverage %. It also prints the share of each parameter that comes from each source. |

### 2.2 Scraping by price band

| ID | Priority | Requirement |
| --- | --- | --- |
| FR-SCR-1 | MUST | Every item SHALL get a `price_band` from the site's band thresholds (default cheap < 800, affordable 800–1,499, luxury ≥ 1,500, in the store currency). The price is the lowest variant price; MRP and discount % are stored. |
| FR-SCR-2 | MUST | The scraper SHALL fill up to `--per-cell` items (default 20, 0 = unlimited) for each (price band × category) cell, and stop requesting pages once every cell is full. |
| FR-SCR-3 | MUST | `--bands` and `--categories` SHALL restrict scraping to the named bands or categories. |
| FR-SCR-4 | MUST | Products without images SHALL be skipped. Products SHALL be de-duplicated by id. |
| FR-SCR-5 | MUST | robots.txt SHALL be honoured (a disallowed feed gives status `blocked`). Requests SHALL be throttled (`--delay`, default 1 s). 429 and 5xx responses SHALL be retried with backoff. The User-Agent SHALL carry the contact address from `PIPELINE_CONTACT`, and a warning SHALL be printed while it is the placeholder. |
| FR-SCR-6 | MUST | Non-Shopify sites plug in through `SiteAdapter.iter_products()` and `register_adapter()`, without changes to classification or storage. |
| FR-SCR-7 | MUST | The status SHALL be `short` when a whole price band has no stock, and `error` or `blocked` on failure. A band × category count matrix SHALL be printed and logged. |

### 2.3 Parameters

| ID | Priority | Requirement |
| --- | --- | --- |
| FR-PAR-1 | MUST | Every item SHALL carry these nine parameters: **colour, secondary colour, pattern, fit, fabric, sleeve length, neckline, occasion, size**. It SHALL also carry category (15 classes), department, gender, price, MRP, discount and price band. |
| FR-PAR-2 | MUST | Values SHALL be taken from labelled site fields first, then tags, title, description, image pixels and category default, in that order. `attr_source` SHALL record the source per parameter. |
| FR-PAR-3 | MUST | Fabric SHALL parse the composition into fibre shares (e.g. `{"cotton": 60, "polyester": 40}`) and GSM. Size SHALL list all sizes and the sizes in stock. Colour SHALL keep the site's own colour name alongside the normalised palette colour. |
| FR-PAR-4 | MUST | Sleeve length and neckline SHALL be `n/a` for bottomwear. Vague marketing words in descriptions SHALL NOT set a parameter. |
| FR-PAR-5 | MUST | Accessories, innerwear, footwear and kids' items SHALL be out of scope. Colour words such as "bottle green" and slang such as "no cap" SHALL NOT exclude garments. |
| FR-PAR-6 | MUST | Every rule change SHALL come with a unit test. |

### 2.4 Flat images

| ID | Priority | Requirement |
| --- | --- | --- |
| FR-SKT-1 | MUST | Every catalogue item SHALL have a flat sketch: an SVG at `web/sketch/<site>/<id>.svg`, garment only, front and back views, solid colour fill with outline and stitch lines, drawn from its category, fit, sleeve, neckline, colour, secondary colour, pattern and wear types (`pipeline/sketch.py`). |

The photo cut-out requirements below remain available through `images` for
small samples.


| ID | Priority | Requirement |
| --- | --- | --- |
| FR-IMG-1 | MUST | `images` SHALL download each item's photos and cut out the garment only: no person, no background. It SHALL save up to `--max-views` (default 4) angles as square transparent PNGs under `web/flat/<site>/<id>/`. |
| FR-IMG-2 | MUST | The garment region SHALL match the item: upper body for topwear, lower body for bottomwear, top + bottom for co-ord sets, everything for dresses. |
| FR-IMG-3 | MUST | Views SHALL be rejected if empty, frame-filling or edge-cropped (close-ups), fragmented or ragged, or duplicates. The rejection reasons SHALL be reported. |
| FR-IMG-4 | MUST | The garment pixels SHALL yield `image_colors` and SHALL fill a missing secondary colour (source `image`). |
| FR-IMG-5 | MUST | The step SHALL be resumable, and a rescrape SHALL keep existing flat images. A no-ML `plain` segmenter SHALL exist for tests and packshots. |

### 2.5 Frontend

| ID | Priority | Requirement |
| --- | --- | --- |
| FR-UI-1 | MUST | The Catalogue tab SHALL show cards (flat cut-out or site photo), facet filters with live counts (OR within a facet, AND across facets), colour swatches, search, sort, load more, and a detail drawer with every angle and each parameter with its source. |
| FR-UI-2 | MUST | The Analytics tab SHALL show summary tables in percent for **colour, pattern, fit and fabric** of the items the filters leave (value, % of items, item count), with one line giving the number and share of items in view. Fit and fabric SHALL count only items that have one. No charts. Clicking a row SHALL filter by that value. |
| FR-UI-6 | MUST | The header SHALL have one row of dropdown filters (Department, Style, Category, Site, Price band, Colour, Occasion, Gender); each option SHALL show its share of the items the other filters leave. Every card SHALL carry a style tag. |
| FR-UI-3 | MUST | The filters SHALL apply to the Catalogue, Analytics and Outfits tabs. Active filters SHALL be shown as removable pills with Clear all. |
| FR-UI-4 | MUST | Scraped text SHALL be HTML-escaped, and URLs restricted to http(s) or local `flat/` paths. A broken image SHALL NOT break a card. A missing `catalogue.json` SHALL show an instruction. |
| FR-UI-5 | SHOULD | The UI SHOULD support light and dark themes and phone widths without horizontal scroll. |
| FR-UI-7 | MUST | The Catalogue tab SHALL offer **Group similar**: items grouped by category › an attribute (colour › print by default; print, fit, fabric, sleeve, neckline or sub-type) with a heading and count per group, the remaining parameters ordering items inside a group. Clicking a heading SHALL filter to that group. |
| FR-UI-8 | MUST | The server SHALL send pages and scripts with `Cache-Control: no-cache` so a normal refresh shows the latest UI. |

### 2.6 Styles and catalogue balance (see `style_taxonomy_men.md`)

| ID | Priority | Requirement |
| --- | --- | --- |
| FR-STY-1 | MUST | Every item SHALL get `primary_style`, `style_tags` (≤ 3), `style_scores`, `style_confidence` and `style_source`, computed by `pipeline/style.py` from the rules in `pipeline/style_rules.yaml` (taxonomy §5–§7). |
| FR-STY-2 | MUST | Only men's items SHALL be kept. Unisex or unlabelled items are kept only from a men-only store or a men's collection, and everything dropped is counted (taxonomy §8). |
| FR-STY-3 | MUST | Exact duplicates (title + photo) and near-duplicates (title + colour within a site) SHALL be removed. The catalogue SHALL aim for 1,600–1,900 items per style, with no site above 12%, and unclassified items are left out, never relabelled (taxonomy §11). |
| FR-STY-4 | MUST | `build` SHALL write `catalogue_report.md` with counts per style and site, top keywords per style, the confidence split, the drop reasons and shortfalls. `audit` SHALL print a random sample per style for the §10 review. |
| FR-STY-5 | MUST | The garment sub-type field SHALL be called `wear_types`. |

### 2.6b Footwear and accessories

| ID | Priority | Requirement |
| --- | --- | --- |
| FR-ACC-1 | MUST | `build` SHALL also collect every men's footwear and accessory item from the same feeds, under the same men's scope (plus `men_accessory_collections`), without changing the garment catalogue. |
| FR-ACC-2 | MUST | Categories: shoes, sandals and ethnic footwear; and belt, wallet, bag, cap, sunglasses, tie, socks, watch, jewellery, scarf and ethnic accessory. Styles come from `accessory_styles`. Garment sets sold with a dupatta or safa are not accessories. |
| FR-ACC-3 | MUST | Every footwear item SHALL get a side and top sketch, and every accessory a front and back sketch. The UI SHALL filter by department. |

### 2.7 Storage and CLI

| ID | Priority | Requirement |
| --- | --- | --- |
| FR-STO-1 | MUST | A site's rows SHALL be replaced in one transaction. A failed or blocked run SHALL NOT delete good data. One `scrape_runs` row per run SHALL be logged. |
| FR-STO-2 | MUST | A v1 database SHALL be preserved as `items_v1` rather than deleted. |
| FR-CLI-1 | MUST | The commands SHALL be `check` (`--count`), `fetch`, `build`, `scrape` (fetch + build), `sketch`, `audit`, `params`, `images`, `export`, `report` and `serve`. `fetch` caches raw feeds so `build` runs offline. The trim steps are `python -m pipeline.size_trim` (`--accessories`) and `python -m pipeline.diversity_cap`, each with `--gender` and `--dry-run`. |

### 2.8 Women's catalogue (v3.1, see `style_taxonomy_women.md`)

| ID | Priority | Requirement |
| --- | --- | --- |
| FR-WOM-1 | MUST | Every command SHALL accept `--gender women` and then use `sites_women.json`, `data/raw_women/`, `data/catalogue_women.db`, `web/catalogue_women.json`, `web/sketch_women/` and `catalogue_report_women.md`. A women's run SHALL NOT modify any men's file or change the men's catalogue. |
| FR-WOM-2 | MUST | One style engine SHALL load `style_rules.yaml` (men) or `style_rules_women.yaml` (women); the women's catalogue uses nine styles (adds `edgy`) and the women's section 3 conflict rules. |
| FR-WOM-3 | MUST | Women's scope (taxonomy section 8): keep gender women; unisex or unlabelled items only from a women-only store or a `women_collections` collection. Lingerie (except sports bras), sleepwear, swimwear, kids', unstitched material and combo packs SHALL be excluded, with drop reasons counted. |
| FR-WOM-4 | MUST | Women's garments SHALL target 1,450-1,650 per style and 13,000-15,000 in total, with no site above 12%. Footwear and accessories SHALL be collected afterwards without changing the garments. |
| FR-WOM-5 | MUST | Every women's item SHALL get a front/back (footwear: side/top) sketch drawn by `pipeline/sketch_women.py`. |
| FR-WOM-6 | MUST | The UI SHALL have a Men / Women switch that loads each catalogue with its own styles (nine for women), filters and analytics. |

### 2.9 Trimming (v3.2)

| ID | Priority | Requirement |
| --- | --- | --- |
| FR-TRIM-1 | MUST | **Size trim** (`pipeline/size_trim.py`): items whose detail-panel parameters all match (style, wear type, category, gender, colour, secondary colour, pattern, fit, fabric, sleeve, neckline, occasion) SHALL keep the fewest items that cover every size the group offers; the rest SHALL be deleted from the catalogue database, its export and their sketches. Clothes by default; footwear and accessories with `--accessories`. |
| FR-TRIM-2 | MUST | **Diversity cap** (`pipeline/diversity_cap.py`): at most `--cap` (10) items per style x category x colour, picked round-robin across varieties (pattern, fit, fabric, sleeve, neckline, sub-type) with at most `--per-variety` (3) of each. A backup SHALL be written to `data/backup_before_diversity/` before deleting. |
| FR-TRIM-3 | MUST | The trims SHALL NOT touch the raw feeds. After any `build` or `scrape`, they SHALL be rerun in the order size trim, size trim `--accessories`, diversity cap. |

### 2.10 Outfit recommender (v3.2, see `outfit_styling_rules.md`)

| ID | Priority | Requirement |
| --- | --- | --- |
| FR-REC-1 | MUST | `web/recommend.js` SHALL build outfits in the browser from the catalogue fields, following the templates, must-match rules, scored rules and choice rules of `outfit_styling_rules.md`. |
| FR-REC-2 | MUST | The Outfits tab SHALL find every outfit the catalogue can make (no cap) for a chosen outfit type, style, occasion, budget and size, showing a live count, the first 48 at once and "Show 48 more" for the rest; each outfit SHALL show its pieces' sketches, a short reason, the rules met and the total price. |
| FR-REC-3 | MUST | The item drawer SHALL show **Complete the look**: up to 3 outfits built around that item, with "Other looks". |
| FR-REC-4 | MUST | Within one set a garment SHALL appear once and a footwear or accessory item at most three times. Pieces whose title contradicts their category SHALL never be suggested. |
| FR-REC-5 | MUST | `node tests/test_recommend.js` SHALL pass. |

## 3. Non-functional requirements

| ID | Requirement |
| --- | --- |
| NFR-LEGAL-1 | Respect robots.txt. Never circumvent blocks (no proxies, header spoofing or CAPTCHA solving). Review the site's terms before production use. |
| NFR-LEGAL-2 | Scraped data, photos and derived sketches are for internal use only. `serve` SHALL bind to 127.0.0.1 only. The public tunnel (`serve_live.py` + cloudflared) has been removed and SHALL NOT be reintroduced. |
| NFR-MNT-1 | Rules live in `classify.py`, fetching in `scrape.py`, persistence in `store.py` and image processing in `imaging.py`. |
| NFR-MNT-2 | `python -m pytest tests` passes with no network access. |
| NFR-SEC-1 | No credentials or secrets in code or config. The contact address comes from the environment. |
| NFR-DOC-1 | The README documents setup, commands, parameter sources, the schema and known limitations. |

## 4. Acceptance criteria

1. `pytest` passes offline (247 tests, including every section 9 case of both taxonomies), and `node tests/test_recommend.js` passes (6 tests).
2. `check --count` prints OK and a men's count for each usable site.
3. `build` produces 13,000–15,000 items. Each style meets 1,600–1,900 or is
   reported as short with its pool exhausted, and unclassified is ≤ 10% of the
   pool.
4. The §10 audit (20 items per style) reaches ≥ 80% precision per style.
5. Every item has a front/back sketch, title, URL, category, gender (men or
   unisex), price band and primary style.
6. Changing a dropdown filter updates the Catalogue, Analytics and Outfits tabs,
   and Clear all restores the full catalogue. There are no console errors and no
   horizontal scroll at phone width.
7. Every style returns outfits in the Outfits tab; an empty result happens only
   for contradictory choices (for example an Indian outfit in streetwear).

## 5. Known limitations

- **Thin styles:** boho (1,512) and ethnic fusion (1,309) fall short of 1,600
  because every qualifying item in the pool is already used. Adding boho or
  Indo-western sites with open feeds would close the gap.
- **Keyword rules:** opaque product names (for example "APTO", "SAKAH-WH") get
  their style from tags, the brand prior or a fallback, so they carry medium or
  low confidence.
- **Sketches:** they are parametric drawings from the extracted attributes, not
  traces of the photos. Unusual cuts are drawn as their nearest template.
- **Women's edgy:** 814 items, short of 1,450; every item in the pool with a
  real edgy cue is used. More edgy labels with open feeds would close the gap.
- **Women's site list:** about 20 brands named in `style_taxonomy_women.md` have
  no usable public feed (see README) and are replaced by other Indian labels.
- **Trims are text-based:** the size trim and diversity cap compare extracted
  parameters, not photos, so two different products with identical parameters
  count as the same look. The size trim is permanent; only the diversity cap
  has a backup.
- **Recommender:** outfits rely on the extracted tags; a misread colour or a
  mislabelled item can still enter an outfit. Men's ethnic footwear is thin (2
  items), so men's kurta outfits often use sandals or loafers.
- **Price bands:** cheap < ₹1,000, affordable ₹1,000–2,499, luxury ≥ ₹2,500 for
  every site.

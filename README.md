# Men's style catalogue: Indian fashion sites

This pipeline builds a men's catalogue from 41 Indian storefronts (and a
separate women's catalogue from 77). It sorts every garment into one of the
eight fashion styles in
[`style_taxonomy_men.md`](style_taxonomy_men.md):

- minimalist, classic, streetwear, boho;
- sporty, glam, ethnic fusion, traditional.

Every item also gets:

- the nine parameters (colour, secondary colour, pattern, fit, fabric, sleeve
  length, neckline, occasion and size) and a price band;
- a **front and back technical flat sketch**, drawn from its attributes.

A local web page shows the catalogue, an analytics view and an outfit
recommender.

There is also a separate **women's catalogue** (nine styles). It is built by
the same commands with `--gender women`; see [Women's catalogue](#womens-catalogue).
The header **Men / Women** switch flips the page between the two.

**Current catalogues** (after the size trim and diversity cap, see
[Trimming](#trimming-one-per-size-and-a-diversity-cap)):

| | Clothes | Footwear | Accessories | Total | Report |
| --- | ---: | ---: | ---: | ---: | --- |
| Men | 5,121 | 446 | 958 | **6,525** | [`catalogue_report.md`](catalogue_report.md) |
| Women | 7,458 | 1,102 | 3,254 | **11,814** | [`catalogue_report_women.md`](catalogue_report_women.md) |

As first built, the men's catalogue held 17,445 items (13,957 garments, chosen
from a men's pool of 72,330) and the women's 32,882 (13,614 garments).

```
sites.json ─▶ fetch     public Shopify feeds of 41 sites (+ men's collections) ─▶ data/raw/*.json.gz
           ─▶ build     classify.py  category + 9 parameters
                        style.py     8 styles from style_rules.yaml (taxonomy §5)
                        build.py     men's scope (§8) ▸ dedupe ▸ balance by style, ≤12% per site (§11)
                        sketch.py    front/back flat SVG per item ─▶ web/sketch/<site>/<id>.svg
                        store.py     SQLite data/catalogue.db ─▶ web/catalogue.json
                        run.py       catalogue_report.md
           ─▶ size_trim     one item per size among items with identical parameters
           ─▶ diversity_cap at most 10 per style × category × colour, varied
           ─▶ serve     http://localhost:8000 (this computer only)
                        web/recommend.js  outfits from outfit_styling_rules.md
```

## Run

```bash
pip install -r requirements.txt
set PIPELINE_CONTACT=you@company.com        # contact in the User-Agent (export … on macOS/Linux)
python -m pipeline.run check --count        # feed reachable? robots ok? men's items per site
python -m pipeline.run scrape               # fetch + build (≈15 min fetch, ≈4 min build)
python -m pipeline.size_trim                # one item per size (clothes)
python -m pipeline.size_trim --accessories  # the same for footwear and accessories
python -m pipeline.diversity_cap            # at most 10 per style × category × colour
python -m pipeline.run serve                # open http://localhost:8000
```

A rebuild brings back every item the trims removed, so run the three trim steps
again, in this order, after any `build` or `scrape`. Each takes `--gender men`,
`--gender women` or `both` (the default), and `--dry-run` prints the counts
without changing anything.

The steps can also be run on their own:

| Command | What it does |
| --- | --- |
| `fetch` | Downloads every site's public feed and its men's-collection membership into `data/raw/`. Only this step uses the network. |
| `build` | Classifies, scopes, deduplicates and balances the cached feeds. Then it draws the sketches, stores, exports and writes the report. It runs offline, so you can tune `style_rules.yaml` and rerun it. |
| `audit --seed N` | Prints 20 random items per style for the precision review (taxonomy §10). |
| `sketch` | Redraws every flat sketch. |
| `report` | Prints counts per style, site and band. |
| `export` | Rebuilds `web/catalogue.json` from the database. |
| `images` | Optional photo cut-outs with rembg (slow; for a small sample only). |
| `params` | Shows which parameters a site publishes. |
| `scrape-quota` | The older per-(band × category) quota scrape of one site. |

| `build` flag | Default | Purpose |
| --- | --- | --- |
| `--per-style` | 1875 | Items per primary style |
| `--site-cap` | 0.12 | Largest share of the catalogue one site may hold |
| `--min-total`, `--max-total` | 13000, 15000 | Catalogue size target |
| `--only a,b` | | Limit to some sites |

## Local only

`serve` binds to `127.0.0.1`, so the page is reachable from this computer and
nowhere else:

- no other device on your network can open it;
- there is no public tunnel. The earlier `serve_live.py` / cloudflared setup has
  been removed.

`catalogue.json` is sent gzip-compressed, so the page loads in about a second.
Pages and scripts are sent with `Cache-Control: no-cache`, so a normal refresh
always shows the latest version (after an update, press Ctrl + F5 once if the
browser still holds an older copy).

## Footwear and accessories

`build` also collects **every men's footwear and accessory product** on the same
sites: **3,488 items**, 1,426 footwear and 2,062 accessories. They come from the
same cached feeds and follow the same men's rules. They are added next to the
garments, which stay exactly the same: the build checks the 13,957 garment IDs.
Use `--no-accessories` to build garments only.

| Department | Categories |
| --- | --- |
| Footwear | shoes (sneakers, formal, loafers, boots, sports), sandals and slides, ethnic footwear (mojari, jutti, kolhapuri) |
| Accessories | caps and hats, socks, belts, bags, sunglasses, ties / bow ties / pocket squares, jewellery, scarves / stoles / dupattas, wallets, watches, safas / kalangis |

How they're classified:

- **Category:** the last noun of the title decides between garment and
  accessory. "Chain Print Shirt" is a shirt; "Leather Belt" is a belt.
- **Style:** footwear and accessories use their own keyword lists
  (`accessory_styles` in `style_rules.yaml`), plus a few category rules:
  - mojaris, safas and stoles are traditional (glam with zari or kalangi);
  - sports shoes are sporty, and formal shoes and loafers are classic;
  - plain belts, wallets, ties and watches fall back to classic.

What's left out:

- **Unisex accessories:** caps and socks that streetwear stores (Capsul, Bonkers
  Corner, Urban Monkey, Bluorng) sell outside any men's collection.
- **Women's items:** heels, handbags, bangles and similar.
- **Not accessories:** fragrance, gift cards and shoe-care kits.
- **Dupatta sets:** 484 kurta + pant + dupatta sets, which are clothing.

In the UI, the header **Department** control switches between topwear,
bottomwear, full-body, footwear and accessories. Footwear sketches show a
**side view and a top view**.

## Sites

`sites.json` lists 41 storefronts that passed `check`. Each one has a public
Shopify feed that robots.txt allows.

- **Men-only stores** (Snitch, JadeBlue, Jompers, Kisah, Sojanya, Wrogn,
  Blackberrys, …) set `"default_gender": "men"`.
- **Mixed stores** list their `men_collections`. An item with no gender label
  counts only if it appears in one of those collections (taxonomy §8). Everything
  dropped is counted in the report.

Sites checked and left out:

| Site(s) | Reason |
| --- | --- |
| The Souled Store, Bewakoof, DaMENSCH, XYXX, Jaypore, House of Indya, Tasva, Manyavar, Fabindia | No public product feed |
| Bombay Shirt Company | Feed returns 403 |
| iTokri | Feed returns 400 |
| DFYNE, Norblack Norwhite | Priced in foreign currency |
| Vamas, Vastranand, Raw Mango, Studio Rigu, Proathlix | Little or no men's clothing |

Bluorng and SIX5SIX are listed but contribute 0 items, and Jaywalking only 8.
Their products are unisex with no men's collection, so §8 drops them. The 41
sites in the report therefore include three that add little or nothing.

## Styles (taxonomy §5)

Keyword rules live in `pipeline/style_rules.yaml`.

| Rule | Detail |
| --- | --- |
| Keyword weights | strong 3, medium 2, weak 1; negative −2 |
| Description hits | Half weight, capped at +3 per style |
| Brand prior | +2 |
| Palette, fabric | +1 each |
| Selection | §3 conflict rules first, then threshold 3 / 50% of the top score, at most 3 tags, §5.4 fallbacks |

These tuning rules were added after the precision audit:

- **Pairing advice:** garment nouns in descriptions ("pair with chinos") are
  ignored.
- **Real cue required:** palette, fabric and weak words alone cannot lift a style
  above 2.
- **Minimalist:** never applies to a printed or embellished title.
- **Ethnic fusion:**
  - kurta + jacket sets and jodhpuri suits are ethnic fusion;
  - a Western cut that the store files under ethnic wear is ethnic fusion.
- **Activewear brands:** oversized, cargo or baggy items from these brands are
  streetwear.

The final audit, done by hand on 20 random items per style, measured:

| Style | Precision |
| --- | ---: |
| Glam | 95% |
| Sporty | 95% |
| Classic | 95% |
| Minimalist | 90% |
| Boho | 90% |
| Ethnic fusion | 90% |
| Traditional | 90% |
| Streetwear | ~82% |

The balancer takes high-confidence items first (spread across sites), then
medium, then low. Unclassified is 8.5% of the pool; those items are left
out of the catalogue rather than relabelled.

**Shortfalls (reported, not padded):** boho 1,512 and ethnic fusion 1,309. In
both cases every qualifying item in the pool is already used.

## Flat sketches

`pipeline/sketch.py` draws an SVG tech-pack flat for every item: the garment
only, front and back, solid fill, dark outline and dashed stitching. The drawing
follows the item's data:

| Data | Drawing |
| --- | --- |
| category | silhouette (tee, shirt, polo, hoodie, sweater, jacket, blazer, kurta, Nehru jacket, sherwani, trousers, jeans, joggers, shorts, pyjama, dhoti / churidar, and co-ord / kurta sets with the jacket layered on top) |
| fit | width, drop shoulders, cropped length, leg shape |
| sleeve length | sleeveless, short, three-quarter or long |
| neckline | round, V, polo, shirt collar, Cuban collar, mandarin, hood, high neck or henley |
| colour | fill (the site's colour name first) |
| pattern and secondary colour | stripes, checks, print, embroidery, tie-dye, camo, colour block or wash |
| wear types | details such as cargo pockets, jeans pockets, ribs and drawstrings |

All 13,957 sketches take about 20 seconds to draw. They are drawings made from
the data, not photos: an unusual cut is shown as its closest template.

## Trimming: one per size and a diversity cap

Two steps run on the built catalogue databases (they never touch the raw feeds
in `data/raw/` and `data/raw_women/`):

1. **Size trim** (`pipeline/size_trim.py`). Items whose detail-panel parameters
   all match (style, wear type, category, gender, colour, secondary colour,
   pattern, fit, fabric, sleeve length, neckline, occasion) form a group. Each
   group keeps the fewest items that still cover every size it offers (an item
   with no size list counts as "one size"); the rest are deleted permanently,
   with their sketch files. Clothes by default, footwear and accessories with
   `--accessories`.
2. **Diversity cap** (`pipeline/diversity_cap.py`). At most 10 items per
   style × category × colour (for example, minimalist white shirts), chosen
   round-robin across varieties (pattern, fit, fabric, sleeve, neckline,
   sub-type), at most 3 of each. Change the numbers with `--cap` and
   `--per-variety`. The catalogues from just before this step are kept in
   `data/backup_before_diversity/`; copy them back into `data/` and `web/` to undo.

| Step | Men | Women |
| --- | ---: | ---: |
| As built | 17,445 | 32,882 |
| Size trim, clothes | 14,042 | 31,381 |
| Size trim, footwear and accessories | 12,463 | 23,005 |
| Diversity cap | **6,525** | **11,814** |

## Frontend

Header (all tabs):

- **Men / Women** switch;
- one row of **dropdown filters**: Department, Style, Category, Site, Price
  band, Colour, Occasion and Gender. Each option shows its share, for example
  "shirt · 11%". They filter all three tabs; active filters also show as pills
  with "Clear all".

The **Catalogue** tab has:

- sketch cards with a style tag (switch to site photos with the checkbox);
- **Group similar**: items of one category are grouped under headings such as
  "Shirt › White › Solid", by colour › print (default), print, fit, fabric,
  sleeve, neckline or sub-type; inside a group, items are ordered by their
  remaining parameters, so near-identical pieces sit together. Click a heading
  to filter to that group;
- facet chips with live counts in the sidebar, search, and sorting by price or
  discount;
- a drawer with the large front/back sketch, style scores, every parameter
  with its source, **Complete the look** (3 outfits built around the item) and
  the site photos.

The **Analytics** tab shows four summary tables in percent for the items the
dropdowns leave: **Colour**, **Pattern**, **Fit** and **Fabric** (value, % of
items, item count). Fit and fabric count only the items that have one (clothes).
Clicking a row filters by that value.

The **Outfits** tab finds every outfit the catalogue can make (no cap) for a chosen outfit type (Western, Indian,
dress / jumpsuit, co-ord), style, occasion, budget and size. They are built in
the background with a live count; the first 48 show at once and "Show 48 more"
reveals the rest. "Shuffle" lists them in a different order. See [Outfit recommender](#outfit-recommender).

## Outfit recommender

`web/recommend.js` implements [`outfit_styling_rules.md`](outfit_styling_rules.md)
in the browser (nothing leaves the computer):

1. **Templates**: top + bottom + footwear (+ accessories, optional jacket);
   dress / gown / jumpsuit; kurta, kurta set, saree or lehenga with ethnic
   footwear and an ethnic accessory; co-ord set.
2. **Must match**: same gender, same occasion family (an item with no real
   occasion tag fits the occasions its style is worn for), compatible styles,
   size in stock (S / M / L also match waist sizes 28 to 38 for bottoms).
3. **Scored** (+1 each): colour (at most two non-neutral colours, no clash; a
   safe pair or one colour family), one patterned piece, balanced fit, fabric
   and season, neighbouring price bands.
4. **Choosing**: the best-scoring outfits, with a short reason ("navy + white,
   all solid, casual"). Within a set a garment appears once; a footwear or
   accessory item at most three times. Pieces whose title contradicts their
   category (a "Handkerchief" filed as shoes) are never suggested.

Finding every outfit takes 0.4 to 35 s (men: about 1,100 with no filter, women: about 3,100); the first ones show at once, and a "Complete the look" about
0.05 s. An empty result means the choice contradicts the rules (for example an
Indian outfit in streetwear, or gym wear for a wedding).

## Schema additions (taxonomy §6)

`primary_style`, `style_tags[]`, `style_scores{}`, `style_confidence`,
`style_source` (`rules`), `style_hits[]` (audit), `wear_types[]` (garment
sub-type) and `sketch` (SVG path).

New categories: `kurta`, `kurta_set`, `sherwani`, `ethnic_jacket`, `pyjama` and
`dhoti`.

## Tests

`python -m pytest tests` runs 247 offline tests (132 men's, 115 women's in
`tests/test_style_women.py`), and `node tests/test_recommend.js` runs the 6
recommender tests. They cover:

- all 20 cases in taxonomy §9;
- determinism, the three-tag cap, half-weight description scoring and every
  conflict rule;
- the men's scope, dedupe and balancing;
- sketch rendering;
- an end-to-end `scrape` (fetch + build) against local mock stores;
- the recommender's must-match rules, size matching, scoring, outfit building,
  the mis-label guard, and outfits for every style in both real catalogues.

## Women's catalogue

Rules: [`style_taxonomy_women.md`](style_taxonomy_women.md). Every command takes
`--gender women` and then uses its own files, so a women's run never touches
the men's catalogue (verified at the time: the men's 17,445 items rebuilt
identically). The numbers below describe the women's build before the trims;
the current catalogue is in the table at the top.

| | Men (default) | Women (`--gender women`) |
| --- | --- | --- |
| Sites | `sites.json` (41) | `sites_women.json` (77) |
| Raw feeds | `data/raw/` | `data/raw_women/` |
| Database | `data/catalogue.db` | `data/catalogue_women.db` |
| Export | `web/catalogue.json` | `web/catalogue_women.json` |
| Sketches | `web/sketch/` | `web/sketch_women/` |
| Report | `catalogue_report.md` | `catalogue_report_women.md` |
| Style rules | `pipeline/style_rules.yaml` | `pipeline/style_rules_women.yaml` |

```bash
python -m pipeline.run fetch --gender women     # about 20 min, 77 sites
python -m pipeline.run build --gender women     # about 15 min, offline
python -m pipeline.run audit --gender women --seed 5
```

**Latest build** ([`catalogue_report_women.md`](catalogue_report_women.md)):
13,614 garments from a women's pool of 136,431. Eight styles have 1,600 each;
**edgy has 814**, every item in the pool with a real edgy cue (corset, bustier,
cut-out, mesh, faux leather, studs and so on), reported as a shortfall rather
than padded. Unclassified is 3.2% of the pool; 81% of the catalogue is high
confidence. Footwear: 1,683; accessories: 17,585 (dupattas and stoles,
jewellery, bags, clutches and potlis, belts, hair accessories and so on).

How it differs from the men's pipeline (one shared engine in `classify.py` and
`style.py`, with women's tables behind `catalogue="women"`):

- **Nine styles**: the men's eight plus `edgy`. Edgy needs one strong cue or
  two medium cues in the title, type or tags, so "dark pink" or a single
  "chain" does not count.
- **Categories**: saree, lehenga, gown, jumpsuit, leggings, ethnic bottoms
  (salwar, churidar, sharara, dhoti pants), saree blouse, shrug and cape, plus
  the shared ones. Outfit titles ("Kurta with Pants and Dupatta", "Saree with
  Blouse") are read as one outfit; otherwise the head noun before "with" decides.
- **Scope (section 8)**: lingerie (sports bras are kept), sleepwear and
  loungewear, swimwear, kids', unstitched dress material and combo packs are
  dropped. Women-only stores set `default_gender: women`; mixed stores list
  `women_collections`. Unisex streetwear labels with no women's collection
  (Bluorng, Toffle, Midnight LAW) therefore add almost nothing.
- **Conflict rules (section 3)**: sarees, lehengas and shararas are traditional
  with glam (glam first when the title says sequin, party, bridal and so on);
  pre-draped sarees and Indo-western titles are ethnic fusion; block-print or
  ikat Western cuts are boho; black plus leather, studs, mesh or a cut-out is
  edgy; plain cotton leggings from an ethnic-wear store are churidar leggings
  (traditional).
- **Sketches** (`pipeline/sketch_women.py`): dresses by length and skirt shape,
  gowns with a train, anarkalis with kalis, sarees with pleats and pallu,
  lehengas, kurta sets with palazzo or sharara and a dupatta, corsets, camis,
  sports bras, jumpsuits and skirts; heels, ballerinas, potlis, clutches,
  handbags, jhumkas, bangles, maang tikkas and hair accessories. Shared shapes
  reuse `sketch.py`.
- **Price bands**: the same as the men's (cheap 0-999, affordable 1,000-2,499,
  luxury 2,500 and up).

Sites checked and left out: Kalki Fashion (USD prices); no public or a blocked
feed for Anavila, Meesha, Anomaly, Clarache, Haseena, Qua, Vanaras, Ishaavi,
trueBrowns, Two Point Two, HRX, Cultsport, Aastey, Biba, House of Indya,
Pernia's, Aza, Andaaz, Mirraw, Mohey, FableStreet, Koskii and others. Libas
caps its feed at 100 pages (`max_pages: 100`).

## Good to know

- **Politeness:**
  - robots.txt is honoured and blocks are never bypassed;
  - each site is throttled to 1 request per second;
  - sites are fetched in parallel (8 at a time).
- **Data use:** prices are in INR. Scraped data and photos are for internal use
  only.
- **Old data:** previous databases are kept in
  `data/backup_snitch_formal_2026-11-20/` and `data/backup_bonkers_2026-11-20/`.

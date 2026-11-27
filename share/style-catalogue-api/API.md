# Style Catalogue API

A local JSON API for a men's and a women's fashion catalogue built from Indian
fashion websites. Each item has a style (minimalist, classic, streetwear, boho,
sporty, glam, ethnic fusion, traditional, and edgy for women), nine garment
parameters, a price band and a flat sketch. The API also serves analytics and
an outfit recommender.

**The data is for internal use only.** The server listens on the loopback
addresses only (`127.0.0.1` and `::1`), so only your own computer can reach it. Do not host it publicly or share the data.

## Start

Needs Python 3.9 or newer; nothing to install.

```bash
cd style-catalogue-api
python api.py              # http://localhost:8000
python api.py --port 8080  # another port
```

- API: <http://localhost:8000/api>
- The current page, as a working example: <http://localhost:8000/>

Every response is JSON. Responses are gzip-compressed when the client accepts
it, and they carry `Access-Control-Allow-Origin: *`, so a dev server on another
local port (for example Vite on `localhost:5173`) can call the API directly.

## What's in the folder

| Path | What it is |
| --- | --- |
| `api.py` | The API server |
| `recommend.py` | The outfit rules engine used by the API |
| `data/catalogue_men.json`, `data/catalogue_women.json` | The catalogues (a list of items) |
| `static/sketch/`, `static/sketch_women/` | Flat sketch images (SVG), served at `/sketch/...` and `/sketch_women/...` |
| `web/index.html`, `web/recommend.js` | The current page and the same engine in JavaScript |
| `outfit_styling_rules.md` | The styling rules the recommender follows |

## Common parameters

| Parameter | Meaning |
| --- | --- |
| `gender` | `men` (default) or `women`: which catalogue |
| Filters (any of the names below) | One value or several, comma-separated: `color=white,black`. Several values of one filter match any of them; different filters must all match. |
| `q` | Text search in title, site, vendor and style |

Filter names: `department`, `style`, `style_tag`, `category`, `site`,
`price_band`, `color`, `secondary_color`, `pattern`, `fit`, `fabric`,
`sleeve_length`, `neckline`, `occasion`, `item_gender`, `confidence`, `size`.
Use `/api/filters` to get the valid values. Items with no value for a filter
are listed as `unspecified` (or `n/a` where the parameter doesn't apply).

## Endpoints

### `GET /api/health`

```json
{"status": "ok", "items": {"men": 6525, "women": 11814}}
```

### `GET /api/items`: list, filter, sort and page

| Parameter | Default | |
| --- | --- | --- |
| `page`, `page_size` | 1, 48 | `page_size` at most 200 |
| `sort` | catalogue order | `price-asc`, `price-desc` or `discount` |
| `full` | 0 | `1` returns every field instead of the compact item |

```
/api/items?gender=men&style=minimalist&category=shirt&color=white&page=1
```

```json
{"gender": "men", "total": 54, "share_of_catalogue": 0.8, "page": 1, "page_size": 48, "pages": 2,
 "items": [{"id": "snitch:7891…", "title": "…", "site": "snitch", "category": "shirt",
            "color": "white", "pattern": "solid", "fit": "slim", "price": 1299,
            "price_band": "affordable", "primary_style": "minimalist",
            "sketch": "sketch/snitch/7891….svg", "image": "https://…", "url": "https://…"}]}
```

Compact items carry: `id, title, site, category, department, gender, color,
secondary_color, pattern, fit, fabric, sleeve_length, neckline, occasion,
primary_style, style_tags, price, mrp, discount_pct, price_band,
sizes_available, sketch, image, url`. Fields with no value are left out.

- **Images:** `sketch` is a path on this server: load `http://localhost:8000/` + `sketch`.
- **Photos:** `image` is the shop's own photo URL.
- **Product page:** `url` is the product page on the shop's site.

### `GET /api/items/{id}`: one item, every field

The id contains a colon, so URL-encode it: `/api/items/snitch%3A7891…`.
Returns `{"gender": …, "item": {…}}`, including style scores, every parameter
and where each value came from (`attr_source`).

### `GET /api/filters`: dropdown options with counts and %

```
/api/filters?gender=women&style=boho
/api/filters?gender=women&facets=color,pattern
```

For each facet (default: `department, style, category, site, price_band, color,
occasion, item_gender`) it returns every value with its count and its % share.
Counts follow the *other* filters: with `style=boho`, the `color` options count
boho items only. That's how the page's dropdowns work.

```json
{"gender": "women", "facets": {"color": {"total": 1536, "selected": [],
  "options": [{"value": "white", "count": 210, "pct": 13.7}, …]}}}
```

### `GET /api/analytics`: summary tables in %

```
/api/analytics?gender=men&category=shirt
```

Returns the four tables on the Analytics tab: colour, pattern, fit and
fabric. Each row has a value, count and % share. Fit and fabric count only items
that have one (clothes); `base` says how many.

```json
{"gender": "men", "items_in_view": 714, "share_of_catalogue": 10.9,
 "tables": {"color": {"title": "Colour", "base": 714, "rows": [{"value": "white", "count": 98, "pct": 13.7}, …]},
            "pattern": {…}, "fit": {…}, "fabric": {…}}}
```

### `GET /api/outfits`: recommended outfits, no cap

| Parameter | Values |
| --- | --- |
| `kind` | `western`, `indian`, `onepiece` (dress / gown / jumpsuit), `coord` |
| `style` | a style id, e.g. `minimalist` |
| `occasion` | `casual`, `formal`, `party`, `festive`, `active` |
| `band` | `cheap`, `affordable`, `luxury` |
| `size` | `XS` … `XXL` (S/M/L also match waist sizes for bottoms) |
| `seed` | another number lists the same outfits in another order |
| `offset`, `limit` | paging; `limit` at most 200 (default 48) |

```
/api/outfits?gender=men&style=classic&occasion=formal&limit=24
/api/outfits?gender=men&style=classic&occasion=formal&offset=24&limit=24
```

```json
{"gender": "men", "filters": {"style": "classic", "occasion": "formal"}, "offset": 0, "limit": 24,
 "has_more": true, "search_complete": false, "found_so_far": 25, "took_ms": 310,
 "outfits": [{"items": [{…shirt…}, {…trousers…}, {…shoes…}, {…belt…}],
              "score": 6, "max": 6, "why": "navy + white, all solid, formal", "total_price": 6366}]}
```

- **Outfit fields:** `score` / `max` is how many of the styling rules the outfit meets, and `why` is a short reason.
- **Paging:** outfits are searched lazily. Keep asking for the next `offset` while `has_more` is true. `search_complete` becomes true once every outfit has been found.
- **Response time:** the first page of a new search takes a moment (up to about a second); later pages are quick.

### `GET /api/look/{id}`: "complete the look" for one item

```
/api/look/snitch%3A7891…?n=3&seed=0&size=M
```

Returns up to `n` (at most 10) outfits built around that item:
`{"gender": …, "anchor": {…item…}, "looks": [ {outfit}, … ]}`.

### Errors

Errors return a status and `{"error": "…"}`:
- `400`: a bad parameter;
- `404`: an unknown id or endpoint;
- `500`: a server error.

## Using the recommender in the browser instead

`web/recommend.js` is the same engine in JavaScript (the page uses it). Load it
with `<script src="/recommend.js">` and call
`Recommender.outfitStream(items, {style, occasion, kind, band, size}, seed)`
or `Recommender.completeLook(item, items, {n: 3})` on the item list from
`/catalogue.json` (men) or `/catalogue_women.json` (women). The API and the
script give identical outfits.

## Updating the data

The catalogue owner sends a new `data/` folder (or a new zip) when the
catalogue changes. Replace the folder and restart `api.py`.

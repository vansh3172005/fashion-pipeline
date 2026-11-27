"""Storefront scraper.

The default adapter reads the public Shopify JSON feed at /products.json
(paginated, 250 per page). It avoids brittle HTML parsing and gives structured
variant options (size, colour), tags, the description with the site's own spec
lines, and every product photo.

Items are collected per (price band x category) cell so the catalogue stays
balanced across cheap / affordable / luxury, and scraping stops as soon as
every requested cell is full.

Politeness: robots.txt is honoured, requests are throttled, 429/5xx are
retried with backoff, and a descriptive User-Agent with a contact address is
sent (set PIPELINE_CONTACT).
"""
import logging
import os
import time
import urllib.robotparser
from urllib.parse import urljoin

import requests

from .classify import ALL_CATEGORIES, CATEGORIES, DEFAULT_BANDS, classify_product

log = logging.getLogger("scrape")

PLACEHOLDER_CONTACT = "data-eng@your-company.example"


def contact() -> str:
    return os.environ.get("PIPELINE_CONTACT", "").strip() or PLACEHOLDER_CONTACT


def user_agent() -> str:
    return f"CatalogueResearchBot/2.0 (+contact: {contact()})"


class SiteBlocked(Exception):
    pass


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": user_agent(), "Accept": "application/json"})
    return s


def robots_allows(session, base_url: str, path: str = "/products.json") -> bool:
    rp = urllib.robotparser.RobotFileParser()
    try:
        r = session.get(urljoin(base_url, "/robots.txt"), timeout=15)
        if r.status_code >= 400:
            return True  # no robots.txt -> nothing disallowed
        rp.parse(r.text.splitlines())
    except requests.RequestException:
        return True
    return rp.can_fetch(user_agent(), urljoin(base_url, path))


def fetch_json(session, url, params, retries=6, delay=1.0, timeout=60, backoff=5.0):
    for attempt in range(retries):
        try:
            r = session.get(url, params=params, timeout=timeout)
        except requests.RequestException as e:
            log.warning("network error %s (%s), retry %d", url, e, attempt + 1)
            time.sleep(backoff * 2 ** attempt)  # 5, 10, 20, 40 s ...
            continue
        if r.status_code == 200:
            try:
                return r.json()
            except ValueError:
                raise SiteBlocked(f"{url} did not return JSON (not a Shopify feed?)")
        if r.status_code in (429, 500, 502, 503, 504):
            log.warning("HTTP %s from %s, retry %d", r.status_code, url, attempt + 1)
            time.sleep(backoff * 2 ** attempt)
            continue
        raise SiteBlocked(f"{url} -> HTTP {r.status_code}")
    raise SiteBlocked(f"{url} failed after {retries} attempts")


# --------------------------------------------------------------------------
# adapters: one per storefront platform
# --------------------------------------------------------------------------


class SiteAdapter:
    """Yields products in the Shopify product shape (id, title, handle,
    product_type, tags, body_html, options, variants, images, vendor).

    Subclasses add support for non-Shopify sites without touching
    classification or storage. ``pages`` counts requests made.
    """

    feed_path = "/products.json"  # path checked against robots.txt

    def __init__(self, session, delay=1.0, max_pages=200):
        self.session, self.delay, self.max_pages = session, delay, max_pages
        self.pages = 0

    def product_url(self, base_url, product) -> str:
        return urljoin(base_url, f"/products/{product.get('handle', '')}")

    def iter_products(self, site):  # pragma: no cover - interface
        raise NotImplementedError


class ShopifyAdapter(SiteAdapter):
    def iter_products(self, site):
        base = site["base_url"].rstrip("/") + "/"
        feeds = [f"collections/{c}/products.json" for c in site.get("collections", [])]
        for feed in feeds or ["products.json"]:
            for page in range(1, self.max_pages + 1):
                if self.pages:
                    time.sleep(self.delay)
                data = fetch_json(self.session, urljoin(base, feed),
                                  {"limit": 250, "page": page}, delay=self.delay)
                self.pages += 1
                products = data.get("products") or []
                if not products:
                    break
                yield from products


ADAPTERS = {"shopify": ShopifyAdapter}


def register_adapter(platform: str, cls) -> None:
    ADAPTERS[platform] = cls


def adapter_for(site, session, delay=1.0, max_pages=200) -> SiteAdapter:
    platform = site.get("platform", "shopify")
    if platform not in ADAPTERS:
        raise SiteBlocked(f"no adapter for platform {platform!r}")
    return ADAPTERS[platform](session, delay=delay, max_pages=max_pages)


# --------------------------------------------------------------------------
# item construction + quota-driven scrape
# --------------------------------------------------------------------------


def to_item(site: dict, adapter: SiteAdapter, product: dict, attrs: dict):
    images = [i.get("src") for i in product.get("images") or [] if i.get("src")]
    if not images:
        return None  # a catalogue card without an image is useless
    variants = product.get("variants") or []
    base = site["base_url"].rstrip("/") + "/"
    return {
        "id": f"{site['name']}:{product['id']}",
        "site": site["name"],
        "title": (product.get("title") or "").strip(),
        "url": adapter.product_url(base, product),
        "image": images[0],
        "images": images,
        "available": any(v.get("available") for v in variants) if variants else None,
        "vendor": product.get("vendor"),
        "currency": site.get("currency"),
        **attrs,
    }


def scrape_site(site: dict, per_cell=20, delay=1.0, max_pages=200, session=None,
                bands=None, categories=None):
    """Scrape one site, filling up to ``per_cell`` items per (band, category).

    ``bands`` / ``categories`` restrict which cells are collected (default:
    all). ``per_cell=0`` means no cap (collect everything in scope).

    Site options (sites.json):
      occasion_filter      keep only products the site labels with one of these
                           occasions, e.g. ["formal"] (Occasion field or tags)
      include_accessories  also collect shoes, belts, sunglasses, bags, ...
      default_gender       gender for products with no gender signal
                           (e.g. "men" for a menswear-only store)
    Returns (items, report).
    """
    session = session or make_session()
    name = site["name"]
    band_cfg = site.get("price_bands") or DEFAULT_BANDS
    want_bands = list(bands or band_cfg.keys())
    accessories = bool(site.get("include_accessories"))
    want_cats = list(categories or (ALL_CATEGORIES if accessories else CATEGORIES))
    occ_filter = set(site.get("occasion_filter") or ())
    report = {"site": name, "status": "ok", "pages": 0, "error": None}

    try:
        adapter = adapter_for(site, session, delay=delay, max_pages=max_pages)
    except SiteBlocked as e:
        report.update(status="error", error=str(e), counts={})
        return [], report
    if not robots_allows(session, site["base_url"].rstrip("/") + "/", adapter.feed_path):
        report.update(status="blocked", error=f"robots.txt disallows {adapter.feed_path}",
                      counts={})
        return [], report

    cells = {(b, c): [] for b in want_bands for c in want_cats}
    seen, scanned, off_occasion = set(), 0, 0

    def full():
        return per_cell and all(len(v) >= per_cell for v in cells.values())

    try:
        for p in adapter.iter_products(site):
            scanned += 1
            if p.get("id") in seen:
                continue
            seen.add(p.get("id"))
            attrs = classify_product(p, band_cfg, include_accessories=accessories,
                                     default_gender=site.get("default_gender"))
            if not attrs:
                continue
            if occ_filter and not occ_filter.intersection(attrs["occasions"]):
                off_occasion += 1
                continue
            cell = cells.get((attrs["price_band"], attrs["category"]))
            if cell is None or (per_cell and len(cell) >= per_cell):
                continue
            item = to_item(site, adapter, p, attrs)
            if item:
                cell.append(item)
            if full():
                break  # stop requesting pages as soon as every cell is full
    except SiteBlocked as e:
        report.update(status="error", error=str(e))
    report["pages"] = adapter.pages
    report["scanned"] = scanned
    report["off_occasion"] = off_occasion

    counts = {}
    for (b, c), v in cells.items():
        counts.setdefault(b, {})[c] = len(v)
    report["counts"] = counts
    band_totals = {b: sum(cs.values()) for b, cs in counts.items()}
    if report["status"] == "ok" and any(n == 0 for n in band_totals.values()):
        report["status"] = "short"  # a whole price band has no stock
    items = [i for v in cells.values() for i in v]
    return items, report


# --------------------------------------------------------------------------
# raw feed cache: fetch once, classify offline as often as needed
# --------------------------------------------------------------------------

RAW_KEEP = ("id", "title", "handle", "product_type", "tags", "vendor", "body_html",
            "options", "variants", "images", "created_at")


def _slim(p: dict) -> dict:
    out = {k: p.get(k) for k in RAW_KEEP}
    out["images"] = [{"src": i.get("src")} for i in p.get("images") or [] if i.get("src")]
    out["variants"] = [{k: v.get(k) for k in ("price", "compare_at_price", "available",
                                                "option1", "option2", "option3")}
                       for v in p.get("variants") or []]
    return out


def fetch_collection_ids(session, base: str, handle: str, delay=1.0, max_pages=60):
    """Product ids in one collection (used for the men's-collection gender rule)."""
    ids = set()
    for page in range(1, max_pages + 1):
        time.sleep(delay)
        data = fetch_json(session, urljoin(base, f"collections/{handle}/products.json"),
                          {"limit": 250, "page": page}, delay=delay)
        ps = data.get("products") or []
        if not ps:
            break
        ids.update(p["id"] for p in ps)
    return ids


WOMEN_KEYS = (("women_collections", "women_collection_ids"),
              ("women_accessory_collections", "women_accessory_ids"))


def _collection_ids(session, base, handles, delay):
    """{handle: sorted product ids} for the collections robots.txt allows."""
    out = {}
    for h in handles:
        if robots_allows(session, base, f"/collections/{h}/products.json"):
            out[h] = sorted(fetch_collection_ids(session, base, h, delay=delay))
    return out


def refresh_women_ids(site: dict, raw_dir, delay=1.0, session=None):
    """Fetch only the women's (and women's accessory) collection membership
    into an existing women's cache."""
    import gzip
    import json
    from pathlib import Path
    data = load_raw(raw_dir, site["name"])
    if data is None:
        return {"site": site["name"], "status": "error", "error": "no cache; run fetch"}
    session = session or make_session()
    base = site["base_url"].rstrip("/") + "/"
    try:
        for key, out_key in WOMEN_KEYS:
            data[out_key] = _collection_ids(session, base, site.get(key) or [], delay)
    except SiteBlocked as e:
        return {"site": site["name"], "status": "error", "error": str(e)}
    data["site"] = site
    with gzip.open(Path(raw_dir) / f"{site['name']}.json.gz", "wt", encoding="utf-8") as f:
        json.dump(data, f)
    return {"site": site["name"], "status": "ok",
            "ids": {h: len(v) for k, o in WOMEN_KEYS for h, v in data[o].items()}}


def fetch_raw(site: dict, raw_dir, delay=1.0, max_pages=200, session=None):
    """Download a site's whole public feed (slimmed) plus its collection list and
    the ids in its men's collections to ``raw_dir/<name>.json.gz``.
    Returns a small report dict."""
    import gzip
    import json
    from pathlib import Path

    session = session or make_session()
    base = site["base_url"].rstrip("/") + "/"
    rep = {"site": site["name"], "status": "ok", "products": 0, "error": None}
    if not robots_allows(session, base):
        rep.update(status="blocked", error="robots.txt disallows /products.json")
        return rep
    # a site may cap pagination (Shopify answers 400 past 25,000 products)
    adapter = adapter_for(site, session, delay=delay,
                          max_pages=min(max_pages, site.get("max_pages") or max_pages))
    products, seen = [], set()
    try:
        for p in adapter.iter_products({**site, "collections": []}):
            if p.get("id") not in seen:
                seen.add(p.get("id"))
                products.append(_slim(p))
        try:
            cols = fetch_json(session, urljoin(base, "collections.json"),
                              {"limit": 250}, delay=delay).get("collections") or []
        except SiteBlocked:
            cols = []
        men_ids, acc_ids = {}, {}
        for h in site.get("men_collections") or []:
            if robots_allows(session, base, f"/collections/{h}/products.json"):
                men_ids[h] = sorted(fetch_collection_ids(session, base, h, delay=delay))
        for h in site.get("men_accessory_collections") or []:
            if robots_allows(session, base, f"/collections/{h}/products.json"):
                acc_ids[h] = sorted(fetch_collection_ids(session, base, h, delay=delay))
        women = {}  # women's catalogue (sites_women.json): same idea, women's collections
        for key, out_key in WOMEN_KEYS:
            if site.get(key):
                women[out_key] = _collection_ids(session, base, site[key], delay)
    except SiteBlocked as e:
        rep.update(status="error", error=str(e))
        return rep  # never overwrite a good cache with a partial one
    out = Path(raw_dir) / f"{site['name']}.json.gz"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {"site": site, "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
               "pages": adapter.pages, "products": products,
               "collections": [{"handle": c.get("handle"), "title": c.get("title"),
                                "count": c.get("products_count")} for c in cols],
               "men_collection_ids": men_ids, "men_accessory_ids": acc_ids, **women}
    with gzip.open(out, "wt", encoding="utf-8") as f:
        json.dump(payload, f)
    rep.update(products=len(products), pages=adapter.pages)
    return rep


def load_raw(raw_dir, name):
    import gzip
    import json
    from pathlib import Path
    p = Path(raw_dir) / f"{name}.json.gz"
    if not p.exists():
        return None
    with gzip.open(p, "rt", encoding="utf-8") as f:
        return json.load(f)


def refresh_accessory_ids(site: dict, raw_dir, delay=1.0, session=None):
    """Fetch membership of the site's men's footwear / accessory collections
    (``men_accessory_collections``) into its cache as ``men_accessory_ids``."""
    import gzip
    import json
    from pathlib import Path
    data = load_raw(raw_dir, site["name"])
    if data is None:
        return {"site": site["name"], "status": "error", "error": "no cache; run fetch"}
    session = session or make_session()
    base = site["base_url"].rstrip("/") + "/"
    ids = {}
    try:
        for h in site.get("men_accessory_collections") or []:
            if robots_allows(session, base, f"/collections/{h}/products.json"):
                ids[h] = sorted(fetch_collection_ids(session, base, h, delay=delay))
    except SiteBlocked as e:
        return {"site": site["name"], "status": "error", "error": str(e)}
    data["men_accessory_ids"] = ids
    with gzip.open(Path(raw_dir) / f"{site['name']}.json.gz", "wt", encoding="utf-8") as f:
        json.dump(data, f)
    return {"site": site["name"], "status": "ok", "ids": {h: len(v) for h, v in ids.items()}}


def refresh_men_ids(site: dict, raw_dir, delay=1.0, session=None):
    """Fetch only the men's-collection membership into an existing cache."""
    import gzip
    import json
    from pathlib import Path
    data = load_raw(raw_dir, site["name"])
    if data is None:
        return {"site": site["name"], "status": "error", "error": "no cache; run fetch"}
    session = session or make_session()
    base = site["base_url"].rstrip("/") + "/"
    ids = {}
    try:
        for h in site.get("men_collections") or []:
            if robots_allows(session, base, f"/collections/{h}/products.json"):
                ids[h] = sorted(fetch_collection_ids(session, base, h, delay=delay))
    except SiteBlocked as e:
        return {"site": site["name"], "status": "error", "error": str(e)}
    data["men_collection_ids"] = ids
    data["site"] = site
    with gzip.open(Path(raw_dir) / f"{site['name']}.json.gz", "wt", encoding="utf-8") as f:
        json.dump(data, f)
    return {"site": site["name"], "status": "ok",
            "men_ids": {h: len(v) for h, v in ids.items()}}

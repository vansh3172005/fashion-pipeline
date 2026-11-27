"""CLI:  python -m pipeline.run <command>

  check    probe the sites in sites.json (robots ok? feed reachable?);
           --count also reports how many men's items each site holds
  fetch    download every site's public feed (+ men's collections) to data/raw/
  build    cached feeds -> classify -> men's scope -> dedupe -> balance by style
           -> data/catalogue.db, flat sketches, web/catalogue.json, catalogue_report.md
  scrape   fetch + build
  sketch   (re)draw the front/back technical flat SVG for every item
  audit    print a random sample per style for the precision review
  params   sample a site and show where each of the 9 parameters comes from
  images   optional photo cut-outs (rembg) for a sample of items
  export   rebuild web/catalogue.json from the database
  report   counts per style / site / band, parameter coverage
  serve    serve the catalogue + dashboard on http://localhost:8000 (this PC only)

  --gender women   run any command on the women's catalogue instead
                   (style_taxonomy_women.md): sites_women.json, data/raw_women/,
                   data/catalogue_women.db, web/catalogue_women.json,
                   web/sketch_women/, catalogue_report_women.md. The men's
                   files are never touched by a women's run.
"""
import argparse
import gzip
import http.server
import random
import json
import logging
import re
import socketserver
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import store
from .classify import (_SPEC_KEYS, ALL_CATEGORIES, DEFAULT_BANDS, PARAMETERS,
                       classify_product, description_text)
from .scrape import (PLACEHOLDER_CONTACT, adapter_for, contact, fetch_json, fetch_raw,
                     load_raw, make_session, robots_allows, scrape_site)
from .style import STYLE_LABELS, STYLES, UNCLASSIFIED, styles_for

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "catalogue.db"
RAW = ROOT / "data" / "raw"
REPORT = ROOT / "catalogue_report.md"
WEB = ROOT / "web"
OUT = WEB / "catalogue.json"
GENDER = "men"  # set by --gender; "women" switches every path below


def _use_women():
    global DB, RAW, REPORT, OUT, GENDER, STYLES
    GENDER = "women"
    DB = ROOT / "data" / "catalogue_women.db"
    RAW = ROOT / "data" / "raw_women"
    REPORT = ROOT / "catalogue_report_women.md"
    OUT = WEB / "catalogue_women.json"
    STYLES = styles_for("women")


def _who():
    return "women's" if GENDER == "women" else "men's"

SOURCE_ORDER = ("field", "tags", "title", "description", "image", "default", "n/a", None)
SOURCE_LABEL = {"field": "site field", "tags": "site tags", "title": "title",
                "description": "description", "image": "image", "default": "default", "n/a": "n/a",
                None: "missing"}


def load_sites(path, only=None):
    sites = json.loads(Path(path).read_text(encoding="utf-8"))
    if only:
        wanted = set(only.split(","))
        sites = [s for s in sites if s["name"] in wanted]
    return sites


def _warn_contact():
    if contact() == PLACEHOLDER_CONTACT:
        print("WARNING: User-Agent uses a placeholder contact. Set PIPELINE_CONTACT to a "
              "real address before production runs.\n", file=sys.stderr, flush=True)


def _csv(v):
    return [x.strip() for x in v.split(",") if x.strip()] if v else None


# --------------------------------------------------------------------------
# parameter coverage
# --------------------------------------------------------------------------


def param_coverage(items) -> dict:
    """{parameter: Counter(source -> n)} over classified items."""
    cov = {p: Counter() for p in PARAMETERS}
    for it in items:
        src = it.get("attr_source") or {}
        for p in PARAMETERS:
            cov[p][src.get(p)] += 1
    return cov


def print_coverage(items, title="Parameter sources"):
    n = len(items)
    if not n:
        return
    cov = param_coverage(items)
    cols = [s for s in SOURCE_ORDER if any(cov[p][s] for p in PARAMETERS)]
    print(f"\n{title} (% of {n} items)")
    print(f"  {'parameter':<16}" + "".join(f"{SOURCE_LABEL[s]:>13}" for s in cols))
    for p in PARAMETERS:
        print(f"  {p:<16}" + "".join(f"{100 * cov[p][s] / n:>12.0f}%" for s in cols))


# --------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------


def cmd_check(args):
    _warn_contact()
    session, ok = make_session(), 0
    for site in load_sites(args.sites, args.only):
        base = site["base_url"].rstrip("/") + "/"
        try:
            if not robots_allows(session, base):
                print(f"  BLOCKED  {site['name']:<14} robots.txt disallows feed", flush=True)
                continue
            data = fetch_json(session, base + "products.json", {"limit": 5}, retries=2)
            extra = ""
            if args.count:
                from .build import site_pool
                raw = load_raw(RAW, site["name"])
                if raw is None:
                    fetch_raw(site, RAW, delay=args.delay, max_pages=args.max_pages,
                              session=session)
                    raw = load_raw(RAW, site["name"])
                if raw:
                    items, _ = site_pool(site, raw, catalogue=GENDER)
                    extra = (f"  {len(items):>6} {_who()} items of {len(raw['products'])} products"
                             f" (feed cached {raw['fetched_at'][:10]})")
            print(f"  OK       {site['name']:<16} {len(data.get('products', []))} sample products"
                  f"{extra}", flush=True)
            ok += 1
        except Exception as e:  # noqa: BLE001 - report every failure mode
            print(f"  FAIL     {site['name']:<14} {e}", flush=True)
    print(f"\n{ok} site(s) usable", flush=True)


def cmd_params(args):
    """Show which parameters the site itself publishes, and under which label."""
    _warn_contact()
    session = make_session()
    for site in load_sites(args.sites, args.only):
        adapter = adapter_for(site, session, delay=args.delay, max_pages=args.sample_pages)
        products = list(adapter.iter_products(site))
        labels, options, items = Counter(), Counter(), []
        for p in products:
            for line in description_text(p.get("body_html", "")).splitlines():
                m = re.match(r"([A-Za-z][A-Za-z ]{1,24}?)\s*(?::|\s-\s)\s*\S", line)
                if m and m.group(1).strip().lower() in _SPEC_KEYS:
                    labels[(_SPEC_KEYS[m.group(1).strip().lower()], m.group(1).strip())] += 1
            for o in p.get("options") or []:
                options[o.get("name")] += 1
            a = classify_product(p, site.get("price_bands"),
                                 include_accessories=bool(site.get("include_accessories")),
                                 default_gender=site.get("default_gender"))
            if a and site.get("occasion_filter") and not set(
                    site["occasion_filter"]).intersection(a["occasions"]):
                a = None
            if a:
                items.append(a)
        print(f"\n{site['name']}: {len(products)} products sampled, {len(items)} garments in scope")
        print("\nLabelled fields published by the site:")
        for (param, label), n in sorted(labels.items(), key=lambda kv: (kv[0][0], -kv[1])):
            print(f"  {label!r:<24} -> {param:<14} on {100 * n / max(1, len(products)):.0f}% "
                  "of products")
        for name, n in options.most_common():
            if name and name.lower() != "title":
                low = name.lower()
                param = "size" if "size" in low else ("color" if "col" in low else low)
                print(f"  variant option {name!r:<9} -> {param:<14} on "
                      f"{100 * n / max(1, len(products)):.0f}% of products")
        print("  product tags            -> gender (Men/Women), category, collections")
        print_coverage(items, "Where each parameter comes from")
        bands = site.get("price_bands") or DEFAULT_BANDS
        print("\nPrice bands (" + (site.get("currency") or "store currency") + "): "
              + ", ".join((f"{b} {lo}-{hi}" if hi is not None else f"{b} {lo}+")
                          for b, (lo, hi) in bands.items()))
        print("  in sample: " + ", ".join(f"{b}={n}" for b, n in
                                         Counter(a["price_band"] for a in items).most_common()))


def cmd_scrape(args):
    _warn_contact()
    sites = load_sites(args.sites, args.only)
    con = store.connect(DB)
    all_items = []
    try:
        def work(site):
            return site, *scrape_site(site, per_cell=args.per_cell, delay=args.delay,
                                      max_pages=args.max_pages, bands=_csv(args.bands),
                                      categories=_csv(args.categories))

        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for site, items, report in pool.map(work, sites):
                store.save_site(con, site["name"], items, report)
                all_items += items
                print(f"\n{site['name']}: {report['status']}  pages={report['pages']} "
                      f"scanned={report.get('scanned', 0)} stored={len(items)} "
                      + (f"skipped-other-occasions={report.get('off_occasion', 0)} "
                         if site.get("occasion_filter") else "") +
                      f"{report['error'] or ''}", flush=True)
                _print_matrix(report.get("counts", {}), args.per_cell)
        print_coverage(all_items)
        n = store.export_json(con, OUT)
        print(f"\nexported {n} items -> {OUT}", flush=True)
    finally:
        con.close()


def _print_matrix(counts: dict, per_cell=None):
    if not counts:
        return
    bands = list(counts)
    cats = [c for c in ALL_CATEGORIES if any(counts[b].get(c) for b in bands)]
    print(f"  {'category':<11}" + "".join(f"{b:>11}" for b in bands) + f"{'total':>8}")
    for c in cats:
        row = [counts[b].get(c, 0) for b in bands]
        print(f"  {c:<11}" + "".join(f"{n:>11}" for n in row) + f"{sum(row):>8}")
    tot = [sum(counts[b].values()) for b in bands]
    print(f"  {'total':<11}" + "".join(f"{n:>11}" for n in tot) + f"{sum(tot):>8}")
    if per_cell:
        print(f"  (quota {per_cell} per cell; a smaller number means the site has no more "
              "stock in that cell)")


def _spread(rows, n):
    """Pick n items round-robin across (category, price band) groups so a small
    image sample covers every kind of garment instead of the first category."""
    groups = {}
    for r in rows:
        groups.setdefault((r["category"], r["price_band"]), []).append(r)
    order = sorted(groups, key=lambda k: -len(groups[k]))
    picked, i = [], 0
    while len(picked) < n and any(groups.values()):
        g = groups[order[i % len(order)]]
        if g:
            picked.append(g.pop(0))
        i += 1
    return picked


def cmd_images(args):
    from . import imaging
    _warn_contact()
    con = store.connect(DB)
    try:
        q = "SELECT * FROM items"
        if not args.force:
            q += " WHERE flat_images IS NULL OR flat_images = '[]'"
        rows = [store.decode(r) for r in con.execute(q + " ORDER BY category, price_band")]
        if args.only:
            rows = [r for r in rows if r["site"] in set(args.only.split(","))]
        if args.limit:
            rows = _spread(rows, args.limit)
        if not rows:
            print("nothing to do (all items have flat images; use --force to redo)")
            return
        seg = imaging.make_segmenter(args.segmenter)
        session = make_session()
        session.headers["Accept"] = "image/*"
        t0, done, views, rejected = time.time(), 0, 0, Counter()
        for i, it in enumerate(rows, 1):
            res = imaging.process_item(it, WEB, seg, session, max_views=args.max_views,
                                       size=args.size)
            store.update_images(con, it["id"], res["flat_images"], res["image_colors"],
                                res["secondary_color"])
            done += bool(res["flat_images"])
            views += len(res["flat_images"])
            rejected.update(res["rejected"])
            if i % 10 == 0 or i == len(rows):
                rate = (time.time() - t0) / i
                print(f"  {i}/{len(rows)} items  {views} views  "
                      f"~{rate * (len(rows) - i) / 60:.0f} min left", flush=True)
        print(f"\nflat images for {done}/{len(rows)} items, {views} views "
              f"(segmenter={seg.name})")
        if rejected:
            print("rejected photos: " + ", ".join(f"{k}={v}" for k, v in rejected.most_common()))
        print(f"exported {store.export_json(con, OUT)} items -> {OUT}", flush=True)
    finally:
        con.close()


def cmd_export(_):
    con = store.connect(DB)
    try:
        print(f"exported {store.export_json(con, OUT)} items -> {OUT}", flush=True)
    finally:
        con.close()


def cmd_report(_):
    con = store.connect(DB)
    try:
        items = [store.decode(r) for r in con.execute("SELECT * FROM items")]
        for site in sorted({i["site"] for i in items}):
            its = [i for i in items if i["site"] == site]
            counts = {}
            for i in its:
                counts.setdefault(i["price_band"], Counter())[i["category"]] += 1
            run = con.execute("SELECT * FROM scrape_runs WHERE site = ? ORDER BY run_at DESC "
                              "LIMIT 2", (site,)).fetchall()
            print(f"\n{site}: {len(its)} items  (last run "
                  f"{time.strftime('%Y-%m-%d %H:%M', time.localtime(run[0]['run_at']))} "
                  f"status={run[0]['status']})" if run else f"\n{site}: {len(its)} items")
            if len(run) > 1:
                print(f"  previous run stored {run[1]['total']} items")
            order = [b for b in ("cheap", "affordable", "luxury") if b in counts]
            order += [b for b in counts if b not in order]
            _print_matrix({b: dict(counts[b]) for b in order})
            print("  gender: " + ", ".join(f"{k}={v}" for k, v in
                                         Counter(i["gender"] for i in its).most_common()))
            flat = sum(1 for i in its if i["flat_images"])
            print(f"  flat images: {flat}/{len(its)} items, "
                  f"{sum(len(i['flat_images']) for i in its)} views")
        print_coverage(items)
        print("\ntotal", len(items), flush=True)
    finally:
        con.close()


_GZ = {}


class _Handler(http.server.SimpleHTTPRequestHandler):
    """Static files from web/; catalogue.json is gzipped (about 8x smaller)."""

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(WEB), **kw)

    def log_message(self, *_):
        pass

    def end_headers(self):
        # always fetch the latest page / script, so UI changes show on a normal refresh
        if not self.path.endswith(".json"):
            self.send_header("Cache-Control", "no-cache, must-revalidate")
        super().end_headers()

    def do_GET(self):
        path = Path(self.translate_path(self.path))
        if (path.suffix == ".json" and path.is_file()
                and "gzip" in self.headers.get("Accept-Encoding", "")):
            key = (str(path), path.stat().st_mtime_ns)
            if key not in _GZ:
                _GZ.clear()
                _GZ[key] = gzip.compress(path.read_bytes(), 6)
            body = _GZ[key]
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Encoding", "gzip")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()


class _Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True


def cmd_serve(args):
    # bound to the loopback interface only: the page is reachable from this
    # computer and nowhere else (no LAN access, no public tunnel)
    with _Server(("127.0.0.1", args.port), _Handler) as httpd:
        print(f"http://localhost:{args.port}  (local only; Ctrl+C to stop)", flush=True)
        httpd.serve_forever()


# --------------------------------------------------------------------------
# multi-site style catalogue
# --------------------------------------------------------------------------


def cmd_fetch(args):
    _warn_contact()
    sites = load_sites(args.sites, args.only)

    def work(site):
        return fetch_raw(site, RAW, delay=args.delay, max_pages=args.max_pages)

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        for r in pool.map(work, sites):  # one thread per site; each site is throttled
            print(f"  {r['site']:<16} {r['status']:<8} products={r['products']:<6} "
                  f"pages={r.get('pages', 0):<4} {r['error'] or ''}", flush=True)


def cmd_build(args):
    from . import sketch
    from .build import balance, dedupe, site_pool
    sites = load_sites(args.sites, args.only)
    pool_items, runs, drops, per_site_pool = [], [], Counter(), {}
    acc_items, acc_drops = [], Counter()
    for site in sites:
        raw = load_raw(RAW, site["name"])
        if raw is None:
            print(f"  {site['name']:<16} no cached feed (run fetch)", flush=True)
            runs.append({"site": site["name"], "status": "error", "error": "no cached feed"})
            continue
        items, dropped = site_pool(site, raw, catalogue=GENDER)
        drops.update(dropped)
        per_site_pool[site["name"]] = len(items)
        pool_items += items
        if not args.no_accessories:
            acc, acc_dropped = site_pool(site, raw, accessories=True, catalogue=GENDER)
            acc_items += acc
            acc_drops.update(acc_dropped)
        runs.append({"site": site["name"], "status": "ok", "pages": raw.get("pages", 0),
                     "scanned": len(raw["products"]), "fetched_at": raw["fetched_at"]})
        print(f"  {site['name']:<17} {len(raw['products']):>6} products -> {len(items):>6} "
              f"{_who()} garments, {len(acc) if not args.no_accessories else 0:>5} footwear / "
              "accessories", flush=True)
    pool_items, dup = dedupe(pool_items)
    catalogue, bal = balance(pool_items, per_style=args.per_style,
                             site_cap=args.site_cap, total=(args.min_total, args.max_total),
                             styles=STYLES)
    # footwear and accessories: every men's item in scope (no style balancing),
    # added next to the garment catalogue without changing it
    acc_items, acc_dup = dedupe(acc_items)
    have = {i["id"] for i in catalogue}
    acc_items = [i for i in acc_items if i["id"] not in have]
    garments = catalogue
    catalogue = garments + acc_items
    stored = Counter(i["site"] for i in catalogue)
    for r in runs:
        r["stored"] = stored.get(r["site"], 0)
        r["counts"] = dict(Counter(i["primary_style"] for i in catalogue
                                   if i["site"] == r["site"]))
    if GENDER == "women":
        from . import sketch_women as sketch
    n_new = sketch.write_sketches(catalogue, WEB, force=args.force)
    con = store.connect(DB)
    try:
        store.save_catalogue(con, catalogue, runs)
        n = store.export_json(con, OUT)
    finally:
        con.close()
    write_report(garments, pool_items, bal, drops, dup, runs, per_site_pool,
                 acc_items, acc_drops + acc_dup)
    print(f"\n{_who()} garment pool {len(pool_items)} (after removing "
          f"{sum(dup.values())} duplicates) -> {len(garments)} garments")
    for s in STYLES:
        print(f"  {STYLE_LABELS[s]:<14} {bal['per_style'][s]:>5}   (pool {bal['pool_per_style'][s]})")
    print(f"  unclassified in pool: {bal['pool_per_style'][UNCLASSIFIED]} "
          f"({100 * bal['pool_per_style'][UNCLASSIFIED] / max(1, len(pool_items)):.1f}%)")
    print(f"footwear: {sum(1 for i in acc_items if i['department'] == 'footwear')}, "
          f"accessories: {sum(1 for i in acc_items if i['department'] == 'accessories')} "
          f"(all {_who()} items in scope)")
    print(f"sketches drawn: {n_new} new; exported {n} items -> {OUT}\nreport -> {REPORT}",
          flush=True)


def cmd_scrape_all(args):
    cmd_fetch(args)
    cmd_build(args)


def cmd_sketch(args):
    from . import sketch
    if GENDER == "women":
        from . import sketch_women as sketch
    con = store.connect(DB)
    try:
        items = [store.decode(r) for r in con.execute("SELECT * FROM items")]
        n = sketch.write_sketches(items, WEB, force=True)
        with con:
            con.executemany("UPDATE items SET sketch = ? WHERE id = ?",
                            [(i["sketch"], i["id"]) for i in items])
        print(f"drew {n} sketches; exported {store.export_json(con, OUT)} items", flush=True)
    finally:
        con.close()


def cmd_audit(args):
    """Random sample per style for the section-10 precision review."""
    con = store.connect(DB)
    try:
        items = [store.decode(r) for r in con.execute("SELECT * FROM items")]
    finally:
        con.close()
    rng = random.Random(args.seed)
    for s in STYLES:
        its = [i for i in items if i["primary_style"] == s]
        print(f"\n== {STYLE_LABELS[s]} ({len(its)} items)")
        for i in rng.sample(its, min(args.sample, len(its))):
            print(f"  [ ] {i['site']:<14} {i['category']:<13} {i['style_confidence']:<6} "
                  f"{i['title'][:70]}")


def _top_keywords(items, style, n=10):
    c = Counter()
    for i in items:
        if i["primary_style"] == style:
            c.update(h for h in i.get("style_hits") or [] if h not in ("palette", "fabric"))
    return ", ".join(f"{k} ({v})" for k, v in c.most_common(n))


def _accessory_report(acc, drops):
    from .classify import DEPARTMENT
    n = len(acc)
    L = ["", "## Footwear and accessories", "",
         f"**{n:,} items**: every {_who()} footwear and accessory product in scope on the same "
         "sites (same men's rules; no style balancing). They are stored next to the garments, "
         "which are unchanged.", "",
         "| Department | Category | Items |", "| --- | --- | ---: |"]
    for c, k in Counter(i["category"] for i in acc).most_common():
        L.append(f"| {DEPARTMENT.get(c)} | {c.replace('_', ' ')} | {k:,} |")
    L += ["", "| Style | Items |", "| --- | ---: |"]
    for s in (*STYLES, UNCLASSIFIED):
        k = sum(1 for i in acc if i["primary_style"] == s)
        if k:
            L.append(f"| {STYLE_LABELS[s]} | {k:,} |")
    L += ["", "| Site | Footwear | Accessories | Total |", "| --- | ---: | ---: | ---: |"]
    for site, k in Counter(i["site"] for i in acc).most_common():
        fw = sum(1 for i in acc if i["site"] == site and i["department"] == "footwear")
        L.append(f"| {site} | {fw:,} | {k - fw:,} | {k:,} |")
    L += ["", "Dropped (footwear / accessories):", "", "| Reason | Products |", "| --- | ---: |"]
    for r, k in drops.most_common():
        L.append(f"| {r} | {k:,} |")
    return L


def write_report(cat, pool_items, bal, drops, dup, runs, per_site_pool, acc=(), acc_drops=None):
    """catalogue_report.md: counts per style and site (taxonomy section 11)."""
    from .classify import DEPARTMENT
    n = len(cat)
    title = "Women's catalogue report" if GENDER == "women" else "Catalogue report"
    lo, hi = (1450, 1650) if GENDER == "women" else (1600, 1900)
    L = [f"# {title}", "",
         f"Generated {time.strftime('%Y-%m-%d %H:%M')} by `python -m pipeline.run build"
         + (" --gender women" if GENDER == "women" else "") + "`.", "",
         f"**{n:,} garments** in the catalogue, chosen from a {_who()} pool of "
         f"{len(pool_items):,} items across {sum(1 for r in runs if r['status'] == 'ok')} "
         "Indian sites.", "",
         "## Items per style", "",
         f"| Style | Catalogue | {_who().capitalize()} pool | Target {lo:,}–{hi:,} | "
         "Top keywords that fired |",
         "| --- | ---: | ---: | --- | --- |"]
    for s in STYLES:
        k = bal["per_style"][s]
        status = "met" if k >= lo else f"short by {lo - k:,} (pool exhausted)"
        L.append(f"| {STYLE_LABELS[s]} | {k:,} | {bal['pool_per_style'][s]:,} | {status} | "
                 f"{_top_keywords(cat, s)} |")
    u = bal["pool_per_style"][UNCLASSIFIED]
    L += ["", f"Unclassified: {u:,} items ({100 * u / max(1, len(pool_items)):.1f}% of the pool; "
          "target ≤ 10%). They are left out of the catalogue rather than relabelled.", "",
          "## Confidence", "", "| Confidence | Items | Share |", "| --- | ---: | ---: |"]
    conf = Counter(i["style_confidence"] for i in cat)
    for c in ("high", "medium", "low"):
        L.append(f"| {c} | {conf[c]:,} | {100 * conf[c] / max(1, n):.0f}% |")
    L += ["", "## Items per site", "",
          f"Each site is capped at {bal['site_cap']:,} items (12% of 15,000).", "",
          f"| Site | Catalogue | Share | {_who().capitalize()} pool | Top styles |",
          "| --- | ---: | ---: | ---: | --- |"]
    by_site = Counter(i["site"] for i in cat)
    for site, k in by_site.most_common():
        st = Counter(i["primary_style"] for i in cat if i["site"] == site).most_common(3)
        L.append(f"| {site} | {k:,} | {100 * k / n:.1f}% | {per_site_pool.get(site, 0):,} | "
                 + ", ".join(f"{STYLE_LABELS[a]} {b}" for a, b in st) + " |")
    L += ["", "## Price bands", "", "| Band | Items |", "| --- | ---: |"]
    for b, k in Counter(i["price_band"] for i in cat).most_common():
        L.append(f"| {b} | {k:,} |")
    L += ["", "## Departments", "", "| Department | Items |", "| --- | ---: |"]
    for d, k in Counter(DEPARTMENT.get(i["category"]) for i in cat).most_common():
        L.append(f"| {d} | {k:,} |")
    L += ["", "## What was dropped", "", "| Reason | Products |", "| --- | ---: |"]
    for r, k in (drops + dup).most_common():
        L.append(f"| {r} | {k:,} |")
    L += ["", "## Sites", "", "| Site | Status | Products in feed | Feed fetched |",
          "| --- | --- | ---: | --- |"]
    for r in runs:
        L.append(f"| {r['site']} | {r['status']} | {r.get('scanned', 0):,} | "
                 f"{r.get('fetched_at', '')[:16]} |")
    if acc:
        L += _accessory_report(list(acc), acc_drops or Counter())
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")


def main(argv=None):
    p = argparse.ArgumentParser(prog="pipeline")
    p.add_argument("command", choices=["check", "fetch", "build", "scrape", "sketch", "audit",
                                       "params", "scrape-quota", "images", "export", "serve",
                                       "report"])
    p.add_argument("--gender", choices=["men", "women"], default="men",
                   help="which catalogue: men (default) or women")
    p.add_argument("--sites", help="site list (default sites.json / sites_women.json)")
    p.add_argument("--only", help="comma-separated site names")
    p.add_argument("--per-cell", type=int, default=20,
                   help="items per (price band, category); 0 = no cap")
    p.add_argument("--bands", help="only these price bands, e.g. cheap,luxury")
    p.add_argument("--categories", help="only these categories, e.g. tshirt,jeans")
    p.add_argument("--delay", type=float, default=1.0, help="seconds between requests")
    p.add_argument("--max-pages", type=int, default=200)
    p.add_argument("--sample-pages", type=int, default=1, help="pages sampled by params")
    p.add_argument("--workers", type=int, default=8, help="sites fetched in parallel")
    p.add_argument("--segmenter", choices=["cloth", "plain"], default="cloth")
    p.add_argument("--max-views", type=int, default=4,
                   help="flat images (angles) per item; 0 = every usable photo")
    p.add_argument("--size", type=int, default=512, help="flat image size in px")
    p.add_argument("--limit", type=int, help="images: process at most N items")
    p.add_argument("--force", action="store_true", help="images: redo items already done")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--count", action="store_true", help="check: count items per site")
    p.add_argument("--per-style", type=int,
                   help="build: items per style (default 1875 men, 1600 women)")
    p.add_argument("--site-cap", type=float, default=0.12, help="build: max share per site")
    p.add_argument("--min-total", type=int, default=13000)
    p.add_argument("--no-accessories", action="store_true",
                   help="build: garments only (skip footwear and accessories)")
    p.add_argument("--max-total", type=int, default=15000)
    p.add_argument("--sample", type=int, default=20, help="audit: items per style")
    p.add_argument("--seed", type=int, default=1, help="audit: random seed")
    args = p.parse_args(argv)
    if args.gender == "women":
        _use_women()
    args.sites = args.sites or str(ROOT / ("sites_women.json" if args.gender == "women"
                                           else "sites.json"))
    if args.per_style is None:
        args.per_style = 1600 if args.gender == "women" else 1875
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
    {"check": cmd_check, "fetch": cmd_fetch, "build": cmd_build, "scrape": cmd_scrape_all,
     "sketch": cmd_sketch, "audit": cmd_audit, "params": cmd_params,
     "scrape-quota": cmd_scrape, "images": cmd_images, "export": cmd_export,
     "serve": cmd_serve, "report": cmd_report}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())

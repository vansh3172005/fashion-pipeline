"""Style Catalogue API: the men's and women's catalogues, filters, analytics and
the outfit recommender, as a small local JSON API.

    python api.py                 -> http://localhost:8000   (this computer only)
    python api.py --port 8080

Plain Python 3.9+; nothing to install. See API.md for every endpoint.
The data is internal: the server listens on 127.0.0.1 only and must not be
exposed to the internet.
"""
import argparse
import gzip
import json
import mimetypes
import re
import socket
import threading
import time
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from itertools import islice
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

import recommend as R

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
STATIC = HERE / "static"
WEB = HERE / "web"
GENDERS = ("men", "women")

# facet name -> (item field, multi-valued?)
FACETS = {
    "department": ("department", False), "style": ("primary_style", False),
    "style_tag": ("style_tags", True), "category": ("category", False), "site": ("site", False),
    "price_band": ("price_band", False), "color": ("color", False),
    "secondary_color": ("secondary_color", False), "pattern": ("pattern", False),
    "fit": ("fit", False), "fabric": ("fabric", False), "sleeve_length": ("sleeve_length", False),
    "neckline": ("neckline", False), "occasion": ("occasion", False),
    "item_gender": ("gender", False), "confidence": ("style_confidence", False),
    "size": ("sizes_available", True),
}
DROPDOWNS = ("department", "style", "category", "site", "price_band", "color", "occasion",
             "item_gender")
ANALYTICS = (("color", "Colour"), ("pattern", "Pattern"), ("fit", "Fit"), ("fabric", "Fabric"))
COMPACT = ("id", "title", "site", "category", "department", "gender", "color", "secondary_color",
           "pattern", "fit", "fabric", "sleeve_length", "neckline", "occasion", "primary_style",
           "style_tags", "price", "mrp", "discount_pct", "price_band", "sizes_available", "sketch",
           "image", "url")

# ---------------------------------------------------------------- data
CAT, BY_ID = {}, {}
for g in GENDERS:
    CAT[g] = json.loads((DATA / f"catalogue_{g}.json").read_text(encoding="utf-8"))
    for it in CAT[g]:
        BY_ID[it["id"]] = (g, it)


def compact(it):
    return {k: it[k] for k in COMPACT if k in it}


def vals(it, facet):
    field, multi = FACETS[facet]
    v = it.get(field)
    if multi:
        return [str(x) for x in v or []]
    if v is None:  # same rule as the page: missing values group as "unspecified" / "n/a"
        return ["n/a" if (it.get("attr_source") or {}).get(facet) == "n/a" else "unspecified"]
    return [str(v)]


def parse_filters(q):
    """?style=minimalist&color=white,black -> {"style": {"minimalist"}, "color": {...}}"""
    out = {}
    for f in FACETS:
        raw = ",".join(q.get(f, []))
        vs = {v.strip() for v in raw.split(",") if v.strip()}
        if vs:
            out[f] = vs
    return out


def matches(it, filters, skip=None, text=None):
    for f, wanted in filters.items():
        if f != skip and not wanted.intersection(vals(it, f)):
            return False
    if text:
        hay = " ".join(str(it.get(k) or "") for k in ("title", "site", "vendor", "primary_style"))
        if text not in hay.lower().replace("_", " "):
            return False
    return True


def pct(n, total):
    x = 100 * n / total if total else 0
    return round(x, 1)


def counts(items, facet):
    c = {}
    for it in items:
        for v in vals(it, facet):
            c[v] = c.get(v, 0) + 1
    return sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))


# ---------------------------------------------------------------- outfits: lazy search, cached
_STREAMS, _LOCK = OrderedDict(), threading.Lock()


def outfit_page(gender, f, seed, offset, limit):
    key = (gender, tuple(sorted(f.items())), seed)
    with _LOCK:
        entry = _STREAMS.pop(key, None) or {"gen": R.outfit_stream(CAT[gender], f, seed),
                                           "found": [], "done": False, "lock": threading.Lock()}
        _STREAMS[key] = entry
        while len(_STREAMS) > 12:
            _STREAMS.popitem(last=False)
    with entry["lock"]:
        need = offset + limit + 1
        while not entry["done"] and len(entry["found"]) < need:
            nxt = list(islice(entry["gen"], need - len(entry["found"])))
            entry["found"] += nxt
            if not nxt:
                entry["done"] = True
        found = entry["found"]
        return found[offset:offset + limit], len(found) > offset + limit, entry["done"], len(found)


def outfit_json(o):
    return {"items": [compact(i) for i in o["items"]], "score": o["score"], "max": o["max"],
            "why": o["why"], "total_price": round(sum(i.get("price") or 0 for i in o["items"]), 2)}


# ---------------------------------------------------------------- endpoints
def _gender(q):
    g = (q.get("gender") or ["men"])[0].lower()
    if g not in GENDERS:
        raise ValueError("gender must be 'men' or 'women'")
    return g


def _int(q, name, default, lo, hi):
    try:
        return max(lo, min(hi, int((q.get(name) or [default])[0])))
    except ValueError:
        raise ValueError(f"{name} must be a whole number")


def ep_index(q):
    return {"name": "Style Catalogue API", "docs": "see API.md",
            "endpoints": ["/api/health", "/api/items", "/api/items/{id}", "/api/filters",
                          "/api/analytics", "/api/outfits", "/api/look/{id}"]}


def ep_health(q):
    return {"status": "ok", "items": {g: len(CAT[g]) for g in GENDERS}}


SORTS = {"price-asc": (lambda i: (i.get("price") is None, i.get("price") or 0)),
         "price-desc": (lambda i: (i.get("price") is None, -(i.get("price") or 0))),
         "discount": (lambda i: -(i.get("discount_pct") or 0))}


def ep_items(q):
    g = _gender(q)
    filters = parse_filters(q)
    text = (q.get("q") or [""])[0].strip().lower()
    lst = [it for it in CAT[g] if matches(it, filters, text=text)]
    sort = (q.get("sort") or [""])[0]
    if sort:
        if sort not in SORTS:
            raise ValueError("sort must be price-asc, price-desc or discount")
        lst.sort(key=SORTS[sort])
    size = _int(q, "page_size", 48, 1, 200)
    page = _int(q, "page", 1, 1, 10**6)
    full = (q.get("full") or ["0"])[0] in ("1", "true")
    chunk = lst[(page - 1) * size: page * size]
    return {"gender": g, "total": len(lst), "share_of_catalogue": pct(len(lst), len(CAT[g])),
            "page": page, "page_size": size, "pages": (len(lst) + size - 1) // size,
            "items": chunk if full else [compact(i) for i in chunk]}


def ep_item(q, item_id):
    hit = BY_ID.get(item_id)
    if not hit:
        return None
    g, it = hit
    return {"gender": g, "item": it}


def ep_filters(q):
    g = _gender(q)
    filters = parse_filters(q)
    out = {}
    for f in (q.get("facets") or [",".join(DROPDOWNS)])[0].split(","):
        if f not in FACETS:
            raise ValueError(f"unknown facet {f!r}")
        base = [it for it in CAT[g] if matches(it, filters, skip=f)]
        out[f] = {"total": len(base), "selected": sorted(filters.get(f, [])),
                  "options": [{"value": v, "count": n, "pct": pct(n, len(base))}
                              for v, n in counts(base, f)]}
    return {"gender": g, "facets": out}


def ep_analytics(q):
    g = _gender(q)
    filters = parse_filters(q)
    lst = [it for it in CAT[g] if matches(it, filters)]
    tables = {}
    for f, title in ANALYTICS:
        # fit and fabric only exist for clothes: count only items that have a value
        rows = [it for it in lst if it.get(FACETS[f][0]) is not None] if f in ("fit", "fabric") else lst
        tables[f] = {"title": title, "base": len(rows),
                     "rows": [{"value": v, "count": n, "pct": pct(n, len(rows))}
                              for v, n in counts(rows, f)]}
    return {"gender": g, "items_in_view": len(lst), "share_of_catalogue": pct(len(lst), len(CAT[g])),
            "tables": tables}


def ep_outfits(q):
    g = _gender(q)
    f = {}
    for k in ("kind", "style", "occasion", "band", "size"):
        v = (q.get(k) or [""])[0].strip()
        if v:
            f[k] = v
    if f.get("kind") and f["kind"] not in R.KINDS:
        raise ValueError("kind must be western, onepiece, indian or coord")
    seed = _int(q, "seed", 0, 0, 10**9)
    offset = _int(q, "offset", 0, 0, 10**6)
    limit = _int(q, "limit", 48, 1, 200)
    t = time.time()
    page, more, done, found = outfit_page(g, f, seed, offset, limit)
    return {"gender": g, "filters": f, "seed": seed, "offset": offset, "limit": limit,
            "has_more": more, "search_complete": done, "found_so_far": found,
            "took_ms": round(1000 * (time.time() - t)), "outfits": [outfit_json(o) for o in page]}


def ep_look(q, item_id):
    hit = BY_ID.get(item_id)
    if not hit:
        return None
    g, it = hit
    n = _int(q, "n", 3, 1, 10)
    seed = _int(q, "seed", 0, 0, 10**9)
    size = (q.get("size") or [""])[0] or None
    looks = R.complete_look(it, CAT[g], size=size, n=n, seed=seed)
    return {"gender": g, "anchor": compact(it), "looks": [outfit_json(o) for o in looks]}


ROUTES = {"/api": ep_index, "/api/": ep_index, "/api/health": ep_health, "/api/items": ep_items,
          "/api/filters": ep_filters, "/api/analytics": ep_analytics, "/api/outfits": ep_outfits}
ID_ROUTES = ((re.compile(r"^/api/items/(.+)$"), ep_item), (re.compile(r"^/api/look/(.+)$"), ep_look))


# ---------------------------------------------------------------- HTTP
class Handler(BaseHTTPRequestHandler):
    server_version = "StyleCatalogueAPI/1.0"

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} {fmt % args}", flush=True)

    def _send(self, status, body, ctype, cache=False):
        if "gzip" in self.headers.get("Accept-Encoding", "") and len(body) > 1024:
            body = gzip.compress(body, 6)
            gz = True
        else:
            gz = False
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        if gz:
            self.send_header("Content-Encoding", "gzip")
        self.send_header("Cache-Control", "max-age=86400" if cache else "no-cache")
        # any page served from this computer (e.g. a dev server on :5173) may call the API
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status, obj):
        self._send(status, json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
                   "application/json; charset=utf-8")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def do_GET(self):
        parts = urlsplit(self.path)
        path, q = unquote(parts.path), parse_qs(parts.query)
        try:
            if path.startswith("/api"):
                return self._api(path, q)
            return self._static(path)
        except ValueError as e:
            return self._json(400, {"error": str(e)})
        except Exception as e:  # noqa: BLE001 - report, keep serving
            return self._json(500, {"error": f"{type(e).__name__}: {e}"})

    def _api(self, path, q):
        if path in ROUTES:
            return self._json(200, ROUTES[path](q))
        for rx, fn in ID_ROUTES:
            m = rx.match(path)
            if m:
                res = fn(q, m.group(1))
                return self._json(200, res) if res else self._json(404, {"error": "no item with that id"})
        return self._json(404, {"error": "unknown endpoint; see /api"})

    def _static(self, path):
        # the starter page (web/), the data files it loads, and the sketch images
        alias = {"/": WEB / "index.html", "/index.html": WEB / "index.html",
                 "/recommend.js": WEB / "recommend.js",
                 "/catalogue.json": DATA / "catalogue_men.json",
                 "/catalogue_women.json": DATA / "catalogue_women.json"}
        if path in alias:
            f = alias[path]
        elif path.startswith(("/sketch/", "/sketch_women/")):
            f = (STATIC / path.lstrip("/")).resolve()
            if STATIC.resolve() not in f.parents:  # no "../" escapes
                return self._json(404, {"error": "not found"})
        else:
            return self._json(404, {"error": "not found"})
        if not f.is_file():
            return self._json(404, {"error": "not found"})
        ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/json", "application/javascript", "image/svg+xml"):
            ctype += "; charset=utf-8"
        self._send(200, f.read_bytes(), ctype, cache=path.startswith("/sketch"))


def main():
    ap = argparse.ArgumentParser(description="Style Catalogue API (local only)")
    ap.add_argument("--port", type=int, default=8000)
    a = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)  # this computer only
    srv.daemon_threads = True
    # "localhost" may resolve to the IPv6 loopback first; answer there too (still this
    # computer only) so requests don't wait ~2 s for an IPv4 fallback
    try:
        class V6(ThreadingHTTPServer):
            address_family = socket.AF_INET6
            daemon_threads = True
        v6 = V6(("::1", a.port), Handler)
        threading.Thread(target=v6.serve_forever, daemon=True).start()
    except OSError:
        pass
    print(f"Style Catalogue API on http://localhost:{a.port}  "
          f"(men {len(CAT['men']):,} items, women {len(CAT['women']):,} items)\n"
          f"  API:  http://localhost:{a.port}/api      page: http://localhost:{a.port}/\n"
          "  Ctrl+C to stop", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

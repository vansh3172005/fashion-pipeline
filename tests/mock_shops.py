"""Local mock Shopify stores (ports 9101-9104) for offline end-to-end tests.

Products look like the target site (Bonkers Corner): a spec block in
body_html ("Composition:", "Color:", "Fit:", "Sleeve length:", "Neckline:"),
Men/Women tags, a Size option with per-variant availability, prices across
the cheap / affordable / luxury bands, and real PNG product photos (a garment
shape on a flat studio background) served at /img/<id>-<n>.png.

  shop01  healthy, every band and category in stock
  shop02  returns 403 for the feed (status error, nothing stored)
  shop03  robots.txt disallows /products.json (status blocked)
  shop04  no luxury stock at all (status short)
"""
import io
import json
import random
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from PIL import Image, ImageDraw

COLORS = ["Black", "Navy Blue", "Olive", "Charcoal", "Off White", "Burgundy", "Sand",
          "Sky Blue", "Mustard", "Rust", "Lavender", "Black & White"]
RGB = {"Black": (20, 20, 20), "Navy Blue": (30, 40, 80), "Olive": (90, 100, 50),
       "Charcoal": (70, 70, 72), "Off White": (235, 230, 220), "Burgundy": (110, 20, 35),
       "Sand": (200, 180, 140), "Sky Blue": (120, 170, 220), "Mustard": (200, 160, 30),
       "Rust": (170, 80, 40), "Lavender": (180, 160, 210), "Black & White": (20, 20, 20)}
COMPOSITION = ["100% Cotton", "60% Cotton 40% Polyester", "88% Lenzing Modal 12% Spandex",
               "95% Cotton 5% Spandex", "100% Polyester"]
TEMPLATES = {
    "tshirt": ["Oversized Graphic T-shirt", "Classic Tee", "Long Sleeve T-shirt"],
    "polo": ["Knit Polo", "Polo T-shirt"],
    "shirt": ["Relaxed Fit Shirt", "Striped Oxford Shirt"],
    "top": ["Square Neck Crop Top", "Ribbed Halter Top"],
    "hoodie": ["Oversized Hoodie"],
    "joggers": ["Wide Leg Joggers"],
    "jeans": ["Straight Fit Jeans"],
}
FITS = ["Oversized Fit", "Regular Fit", "Slim fit", "Relaxed Fit"]
NOISE = ["Coffee Club Cap", "Bonkers Socks - Pack of 3", "Canvas Tote", "Lace Boxer Shorts"]
PRICES = {"cheap": [499, 599, 799], "affordable": [899, 1199, 1499], "luxury": [1599, 1999, 2799]}


def body(color, comp, fit, cat):
    lines = [f"<strong>Composition:</strong> {comp}", "<strong>GSM:</strong> 240",
             f"<strong>Color:</strong> <span>{color}</span>",
             "<strong>Wash care:</strong> Machine wash cold with similar colors.",
             f"<strong>Fit:</strong> {fit}"]
    if cat not in ("joggers", "jeans"):
        lines.append("<strong>Sleeve length:</strong> Short Sleeve")
        lines.append("<strong>Neckline:</strong> Round neck")
    return ("<p>PRODUCT DETAILS<br><br>" + "<br>".join(lines) +
            "<br></p><ul><li>MRP: Rs.1999/- incl. of all taxes.</li></ul>"
            "<p>Made for running errands and evening looks.</p>")


def catalogue(idx: int):
    rnd = random.Random(idx)
    bands = ["cheap", "affordable"] if idx == 4 else ["cheap", "affordable", "luxury"]
    products, pid = [], idx * 100000
    for cat, titles in TEMPLATES.items():
        for band in bands:
            for i in range(8):
                pid += 1
                color = rnd.choice(COLORS)
                gender = rnd.choice([["Men"], ["Women"], ["Men", "Women"]])
                sizes = ["XS", "S", "M", "L", "XL"]
                price = rnd.choice(PRICES[band])
                products.append({
                    "id": pid, "title": f"{color} {rnd.choice(titles)} {i}",
                    "handle": f"item-{pid}", "vendor": "Mock", "product_type": "",
                    "tags": gender + ["New In"],
                    "body_html": body(color, rnd.choice(COMPOSITION), rnd.choice(FITS), cat),
                    "options": [{"name": "Size", "values": sizes}],
                    "variants": [{"option1": s, "price": f"{price}.00",
                                  "compare_at_price": f"{price + 200}.00",
                                  "available": s != "XS"} for s in sizes],
                    "images": ([] if i == 7 else
                               [{"src": f"/img/{pid}-{n}.png"} for n in range(3)]),
                    "_rgb": RGB[color],
                })
    for j, n in enumerate(NOISE * 3):
        pid += 1
        products.append({"id": pid, "title": f"{n} {j}", "handle": f"x-{pid}", "tags": [],
                         "options": [], "variants": [{"price": "299.00"}],
                         "images": [{"src": f"/img/{pid}-0.png"}], "_rgb": (0, 0, 0)})
    rnd.shuffle(products)
    return products


def photo(rgb, view: int) -> bytes:
    """A garment-ish shape on a light grey studio backdrop; view 2 is a close-up."""
    im = Image.new("RGB", (300, 400), (236, 236, 234))
    d = ImageDraw.Draw(im)
    if view == 2:  # detail shot: fabric fills the frame -> must be rejected
        d.rectangle([0, 0, 299, 399], fill=rgb)
    else:
        d.rectangle([90, 80, 210, 330], fill=rgb)                    # body
        d.polygon([(90, 80), (40, 150), (60, 170), (90, 120)], fill=rgb)    # sleeve
        d.polygon([(210, 80), (260, 150), (240, 170), (210, 120)], fill=rgb)
        if view == 1:
            d.rectangle([100, 110, 200, 300], fill=(240, 240, 240))  # back print
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def make_handler(idx, port):
    prods = catalogue(idx)
    by_id = {p["id"]: p for p in prods}
    public = []
    for p in prods:
        q = {k: v for k, v in p.items() if k != "_rgb"}
        q["images"] = [{"src": f"http://127.0.0.1:{port}{i['src']}"} for i in p["images"]]
        public.append(q)

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code, body, ctype="application/json"):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.end_headers()
            self.wfile.write(body if isinstance(body, bytes) else body.encode())

        def do_GET(self):
            u = urlparse(self.path)
            if u.path == "/robots.txt":
                if idx == 3:
                    return self._send(200, "User-agent: *\nDisallow: /products.json\n",
                                      "text/plain")
                return self._send(404, "")
            if u.path.startswith("/img/"):
                pid, view = u.path[5:-4].split("-")
                return self._send(200, photo(by_id[int(pid)]["_rgb"], int(view)), "image/png")
            if idx == 2:
                return self._send(403, "forbidden")
            if u.path == "/products.json":
                q = parse_qs(u.query)
                limit, page = int(q.get("limit", [30])[0]), int(q.get("page", [1])[0])
                chunk = public[(page - 1) * limit: page * limit]
                return self._send(200, json.dumps({"products": chunk}))
            self._send(404, "")

    return H


def start(n=4, base_port=9100):
    servers = []
    for idx in range(1, n + 1):
        port = base_port + idx
        s = ThreadingHTTPServer(("127.0.0.1", port), make_handler(idx, port))
        threading.Thread(target=s.serve_forever, daemon=True).start()
        servers.append(s)
    return servers


def sites_config(n=4, base_port=9100):
    return [{"name": f"shop{idx:02d}", "base_url": f"http://127.0.0.1:{base_port + idx}",
             "currency": "INR",
             "price_bands": {"cheap": [0, 799], "affordable": [800, 1499], "luxury": [1500, None]}}
            for idx in range(1, n + 1)]

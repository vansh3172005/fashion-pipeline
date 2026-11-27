"""SQLite persistence + JSON export for the frontend."""
import json
import sqlite3
import time
from pathlib import Path

# columns stored as JSON text
JSON_COLS = ("images", "fabrics", "composition", "sizes", "sizes_available",
             "attr_source", "flat_images", "image_colors", "occasions", "wear_types",
             "style_tags", "style_scores", "style_hits")

COLUMNS = (
    ("id", "TEXT PRIMARY KEY"),
    ("site", "TEXT NOT NULL"),
    ("title", "TEXT NOT NULL"),
    ("url", "TEXT NOT NULL"),
    ("image", "TEXT NOT NULL"),
    ("images", "TEXT"),
    ("price", "REAL"),
    ("mrp", "REAL"),
    ("discount_pct", "INTEGER"),
    ("currency", "TEXT"),
    ("price_band", "TEXT"),
    ("available", "INTEGER"),
    ("vendor", "TEXT"),
    ("category", "TEXT NOT NULL"),
    ("department", "TEXT"),
    ("gender", "TEXT NOT NULL"),
    ("color", "TEXT"),
    ("color_name", "TEXT"),
    ("secondary_color", "TEXT"),
    ("pattern", "TEXT"),
    ("fit", "TEXT"),
    ("fabric", "TEXT"),
    ("fabrics", "TEXT"),
    ("composition", "TEXT"),
    ("gsm", "INTEGER"),
    ("sleeve_length", "TEXT"),
    ("neckline", "TEXT"),
    ("occasion", "TEXT"),
    ("occasions", "TEXT"),
    ("sizes", "TEXT"),
    ("sizes_available", "TEXT"),
    ("attr_source", "TEXT"),
    ("flat_images", "TEXT"),
    ("wear_types", "TEXT"),
    ("primary_style", "TEXT"),
    ("style_tags", "TEXT"),
    ("style_scores", "TEXT"),
    ("style_confidence", "TEXT"),
    ("style_source", "TEXT"),
    ("style_hits", "TEXT"),
    ("sketch", "TEXT"),
    ("packshot", "TEXT"),   # studio product shot from the shop photo (pipeline/packshot.py)
    ("image_colors", "TEXT"),
    ("scraped_at", "INTEGER NOT NULL"),
)
NAMES = [c for c, _ in COLUMNS]

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS items ({", ".join(f"{c} {t}" for c, t in COLUMNS)});
CREATE INDEX IF NOT EXISTS ix_items_cat ON items(category);
CREATE INDEX IF NOT EXISTS ix_items_band ON items(price_band);
CREATE INDEX IF NOT EXISTS ix_items_gender ON items(gender);
CREATE TABLE IF NOT EXISTS scrape_runs (
    site TEXT, run_at INTEGER, status TEXT, pages INTEGER, scanned INTEGER,
    total INTEGER, counts TEXT, error TEXT
);
"""


def connect(path) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    cols = {r[1] for r in con.execute("PRAGMA table_info(items)")}
    if cols and "price_band" not in cols:
        # database from the v1 (multi-site, 4-category) pipeline: keep it aside
        with con:
            con.execute("ALTER TABLE items RENAME TO items_v1")
            con.execute("DROP INDEX IF EXISTS ix_items_cat")
            con.execute("DROP INDEX IF EXISTS ix_items_site")
    con.executescript(SCHEMA)
    have = {r[1] for r in con.execute("PRAGMA table_info(items)")}
    with con:  # columns added in later versions
        for c, t in COLUMNS:
            if c not in have:
                con.execute(f"ALTER TABLE items ADD COLUMN {c} {t.replace(' NOT NULL', '')}")
        con.execute("CREATE INDEX IF NOT EXISTS ix_items_style ON items(primary_style)")
    return con


def _row(item, now):
    out = []
    for c in NAMES:
        v = now if c == "scraped_at" else item.get(c)
        if c in JSON_COLS:
            empty = None if c in ("composition", "style_scores") else []
            v = json.dumps(v if v is not None else empty)
        elif c == "available" and v is not None:
            v = int(v)
        out.append(v)
    return out


def save_site(con, site_name, items, report):
    """Replace a site's rows atomically so reruns never duplicate.

    Flat images already generated for an item are kept when the item is
    re-scraped, so a rescrape does not force reprocessing of photos.
    """
    now = int(time.time())
    with con:
        if report["status"] in ("ok", "short"):
            keep = {r["id"]: (r["flat_images"], r["image_colors"], r["secondary_color"],
                              r["attr_source"])
                    for r in con.execute("SELECT id, flat_images, image_colors, "
                                         "secondary_color, attr_source FROM items "
                                         "WHERE site = ?", (site_name,))}
            con.execute("DELETE FROM items WHERE site = ?", (site_name,))
            rows = []
            for i in items:
                prev = keep.get(i["id"])
                if prev and prev[0] not in (None, "[]"):
                    i = dict(i, flat_images=json.loads(prev[0]),
                             image_colors=json.loads(prev[1] or "null"))
                    old_src = json.loads(prev[3] or "{}")
                    if not i.get("secondary_color") and old_src.get("secondary_color") == "image":
                        i["secondary_color"] = prev[2]
                        i["attr_source"] = dict(i["attr_source"], secondary_color="image")
                rows.append(_row(i, now))
            con.executemany(
                f"INSERT OR REPLACE INTO items ({', '.join(NAMES)}) "
                f"VALUES ({', '.join('?' * len(NAMES))})", rows)
        counts = report.get("counts", {})
        con.execute(
            "INSERT INTO scrape_runs VALUES (?,?,?,?,?,?,?,?)",
            (site_name, now, report["status"], report["pages"], report.get("scanned", 0),
             len(items) if report["status"] in ("ok", "short") else 0,
             json.dumps(counts), report.get("error")),
        )


def save_catalogue(con, items, runs):
    """Replace the whole multi-site catalogue in one transaction (a failed
    build never leaves a half-written catalogue) and log one run row per site."""
    now = int(time.time())
    with con:
        keep = {r["id"]: (r["flat_images"], r["image_colors"])
                for r in con.execute("SELECT id, flat_images, image_colors FROM items")}
        con.execute("DELETE FROM items")
        rows = []
        for i in items:
            prev = keep.get(i["id"])
            if prev and prev[0] not in (None, "[]") and not i.get("flat_images"):
                i = dict(i, flat_images=json.loads(prev[0]),
                         image_colors=json.loads(prev[1] or "null"))
            rows.append(_row(i, now))
        con.executemany(
            f"INSERT OR REPLACE INTO items ({', '.join(NAMES)}) "
            f"VALUES ({', '.join('?' * len(NAMES))})", rows)
        for r in runs:
            con.execute("INSERT INTO scrape_runs VALUES (?,?,?,?,?,?,?,?)",
                        (r["site"], now, r["status"], r.get("pages", 0), r.get("scanned", 0),
                         r.get("stored", 0), json.dumps(r.get("counts", {})), r.get("error")))


def update_images(con, item_id, flat_images, image_colors, secondary_color=None):
    """Store flat-image paths; fill secondary colour from pixels if missing."""
    with con:
        row = con.execute("SELECT secondary_color, attr_source FROM items WHERE id = ?",
                          (item_id,)).fetchone()
        if row is None:
            return
        src = json.loads(row["attr_source"] or "{}")
        sec = row["secondary_color"]
        if not sec and secondary_color:
            sec, src["secondary_color"] = secondary_color, "image"
        con.execute("UPDATE items SET flat_images = ?, image_colors = ?, secondary_color = ?,"
                    " attr_source = ? WHERE id = ?",
                    (json.dumps(flat_images), json.dumps(image_colors), sec,
                     json.dumps(src), item_id))


def decode(row) -> dict:
    d = dict(row)
    for k in JSON_COLS:
        if k in d:
            d[k] = json.loads(d[k]) if d[k] else ([] if k not in ("composition",
                                                                  "image_colors") else None)
    return d


def export_json(con, out_path):
    rows = con.execute("SELECT * FROM items ORDER BY primary_style, category, title").fetchall()
    data = [decode(r) for r in rows]
    # stable mixed order, so the default catalogue view is not one style per screen
    import hashlib
    data.sort(key=lambda d: hashlib.md5(d["id"].encode()).hexdigest())
    for d in data:
        for k in ("scraped_at", "style_hits", "currency"):
            d.pop(k, None)
        d["images"] = (d.get("images") or [])[:6]  # the drawer shows up to six photos
        if not d.get("composition"):
            d.pop("composition", None)
        for k in [k for k, v in d.items() if v in (None, [], "")]:
            d.pop(k)  # the frontend treats a missing key as empty
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    return len(data)

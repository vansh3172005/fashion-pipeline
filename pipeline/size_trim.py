"""Keep one garment per size among garments with identical parameters.

Usage:  python -m pipeline.size_trim [--gender men|women] [--accessories] [--dry-run]

Garments (topwear, bottomwear, full-body; never footwear or accessories) are
grouped when every parameter shown in the detail panel matches: style, wear
type, category, gender, colour, secondary colour, pattern, fit, fabric, sleeve
length, neckline and occasion. In each group the fewest garments are kept that
still cover every size the group offers (a garment with no size list counts as
"one size"), preferring garments with more sizes, in stock, with a confident
style. The rest are deleted from the catalogue database, its JSON export and
their sketch files. This is permanent; the raw scraped feeds are not touched.
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path

from . import store

ROOT = Path(__file__).resolve().parent.parent
GARMENT_DEPTS = ("topwear", "bottomwear", "fullbody")
ACCESSORY_DEPTS = ("footwear", "accessories")   # --accessories: same rule for these
PARAMS = ("primary_style", "category", "gender", "color", "secondary_color", "pattern", "fit",
          "fabric", "sleeve_length", "neckline", "occasion")
CONF = {"high": 0, "medium": 1, "low": 2}


def group_key(it):
    return tuple(it.get(k) for k in PARAMS) + ((it.get("wear_types") or ["-"])[0],)


def choose(items, depts=GARMENT_DEPTS):
    """(keep, drop) for one catalogue's items; only the departments in ``depts`` are trimmed."""
    groups = defaultdict(list)
    keep, drop = [], []
    for it in items:
        if it.get("department") in depts:
            groups[group_key(it)].append(it)
        else:
            keep.append(it)  # other departments are left alone
    for members in groups.values():
        sizes = lambda i: set(i.get("sizes") or ["one size"])  # noqa: E731
        need = set().union(*(sizes(i) for i in members))
        members.sort(key=lambda i: (-len(sizes(i)), not i.get("available"),
                                    CONF.get(i.get("style_confidence"), 3), i["id"]))
        for it in members:
            if sizes(it) & need:
                keep.append(it)
                need -= sizes(it)
            else:
                drop.append(it)
    return keep, drop


def run(gender, dry_run=False, depts=GARMENT_DEPTS):
    db = ROOT / "data" / ("catalogue_women.db" if gender == "women" else "catalogue.db")
    out = ROOT / "web" / ("catalogue_women.json" if gender == "women" else "catalogue.json")
    con = store.connect(db)
    try:
        items = [store.decode(r) for r in con.execute("SELECT * FROM items")]
        keep, drop = choose(items, depts)
        n_in = sum(1 for i in items if i.get("department") in depts)
        print(f"{gender}: {len(items)} items ({n_in} in {'/'.join(depts)}) -> delete {len(drop)}, "
              f"keep {len(keep)}")
        if dry_run:
            return keep, drop
        with con:
            con.executemany("DELETE FROM items WHERE id = ?", [(i["id"],) for i in drop])
        removed = 0
        for i in drop:
            if i.get("sketch"):
                p = ROOT / "web" / i["sketch"]
                if p.exists():
                    p.unlink()
                    removed += 1
        n = store.export_json(con, out)
        print(f"   deleted {len(drop)} rows and {removed} sketch files; exported {n} items -> {out.name}")
        return keep, drop
    finally:
        con.close()


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pipeline.size_trim")
    ap.add_argument("--gender", choices=["men", "women", "both"], default="both")
    ap.add_argument("--dry-run", action="store_true", help="print the counts, delete nothing")
    ap.add_argument("--accessories", action="store_true",
                    help="trim footwear and accessories instead of garments")
    a = ap.parse_args(argv)
    for g in (("men", "women") if a.gender == "both" else (a.gender,)):
        run(g, a.dry_run, ACCESSORY_DEPTS if a.accessories else GARMENT_DEPTS)


if __name__ == "__main__":
    main()

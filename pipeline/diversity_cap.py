"""Diversity cap: at most N items per style x category x colour, spread over varieties.

Usage:  python -m pipeline.diversity_cap [--gender men|women|both] [--cap 10] [--per-variety 3]
                                         [--dry-run]

For every (primary style, category, colour) group, e.g. minimalist white shirts,
at most ``--cap`` items are kept. They are picked round-robin across varieties
(the same pattern, fit, fabric, sleeve length, neckline and sub-type), at most
``--per-variety`` of each, so the 10 white shirts are different kinds of white
shirt. In-stock and confidently styled items are preferred. Applies to clothes,
footwear and accessories.

Before deleting, the catalogue database and its JSON export are copied to
data/backup_before_diversity/ (restore by copying them back). The removed rows
are deleted from the catalogue database and the website export; their sketch
files are kept so a restore needs no redraw.
"""
import argparse
import shutil
from collections import defaultdict
from pathlib import Path

from . import store

ROOT = Path(__file__).resolve().parent.parent
BACKUP = ROOT / "data" / "backup_before_diversity"
VARIETY = ("pattern", "fit", "fabric", "sleeve_length", "neckline")
CONF = {"high": 0, "medium": 1, "low": 2}


def variety(it):
    return tuple(it.get(k) for k in VARIETY) + ((it.get("wear_types") or ["-"])[0],)


def pick(members, cap=10, per_variety=3):
    """Up to ``cap`` items, round-robin over varieties, at most ``per_variety`` each."""
    var = defaultdict(list)
    for it in sorted(members, key=lambda i: (not i.get("available"),
                                             CONF.get(i.get("style_confidence"), 3), i["id"])):
        var[variety(it)].append(it)
    order = sorted(var, key=lambda v: (-len(var[v]), str(v)))
    chosen = []
    for rnd in range(per_variety):
        for v in order:
            if len(chosen) >= cap:
                return chosen
            if len(var[v]) > rnd:
                chosen.append(var[v][rnd])
    return chosen


def choose(items, cap=10, per_variety=3):
    groups = defaultdict(list)
    for it in items:
        groups[(it.get("primary_style"), it.get("category"), it.get("color"))].append(it)
    keep_ids = {i["id"] for g in groups.values() for i in pick(g, cap, per_variety)}
    return ([i for i in items if i["id"] in keep_ids],
            [i for i in items if i["id"] not in keep_ids])


def run(gender, cap=10, per_variety=3, dry_run=False):
    db = ROOT / "data" / ("catalogue_women.db" if gender == "women" else "catalogue.db")
    out = ROOT / "web" / ("catalogue_women.json" if gender == "women" else "catalogue.json")
    con = store.connect(db)
    try:
        items = [store.decode(r) for r in con.execute("SELECT * FROM items")]
        keep, drop = choose(items, cap, per_variety)
        print(f"{gender}: {len(items)} items -> keep {len(keep)}, remove {len(drop)}")
        if dry_run:
            return keep, drop
        BACKUP.mkdir(parents=True, exist_ok=True)
        for f in (db, out):
            dst = BACKUP / f.name
            if not dst.exists():  # never overwrite the first backup
                shutil.copy2(f, dst)
        with con:
            con.executemany("DELETE FROM items WHERE id = ?", [(i["id"],) for i in drop])
        n = store.export_json(con, out)
        print(f"   backup in {BACKUP.relative_to(ROOT)}; exported {n} items -> {out.name}")
        return keep, drop
    finally:
        con.close()


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pipeline.diversity_cap")
    ap.add_argument("--gender", choices=["men", "women", "both"], default="both")
    ap.add_argument("--cap", type=int, default=10)
    ap.add_argument("--per-variety", type=int, default=3)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    for g in (("men", "women") if a.gender == "both" else (a.gender,)):
        run(g, a.cap, a.per_variety, a.dry_run)


if __name__ == "__main__":
    main()

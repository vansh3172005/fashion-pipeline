"""Assemble share/style-catalogue-api/ (and a zip of it) from the current catalogues.

    python share/make_package.py

Copies only what the API needs: the two catalogue JSON exports, the sketch
files they reference, the starter page and the browser recommender. Raw
scraped feeds, databases, backups and trial pictures are never included.
Rerun after the catalogue changes, then send the new zip.
"""
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "share" / "style-catalogue-api"
ZIP = ROOT / "share" / "style-catalogue-api.zip"


def main():
    (PKG / "data").mkdir(parents=True, exist_ok=True)
    for d in ("static", "web"):
        shutil.rmtree(PKG / d, ignore_errors=True)
    n_sk = 0
    for g, src in (("men", "catalogue.json"), ("women", "catalogue_women.json")):
        items = json.loads((ROOT / "web" / src).read_text(encoding="utf-8"))
        for it in items:
            it.pop("packshot", None)  # trial product pictures are not shared
            sk = it.get("sketch")
            if sk and (ROOT / "web" / sk).is_file():
                dst = PKG / "static" / sk
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / "web" / sk, dst)
                n_sk += 1
            elif sk:
                it.pop("sketch")
        (PKG / "data" / f"catalogue_{g}.json").write_text(
            json.dumps(items, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"{g}: {len(items):,} items")
    (PKG / "web").mkdir(exist_ok=True)
    for f in ("index.html", "recommend.js"):
        shutil.copy2(ROOT / "web" / f, PKG / "web" / f)
    for f in ("outfit_styling_rules.md",):
        shutil.copy2(ROOT / f, PKG / f)
    print(f"sketches: {n_sk:,}")
    if ZIP.exists():
        ZIP.unlink()
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in sorted(PKG.rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts:
                z.write(p, Path("style-catalogue-api") / p.relative_to(PKG))
    print(f"zip: {ZIP} ({ZIP.stat().st_size / 1e6:.0f} MB)")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Étape 2 : extrait et nettoie le texte de tout le corpus.

Lit data/corpus_metadata.json, écrit un JSON par document dans data/processed/
et un rapport récapitulatif data/processed/_rapport.json.

Usage :
    python scripts/parse_corpus.py                 # tout le corpus
    python scripts/parse_corpus.py --only pdf03 html01
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from webcognitive.config import METADATA_FILE, PROCESSED_DIR  # noqa: E402
from webcognitive.parsing.pipeline import parse_document  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Parsing et nettoyage du corpus WebCognitive.")
    parser.add_argument("--only", nargs="*", help="identifiants à traiter (ex. pdf03 html01)")
    args = parser.parse_args()

    documents = json.loads(METADATA_FILE.read_text(encoding="utf-8"))["documents"]
    if args.only:
        documents = [d for d in documents if d["id"] in set(args.only)]
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    report, failures = [], 0
    print(f"{'ID':<7} {'unités':>6} {'mots':>7} {'brut':>9} {'propre':>9}  remarques")
    for meta in documents:
        start = time.perf_counter()
        try:
            doc = parse_document(meta)
        except Exception as exc:  # noqa: BLE001 - un document en échec ne bloque pas les autres
            failures += 1
            print(f"{meta['id']:<7} ÉCHEC : {exc}")
            report.append({"id": meta["id"], "error": str(exc)})
            continue
        out = PROCESSED_DIR / f"{doc['id']}.json"
        out.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        s = doc["stats"]
        print(f"{doc['id']:<7} {s['units']:>6} {s['words']:>7} {s['raw_chars']:>9} {s['clean_chars']:>9}  "
              f"{' ; '.join(doc['warnings'])}")
        report.append({"id": doc["id"], "filename": doc["filename"], "format": doc["format"], "lang": doc["lang"],
                       **s, "seconds": round(time.perf_counter() - start, 2), "warnings": doc["warnings"]})

    if not args.only:
        (PROCESSED_DIR / "_rapport.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    total_words = sum(r.get("words", 0) for r in report)
    print(f"\n{len(report) - failures} documents traités, {failures} échec(s), {total_words} mots au total.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

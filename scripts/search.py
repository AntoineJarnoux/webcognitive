#!/usr/bin/env python3
"""
Recherche sémantique de démonstration sur l'index de l'étape 3 (sans base de données).

Usage :
    python scripts/search.py "Qui a inventé le DNS ?"
    python scripts/search.py "premier courrier électronique" -k 10
"""
from __future__ import annotations

import argparse
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from webcognitive import config  # noqa: E402
from webcognitive.embeddings import embed, load_index, search  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Recherche sémantique dans le corpus.")
    parser.add_argument("query")
    parser.add_argument("-k", type=int, default=5)
    args = parser.parse_args()

    chunks, vectors, manifest = load_index(config.EMBEDDINGS_DIR)
    # la question est vectorisée avec exactement les réglages qui ont servi à construire l'index
    query = embed([manifest.get("query_prefix", "") + args.query], manifest["model"],
                  max_seq_length=manifest.get("max_seq_length"))[0]
    for rank, (i, score) in enumerate(search(query, vectors, args.k), start=1):
        c = chunks[i]
        where = f"p. {c['page']}" if c["page"] else f"§ {c['section']}"
        print(f"\n{rank}. [{score:.3f}] {c['filename']} ({where})")
        print(textwrap.indent(textwrap.fill(c["text"], 100), "   "))
    return 0


if __name__ == "__main__":
    sys.exit(main())

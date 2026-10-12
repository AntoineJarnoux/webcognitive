#!/usr/bin/env python3
"""
Étape 4 : charge les segments et les vecteurs de l'étape 3 dans la base ChromaDB.

Entrée  : data/embeddings/chunks.jsonl, embeddings.npy, manifest.json (étape 3)
Sortie  : data/vectordb/ (base ChromaDB enregistrée sur disque ; voir config.VECTORDB_DIR
          si le chemin du projet contient des accents sous Windows)

Rien n'est revectorisé : quelques secondes suffisent. La collection est recréée à
chaque lancement, pour qu'elle corresponde exactement au dernier découpage.

Usage :
    python scripts/build_vectordb.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from webcognitive import config  # noqa: E402
from webcognitive.indexing import index_vectordb  # noqa: E402


def main() -> int:
    try:
        index_vectordb()
    except FileNotFoundError as exc:
        print(exc)
        return 1
    print(f"Base enregistrée dans {config.VECTORDB_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

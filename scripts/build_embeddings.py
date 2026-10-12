#!/usr/bin/env python3
"""
Étape 3 : découpe le corpus nettoyé en segments et calcule leurs vecteurs.

Entrée  : data/processed/<id>.json (étape 2)
Sorties : data/embeddings/chunks.jsonl   un segment par ligne (texte, document, page/section)
          data/embeddings/embeddings.npy  matrice (nb_segments x dimensions), même ordre
          data/embeddings/manifest.json   modèle et paramètres utilisés

Les réglages par défaut sont ceux retenus après l'évaluation (src/webcognitive/config.py).
Le code de la chaîne est dans src/webcognitive/indexing.py (partagé avec l'API, POST /ingest).

Usage :
    python scripts/build_embeddings.py
    python scripts/build_embeddings.py --size 800 --model sentence-transformers/all-MiniLM-L6-v2 --no-header
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from webcognitive import config  # noqa: E402
from webcognitive.indexing import build_embeddings  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Chunking et vectorisation du corpus.")
    parser.add_argument("--size", type=int, default=config.CHUNK_SIZE)
    parser.add_argument("--overlap", type=int, default=config.CHUNK_OVERLAP)
    parser.add_argument("--min-size", type=int, default=config.CHUNK_MIN_SIZE)
    parser.add_argument("--model", default=config.EMBEDDING_MODEL)
    parser.add_argument("--max-seq-length", type=int, default=config.EMBEDDING_MAX_SEQ_LENGTH)
    parser.add_argument("--no-header", dest="header", action="store_false", default=config.EMBEDDING_HEADER)
    args = parser.parse_args()

    build_embeddings(args.size, args.overlap, args.min_size, args.model, args.max_seq_length, args.header,
                     show_progress=True)
    print(f"Index écrit dans {config.EMBEDDINGS_DIR.relative_to(config.ROOT)}")
    print("Pensez à recharger la base vectorielle : python scripts/build_vectordb.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Étape 3 : découpe le corpus nettoyé en segments et calcule leurs vecteurs.

Entrée  : data/processed/<id>.json (étape 2)
Sorties : data/embeddings/chunks.jsonl   un segment par ligne (texte, document, page/section)
          data/embeddings/embeddings.npy  matrice (nb_segments x dimensions), même ordre
          data/embeddings/manifest.json   modèle et paramètres utilisés

Les réglages par défaut sont ceux retenus après l'évaluation (src/webcognitive/config.py).

Usage :
    python scripts/build_embeddings.py
    python scripts/build_embeddings.py --size 800 --model sentence-transformers/all-MiniLM-L6-v2 --no-header
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from webcognitive import config  # noqa: E402
from webcognitive.chunking import chunk_corpus, embedding_text  # noqa: E402
from webcognitive.embeddings import embed, save_index  # noqa: E402


def load_processed() -> list[dict]:
    files = sorted(p for p in config.PROCESSED_DIR.glob("*.json") if not p.name.startswith("_"))
    return [json.loads(p.read_text(encoding="utf-8")) for p in files]


def main() -> int:
    parser = argparse.ArgumentParser(description="Chunking et vectorisation du corpus.")
    parser.add_argument("--size", type=int, default=config.CHUNK_SIZE)
    parser.add_argument("--overlap", type=int, default=config.CHUNK_OVERLAP)
    parser.add_argument("--min-size", type=int, default=config.CHUNK_MIN_SIZE)
    parser.add_argument("--model", default=config.EMBEDDING_MODEL)
    parser.add_argument("--max-seq-length", type=int, default=config.EMBEDDING_MAX_SEQ_LENGTH)
    parser.add_argument("--no-header", dest="header", action="store_false", default=config.EMBEDDING_HEADER)
    args = parser.parse_args()

    docs = [d for d in load_processed() if d["units"]]
    chunks = chunk_corpus(docs, args.size, args.overlap, args.min_size)
    lengths = [len(c["text"]) for c in chunks]
    print(f"{len(docs)} documents -> {len(chunks)} segments "
          f"(taille moyenne {statistics.mean(lengths):.0f} car., min {min(lengths)}, max {max(lengths)})")

    start = time.perf_counter()
    texts = [config.PASSAGE_PREFIX + embedding_text(c, args.header) for c in chunks]
    vectors = embed(texts, args.model, max_seq_length=args.max_seq_length, show_progress=True)
    print(f"Vectorisation : {vectors.shape[0]} x {vectors.shape[1]} en {time.perf_counter() - start:.0f} s")

    save_index(config.EMBEDDINGS_DIR, chunks, vectors, {
        "model": args.model,
        "max_seq_length": args.max_seq_length,
        "header": args.header,
        "query_prefix": config.QUERY_PREFIX,
        "passage_prefix": config.PASSAGE_PREFIX,
        "chunk_size": args.size,
        "chunk_overlap": args.overlap,
        "chunk_min_size": args.min_size,
        "documents": len(docs),
        "normalized": True,
    })
    print(f"Index écrit dans {config.EMBEDDINGS_DIR.relative_to(config.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

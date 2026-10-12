"""Chaîne d'indexation : documents nettoyés -> segments + vecteurs (étape 3) -> base ChromaDB (étape 4).

Utilisée par les scripts (build_embeddings.py, build_vectordb.py) et par l'API (POST /ingest),
pour que les deux passent exactement par le même code.
"""
from __future__ import annotations

import json
import statistics
import time
from pathlib import Path

from . import config, vectordb
from .chunking import chunk_corpus, embedding_text
from .embeddings import embed, load_index, save_index


def load_processed(processed_dir: Path | None = None) -> list[dict]:
    """Documents de l'étape 2 qui contiennent du texte (le scan de Baran sans OCR est ignoré)."""
    files = sorted(p for p in Path(processed_dir or config.PROCESSED_DIR).glob("*.json") if not p.name.startswith("_"))
    docs = [json.loads(p.read_text(encoding="utf-8")) for p in files]
    return [d for d in docs if d["units"]]


def build_embeddings(size: int = config.CHUNK_SIZE, overlap: int = config.CHUNK_OVERLAP,
                     min_size: int = config.CHUNK_MIN_SIZE, model: str = config.EMBEDDING_MODEL,
                     max_seq_length: int | None = config.EMBEDDING_MAX_SEQ_LENGTH,
                     header: bool = config.EMBEDDING_HEADER, show_progress: bool = False, log=print) -> dict:
    """Étape 3 : découpe le corpus, vectorise les segments et écrit data/embeddings/."""
    docs = load_processed()
    chunks = chunk_corpus(docs, size, overlap, min_size)
    lengths = [len(c["text"]) for c in chunks]
    log(f"{len(docs)} documents -> {len(chunks)} segments "
        f"(taille moyenne {statistics.mean(lengths):.0f} car., min {min(lengths)}, max {max(lengths)})")

    start = time.perf_counter()
    texts = [config.PASSAGE_PREFIX + embedding_text(c, header) for c in chunks]
    vectors = embed(texts, model, max_seq_length=max_seq_length, show_progress=show_progress)
    seconds = time.perf_counter() - start
    log(f"Vectorisation : {vectors.shape[0]} x {vectors.shape[1]} en {seconds:.0f} s")

    save_index(config.EMBEDDINGS_DIR, chunks, vectors, {
        "model": model,
        "max_seq_length": max_seq_length,
        "header": header,
        "query_prefix": config.QUERY_PREFIX,
        "passage_prefix": config.PASSAGE_PREFIX,
        "chunk_size": size,
        "chunk_overlap": overlap,
        "chunk_min_size": min_size,
        "documents": len(docs),
        "normalized": True,
    })
    return {"documents": len(docs), "chunks": len(chunks), "seconds": round(seconds, 1)}


def index_vectordb(vectordb_dir: Path | None = None, log=print) -> dict:
    """Étape 4 : charge data/embeddings/ (segments + vecteurs) dans la base ChromaDB."""
    if not (config.EMBEDDINGS_DIR / "embeddings.npy").exists():
        raise FileNotFoundError("data/embeddings/embeddings.npy est absent : lancez d'abord "
                                "python scripts/build_embeddings.py (étape 3)")
    start = time.perf_counter()
    chunks, vectors, manifest = load_index(config.EMBEDDINGS_DIR)
    collection = vectordb.create_collection(vectordb.get_client(vectordb_dir), chunks, vectors, manifest)
    seconds = time.perf_counter() - start
    documents = len({c["doc_id"] for c in chunks})
    log(f"ChromaDB : {collection.count()} segments de {documents} documents indexés en {seconds:.1f} s "
        f"(modèle {manifest['model']})")
    return {"documents": documents, "chunks": collection.count(), "seconds": round(seconds, 1),
            "model": manifest["model"]}

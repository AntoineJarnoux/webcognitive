"""Étape 3 : vectorisation locale des segments avec sentence-transformers.

Le modèle est téléchargé une seule fois depuis Hugging Face (cache local),
puis tout tourne sur le poste, sans service externe.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

_MODELS: dict = {}


def load_model(name: str, max_seq_length: int | None = None):
    """Charge (une seule fois) un modèle sentence-transformers."""
    from sentence_transformers import SentenceTransformer  # import lourd : seulement si besoin

    key = (name, max_seq_length)
    if key not in _MODELS:
        model = SentenceTransformer(name, device="cpu")
        if max_seq_length:
            model.max_seq_length = max_seq_length
        _MODELS[key] = model
    return _MODELS[key]


def embed(texts: list[str], model_name: str, batch_size: int = 64, max_seq_length: int | None = None,
          show_progress: bool = False) -> np.ndarray:
    """Vecteurs normalisés (norme 1) : le produit scalaire est alors la similarité cosinus."""
    model = load_model(model_name, max_seq_length)
    vectors = model.encode(texts, batch_size=batch_size, normalize_embeddings=True,
                           convert_to_numpy=True, show_progress_bar=show_progress)
    return vectors.astype(np.float32)


def search(query_vector: np.ndarray, matrix: np.ndarray, k: int = 5) -> list[tuple[int, float]]:
    """Les k segments les plus proches (indice, score cosinus)."""
    scores = matrix @ query_vector
    top = np.argpartition(-scores, min(k, len(scores) - 1))[:k]
    top = top[np.argsort(-scores[top])]
    return [(int(i), float(scores[i])) for i in top]


# --------------------------------------------------------------------------- #
# Sauvegarde / chargement : chunks.jsonl (texte + métadonnées) et
# embeddings.npy (une ligne par chunk, dans le même ordre)
# --------------------------------------------------------------------------- #
def save_index(directory: Path, chunks: list[dict], vectors: np.ndarray, manifest: dict) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "chunks.jsonl").open("w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    np.save(directory / "embeddings.npy", vectors)
    manifest = {**manifest, "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "count": len(chunks), "dimensions": int(vectors.shape[1])}
    (directory / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def load_index(directory: Path) -> tuple[list[dict], np.ndarray, dict]:
    with (directory / "chunks.jsonl").open(encoding="utf-8") as f:
        chunks = [json.loads(line) for line in f]
    vectors = np.load(directory / "embeddings.npy")
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    return chunks, vectors, manifest

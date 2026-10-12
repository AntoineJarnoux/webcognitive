"""Étape 4 : base vectorielle locale (ChromaDB).

ChromaDB conserve, pour chaque segment de l'étape 3 :
- son identifiant (`pdf02_0014`),
- son vecteur (384 nombres),
- son texte,
- ses métadonnées (document, page ou section, langue, année…).

La base est enregistrée sur disque dans data/vectordb/ : on indexe une fois,
puis on interroge autant qu'on veut, même après un redémarrage.

Choix importants :
- On fournit nous-mêmes les vecteurs calculés à l'étape 3 (`embedding_function=None`) :
  ChromaDB ne recalcule rien. La question devra donc être vectorisée avec le même
  modèle que les segments. Le manifeste de l'étape 3 est copié dans les métadonnées de
  la collection pour le garantir.
- Distance cosinus (`hnsw:space = cosine`) : c'est la mesure utilisée à l'étape 3.
  ChromaDB renvoie une distance d = 1 - similarité ; on la reconvertit en score.
- Index HNSW : un graphe de voisinage qui évite de comparer la question à tous les
  segments. La recherche est approchée, mais très rapide.
"""
from __future__ import annotations

import json
from pathlib import Path

import chromadb
import numpy as np
from chromadb.config import Settings

from . import config

# Métadonnées gardées pour chaque segment (le texte est stocké à part, comme « document »)
METADATA_FIELDS = ("doc_id", "chunk_index", "page", "page_end", "section", "filename", "format",
                   "title", "author", "lang", "year", "char_start", "char_end")


def get_client(path: Path | str | None = None) -> chromadb.ClientAPI:
    """Client ChromaDB local, enregistré dans `path` (data/vectordb/ par défaut)."""
    path = Path(path or config.VECTORDB_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(path), settings=Settings(anonymized_telemetry=False))


def chunk_metadata(chunk: dict) -> dict:
    """ChromaDB n'accepte que des chaînes, des nombres et des booléens : les valeurs absentes sont omises."""
    return {k: chunk[k] for k in METADATA_FIELDS if chunk.get(k) is not None}


def create_collection(client: chromadb.ClientAPI, chunks: list[dict], vectors: np.ndarray, manifest: dict,
                      name: str = config.COLLECTION_NAME):
    """(Re)crée la collection à partir des segments et des vecteurs de l'étape 3."""
    if len(chunks) != len(vectors):
        raise ValueError(f"{len(chunks)} segments mais {len(vectors)} vecteurs : l'index de l'étape 3 est incohérent")
    try:
        client.delete_collection(name)  # on repart de zéro : pas de segment orphelin d'un ancien découpage
    except Exception:  # noqa: BLE001 - la collection n'existait pas encore
        pass
    collection = client.create_collection(
        name,
        embedding_function=None,
        metadata={"hnsw:space": "cosine", "manifest": json.dumps(manifest, ensure_ascii=False)},
    )
    batch = client.get_max_batch_size()  # ChromaDB limite le nombre d'ajouts par appel (environ 5 000)
    for start in range(0, len(chunks), batch):
        part = chunks[start:start + batch]
        collection.add(
            ids=[c["chunk_id"] for c in part],
            embeddings=vectors[start:start + batch],
            documents=[c["text"] for c in part],
            metadatas=[chunk_metadata(c) for c in part],
        )
    return collection


def get_collection(client: chromadb.ClientAPI, name: str = config.COLLECTION_NAME):
    """La collection existante, ou None si l'indexation n'a pas encore été faite."""
    try:
        return client.get_collection(name, embedding_function=None)
    except Exception:  # noqa: BLE001 - ChromaDB lève une erreur si la collection n'existe pas
        return None


def manifest_of(collection) -> dict:
    """Réglages de l'étape 3 (modèle, préfixes…) enregistrés avec la collection."""
    return json.loads((collection.metadata or {}).get("manifest", "{}"))


def build_where(doc_ids: list[str] | None = None, formats: list[str] | None = None, lang: str | None = None,
                year_min: int | None = None, year_max: int | None = None) -> dict | None:
    """Traduit les filtres de recherche en clause `where` de ChromaDB (filtrage sur les métadonnées)."""
    conditions = []
    if doc_ids:
        conditions.append({"doc_id": {"$in": list(doc_ids)}})
    if formats:
        conditions.append({"format": {"$in": list(formats)}})
    if lang:
        conditions.append({"lang": lang})
    if year_min is not None:
        conditions.append({"year": {"$gte": year_min}})
    if year_max is not None:
        conditions.append({"year": {"$lte": year_max}})
    if not conditions:
        return None
    return conditions[0] if len(conditions) == 1 else {"$and": conditions}


def query(collection, vector: np.ndarray, k: int, where: dict | None = None) -> list[dict]:
    """Les k segments les plus proches du vecteur, du plus proche au moins proche."""
    k = min(k, collection.count())
    if k == 0:
        return []
    result = collection.query(query_embeddings=[np.asarray(vector, dtype=np.float32)], n_results=k, where=where,
                              include=["documents", "metadatas", "distances"])
    return [
        {"chunk_id": cid, "score": 1.0 - dist, "text": text, **meta}
        for cid, text, meta, dist in zip(result["ids"][0], result["documents"][0],
                                         result["metadatas"][0], result["distances"][0])
    ]

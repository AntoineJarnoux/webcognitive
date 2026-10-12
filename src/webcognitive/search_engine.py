"""Étape 4 : moteur de recherche, utilisé par l'API.

Il réunit :
- la base vectorielle ChromaDB (recherche sémantique, filtres sur les métadonnées) ;
- l'index BM25 (recherche par mots-clés) ;
- le catalogue des documents (data/processed/, étape 2).

Trois modes de recherche :
- `semantic` : la question est vectorisée avec le modèle de l'étape 3, puis ChromaDB
  renvoie les segments les plus proches (similarité cosinus) ;
- `lexical`  : BM25 seul ;
- `hybrid`   : on prend les 50 meilleurs candidats de chaque méthode et on les fusionne
  par leurs **rangs** (Reciprocal Rank Fusion) : score = somme de 1 / (60 + rang).
  On fusionne les rangs et non les scores, parce qu'un cosinus (entre -1 et 1) et
  un score BM25 (sans borne) ne sont pas sur la même échelle.
"""
from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

import numpy as np

from . import config, vectordb
from .lexical import BM25Index

MODES = ("semantic", "lexical", "hybrid")


@dataclass
class Filters:
    """Restreint la recherche à une partie du corpus (grâce aux métadonnées de chaque segment)."""
    doc_ids: list[str] | None = None
    formats: list[str] | None = None
    lang: str | None = None
    year_min: int | None = None
    year_max: int | None = None

    def is_empty(self) -> bool:
        return not any(v not in (None, []) for v in asdict(self).values())

    def where(self) -> dict | None:
        """Clause ChromaDB (recherche sémantique)."""
        return vectordb.build_where(self.doc_ids, self.formats, self.lang, self.year_min, self.year_max)

    def accepts(self, meta: dict) -> bool:
        """Même règle, appliquée en Python (recherche BM25)."""
        year = meta.get("year")
        return ((not self.doc_ids or meta.get("doc_id") in self.doc_ids)
                and (not self.formats or meta.get("format") in self.formats)
                and (not self.lang or meta.get("lang") == self.lang)
                and (self.year_min is None or (year is not None and year >= self.year_min))
                and (self.year_max is None or (year is not None and year <= self.year_max)))


def location(meta: dict) -> str:
    """Localisation lisible d'un segment : « p. 3 », « p. 3-4 » ou « § Origines de l'Internet »."""
    page, page_end = meta.get("page"), meta.get("page_end")
    if page:
        return f"p. {page}" if not page_end or page_end == page else f"p. {page}-{page_end}"
    return f"§ {meta['section']}" if meta.get("section") else ""


def citation(meta: dict) -> str:
    """Référence courte à afficher sous une réponse : « clark_1988_….pdf, p. 2 »."""
    where = location(meta)
    return f"{meta.get('filename', meta.get('doc_id'))}, {where}" if where else meta.get("filename", "")


class SearchEngine:
    def __init__(self, vectordb_dir: Path | str | None = None, processed_dir: Path | str | None = None,
                 encoder: Callable[[str], np.ndarray] | None = None):
        """`encoder` : fonction texte -> vecteur. Par défaut, le modèle de l'étape 3 (remplaçable dans les tests)."""
        self.vectordb_dir = Path(vectordb_dir or config.VECTORDB_DIR)
        self.processed_dir = Path(processed_dir or config.PROCESSED_DIR)
        self._encoder = encoder
        self._lock = threading.Lock()
        self.reload()

    # ------------------------------------------------------------------ chargement
    def reload(self) -> None:
        """Relit la collection (après une réindexation) et vide les caches."""
        with self._lock:
            self.collection = vectordb.get_collection(vectordb.get_client(self.vectordb_dir))
            self.manifest = vectordb.manifest_of(self.collection) if self.collection else {}
            self._chunks: list[dict] | None = None
            self._positions: dict[str, int] = {}
            self._bm25: BM25Index | None = None
            self._documents: dict[str, dict] | None = None

    @property
    def ready(self) -> bool:
        return self.collection is not None and self.collection.count() > 0

    def _all_chunks(self) -> list[dict]:
        """Tous les segments (texte + métadonnées), triés par document puis par position."""
        with self._lock:
            if self._chunks is None:
                data = self.collection.get(include=["documents", "metadatas"])
                chunks = [{"chunk_id": cid, "text": text, **meta}
                          for cid, text, meta in zip(data["ids"], data["documents"], data["metadatas"])]
                chunks.sort(key=lambda c: (c["doc_id"], c["chunk_index"]))
                self._chunks = chunks
                self._positions = {c["chunk_id"]: i for i, c in enumerate(chunks)}
            return self._chunks

    def _lexical_index(self) -> BM25Index:
        chunks = self._all_chunks()
        with self._lock:
            if self._bm25 is None:
                self._bm25 = BM25Index([c["text"] for c in chunks])
            return self._bm25

    def encode(self, text: str) -> np.ndarray:
        """Vectorise la question exactement comme les segments l'ont été (même modèle, même préfixe)."""
        if self._encoder is not None:
            return self._encoder(text)
        from .embeddings import embed  # import lourd (PyTorch) seulement si nécessaire
        return embed([self.manifest.get("query_prefix", "") + text], self.manifest["model"],
                     max_seq_length=self.manifest.get("max_seq_length"))[0]

    def warmup(self) -> None:
        """Charge le modèle et l'index BM25 à l'avance, pour que la première requête soit rapide."""
        self.encode("warmup")
        self._lexical_index()

    # ------------------------------------------------------------------ recherche
    def search(self, query: str, k: int = config.SEARCH_K, mode: str = "semantic",
               filters: Filters | None = None) -> list[dict]:
        if mode not in MODES:
            raise ValueError(f"mode inconnu : {mode} (attendu : {', '.join(MODES)})")
        filters = filters or Filters()
        if mode == "semantic":
            hits = self._semantic(query, k, filters)
        elif mode == "lexical":
            hits = self._lexical(query, k, filters)
        else:
            hits = self._hybrid(query, k, filters)
        for rank, hit in enumerate(hits, start=1):
            hit["rank"] = rank
            hit["location"] = location(hit)
            hit["citation"] = citation(hit)
        return hits

    def _semantic(self, query: str, k: int, filters: Filters) -> list[dict]:
        hits = vectordb.query(self.collection, self.encode(query), k, filters.where())
        for h in hits:
            h["semantic_score"] = h["score"]
        return hits

    def _lexical(self, query: str, k: int, filters: Filters) -> list[dict]:
        chunks = self._all_chunks()
        allowed = None if filters.is_empty() else np.array([filters.accepts(c) for c in chunks])
        hits = []
        for i, score in self._lexical_index().search(query, k, allowed):
            hits.append({**chunks[i], "score": score, "lexical_score": score})
        return hits

    def _hybrid(self, query: str, k: int, filters: Filters) -> list[dict]:
        n = max(k, config.HYBRID_CANDIDATES)
        fused: dict[str, dict] = {}
        for name, hits in (("semantic", self._semantic(query, n, filters)), ("lexical", self._lexical(query, n, filters))):
            for rank, hit in enumerate(hits, start=1):
                entry = fused.setdefault(hit["chunk_id"], {**hit, "score": 0.0})
                entry["score"] += 1.0 / (config.RRF_K + rank)
                entry[f"{name}_rank"] = rank
                entry[f"{name}_score"] = hit["score"]
        return sorted(fused.values(), key=lambda h: -h["score"])[:k]

    # ------------------------------------------------------------------ consultation
    def chunk(self, chunk_id: str) -> dict | None:
        """Un segment, avec les identifiants des segments voisins (pour relire le contexte)."""
        chunks = self._all_chunks()
        i = self._positions.get(chunk_id)
        if i is None:
            return None
        c = dict(chunks[i])
        prev_c = chunks[i - 1] if i > 0 else None
        next_c = chunks[i + 1] if i + 1 < len(chunks) else None
        c["previous"] = prev_c["chunk_id"] if prev_c and prev_c["doc_id"] == c["doc_id"] else None
        c["next"] = next_c["chunk_id"] if next_c and next_c["doc_id"] == c["doc_id"] else None
        c["location"], c["citation"] = location(c), citation(c)
        return c

    def documents(self) -> dict[str, dict]:
        """Catalogue du corpus : métadonnées de l'étape 2 et nombre de segments indexés par document."""
        if self._documents is None:
            counts: dict[str, int] = {}
            for c in self._all_chunks() if self.ready else []:
                counts[c["doc_id"]] = counts.get(c["doc_id"], 0) + 1
            docs = {}
            for path in sorted(self.processed_dir.glob("*.json")):
                if path.name.startswith("_"):
                    continue
                d = json.loads(path.read_text(encoding="utf-8"))
                docs[d["id"]] = {
                    "id": d["id"], "filename": d["filename"], "format": d["format"], "title": d.get("title"),
                    "author": d.get("author"), "year": d.get("year"), "lang": d.get("lang"), "url": d.get("url"),
                    "type": d.get("type"), "words": d.get("stats", {}).get("words", 0),
                    "units": len(d.get("units", [])), "chunks": counts.get(d["id"], 0),
                    "warnings": d.get("warnings", []),
                }
            self._documents = docs
        return self._documents

    def document_content(self, doc_id: str) -> dict | None:
        """Texte nettoyé d'un document, découpé en pages ou sections (pour l'afficher en entier)."""
        path = self.processed_dir / f"{doc_id}.json"
        if doc_id not in self.documents() or not path.exists():
            return None
        d = json.loads(path.read_text(encoding="utf-8"))
        return {"units": d.get("units", []), "text": d.get("text", "")}

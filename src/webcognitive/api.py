"""Étape 4 : API REST (FastAPI) du moteur WebCognitive.

Lancement :
    python scripts/serve_api.py          (ou : uvicorn webcognitive.api:app --app-dir src)
Documentation interactive générée par FastAPI : http://127.0.0.1:8000/docs

Routes :
    GET  /health                 état du moteur (nombre de segments, modèle)
    GET  /documents              catalogue du corpus (filtres : format, lang)
    GET  /documents/{doc_id}     un document ; ?include_text=true pour son texte nettoyé
    GET  /chunks/{chunk_id}      un segment, avec ses voisins (traçabilité)
    GET  /search?q=...           recherche (mode semantic, lexical ou hybrid, filtres)
    POST /search                 même recherche, paramètres dans un corps JSON
    POST /ingest                 relance l'indexation en arrière-plan
    GET  /ingest                 état de la dernière indexation
"""
from __future__ import annotations

import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Callable, Literal

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from . import config
from .search_engine import Filters, SearchEngine

Mode = Literal["semantic", "lexical", "hybrid"]
Format = Literal["pdf", "txt", "html", "docx"]
Lang = Literal["fr", "en"]


# --------------------------------------------------------------------------- #
# Modèles de données : ils valident les entrées et documentent les sorties (/docs)
# --------------------------------------------------------------------------- #
class SearchRequest(BaseModel):
    q: str = Field(..., min_length=1, max_length=1000, description="question en langage naturel")
    k: int = Field(config.SEARCH_K, ge=1, le=config.SEARCH_K_MAX, description="nombre de segments renvoyés")
    mode: Mode = "semantic"
    doc_id: list[str] | None = Field(None, description="limiter à certains documents (ex. pdf02)")
    format: list[Format] | None = None
    lang: Lang | None = None
    year_min: int | None = None
    year_max: int | None = None

    def filters(self) -> Filters:
        return Filters(self.doc_id, self.format, self.lang, self.year_min, self.year_max)


class Hit(BaseModel):
    rank: int
    chunk_id: str
    score: float = Field(..., description="cosinus (semantic), BM25 (lexical) ou fusion des rangs (hybrid)")
    semantic_score: float | None = None
    lexical_score: float | None = None
    semantic_rank: int | None = None
    lexical_rank: int | None = None
    text: str
    doc_id: str
    filename: str
    format: str
    title: str | None = None
    author: str | None = None
    year: int | None = None
    lang: str | None = None
    page: int | None = None
    page_end: int | None = None
    section: str | None = None
    location: str = Field("", description="« p. 3 » ou « § Section »")
    citation: str = Field("", description="référence courte à afficher")


class SearchResponse(BaseModel):
    query: str
    mode: Mode
    k: int
    filters: dict
    took_ms: float
    count: int
    results: list[Hit]


class Chunk(Hit):
    rank: int = 0
    score: float = 0.0
    chunk_index: int
    char_start: int
    char_end: int
    previous: str | None = None
    next: str | None = None


class Document(BaseModel):
    id: str
    filename: str
    format: str
    title: str | None = None
    author: str | None = None
    year: int | None = None
    lang: str | None = None
    url: str | None = None
    type: str | None = None
    words: int
    units: int
    chunks: int = Field(..., description="segments indexés dans ChromaDB (0 : document absent de l'index)")
    warnings: list[str] = []


class DocumentDetail(Document):
    content: list[dict] | None = Field(None, description="pages ou sections, si include_text=true")


class IngestRequest(BaseModel):
    reembed: bool = Field(False, description="refaire aussi le découpage et la vectorisation (étape 3, ~10 min sur CPU)")


# --------------------------------------------------------------------------- #
# Indexation en arrière-plan
# --------------------------------------------------------------------------- #
class IngestJob:
    """État de la dernière indexation lancée par POST /ingest (une seule à la fois)."""

    def __init__(self):
        self.lock = threading.Lock()
        self.status = {"state": "idle"}

    def start(self, reembed: bool) -> bool:
        with self.lock:
            if self.status["state"] == "running":
                return False
            self.status = {"state": "running", "reembed": reembed, "log": [],
                           "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
            return True

    def run(self, engine: SearchEngine, reembed: bool) -> None:
        from .indexing import build_embeddings, index_vectordb  # imports lourds seulement si on indexe
        log = self.status["log"].append
        try:
            if reembed:
                build_embeddings(log=log)
            summary = index_vectordb(engine.vectordb_dir, log=log)
            engine.reload()
            self.status.update(state="done", result=summary)
        except Exception as exc:  # noqa: BLE001 - l'erreur est renvoyée par GET /ingest
            self.status.update(state="error", error=str(exc))
        self.status["finished_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")


# --------------------------------------------------------------------------- #
# Application
# --------------------------------------------------------------------------- #
def create_app(engine_factory: Callable[[], SearchEngine] = SearchEngine, warmup: bool = True) -> FastAPI:
    """`engine_factory` est remplaçable dans les tests (base temporaire, faux modèle)."""
    state: dict = {}

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        engine = engine_factory()
        if warmup and engine.ready:
            try:
                engine.warmup()  # charge le modèle au démarrage plutôt qu'à la première question
            except Exception as exc:  # noqa: BLE001 - le catalogue et la recherche BM25 restent utilisables
                print(f"Attention : modèle d'embedding non chargé ({exc}). La recherche sémantique échouera.")
        state["engine"], state["ingest"] = engine, IngestJob()
        yield

    app = FastAPI(
        title="WebCognitive Engine",
        description="Recherche sémantique dans un corpus sur l'histoire d'Internet (étape 4 : ChromaDB + FastAPI).",
        version="0.4.0",
        lifespan=lifespan,
    )

    def engine(require_index: bool = True) -> SearchEngine:
        e = state["engine"]
        if require_index and not e.ready:
            raise HTTPException(503, "Base vectorielle vide : lancez python scripts/build_vectordb.py ou POST /ingest")
        return e

    @app.get("/health", tags=["état"])
    def health():
        e = engine(require_index=False)
        return {
            "status": "ok" if e.ready else "index_vide",
            "chunks": e.collection.count() if e.collection else 0,
            "documents_indexed": len({c["doc_id"] for c in e._all_chunks()}) if e.ready else 0,
            "model": e.manifest.get("model"),
            "chunk_size": e.manifest.get("chunk_size"),
            "index_created_at": e.manifest.get("created_at"),
        }

    @app.get("/documents", response_model=list[Document], tags=["corpus"])
    def list_documents(format: Format | None = None, lang: Lang | None = None):
        docs = engine(require_index=False).documents().values()
        return [d for d in docs if (not format or d["format"] == format) and (not lang or d["lang"] == lang)]

    @app.get("/documents/{doc_id}", response_model=DocumentDetail, tags=["corpus"])
    def get_document(doc_id: str, include_text: bool = False):
        e = engine(require_index=False)
        doc = e.documents().get(doc_id)
        if doc is None:
            raise HTTPException(404, f"document inconnu : {doc_id}")
        content = e.document_content(doc_id)["units"] if include_text else None
        return {**doc, "content": content}

    @app.get("/chunks/{chunk_id}", response_model=Chunk, tags=["corpus"])
    def get_chunk(chunk_id: str):
        chunk = engine().chunk(chunk_id)
        if chunk is None:
            raise HTTPException(404, f"segment inconnu : {chunk_id}")
        return chunk

    def run_search(req: SearchRequest) -> SearchResponse:
        e = engine()
        start = time.perf_counter()
        hits = e.search(req.q, req.k, req.mode, req.filters())
        took = (time.perf_counter() - start) * 1000
        filters = {k: v for k, v in req.model_dump(include={"doc_id", "format", "lang", "year_min", "year_max"}).items()
                   if v is not None}
        return SearchResponse(query=req.q, mode=req.mode, k=req.k, filters=filters, took_ms=round(took, 1),
                              count=len(hits), results=hits)

    @app.get("/search", response_model=SearchResponse, tags=["recherche"])
    def search_get(q: str = Query(..., min_length=1, max_length=1000, description="question en langage naturel"),
                   k: int = Query(config.SEARCH_K, ge=1, le=config.SEARCH_K_MAX),
                   mode: Mode = "semantic",
                   doc_id: list[str] | None = Query(None),
                   format: list[Format] | None = Query(None),
                   lang: Lang | None = None,
                   year_min: int | None = None,
                   year_max: int | None = None):
        return run_search(SearchRequest(q=q, k=k, mode=mode, doc_id=doc_id, format=format, lang=lang,
                                        year_min=year_min, year_max=year_max))

    @app.post("/search", response_model=SearchResponse, tags=["recherche"])
    def search_post(req: SearchRequest):
        return run_search(req)

    @app.post("/ingest", status_code=202, tags=["indexation"])
    def ingest(background: BackgroundTasks, req: IngestRequest | None = None):
        reembed = req.reembed if req else False
        job: IngestJob = state["ingest"]
        if not job.start(reembed):
            raise HTTPException(409, "une indexation est déjà en cours (GET /ingest pour suivre)")
        background.add_task(job.run, engine(require_index=False), reembed)
        return {"message": "indexation lancée", "suivi": "GET /ingest", **job.status}

    @app.get("/ingest", tags=["indexation"])
    def ingest_status():
        return state["ingest"].status

    return app


app = create_app()

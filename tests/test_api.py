"""Tests de l'étape 4 : base vectorielle, moteur de recherche et API.

Ils tournent sans le vrai modèle d'embedding (ni téléchargement, ni GPU) :
- un petit corpus de 3 documents est créé dans un dossier temporaire ;
- un « faux modèle » transforme un texte en vecteur à partir de ses mots
  (sac de mots haché, normalisé). Il suffit pour vérifier la mécanique :
  stockage, filtres, classement, format des réponses.

Lancement :
    python -m pytest tests -q
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from webcognitive import vectordb  # noqa: E402
from webcognitive.api import create_app  # noqa: E402
from webcognitive.chunking import chunk_corpus  # noqa: E402
from webcognitive.lexical import tokenize  # noqa: E402
from webcognitive.search_engine import Filters, SearchEngine  # noqa: E402

DIM = 64


def fake_encoder(text: str) -> np.ndarray:
    """Vecteur déterministe : chaque mot active une dimension (choisie par hachage)."""
    v = np.zeros(DIM, dtype=np.float32)
    for token in tokenize(text):
        v[int(hashlib.md5(token.encode()).hexdigest(), 16) % DIM] += 1.0
    n = np.linalg.norm(v)
    return v / n if n else v


DOCS = [
    {"id": "txt01", "filename": "rfc0001.txt", "format": "txt", "title": "Host Software", "author": "Steve Crocker",
     "year": 1969, "lang": "en", "url": None, "type": "RFC", "stats": {"words": 40}, "warnings": [],
     "units": [{"page": 1, "section": None, "text": "Host Software. Steve Crocker wrote the first Request for Comments "
                "on 7 April 1969 about the IMP and host protocols."},
               {"page": 2, "section": None, "text": "The IMP network connects hosts at UCLA and SRI. "
                "Each host runs a network control program."}]},
    {"id": "html01", "filename": "isoc.html", "format": "html", "title": "Bref historique", "author": "ISOC",
     "year": 1997, "lang": "fr", "url": None, "type": "article", "stats": {"words": 50}, "warnings": [],
     "units": [{"page": None, "section": "Démontrer les idées", "text": "Le système DNS fut inventé par Paul "
                "Mockapetris. La transition de NCP vers TCP/IP eut lieu le 1er janvier 1983."},
               {"page": None, "section": "Origines", "text": "Le premier courrier électronique fut envoyé par Ray "
                "Tomlinson en 1972 sur le réseau ARPANET."}]},
    {"id": "docx01", "filename": "note_minitel.docx", "format": "docx", "title": "Minitel", "author": None,
     "year": 2020, "lang": "fr", "url": None, "type": "note", "stats": {"words": 30}, "warnings": [],
     "units": [{"page": None, "section": "Histoire", "text": "Le Minitel est un terminal français lancé par les PTT "
                "en 1982, relié au réseau Transpac."}]},
]


@pytest.fixture(scope="module")
def engine(tmp_path_factory) -> SearchEngine:
    root = tmp_path_factory.mktemp("wc")
    processed = root / "processed"
    processed.mkdir()
    for d in DOCS:
        doc = {**d, "text": "\n\n".join(u["text"] for u in d["units"])}
        (processed / f"{d['id']}.json").write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    chunks = chunk_corpus(DOCS, size=120, overlap=30, min_size=20)
    vectors = np.stack([fake_encoder(c["text"]) for c in chunks])
    manifest = {"model": "faux-modele", "chunk_size": 120, "query_prefix": ""}
    vectordb.create_collection(vectordb.get_client(root / "vectordb"), chunks, vectors, manifest)
    return SearchEngine(root / "vectordb", processed, encoder=fake_encoder)


@pytest.fixture(scope="module")
def client(engine) -> TestClient:
    with TestClient(create_app(lambda: engine, warmup=False)) as c:
        yield c


# --------------------------------------------------------------------------- base et moteur
def test_build_where():
    assert vectordb.build_where() is None
    assert vectordb.build_where(lang="fr") == {"lang": "fr"}
    assert vectordb.build_where(lang="fr", year_min=1980) == {"$and": [{"lang": "fr"}, {"year": {"$gte": 1980}}]}


def test_chunk_metadata_drops_none():
    meta = vectordb.chunk_metadata({"doc_id": "x", "page": None, "section": "S", "year": None})
    assert meta == {"doc_id": "x", "section": "S"}


def test_semantic_matches_exact_computation(engine):
    chunks = engine._all_chunks()
    query = "Who wrote the first Request for Comments?"
    hits = engine.search(query, k=3)
    scores = np.stack([fake_encoder(c["text"]) for c in chunks]) @ fake_encoder(query)
    exact = np.argsort(-scores)[:3]
    # mêmes scores (cosinus) que le calcul exact de l'étape 3 (les ex aequo peuvent être permutés)
    assert [h["score"] for h in hits] == pytest.approx([float(scores[i]) for i in exact], abs=1e-4)
    assert hits[0]["chunk_id"] == chunks[exact[0]]["chunk_id"]
    assert hits[0]["doc_id"] == "txt01"


def test_filters_semantic_and_lexical_agree(engine):
    f = Filters(lang="fr", year_max=2000)
    for mode in ("semantic", "lexical", "hybrid"):
        hits = engine.search("réseau DNS Mockapetris", k=10, mode=mode, filters=f)
        assert hits and all(h["lang"] == "fr" and h["year"] <= 2000 for h in hits), mode


def test_lexical_finds_proper_noun(engine):
    hits = engine.search("Mockapetris", k=1, mode="lexical")
    assert hits[0]["doc_id"] == "html01" and "Mockapetris" in hits[0]["text"]


def test_hybrid_records_both_ranks(engine):
    hits = engine.search("Steve Crocker RFC", k=3, mode="hybrid")
    assert hits[0]["doc_id"] == "txt01"
    assert hits[0]["semantic_rank"] and hits[0]["lexical_rank"]


def test_unknown_mode(engine):
    with pytest.raises(ValueError):
        engine.search("x", mode="magique")


# --------------------------------------------------------------------------- API
def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok" and body["chunks"] > 0 and body["model"] == "faux-modele"
    assert body["documents_indexed"] == 3


def test_documents(client):
    docs = client.get("/documents").json()
    assert {d["id"] for d in docs} == {"txt01", "html01", "docx01"}
    assert all(d["chunks"] > 0 for d in docs)
    assert [d["id"] for d in client.get("/documents", params={"lang": "en"}).json()] == ["txt01"]


def test_document_detail(client):
    assert client.get("/documents/html01").json()["content"] is None
    detail = client.get("/documents/html01", params={"include_text": True}).json()
    assert detail["content"][0]["section"] == "Démontrer les idées"
    assert client.get("/documents/inconnu").status_code == 404


def test_search_get(client):
    r = client.get("/search", params={"q": "Qui a inventé le DNS ?", "k": 2})
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == len(body["results"]) <= 2
    top = body["results"][0]
    assert top["rank"] == 1 and top["doc_id"] == "html01"
    assert top["location"] == "§ Démontrer les idées" and top["citation"].startswith("isoc.html")


def test_search_post_equals_get(client):
    params = {"q": "premier courrier électronique", "k": 3, "mode": "hybrid"}
    get = client.get("/search", params=params).json()["results"]
    post = client.post("/search", json=params).json()["results"]
    assert [h["chunk_id"] for h in get] == [h["chunk_id"] for h in post]


def test_search_filters_api(client):
    r = client.get("/search", params={"q": "réseau", "k": 10, "format": ["docx"]}).json()
    assert r["results"] and {h["format"] for h in r["results"]} == {"docx"}
    assert r["filters"] == {"format": ["docx"]}
    r = client.get("/search", params={"q": "réseau", "doc_id": "txt01"}).json()
    assert {h["doc_id"] for h in r["results"]} == {"txt01"}


def test_search_validation(client):
    assert client.get("/search", params={"q": ""}).status_code == 422
    assert client.get("/search", params={"q": "x", "k": 0}).status_code == 422
    assert client.get("/search", params={"q": "x", "mode": "magique"}).status_code == 422
    assert client.get("/search", params={"q": "x", "lang": "de"}).status_code == 422


def test_chunk_and_neighbours(client):
    first = client.get("/search", params={"q": "Steve Crocker 1969", "k": 1}).json()["results"][0]
    chunk = client.get(f"/chunks/{first['chunk_id']}").json()
    assert chunk["text"] == first["text"] and chunk["doc_id"] == "txt01"
    neighbour = chunk["next"] or chunk["previous"]
    assert neighbour and client.get(f"/chunks/{neighbour}").json()["doc_id"] == "txt01"
    assert client.get("/chunks/inconnu_0000").status_code == 404


def test_empty_index_returns_503(tmp_path):
    empty = SearchEngine(tmp_path / "vide", tmp_path, encoder=fake_encoder)
    with TestClient(create_app(lambda: empty, warmup=False)) as c:
        assert c.get("/health").json()["status"] == "index_vide"
        assert c.get("/search", params={"q": "DNS"}).status_code == 503


def test_ingest_runs_in_background(client, engine, monkeypatch):
    import webcognitive.indexing as indexing
    calls = []
    monkeypatch.setattr(indexing, "index_vectordb", lambda path, log: calls.append(path) or {"chunks": 7})
    r = client.post("/ingest", json={"reembed": False})
    assert r.status_code == 202 and r.json()["state"] == "running"
    status = client.get("/ingest").json()  # TestClient exécute la tâche de fond avant de rendre la main
    assert status["state"] == "done" and status["result"] == {"chunks": 7}
    assert calls == [engine.vectordb_dir]

"""Éléments communs aux tests : petit corpus de 3 documents et « faux modèle » d'embedding.

Le faux modèle transforme un texte en vecteur à partir de ses mots (sac de mots
haché, normalisé). Il suffit pour vérifier la mécanique (stockage, filtres,
classement, format des réponses) sans télécharger le vrai modèle.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from webcognitive import vectordb  # noqa: E402
from webcognitive.chunking import chunk_corpus  # noqa: E402
from webcognitive.lexical import tokenize  # noqa: E402
from webcognitive.search_engine import SearchEngine  # noqa: E402

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


@pytest.fixture(scope="session")
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

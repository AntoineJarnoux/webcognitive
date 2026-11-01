"""Tests de l'étape 5 : pipeline RAG et route /ask.

Le LLM est remplacé par un « faux LLM » qui renvoie une réponse écrite à l'avance :
on vérifie la mécanique (consigne, numérotation des extraits, citations, refus,
streaming, erreurs) sans avoir besoin d'Ollama.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from webcognitive.analytics import QuestionLog
from webcognitive.api import create_app
from webcognitive.rag import (REFUSAL, SYSTEM_PROMPT, LLMUnavailable, RagPipeline, build_messages,
                              cited_numbers, is_refusal)


class FakeLLM:
    """Remplace Ollama : renvoie `answer` mot par mot et garde les messages reçus."""
    model = "faux-llm"

    def __init__(self, answer: str = "", fail: bool = False):
        self.answer, self.fail, self.calls = answer, fail, []

    def status(self) -> dict:
        return {"model": self.model, "ollama": not self.fail, "model_available": not self.fail}

    def chat(self, messages):
        self.calls.append(messages)
        if self.fail:
            raise LLMUnavailable("Ollama ne répond pas")
        for word in self.answer.split(" "):
            yield word + " "


# Avec le faux modèle, les cosinus sont plus bas qu'avec le vrai : on désactive le garde-fou (min_score=0),
# sauf dans le test qui lui est consacré.
def make_client(engine, llm: FakeLLM, log: QuestionLog | None = None) -> TestClient:
    log = log or QuestionLog(Path(tempfile.mkdtemp()) / "questions.jsonl")  # jamais le vrai journal
    return TestClient(create_app(lambda: engine, warmup=False, question_log=log,
                                 rag_factory=lambda e: RagPipeline(e, llm, min_score=0)))


# --------------------------------------------------------------------------- prompt et citations
def test_prompt_contains_rules_numbered_sources_and_question(engine):
    hits = engine.search("Qui a inventé le DNS ?", k=2)
    system, user = build_messages("Qui a inventé le DNS ?", hits)
    assert system["role"] == "system" and "UNIQUEMENT" in system["content"] and REFUSAL in system["content"]
    assert user["content"].startswith("CONTEXTE")
    assert "[1] Source : " in user["content"] and "[2] Source : " in user["content"]
    assert hits[0]["text"] in user["content"] and "QUESTION : Qui a inventé le DNS ?" in user["content"]


def test_cited_numbers():
    assert cited_numbers("Mockapetris [1]. En 1983 [2][3], puis [1, 4] et [2 et 5].", 5) == [1, 2, 3, 4, 5]
    assert cited_numbers("Une source inventée [9].", 5) == []
    assert is_refusal(REFUSAL) and not is_refusal("Paul Mockapetris [1].")


def test_system_prompt_forbids_outside_knowledge():
    assert "connaissances personnelles" in SYSTEM_PROMPT and "N'invente jamais" in SYSTEM_PROMPT


# --------------------------------------------------------------------------- pipeline
def test_answer_with_citation(engine):
    llm = FakeLLM("Le DNS a été inventé par Paul Mockapetris [1].")
    result = RagPipeline(engine, llm, min_score=0).ask("Qui a inventé le DNS ?", k=3)
    assert not result["refused"] and result["cited"] == [1]
    assert result["sources"][0]["cited"] and not result["sources"][1]["cited"]
    assert result["sources"][0]["doc_id"] == "html01" and result["model"] == "faux-llm"
    assert len(llm.calls) == 1


def test_llm_refusal(engine):
    result = RagPipeline(engine, FakeLLM(REFUSAL), min_score=0).ask("Qui a inventé le Minitel au Japon ?")
    assert result["refused"] and result["cited"] == [] and not result["guard"]


def test_guard_refuses_off_topic_without_calling_llm(engine):
    llm = FakeLLM("ne doit pas être appelé")
    # seuil volontairement très haut : aucun extrait n'est assez proche, le LLM n'est pas appelé
    result = RagPipeline(engine, llm, min_score=0.99).ask("Quelle est la capitale de l'Australie ?")
    assert result["refused"] and result["guard"] and result["answer"] == REFUSAL
    assert llm.calls == []


# --------------------------------------------------------------------------- route /ask
def test_ask_json(engine):
    with make_client(engine, FakeLLM("Paul Mockapetris [1].")) as c:
        body = c.post("/ask", json={"question": "Qui a inventé le DNS ?", "k": 2}).json()
        assert body["question"] == "Qui a inventé le DNS ?" and body["cited"] == [1]
        assert body["sources"][0]["citation"].startswith("isoc.html")
        assert c.get("/health").json()["llm"]["model"] == "faux-llm"


def test_ask_stream(engine):
    with make_client(engine, FakeLLM("Ray Tomlinson en 1972 [1].")) as c:
        r = c.post("/ask", json={"question": "premier courrier électronique", "stream": True})
        assert r.headers["content-type"].startswith("application/x-ndjson")
        events = [json.loads(line) for line in r.text.splitlines() if line]
        assert events[0]["type"] == "sources" and events[0]["sources"]
        tokens = [e["text"] for e in events if e["type"] == "token"]
        assert "".join(tokens).strip() == "Ray Tomlinson en 1972 [1]."
        assert events[-1]["type"] == "done" and events[-1]["cited"] == [1]


def test_ask_llm_unavailable(engine):
    with make_client(engine, FakeLLM(fail=True)) as c:
        r = c.post("/ask", json={"question": "Qui a inventé le DNS ?"})
        assert r.status_code == 503 and "Ollama" in r.json()["detail"]
        events = [json.loads(l) for l in c.post("/ask", json={"question": "DNS Mockapetris", "stream": True}).text.splitlines()]
        assert events[-1]["type"] == "error"


def test_ask_validation(engine):
    with make_client(engine, FakeLLM("x")) as c:
        assert c.post("/ask", json={"question": ""}).status_code == 422
        assert c.post("/ask", json={"question": "x", "k": 50}).status_code == 422

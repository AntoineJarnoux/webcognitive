"""Tests de l'étape 7 : indicateurs du corpus, journal des questions et routes /stats."""
from __future__ import annotations

import json

from test_rag import FakeLLM, make_client
from webcognitive import analytics, config
from webcognitive.analytics import QuestionLog, corpus_stats


def test_corpus_stats(engine):
    s = corpus_stats(engine)
    assert s["totals"]["documents"] == 3 and s["totals"]["chunks"] == len(engine._all_chunks())
    assert {f["format"] for f in s["by_format"]} == {"txt", "html", "docx"}
    assert sum(f["documents"] for f in s["by_format"]) == 3
    assert {l["lang"]: l["documents"] for l in s["by_lang"]} == {"fr": 2, "en": 1}
    assert sum(b["count"] for b in s["chunk_histogram"]) == s["totals"]["chunks"]
    # thématiques comptées dans le bon document
    rows = {d["id"]: d["counts"] for d in s["themes_by_document"]}
    assert rows["html01"]["DNS"] == 1 and rows["docx01"]["Minitel / Transpac"] == 2 and rows["txt01"]["DNS"] == 0
    assert any(t["term"] == "minitel" for t in s["top_terms"]["fr"])


def test_question_log(tmp_path):
    log = QuestionLog(tmp_path / "q.jsonl")
    source = {"doc_id": "html01", "cited": True}
    log.add("Qui a inventé le DNS ?", "hybrid", 8,
            {"refused": False, "guard": False, "sources": [source], "total_ms": 2000})
    log.add("Capitale de l'Australie ?", "hybrid", 8,
            {"refused": True, "guard": True, "sources": [], "total_ms": 10})
    st = log.stats({"html01": {"title": "Bref historique", "filename": "isoc.html"}})
    assert st["questions"] == 2 and st["refused"] == 1 and st["guard"] == 1
    assert st["mean_seconds"] == 2.0 and st["most_cited"][0]["id"] == "html01"
    assert st["recent"][0]["question"] == "Capitale de l'Australie ?"


def test_stats_routes(engine, tmp_path, monkeypatch):
    log = QuestionLog(tmp_path / "q.jsonl")
    with make_client(engine, FakeLLM("Paul Mockapetris [1]."), log) as c:
        assert c.get("/stats").json()["totals"]["documents"] == 3
        assert c.get("/stats/questions").json()["questions"] == 0
        c.post("/ask", json={"question": "Qui a inventé le DNS ?"})
        c.post("/ask", json={"question": "premier courrier", "stream": True})
        q = c.get("/stats/questions").json()
        assert q["questions"] == 2 and q["refused"] == 0


def test_map_route(engine, tmp_path, monkeypatch):
    path = tmp_path / "carte.json"
    monkeypatch.setattr(config, "MAP_FILE", path)
    with make_client(engine, FakeLLM("x")) as c:
        assert c.get("/stats/map").status_code == 404
        path.write_text(json.dumps({"x": [1.0], "y": [2.0], "doc": ["html01"]}), encoding="utf-8")
        assert c.get("/stats/map").json()["doc"] == ["html01"]


def test_plotly_is_served_locally(engine):
    with make_client(engine, FakeLLM("x")) as c:
        r = c.get("/vendor/plotly.min.js")
        assert r.status_code == 200 and r.headers["content-type"].startswith("application/javascript")
        assert "plotly" in r.text[:2000].lower()


def test_themes_are_valid_regex():
    for pattern in analytics.THEMES.values():
        assert analytics.re.compile(pattern)

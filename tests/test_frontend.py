"""Tests de l'étape 6 : l'interface web est servie par l'API."""
from __future__ import annotations

from fastapi.testclient import TestClient

from webcognitive.api import create_app
from webcognitive.rag import RagPipeline
from test_rag import FakeLLM


def test_frontend_is_served(engine):
    app = create_app(lambda: engine, warmup=False, rag_factory=lambda e: RagPipeline(e, FakeLLM("x")))
    with TestClient(app) as c:
        assert c.get("/", follow_redirects=False).headers["location"] == "/app/"
        page = c.get("/app/")
        assert page.status_code == 200 and "WebCognitive" in page.text
        assert c.get("/app/app.js").status_code == 200 and c.get("/app/style.css").status_code == 200

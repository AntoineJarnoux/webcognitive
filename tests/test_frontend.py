"""Tests de l'étape 6 : l'interface web est servie par l'API."""
from __future__ import annotations

from test_rag import FakeLLM, make_client


def test_frontend_is_served(engine):
    with make_client(engine, FakeLLM("x")) as c:
        assert c.get("/", follow_redirects=False).headers["location"] == "/app/"
        page = c.get("/app/")
        assert page.status_code == 200 and "WebCognitive" in page.text
        assert c.get("/app/app.js").status_code == 200 and c.get("/app/style.css").status_code == 200

#!/usr/bin/env python3
"""
Étape 8 : recette (tests d'intégration) de l'application complète, à travers l'API REST.

Le script joue le rôle d'un utilisateur : il interroge l'application en marche, comme le
ferait l'interface web, et vérifie chaque maillon de la chaîne :

    1. état         GET  /health                    base remplie, Ollama et modèle prêts
    2. ingestion    POST /ingest, GET /ingest       réindexation automatique via l'API
    3. corpus       GET  /documents, /documents/id, /chunks/id
    4. recherche    GET  /search (3 modes)          la bonne source arrive en tête
    5. RAG          POST /ask (JSON et flux)        réponse sourcée, refus hors corpus
    6. dataviz      GET  /stats, /stats/map, /stats/questions, /vendor/plotly.min.js
    7. interface    GET  /, /app/, app.js, dashboard.js, style.css
    8. validation   les 29 questions de l'étape 1 via POST /ask (avec --validation)

Prérequis : l'application tourne (python scripts/serve_api.py) et Ollama est lancé.
Sortie : un rapport dans docs/etape8_recette.md

Usage :
    python scripts/recette.py                  # contrôles 1 à 7 (≈ 1 min)
    python scripts/recette.py --validation     # + les questions de validation (≈ 2 min de plus)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from webcognitive import config  # noqa: E402

REPORT = config.ROOT / "docs" / "etape8_recette.md"


class Recette:
    def __init__(self, url: str):
        self.url = url.rstrip("/")
        self.results: list[tuple[str, str, bool, str]] = []   # (étape, contrôle, réussi, détail)

    def get(self, path: str, **kw):
        return requests.get(self.url + path, timeout=300, **kw)

    def post(self, path: str, body: dict, **kw):
        return requests.post(self.url + path, json=body, timeout=300, **kw)

    def check(self, step: str, name: str, ok: bool, detail: str = "") -> bool:
        self.results.append((step, name, bool(ok), detail))
        print(f"  {'OK ' if ok else 'ÉCHEC'}  {name}" + (f" — {detail}" if detail else ""))
        return ok

    def run(self, step: str, func) -> None:
        print(f"\n{step}")
        try:
            func()
        except Exception as exc:  # noqa: BLE001 - une étape en erreur n'arrête pas la recette
            self.check(step, "étape exécutée sans erreur", False, f"{type(exc).__name__} : {exc}")

    # ------------------------------------------------------------------ étapes
    def health(self):
        h = self.get("/health").json()
        self.check("1. État", "base vectorielle remplie", h["status"] == "ok", f"{h['chunks']} segments")
        self.check("1. État", "Ollama répond", h["llm"]["ollama"], h["llm"]["model"])
        self.check("1. État", "modèle LLM téléchargé", h["llm"]["model_available"], h["llm"]["model"])
        self.chunks = h["chunks"]

    def ingestion(self):
        r = self.post("/ingest", {"reembed": False})
        self.check("2. Ingestion", "POST /ingest accepté", r.status_code == 202, r.json().get("state", ""))
        status = {}
        for _ in range(120):
            status = self.get("/ingest").json()
            if status.get("state") in ("done", "error"):
                break
            time.sleep(1)
        result = status.get("result", {})
        self.check("2. Ingestion", "indexation terminée", status.get("state") == "done",
                   f"{result.get('chunks')} segments en {result.get('seconds')} s" if result else status.get("error", ""))
        after = self.get("/health").json()["chunks"]
        self.check("2. Ingestion", "même nombre de segments après réindexation", after == self.chunks, f"{after}")

    def corpus(self):
        docs = self.get("/documents").json()
        self.check("3. Corpus", "catalogue complet", len(docs) == 41, f"{len(docs)} documents")
        formats = {d["format"] for d in docs}
        self.check("3. Corpus", "4 formats présents", formats == {"pdf", "txt", "html", "docx"}, ", ".join(sorted(formats)))
        detail = self.get("/documents/pdf02", params={"include_text": True}).json()
        self.check("3. Corpus", "texte d'un document consultable (pdf02, par page)",
                   detail.get("content") and detail["content"][0]["page"] == 1, f"{len(detail.get('content') or [])} pages")
        chunk = self.get("/chunks/html01_0001").json()
        self.check("3. Corpus", "segment consultable avec ses voisins", chunk.get("next") == "html01_0002",
                   chunk.get("citation", ""))
        self.check("3. Corpus", "document inconnu → 404", self.get("/documents/inconnu").status_code == 404)

    def search(self):
        for mode in ("semantic", "lexical", "hybrid"):
            r = self.get("/search", params={"q": "Qui a inventé le DNS ?", "k": 5, "mode": mode}).json()
            top = r["results"]
            ok = any("Mockapetris" in h["text"] for h in top)
            self.check("4. Recherche", f"mode {mode} : passage sur Mockapetris dans le top 5", ok,
                       f"{top[0]['citation']} ({r['took_ms']} ms)" if top else "aucun résultat")
        r = self.get("/search", params={"q": "réseau", "lang": "fr", "format": "docx", "k": 10}).json()
        self.check("4. Recherche", "filtres langue + format respectés",
                   r["results"] and all(h["lang"] == "fr" and h["format"] == "docx" for h in r["results"]))
        self.check("4. Recherche", "paramètre invalide → 422", self.get("/search", params={"q": "x", "k": 0}).status_code == 422)

    def rag(self):
        r = self.post("/ask", {"question": "Qui a inventé le DNS ?"}).json()
        cited = [s for s in r["sources"] if s["cited"]]
        self.check("5. RAG", "réponse correcte (Mockapetris)", "Mockapetris" in r["answer"], r["answer"][:90])
        self.check("5. RAG", "sources citées avec fichier et page/section",
                   cited and all(s["filename"] and s["location"] for s in cited),
                   "; ".join(list(dict.fromkeys(s["citation"] for s in cited))[:2]))
        r = self.post("/ask", {"question": "Quel est le chiffre d'affaires de Google en 2024 ?"}).json()
        self.check("5. RAG", "question hors corpus refusée", r["refused"], r["answer"][:70])
        lines = self.post("/ask", {"question": "Qui a écrit le premier courrier électronique ?", "stream": True},
                          stream=True).iter_lines()
        events = [json.loads(line) for line in lines if line]
        types = [e["type"] for e in events]
        self.check("5. RAG", "flux NDJSON : sources, morceaux de texte, fin",
                   types[0] == "sources" and "token" in types and types[-1] == "done", f"{types.count('token')} morceaux")

    def dataviz(self):
        s = self.get("/stats").json()
        self.check("6. Dataviz", "indicateurs du corpus", s["totals"]["documents"] == 41 and s["by_format"],
                   f"{s['totals']['words']} mots, {len(s['themes'])} thématiques")
        m = self.get("/stats/map")
        self.check("6. Dataviz", "carte sémantique disponible", m.status_code == 200,
                   f"{len(m.json()['x'])} points" if m.ok else m.json().get("detail", ""))
        q = self.get("/stats/questions").json()
        self.check("6. Dataviz", "questions posées comptabilisées", q["questions"] >= 3, f"{q['questions']} questions")
        p = self.get("/vendor/plotly.min.js")
        self.check("6. Dataviz", "Plotly servi en local", p.status_code == 200, f"{len(p.content) // 1024} Ko")

    def frontend(self):
        r = self.get("/", allow_redirects=False)
        self.check("7. Interface", "/ redirige vers l'interface", r.status_code in (302, 307) and r.headers["location"] == "/app/")
        page = self.get("/app/")
        self.check("7. Interface", "page d'accueil", page.ok and "Tableau de bord" in page.text)
        for f in ("app.js", "dashboard.js", "style.css"):
            self.check("7. Interface", f"ressource {f}", self.get(f"/app/{f}").ok)

    def validation(self):
        questions = json.loads(config.VALIDATION_FILE.read_text(encoding="utf-8"))["questions"]
        ok_real = real = ok_traps = traps = 0
        self.validation_rows = []
        for q in questions:
            r = self.post("/ask", {"question": q["question"]}).json()
            cited = [s for s in r["sources"] if s["cited"]]
            if q["type"] == "P":
                traps += 1
                ok = r["refused"]
                ok_traps += ok
            else:
                real += 1
                correct = not r["refused"] and re.search(q["rag_pattern"], r["answer"], re.I) is not None
                good_source = any(s["doc_id"] in q["expected_docs"]
                                  or re.search(q["answer_pattern"], s["text"], re.I | re.S)
                                  or re.search(q["rag_pattern"], s["text"], re.I | re.S) for s in cited)
                ok = correct and good_source
                ok_real += ok
            self.validation_rows.append((q["id"], ok, r["answer"], list(dict.fromkeys(s["citation"] for s in cited))))
            print(f"  {'OK ' if ok else '-- '}  {q['id']}  {r['answer'][:90]}")
        self.check("8. Validation", "succès ≥ 80 % (réponse correcte + bonne source)", ok_real / real >= 0.8,
                   f"{ok_real}/{real} = {ok_real / real:.0%}")
        self.check("8. Validation", "pièges hors corpus refusés (100 %)", ok_traps == traps, f"{ok_traps}/{traps}")

    # ------------------------------------------------------------------ rapport
    def write_report(self, seconds: float) -> None:
        passed = sum(r[2] for r in self.results)
        lines = [
            "# Étape 8 : recette de l'application",
            "",
            f"Rapport généré par `scripts/recette.py` le {datetime.now():%d/%m/%Y à %H:%M}, contre l'application "
            f"en marche ({self.url}), en {seconds:.0f} s. Chaque contrôle passe par l'API REST, comme l'interface web.",
            "",
            f"**{passed} contrôles réussis sur {len(self.results)}.**",
            "",
            "| Étape | Contrôle | Résultat | Détail |",
            "|---|---|---|---|",
        ]
        for step, name, ok, detail in self.results:
            lines.append(f"| {step} | {name} | {'✅' if ok else '❌'} | {detail.replace('|', '/')} |")
        if getattr(self, "validation_rows", None):
            lines += ["", "## Questions de validation (étape 1), posées à l'application", "",
                      "| Question | Succès | Réponse | Sources citées |", "|---|---|---|---|"]
            for qid, ok, answer, cites in self.validation_rows:
                answer = answer.replace("\n", " ").replace("|", "/")
                answer = answer[:200] + ("…" if len(answer) > 200 else "")
                lines.append(f"| {qid} | {'✅' if ok else '❌'} | {answer} | {'<br>'.join(cites[:3]) or '–'} |")
        REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Recette de l'application WebCognitive Engine.")
    parser.add_argument("--url", default=f"http://{config.API_HOST}:{config.API_PORT}")
    parser.add_argument("--validation", action="store_true", help="poser aussi les 29 questions de validation")
    args = parser.parse_args()

    recette = Recette(args.url)
    try:
        requests.get(recette.url + "/health", timeout=5)
    except requests.RequestException:
        print(f"L'application ne répond pas sur {recette.url} : lancez d'abord python scripts/serve_api.py")
        return 1

    start = time.perf_counter()
    recette.run("1. État", recette.health)
    recette.run("2. Ingestion", recette.ingestion)
    recette.run("3. Corpus", recette.corpus)
    recette.run("4. Recherche", recette.search)
    recette.run("5. RAG", recette.rag)
    recette.run("6. Dataviz", recette.dataviz)
    recette.run("7. Interface", recette.frontend)
    if args.validation:
        recette.run("8. Validation", recette.validation)
    recette.write_report(time.perf_counter() - start)

    passed = sum(r[2] for r in recette.results)
    print(f"\n{passed}/{len(recette.results)} contrôles réussis. Rapport : {REPORT.relative_to(config.ROOT)}")
    return 0 if passed == len(recette.results) else 1


if __name__ == "__main__":
    sys.exit(main())

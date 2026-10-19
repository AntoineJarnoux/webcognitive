#!/usr/bin/env python3
"""
Étape 5 : évalue l'assistant RAG de bout en bout sur les questions de validation.

Pour chaque question de data/validation_questions.json, on obtient la réponse du
LLM (exactement comme POST /ask), puis on vérifie :
- réponse correcte : la réponse contient l'information attendue (`rag_pattern`) ;
- bonne source     : un des extraits cités ([n]) justifie la réponse : il vient d'un document
                     attendu, ou son texte contient lui-même l'information attendue (le corpus
                     répète certains faits : la date de 1983 est dans trois documents) ;
- succès           : les deux à la fois, c'est le critère du projet (objectif : 80 %) ;
- pièges (P)       : le moteur doit répondre « je ne sais pas ».

Ollama doit être lancé, avec le modèle téléchargé (ollama pull mistral).

Chaque réglage mesuré (modèle, mode de recherche, k) est ajouté au tableau comparatif.

Sorties : data/evaluation_rag.json et docs/etape5_resultats.md

Usage :
    python scripts/evaluate_rag.py                       # mode de recherche par défaut
    python scripts/evaluate_rag.py --mode hybrid --k 8
    python scripts/evaluate_rag.py --only F15 P02        # quelques questions
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from webcognitive import config  # noqa: E402
from webcognitive.rag import LLMUnavailable, RagPipeline  # noqa: E402
from webcognitive.search_engine import MODES, SearchEngine  # noqa: E402

RESULTS_FILE = config.DATA_DIR / "evaluation_rag.json"
REPORT_FILE = config.ROOT / "docs" / "etape5_resultats.md"


def write_markdown(runs: list[dict]) -> None:
    lines = [
        "# Étape 5 : évaluation de l'assistant RAG",
        "",
        "Fichier généré par `scripts/evaluate_rag.py` (une ligne par réglage mesuré). Critère du projet : "
        "**succès** = réponse correcte **et** extrait cité qui la justifie, objectif 80 % ; pièges refusés, "
        "objectif 100 %. Explications : `docs/etape5_rag.md`.",
        "",
        "| LLM | Recherche | k | Réponse correcte | Bonne source | **Succès** | Pièges refusés | Refus à tort | s/question |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for run in runs:
        m = run["summary"]
        lines.append(f"| {m['model']} | {m['mode']} | {m['k']} | {pct(m['correct'])} | {pct(m['good_source'])} | "
                     f"**{pct(m['success'])}** | {pct(m['traps_refused'])} | {m['false_refusals']} | "
                     f"{m['seconds_per_question']:.1f} |")
    best = max(runs, key=lambda r: (r["summary"]["success"] or 0, r["summary"]["traps_refused"] or 0))
    m = best["summary"]
    lines += ["", f"## Détail du meilleur réglage : {m['model']}, recherche {m['mode']}, k = {m['k']}", "",
              "| Question | Succès | Réponse | Documents cités |", "|---|---|---|---|"]
    for r in best["questions"]:
        answer = r["answer"].replace("\n", " ").replace("|", "/")
        answer = answer[:220] + ("…" if len(answer) > 220 else "")
        lines.append(f"| {r['id']} | {'✅' if r['ok'] else '❌'} | {answer} | {', '.join(r['cited_docs']) or '–'} |")
    REPORT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def supports(source: dict, q: dict) -> bool:
    """L'extrait cité justifie-t-il la réponse attendue ?"""
    return (source["doc_id"] in q["expected_docs"]
            or re.search(q["answer_pattern"], source["text"], re.I | re.S) is not None
            or re.search(q["rag_pattern"], source["text"], re.I | re.S) is not None)


def pct(v) -> str:
    return "–" if v is None else f"{v:.0%}".replace("%", " %")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=MODES, default=config.RAG_MODE)
    parser.add_argument("--k", type=int, default=config.RAG_K)
    parser.add_argument("--only", nargs="*")
    args = parser.parse_args()

    engine = SearchEngine()
    if not engine.ready:
        print("Base vectorielle vide : lancez d'abord python scripts/build_vectordb.py")
        return 1
    rag = RagPipeline(engine)
    status = rag.llm.status()
    if not status["model_available"]:
        print(f"Ollama ou le modèle « {rag.llm.model} » est indisponible : lancez Ollama puis « ollama pull {rag.llm.model} ».")
        return 1

    questions = json.loads(config.VALIDATION_FILE.read_text(encoding="utf-8"))["questions"]
    if args.only:
        questions = [q for q in questions if q["id"] in args.only]

    rows = []
    for q in questions:
        start = time.perf_counter()
        try:
            r = rag.ask(q["question"], args.k, args.mode)
        except LLMUnavailable as exc:
            print(exc)
            return 1
        cited = [s for s in r["sources"] if s["cited"]]
        cited_docs = sorted({s["doc_id"] for s in cited})
        row = {"id": q["id"], "type": q["type"], "question": q["question"], "answer": r["answer"],
               "refused": r["refused"], "guard": r["guard"], "cited_docs": cited_docs,
               "seconds": round(time.perf_counter() - start, 1)}
        if q["type"] == "P":
            row["ok"] = r["refused"]
        else:
            row["correct"] = not r["refused"] and re.search(q["rag_pattern"], r["answer"], re.I) is not None
            row["good_source"] = any(supports(s, q) for s in cited)
            row["ok"] = row["correct"] and row["good_source"]
        rows.append(row)
        mark = "OK " if row["ok"] else "-- "
        print(f"{mark}{q['id']}  ({row['seconds']:>5.1f} s)  {r['answer'][:110].replace(chr(10), ' ')}")

    real = [r for r in rows if r["type"] != "P"]
    traps = [r for r in rows if r["type"] == "P"]
    summary = {
        "model": rag.llm.model, "mode": args.mode, "k": args.k,
        "correct": sum(r["correct"] for r in real) / len(real) if real else None,
        "good_source": sum(r["good_source"] for r in real) / len(real) if real else None,
        "success": sum(r["ok"] for r in real) / len(real) if real else None,
        "traps_refused": sum(r["ok"] for r in traps) / len(traps) if traps else None,
        "false_refusals": sum(r["refused"] for r in real),
        "seconds_per_question": sum(r["seconds"] for r in rows) / len(rows),
    }
    print(f"\nRéponse correcte {pct(summary['correct'])} · bonne source {pct(summary['good_source'])} · "
          f"succès {pct(summary['success'])} · pièges refusés {pct(summary['traps_refused'])}")

    if not args.only:
        previous = json.loads(RESULTS_FILE.read_text(encoding="utf-8")) if RESULTS_FILE.exists() else []
        if isinstance(previous, dict):  # ancien format : une seule évaluation
            previous = []
        same = ("model", "mode", "k")
        runs = [p for p in previous if any(p["summary"][key] != summary[key] for key in same)]
        runs.append({"summary": summary, "questions": rows})
        RESULTS_FILE.write_text(json.dumps(runs, ensure_ascii=False, indent=2), encoding="utf-8")
        write_markdown(runs)
        print(f"Résultats : {REPORT_FILE.relative_to(config.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

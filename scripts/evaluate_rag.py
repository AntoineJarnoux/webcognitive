#!/usr/bin/env python3
"""
Étape 5 : évalue l'assistant RAG de bout en bout sur les questions de validation.

Pour chaque question de data/validation_questions.json, on obtient la réponse du
LLM (exactement comme POST /ask), puis on vérifie :
- réponse correcte : la réponse contient l'information attendue (`rag_pattern`) ;
- bonne source     : un des extraits cités ([n]) vient d'un document attendu ;
- succès           : les deux à la fois, c'est le critère du projet (objectif : 80 %) ;
- pièges (P)       : le moteur doit répondre « je ne sais pas ».

Ollama doit être lancé, avec le modèle téléchargé (ollama pull mistral).

Sorties : data/evaluation_rag.json et docs/etape5_resultats.md

Usage :
    python scripts/evaluate_rag.py                       # mode de recherche par défaut
    python scripts/evaluate_rag.py --mode hybrid --k 5
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
        cited_docs = sorted({s["doc_id"] for s in r["sources"] if s["cited"]})
        row = {"id": q["id"], "type": q["type"], "question": q["question"], "answer": r["answer"],
               "refused": r["refused"], "guard": r["guard"], "cited_docs": cited_docs,
               "seconds": round(time.perf_counter() - start, 1)}
        if q["type"] == "P":
            row["ok"] = r["refused"]
        else:
            row["correct"] = not r["refused"] and re.search(q["rag_pattern"], r["answer"], re.I) is not None
            row["good_source"] = any(d in q["expected_docs"] for d in cited_docs)
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
    pct = lambda v: "–" if v is None else f"{v:.0%}".replace("%", " %")  # noqa: E731
    print(f"\nRéponse correcte {pct(summary['correct'])} · bonne source {pct(summary['good_source'])} · "
          f"succès {pct(summary['success'])} · pièges refusés {pct(summary['traps_refused'])}")

    if not args.only:
        RESULTS_FILE.write_text(json.dumps({"summary": summary, "questions": rows}, ensure_ascii=False, indent=2),
                                encoding="utf-8")
        lines = [
            "# Étape 5 : évaluation de l'assistant RAG",
            "",
            f"Fichier généré par `scripts/evaluate_rag.py`. LLM : `{summary['model']}` (Ollama) · recherche : "
            f"`{args.mode}` · {args.k} extraits par question. Explications : `docs/etape5_rag.md`.",
            "",
            "| Mesure | Résultat |",
            "|---|---|",
            f"| Réponse correcte | {pct(summary['correct'])} |",
            f"| Bonne source citée | {pct(summary['good_source'])} |",
            f"| **Succès (réponse correcte + bonne source)**, objectif 80 % | **{pct(summary['success'])}** |",
            f"| Pièges hors corpus refusés, objectif 100 % | {pct(summary['traps_refused'])} |",
            f"| Refus à tort (vraies questions) | {summary['false_refusals']} |",
            f"| Temps moyen par question | {summary['seconds_per_question']:.1f} s |",
            "",
            "| Question | Succès | Réponse | Sources citées |",
            "|---|---|---|---|",
        ]
        for r in rows:
            answer = r["answer"].replace("\n", " ").replace("|", "/")
            answer = answer[:220] + ("…" if len(answer) > 220 else "")
            ok = "✅" if r["ok"] else "❌"
            lines.append(f"| {r['id']} | {ok} | {answer} | {', '.join(r['cited_docs']) or '–'} |")
        REPORT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"Résultats : {REPORT_FILE.relative_to(config.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

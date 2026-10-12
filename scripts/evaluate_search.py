#!/usr/bin/env python3
"""
Étape 4 : évalue la recherche servie par l'API (ChromaDB) sur les questions de validation.

Pour chaque mode (semantic, lexical, hybrid), on pose les questions de
data/validation_questions.json au moteur, exactement comme le fait l'API, et on
calcule les mêmes mesures qu'à l'étape 3 (succès@1, succès@5, réponse@5, doc@5, MRR@10).

On vérifie aussi que ChromaDB renvoie les mêmes segments que le calcul exact de
l'étape 3 (produit scalaire sur tous les vecteurs) : son index HNSW est approché.

Sorties : data/evaluation_search.json et docs/etape4_resultats.md

Usage :
    python scripts/evaluate_search.py                    # les trois modes (~1 min)
    python scripts/evaluate_search.py --modes lexical    # sans le modèle d'embedding
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np  # noqa: E402

from webcognitive import config  # noqa: E402
from webcognitive.search_engine import MODES, SearchEngine  # noqa: E402

RESULTS_FILE = config.DATA_DIR / "evaluation_search.json"
REPORT_FILE = config.ROOT / "docs" / "etape4_resultats.md"
LABELS = {"semantic": "Sémantique (ChromaDB)", "lexical": "Mots-clés (BM25)", "hybrid": "Hybride (fusion des rangs)"}


def has_answer(hit: dict, q: dict) -> bool:
    return re.search(q["answer_pattern"], hit["text"], re.I | re.S) is not None


def evaluate(engine: SearchEngine, questions: list[dict], mode: str) -> dict:
    rows = []
    start = time.perf_counter()
    for q in questions:
        hits = engine.search(q["question"], 10, mode)
        row = {"id": q["id"], "top1": hits[0]["chunk_id"] if hits else None,
               "top10": [h["chunk_id"] for h in hits]}
        if q["type"] != "P":
            row["rank"] = next((h["rank"] for h in hits if h["doc_id"] in q["expected_docs"] and has_answer(h, q)), None)
            row["answer5"] = any(has_answer(h, q) for h in hits[:5])
            row["doc5"] = any(h["doc_id"] in q["expected_docs"] for h in hits[:5])
        rows.append(row)
    seconds = time.perf_counter() - start
    real = [r for r in rows if "rank" in r]
    n = len(real)
    return {
        "mode": mode,
        "success@1": sum(r["rank"] == 1 for r in real) / n,
        "success@5": sum(r["rank"] is not None and r["rank"] <= 5 for r in real) / n,
        "answer@5": sum(r["answer5"] for r in real) / n,
        "doc@5": sum(r["doc5"] for r in real) / n,
        "mrr@10": sum(1 / r["rank"] for r in real if r["rank"]) / n,
        "ms_per_query": seconds / len(questions) * 1000,
        "questions": rows,
    }


def exact_agreement(engine: SearchEngine, questions: list[dict], semantic_rows: list[dict]) -> float:
    """Part des segments du top 10 de ChromaDB qui sont aussi dans le top 10 du calcul exact (étape 3)."""
    vectors = np.load(config.EMBEDDINGS_DIR / "embeddings.npy")
    ids = [json.loads(line)["chunk_id"] for line in
           (config.EMBEDDINGS_DIR / "chunks.jsonl").read_text(encoding="utf-8").splitlines()]
    common = 0
    for q, row in zip(questions, semantic_rows):
        exact = {ids[i] for i in np.argsort(-(vectors @ engine.encode(q["question"])))[:10]}
        common += len(exact & set(row["top10"]))
    return common / (10 * len(questions))


def write_markdown(results: list[dict], agreement: float | None) -> None:
    lines = [
        "# Étape 4 : évaluation de la recherche servie par l'API",
        "",
        "Fichier généré par `scripts/evaluate_search.py`. Mêmes questions et mêmes mesures qu'à l'étape 3 "
        "(`data/validation_questions.json`, 26 questions F et C ; succès = la réponse **et** le bon document). "
        "Explications : `docs/etape4_api.md`.",
        "",
        "| Mode | Succès@1 | **Succès@5** | Réponse@5 | Doc@5 | MRR@10 | Temps par question |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in results:
        lines.append(f"| {LABELS[r['mode']]} | {r['success@1']:.0%} | **{r['success@5']:.0%}** | {r['answer@5']:.0%} | "
                     f"{r['doc@5']:.0%} | {r['mrr@10']:.2f} | {r['ms_per_query']:.0f} ms |".replace("%", " %"))
    if agreement is not None:
        lines += ["", f"Accord entre ChromaDB (index HNSW, approché) et le calcul exact de l'étape 3 : "
                      f"**{agreement:.0%}** des segments du top 10 sont identiques.".replace("%", " %")]
    lines += ["", "## Rang de la première bonne réponse, par question", "",
              "| Question | " + " | ".join(LABELS[r["mode"]] for r in results) + " |",
              "|---|" + "---|" * len(results)]
    for i, q in enumerate(results[0]["questions"]):
        cells = []
        for r in results:
            row = r["questions"][i]
            cells.append("piège" if "rank" not in row else (str(row["rank"]) if row["rank"] else "–"))
        lines.append(f"| {q['id']} | " + " | ".join(cells) + " |")
    REPORT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--modes", nargs="*", choices=MODES, default=list(MODES))
    args = parser.parse_args()

    engine = SearchEngine()
    if not engine.ready:
        print("Base vectorielle vide : lancez d'abord python scripts/build_vectordb.py")
        return 1
    questions = json.loads(config.VALIDATION_FILE.read_text(encoding="utf-8"))["questions"]

    results = []
    for mode in args.modes:
        r = evaluate(engine, questions, mode)
        results.append(r)
        print(f"{LABELS[mode]:<28} succès@5 {r['success@5']:.0%}  réponse@5 {r['answer@5']:.0%}  "
              f"MRR {r['mrr@10']:.2f}  ({r['ms_per_query']:.0f} ms/question)")

    agreement = None
    if "semantic" in args.modes:
        agreement = exact_agreement(engine, questions, results[args.modes.index("semantic")]["questions"])
        print(f"Accord ChromaDB / calcul exact (top 10) : {agreement:.0%}")

    RESULTS_FILE.write_text(json.dumps({"results": results, "hnsw_exact_agreement": agreement},
                                       ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(results, agreement)
    print(f"Résultats : {REPORT_FILE.relative_to(config.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

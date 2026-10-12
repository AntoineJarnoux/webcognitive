#!/usr/bin/env python3
"""
Étape 3 : test et optimisation du chunking et du modèle d'embedding.

Pour chaque configuration (modèle, taille de segment, en-tête contextuel,
longueur maximale lue par le modèle), on découpe le corpus, on vectorise, puis
on pose les questions de data/validation_questions.json.

Mesures (sur les 26 questions F et C) :
- succès@1 / succès@5 : un des 1 / 5 premiers segments contient la réponse
  (answer_pattern) ET vient d'un document attendu ;
- réponse@5 : un des 5 premiers segments contient la réponse, quel que soit le
  document (le corpus répète certains faits : la date de 1983 est aussi dans la
  note sur l'histoire d'Internet) ;
- doc@5 : un des 5 premiers segments vient d'un document attendu ;
- MRR@10 : moyenne de 1/rang du premier segment correct (0 s'il est absent du top 10) ;
- scores : similarité du 1er segment pour les vraies questions et pour les
  pièges (P), pour savoir si un seuil peut séparer les deux.

Les résultats s'accumulent dans data/embeddings/evaluation.json (une
configuration déjà mesurée est remplacée) et docs/etape3_resultats.md est
régénéré à partir de toutes les configurations mesurées.

Usage :
    python scripts/evaluate_chunking.py --sizes 300 500 800                    # grille de base (~1 h sur CPU)
    python scripts/evaluate_chunking.py --models multi-minilm --sizes 500 --header --max-seq-length 256
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from webcognitive import config  # noqa: E402
from webcognitive.chunking import chunk_corpus, embedding_text  # noqa: E402
from webcognitive.embeddings import embed, load_model, search  # noqa: E402

MODELS = {
    # modèle cité dans la fiche : rapide, 384 dimensions, entraîné sur de l'anglais
    "minilm": {"name": "sentence-transformers/all-MiniLM-L6-v2", "query": "", "passage": ""},
    # même famille, multilingue (50+ langues), 384 dimensions
    "multi-minilm": {"name": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", "query": "", "passage": ""},
    # multilingue, 384 dimensions, demande des préfixes « query: » / « passage: »
    "e5-small": {"name": "intfloat/multilingual-e5-small", "query": "query: ", "passage": "passage: "},
}
RESULTS_FILE = config.EMBEDDINGS_DIR / "evaluation.json"


def load_processed() -> list[dict]:
    files = sorted(p for p in config.PROCESSED_DIR.glob("*.json") if not p.name.startswith("_"))
    return [d for d in (json.loads(p.read_text(encoding="utf-8")) for p in files) if d["units"]]


def has_answer(chunk: dict, q: dict) -> bool:
    return re.search(q["answer_pattern"], chunk["text"], re.I | re.S) is not None


def evaluate(chunks, vectors, questions, qvectors) -> dict:
    rows, real, traps = [], [], []
    for q, qv in zip(questions, qvectors):
        hits = search(qv, vectors, 10)
        top = [chunks[i] for i, _ in hits]
        if q["type"] == "P":
            traps.append(hits[0][1])
            rows.append({"id": q["id"], "top1_score": round(hits[0][1], 3), "top1": top[0]["chunk_id"]})
            continue
        rank = next((r for r, c in enumerate(top, start=1)
                     if c["doc_id"] in q["expected_docs"] and has_answer(c, q)), None)
        real.append(hits[0][1])
        rows.append({
            "id": q["id"], "rank": rank, "top1_score": round(hits[0][1], 3), "top1": top[0]["chunk_id"],
            "answer5": any(has_answer(c, q) for c in top[:5]),
            "doc5": any(c["doc_id"] in q["expected_docs"] for c in top[:5]),
        })
    answerable = [r for r in rows if "rank" in r]
    n = len(answerable)
    return {
        "success@1": sum(r["rank"] == 1 for r in answerable) / n,
        "success@5": sum(r["rank"] is not None and r["rank"] <= 5 for r in answerable) / n,
        "answer@5": sum(r["answer5"] for r in answerable) / n,
        "doc@5": sum(r["doc5"] for r in answerable) / n,
        "mrr@10": sum(1 / r["rank"] for r in answerable if r["rank"]) / n,
        "score_real_mean": statistics.mean(real),
        "score_real_min": min(real),
        "score_trap_max": max(traps),
        "questions": rows,
    }


def truncated_ratio(model, texts: list[str]) -> float:
    """Part des segments plus longs que la fenêtre du modèle (la fin est alors ignorée)."""
    lengths = [len(ids) for ids in model.tokenizer(texts, add_special_tokens=True)["input_ids"]]
    return sum(l > model.max_seq_length for l in lengths) / len(lengths)


def config_label(r: dict) -> str:
    label = r["model_key"]
    if r.get("header"):
        label += " + en-tête"
    if r.get("max_seq_length"):
        label += f" + {r['max_seq_length']} tokens"
    return label


def write_markdown(results: list[dict], path: Path) -> None:
    lines = [
        "# Étape 3 : résultats de l'évaluation du chunking",
        "",
        "Fichier généré par `scripts/evaluate_chunking.py` à partir de `data/embeddings/evaluation.json`. "
        "Questions : `data/validation_questions.json` (26 questions F et C, dont F09 impossible tant que le PDF "
        "de Baran n'est pas passé à l'OCR, et 3 pièges P). Explications : `docs/etape3_chunking_embeddings.md`.",
        "",
        "| Configuration | Taille | Chevauch. | Segments | Tronqués | Succès@1 | **Succès@5** | Réponse@5 | Doc@5 | MRR@10 | Score moyen (vraies) | Score max (pièges) | Temps |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        m = r["metrics"]
        answer5 = f"{m['answer@5'] * 100:.0f} %" if "answer@5" in m else "–"
        lines.append(
            f"| {config_label(r)} | {r['size']} | {r['overlap']} | {r['chunks']} | {r['truncated'] * 100:.0f} % | "
            f"{m['success@1'] * 100:.0f} % | **{m['success@5'] * 100:.0f} %** | {answer5} | {m['doc@5'] * 100:.0f} % | "
            f"{m['mrr@10']:.2f} | {m['score_real_mean']:.2f} | {m['score_trap_max']:.2f} | {r['seconds']:.0f} s |"
        )
    best = max(results, key=lambda r: (r["metrics"]["success@5"], r["metrics"]["mrr@10"]))
    lines += ["", f"## Détail par question : {config_label(best)}, taille {best['size']}", "",
              "| Question | Rang de la 1re bonne réponse (bon document) | Score du 1er segment | 1er segment |",
              "|---|---|---|---|"]
    for q in best["metrics"]["questions"]:
        rank = q.get("rank", "piège")
        lines.append(f"| {q['id']} | {rank if rank is not None else 'absent du top 10'} | {q['top1_score']} | `{q['top1']}` |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizes", type=int, nargs="*", default=[300, 500, 800])
    parser.add_argument("--models", nargs="*", default=list(MODELS))
    parser.add_argument("--overlap-ratio", type=float, default=0.2)
    parser.add_argument("--header", action="store_true", help="ajoute « titre (auteur, année) » avant chaque segment")
    parser.add_argument("--max-seq-length", type=int, default=None, help="tokens lus par le modèle (sinon sa valeur par défaut)")
    args = parser.parse_args()

    docs = load_processed()
    questions = json.loads(config.VALIDATION_FILE.read_text(encoding="utf-8"))["questions"]
    previous = json.loads(RESULTS_FILE.read_text(encoding="utf-8")) if RESULTS_FILE.exists() else []

    for key in args.models:
        spec = MODELS[key]
        model = load_model(spec["name"], args.max_seq_length)
        qvectors = embed([spec["query"] + q["question"] for q in questions], spec["name"],
                         max_seq_length=args.max_seq_length)
        for size in args.sizes:
            overlap = int(size * args.overlap_ratio)
            start = time.perf_counter()
            chunks = chunk_corpus(docs, size, overlap, min(100, size // 2))
            texts = [spec["passage"] + embedding_text(c, args.header) for c in chunks]
            vectors = embed(texts, spec["name"], max_seq_length=args.max_seq_length)
            metrics = evaluate(chunks, vectors, questions, qvectors)
            result = {"model_key": key, "model": spec["name"], "size": size, "overlap": overlap,
                      "header": args.header, "max_seq_length": args.max_seq_length,
                      "chunks": len(chunks), "truncated": truncated_ratio(model, texts),
                      "seconds": time.perf_counter() - start, "metrics": metrics}
            same = ("model_key", "size", "overlap", "header", "max_seq_length")
            previous = [r for r in previous if any(r.get(k) != result[k] for k in same)] + [result]
            print(f"{config_label(result):<35} taille {size:>5} : succès@5 {metrics['success@5']:.0%}, "
                  f"réponse@5 {metrics['answer@5']:.0%}, MRR {metrics['mrr@10']:.2f}, "
                  f"pièges max {metrics['score_trap_max']:.2f} ({result['seconds']:.0f} s)", flush=True)

    config.EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_FILE.write_text(json.dumps(previous, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(previous, config.ROOT / "docs" / "etape3_resultats.md")
    print("Résultats : docs/etape3_resultats.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())

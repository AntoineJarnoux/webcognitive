"""Étape 7 : indicateurs statistiques sur le corpus, la base vectorielle et les questions posées.

Trois sources de données :
- le catalogue des documents (étape 2 : format, langue, année, nombre de mots, texte) ;
- les segments indexés dans ChromaDB (étapes 3-4 : nombre et taille) ;
- le journal des questions posées à l'assistant (étape 5), écrit dans data/logs/questions.jsonl.

Tout est calculé en Python (quelques dixièmes de seconde) puis mis en cache ; l'interface
web reçoit des données déjà agrégées (GET /stats) et ne fait que les dessiner.
"""
from __future__ import annotations

import json
import re
import statistics
import threading
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from . import config
from .lexical import STOPWORDS, TOKEN, normalize
from .search_engine import SearchEngine

# Thématiques suivies : nom affiché -> expression régulière (sur le texte en minuscules, sans accents).
# Elles reprennent les axes du corpus définis à l'étape 1 (README, § 1.1).
THEMES = {
    "ARPANET": r"\barpanet\b",
    "Commutation de paquets": r"packet[- ]switch\w*|commutation (?:de|par) paquets",
    "TCP/IP": r"\btcp\b",
    "Datagramme": r"\bdatagram\w*",
    "Cyclades / Pouzin": r"\bcyclades\b|\bpouzin\b",
    "Courrier électronique": r"\be-?mail\b|electronic mail|courrier electronique",
    "DNS": r"\bdns\b|domain names?\b",
    "Web / HTTP": r"world wide web|\bweb\b|\bhttp\b|hypertext",
    "Minitel / Transpac": r"\bminitel\b|\btranspac\b",
    "RFC": r"\brfcs?\b",
}

# Mots très fréquents mais peu parlants, en plus des mots vides de la recherche BM25
EXTRA_STOPWORDS = set("""
plus etait comme entre ainsi aussi alors fut deux tres ans etaient autres autre fait faire peut tout tous toute
sont ete cela leurs etre avoir dont lors apres avant sous chez sans selon meme donc bien encore
may one will can all other use some used must would any each should there more also new only such than into
then so we you our its out may two first well see per however these those were been being both same
""".split())


def _short_title(doc: dict, size: int = 34) -> str:
    title = doc.get("title") or doc["filename"]
    return title if len(title) <= size else title[: size - 1].rstrip() + "…"


def _decade(year: int | None) -> str:
    return f"{year // 10 * 10}s" if year else "date inconnue"


def corpus_stats(engine: SearchEngine) -> dict:
    """Indicateurs sur les documents et les segments indexés."""
    docs = list(engine.documents().values())
    chunks = engine._all_chunks() if engine.ready else []
    lengths = [len(c["text"]) for c in chunks]
    words = sum(d["words"] for d in docs)

    # Répartitions par format, par langue et par décennie de publication
    by_format = defaultdict(lambda: {"documents": 0, "words": 0, "chunks": 0})
    for d in docs:
        f = by_format[d["format"]]
        f["documents"] += 1
        f["words"] += d["words"]
        f["chunks"] += d["chunks"]
    by_lang = Counter(d["lang"] for d in docs)
    by_decade = defaultdict(Counter)
    for d in docs:
        by_decade[_decade(d.get("year"))][d["lang"]] += 1
    decades = sorted(by_decade, key=lambda k: (k == "date inconnue", k))

    # Taille des segments : histogramme par tranches de 25 caractères
    width = 25
    bins = Counter(min(l // width, 20) for l in lengths)
    histogram = [{"from": i * width, "to": (i + 1) * width, "count": bins.get(i, 0)} for i in range(0, 21)]

    # Thématiques : occurrences par document, ramenées à 10 000 mots pour comparer des textes de tailles différentes
    patterns = {name: re.compile(rx) for name, rx in THEMES.items()}
    raw = {d["id"]: engine.document_content(d["id"])["text"].lower() for d in docs}
    texts = {doc_id: normalize(text) for doc_id, text in raw.items()}
    per_doc = []
    decade_totals = defaultdict(lambda: Counter())
    decade_words = Counter()
    for d in sorted(docs, key=lambda d: (d.get("year") or 9999, d["id"])):
        counts = {name: len(p.findall(texts[d["id"]])) for name, p in patterns.items()}
        per_10k = {name: round(n / d["words"] * 10_000, 1) if d["words"] else 0 for name, n in counts.items()}
        per_doc.append({"id": d["id"], "label": f"{d['id']} · {_short_title(d)}", "title": d.get("title"),
                        "year": d.get("year"), "format": d["format"], "lang": d["lang"],
                        "counts": counts, "per_10k": per_10k})
        if d.get("year"):
            decade_totals[_decade(d["year"])].update(counts)
            decade_words[_decade(d["year"])] += d["words"]
    themes_by_decade = [
        {"decade": dec, "documents": sum(1 for d in docs if _decade(d.get("year")) == dec),
         "per_10k": {name: round(decade_totals[dec][name] / decade_words[dec] * 10_000, 1) for name in THEMES}}
        for dec in sorted(decade_totals)
    ]

    # Termes les plus fréquents, par langue (sans mots vides, nombres ni mots de 1-2 lettres)
    # (« réseau » et « reseau » sont comptés ensemble ; on affiche la graphie la plus fréquente)
    top_terms = {}
    for lang in ("fr", "en"):
        counter, spellings = Counter(), defaultdict(Counter)
        for d in docs:
            if d["lang"] != lang:
                continue
            for word in TOKEN.findall(raw[d["id"]]):
                key = normalize(word)
                if len(key) > 2 and not key.isdigit() and key not in STOPWORDS and key not in EXTRA_STOPWORDS:
                    counter[key] += 1
                    spellings[key][word] += 1
        top_terms[lang] = [{"term": spellings[k].most_common(1)[0][0], "count": n} for k, n in counter.most_common(15)]

    return {
        "totals": {
            "documents": len(docs),
            "documents_indexed": sum(1 for d in docs if d["chunks"]),
            "chunks": len(chunks),
            "words": words,
            "chunk_mean": round(statistics.mean(lengths)) if lengths else 0,
            "chunk_median": round(statistics.median(lengths)) if lengths else 0,
            "years": [min((d["year"] for d in docs if d.get("year")), default=None),
                      max((d["year"] for d in docs if d.get("year")), default=None)],
            "undated": sum(1 for d in docs if not d.get("year")),
        },
        "by_format": [{"format": k, **v} for k, v in sorted(by_format.items(), key=lambda kv: -kv[1]["documents"])],
        "by_lang": [{"lang": k, "documents": v} for k, v in by_lang.most_common()],
        "by_decade": [{"decade": dec, "fr": by_decade[dec]["fr"], "en": by_decade[dec]["en"]} for dec in decades],
        "chunk_histogram": histogram,
        "chunks_per_document": sorted(({"id": d["id"], "label": _short_title(d), "chunks": d["chunks"],
                                         "format": d["format"]} for d in docs), key=lambda x: -x["chunks"]),
        "themes": list(THEMES),
        "themes_by_document": per_doc,
        "themes_by_decade": themes_by_decade,
        "top_terms": top_terms,
    }


# --------------------------------------------------------------------------- #
# Journal des questions posées à l'assistant
# --------------------------------------------------------------------------- #
class QuestionLog:
    """Une ligne JSON par question (fichier local, ignoré par Git)."""

    def __init__(self, path: Path | None = None):
        self.path = Path(path or config.QUESTION_LOG)
        self.lock = threading.Lock()

    def add(self, question: str, mode: str, k: int, result: dict) -> None:
        entry = {
            "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "question": question, "mode": mode, "k": k,
            "refused": result["refused"], "guard": result["guard"],
            "cited_docs": sorted({s["doc_id"] for s in result["sources"] if s["cited"]}),
            "total_ms": result["total_ms"],
        }
        with self.lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def entries(self) -> list[dict]:
        if not self.path.exists():
            return []
        with self.lock:
            lines = self.path.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines if line.strip()]

    def stats(self, documents: dict[str, dict]) -> dict:
        entries = self.entries()
        cited = Counter(doc for e in entries for doc in e["cited_docs"])
        answered = [e for e in entries if not e["refused"]]
        return {
            "questions": len(entries),
            "refused": sum(e["refused"] for e in entries),
            "guard": sum(e["guard"] for e in entries),
            "mean_seconds": round(statistics.mean(e["total_ms"] for e in answered) / 1000, 1) if answered else None,
            "most_cited": [{"id": d, "label": _short_title(documents[d]) if d in documents else d, "count": n}
                           for d, n in cited.most_common(10)],
            "recent": [{"at": e["at"], "question": e["question"], "refused": e["refused"]} for e in entries[-8:][::-1]],
        }


def load_map(path: Path | None = None) -> dict | None:
    """Carte 2D des segments (projection t-SNE), produite par scripts/carte_vecteurs.py."""
    path = Path(path or config.MAP_FILE)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

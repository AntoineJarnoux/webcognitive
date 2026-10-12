"""Étape 3 : découpage des documents en segments (chunks) avec chevauchement.

Principe :
- on vise des segments d'environ `size` caractères ;
- on coupe de préférence à une fin de phrase, sinon entre deux mots,
  jamais au milieu d'un mot ;
- le segment suivant reprend les `overlap` derniers caractères du précédent
  (en repartant d'un début de phrase quand c'est possible), pour qu'une idée
  coupée à la frontière reste lisible en entier dans au moins un segment ;
- chaque segment garde sa provenance : document, page (PDF/TXT) ou section
  (HTML/DOCX), et positions de début et de fin dans le texte du document.
"""
from __future__ import annotations

import bisect
import re

# Début de phrase : après . ! ? … (éventuellement suivis d'un guillemet ou d'une parenthèse)
# et une espace, ou après un changement de paragraphe. Les initiales (« J.C.R. Licklider »)
# et abréviations courantes (« Fig. 1 ») ne terminent pas une phrase.
SENTENCE_START = re.compile(
    r"(?<=[.!?…][\"»)\]'])\s+"
    r"|(?<=[.!?…])(?<!\b[A-Z]\.)(?<!\bFig\.)(?<!\bvol\.)(?<!\bno\.)(?<!\bp\.)(?<!\bet al\.)\s+"
    r"|\n\n+"
)
WORD_START = re.compile(r"\s+")


def _boundaries(pattern: re.Pattern, text: str) -> list[int]:
    return [m.end() for m in pattern.finditer(text)]


def _last_before(points: list[int], low: int, high: int) -> int | None:
    """Plus grande frontière dans l'intervalle ]low, high]."""
    i = bisect.bisect_right(points, high) - 1
    return points[i] if i >= 0 and points[i] > low else None


def _first_after(points: list[int], low: int, high: int) -> int | None:
    """Plus petite frontière dans l'intervalle [low, high[."""
    i = bisect.bisect_left(points, low)
    return points[i] if i < len(points) and points[i] < high else None


def split_text(text: str, size: int = 500, overlap: int = 100, min_size: int = 100) -> list[tuple[int, int]]:
    """Découpe `text` et renvoie les intervalles (début, fin) de chaque segment."""
    if overlap >= size:
        raise ValueError("le chevauchement doit être plus petit que la taille des segments")
    n = len(text)
    sentences = _boundaries(SENTENCE_START, text)
    words = _boundaries(WORD_START, text)
    spans: list[tuple[int, int]] = []
    start = 0
    while start < n:
        limit = start + size
        if limit >= n:
            end = n
        else:
            # fin de phrase dans la seconde moitié du segment, sinon fin de mot, sinon coupure nette
            end = (_last_before(sentences, start + size // 2, limit)
                   or _last_before(words, start, limit)
                   or limit)
        spans.append((start, end))
        if end >= n:
            break
        # début du segment suivant : un début de phrase dans la zone de chevauchement, sinon le début
        # de phrase juste avant (chevauchement un peu plus long, au plus le double), sinon un début de mot
        zone = end - overlap
        nxt = (_first_after(sentences, zone, end)
               or _last_before(sentences, max(start, zone - overlap), zone)
               or _first_after(words, zone, end)
               or end)
        start = nxt if nxt > start else end

    # un dernier segment trop court est rattaché au précédent
    if len(spans) >= 2 and spans[-1][1] - spans[-1][0] < min_size:
        last = spans.pop()
        spans[-1] = (spans[-1][0], last[1])
    return spans


def chunk_document(doc: dict, size: int = 500, overlap: int = 100, min_size: int = 100) -> list[dict]:
    """Segments d'un document produit par l'étape 2 (data/processed/<id>.json)."""
    # Texte complet + position de départ de chaque unité (page ou section)
    parts, offsets, pos = [], [], 0
    for unit in doc["units"]:
        offsets.append(pos)
        parts.append(unit["text"])
        pos += len(unit["text"]) + 2  # séparateur « \n\n »
    text = "\n\n".join(parts)

    def unit_at(offset: int) -> dict:
        return doc["units"][max(0, bisect.bisect_right(offsets, offset) - 1)]

    chunks = []
    for i, (start, end) in enumerate(split_text(text, size, overlap, min_size)):
        raw = text[start:end]
        lead = len(raw) - len(raw.lstrip())
        content = raw.strip()
        if not content:
            continue
        first, last = unit_at(start + lead), unit_at(end - 1)
        chunks.append({
            "chunk_id": f"{doc['id']}_{i:04d}",
            "doc_id": doc["id"],
            "chunk_index": i,
            "text": content,
            "char_start": start + lead,
            "char_end": start + lead + len(content),
            "page": first["page"],
            "page_end": last["page"],
            "section": first["section"],
            "filename": doc["filename"],
            "format": doc["format"],
            "title": doc["title"],
            "author": doc["author"],
            "lang": doc["lang"],
            "year": doc["year"],
        })
    return chunks


def embedding_text(chunk: dict, with_header: bool = True) -> str:
    """Texte réellement vectorisé : le segment, précédé d'un en-tête contextuel.

    Un segment isolé ne dit pas de quel document il vient (« The ARPANET, for
    example, returns a packet… » ne mentionne ni Saltzer ni l'article). On ajoute
    donc « titre (auteur, année) » devant : la question « selon Saltzer et al. »
    retrouve alors le bon passage. Le texte affiché et cité reste le segment seul.
    """
    if not with_header:
        return chunk["text"]
    parts = [chunk["title"] or chunk["filename"]]
    meta = ", ".join(str(v) for v in (chunk.get("author"), chunk.get("year")) if v)
    header = f"{parts[0]} ({meta})" if meta else parts[0]
    return f"{header}\n{chunk['text']}"


def chunk_corpus(docs: list[dict], size: int = 500, overlap: int = 100, min_size: int = 100) -> list[dict]:
    return [c for doc in docs for c in chunk_document(doc, size, overlap, min_size)]

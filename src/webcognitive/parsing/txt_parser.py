"""Extraction des fichiers texte (ici les RFC).

Les RFC sont en texte à largeur fixe : 72 caractères par ligne, pages séparées
par un saut de page (\\f), en-tête « RFC 791  Internet Protocol  September 1981 »
et pied « Postel  [Page 3] » sur chaque page, sommaire à points de suite et
schémas en ASCII.
"""
from __future__ import annotations

import re
from pathlib import Path

from . import cleaning

RFC_HEADER = re.compile(r"^RFC ?\d+\b.*\b(19|20)\d{2}\s*$")
RFC_FOOTER = re.compile(r"\[Page (\d+|[ivxlc]+)\]\s*$")   # « [Page 3] », « [Page iii] »
TOC_LINE = re.compile(r"\.{4,}\s*\d+\s*$")             # « 3.1 Format ........ 11 »


def _is_ascii_art(line: str) -> bool:
    """Ligne de schéma (« +-+-+-+ », « |  Version  | ») : peu de lettres, beaucoup de symboles."""
    stripped = line.strip()
    if not stripped:
        return False
    letters = sum(c.isalnum() for c in stripped)
    symbols = sum(c in "+-|=_/\\<>*:." for c in stripped)
    return letters / len(stripped) < 0.4 and symbols >= 3


def parse_txt(path: Path) -> dict:
    raw = path.read_bytes().decode("utf-8", errors="replace")
    raw = raw.replace("\r\n", "\n")
    pages = raw.split("\f")
    page_lines = [p.split("\n") for p in pages]
    repeated = cleaning.find_repeated_lines(page_lines)

    units, removed = [], 0
    for number, lines in enumerate(page_lines, start=1):
        kept = []
        for line in lines:
            if RFC_HEADER.match(line.strip()) or RFC_FOOTER.search(line) or TOC_LINE.search(line) or _is_ascii_art(line):
                removed += 1
                continue
            kept.append(line)
        kept, n = cleaning.remove_noise_lines(kept, repeated)
        removed += n
        # Les lignes vides séparent déjà les paragraphes : il suffit de recoller les autres.
        text = cleaning.clean_text(cleaning.join_lines(cleaning.dehyphenate("\n".join(kept))))
        if len(text) >= 30:
            units.append({"page": number, "section": None, "text": text})

    return {
        "units": units,
        "pages_total": len(pages),
        "raw_chars": len(raw),
        "removed_lines": removed,
        "warnings": [f"{removed} ligne(s) d'en-tête, pied de page, sommaire ou schéma supprimée(s)"],
        "parser": "texte brut (RFC)",
    }

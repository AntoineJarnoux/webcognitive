"""Extraction des documents Word avec python-docx.

Les styles Word donnent directement la structure : « Title » et « Heading n »
ouvrent une section, le reste est du corps de texte. La ligne « Source : … »
ajoutée en tête des notes est une métadonnée, pas du contenu.
"""
from __future__ import annotations

from pathlib import Path

from docx import Document

from . import cleaning


def parse_docx(path: Path) -> dict:
    doc = Document(path)
    title = doc.core_properties.title or None
    sections: list[dict] = []
    current = {"section": title, "parts": []}
    raw_chars = 0
    for para in doc.paragraphs:
        text = para.text.strip()
        raw_chars += len(para.text)
        if not text:
            continue
        style = para.style.name if para.style is not None else ""
        if style == "Title":
            title = title or text
            current["section"] = text
        elif style.startswith("Heading"):
            sections.append(current)
            current = {"section": text, "parts": []}
        elif text.startswith("Source :") and not sections and not current["parts"]:
            continue  # ligne de provenance (déjà dans les métadonnées)
        else:
            current["parts"].append(text)
    sections.append(current)

    # Les tableaux éventuels sont lus ligne par ligne, cellules séparées par « | ».
    for table in doc.tables:
        rows = [" | ".join(c.text.strip() for c in row.cells) for row in table.rows]
        sections.append({"section": "Tableau", "parts": rows})

    units = []
    for sec in sections:
        text = cleaning.clean_text("\n\n".join(sec["parts"]))
        if len(text) >= 30:
            units.append({"page": None, "section": sec["section"], "text": text})

    return {
        "units": units,
        "title_detected": title,
        "pages_total": None,
        "raw_chars": raw_chars,
        "removed_lines": None,
        "warnings": [],
        "parser": "python-docx",
    }

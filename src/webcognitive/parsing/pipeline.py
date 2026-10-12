"""Pipeline de l'étape 2 : un document brut -> un JSON normalisé.

Format de sortie (data/processed/<id>.json) :
{
  "id", "filename", "format", "title", "author", "year", "lang", "url", "type",
  "source_path", "sha256", "retrieved_at", "parsed_at", "parser",
  "units": [{"page": 3, "section": null, "text": "..."}],   # page (PDF/TXT) ou section (HTML/DOCX)
  "text": "texte complet, paragraphes séparés par une ligne vide",
  "stats": {...}, "warnings": [...]
}
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from ..config import ROOT
from . import cleaning
from .docx_parser import parse_docx
from .html_parser import parse_html
from .pdf_parser import parse_pdf
from .txt_parser import parse_txt

PARSERS = {"pdf": parse_pdf, "txt": parse_txt, "html": parse_html, "docx": parse_docx}


def parse_document(meta: dict) -> dict:
    """`meta` est une entrée de data/corpus_metadata.json."""
    path = ROOT / meta["path"]
    result = PARSERS[meta["format"]](path)
    units = result["units"]
    text = "\n\n".join(u["text"] for u in units)

    return {
        "id": meta["id"],
        "filename": meta["filename"],
        "format": meta["format"],
        "title": meta.get("title") or result.get("title_detected"),
        "author": meta.get("author"),
        "year": meta.get("year"),
        "lang": cleaning.detect_language(text) if text else meta.get("lang"),
        "url": meta.get("url"),
        "type": meta.get("type"),
        "source_path": meta["path"],
        "sha256": meta.get("sha256"),
        "retrieved_at": meta.get("retrieved_at"),
        "parsed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "parser": result["parser"],
        "units": units,
        "text": text,
        "stats": {
            "raw_chars": result["raw_chars"],
            "clean_chars": len(text),
            "words": len(re.findall(r"\w+", text)),
            "units": len(units),
            "pages_total": result.get("pages_total"),
            "removed_lines": result.get("removed_lines"),
        },
        "warnings": result["warnings"],
    }

"""Extraction des PDF avec pdfplumber.

Difficultés traitées (voir docs/journal_audit.md) :
- mise en page sur deux colonnes : on repère la gouttière et on lit la
  colonne gauche puis la droite, au lieu de mélanger les lignes ;
- mots collés (pdf03) : on réduit la tolérance horizontale de pdfplumber ;
- en-têtes, pieds de page et numéros de page répétés ;
- pages scannées sans texte : OCR facultatif avec Tesseract.
"""
from __future__ import annotations

from pathlib import Path

import pdfplumber

from . import cleaning

DEFAULT_X_TOLERANCE = 3     # valeur par défaut de pdfplumber
TIGHT_X_TOLERANCE = 1.5     # pour les PDF dont les espaces sont très étroits
MIN_CHARS_PER_PAGE = 30     # en dessous, la page est considérée comme vide (scan)


def _find_gutter(page, words) -> tuple[float, float, float] | None:
    """Cherche une gouttière verticale entre deux colonnes.

    Renvoie (x de la gouttière, y de fin du bandeau haut, y de début du bandeau bas)
    ou None si la page est sur une seule colonne. Le titre et les pieds de page
    peuvent traverser la gouttière : on les isole en bandeaux pleine largeur.
    """
    if len(words) < 80:
        return None
    width, height = page.width, page.height
    best_x, best_cross = None, None
    for x in range(int(width * 0.35), int(width * 0.65), 2):
        crossing = sum(1 for w in words if w["x0"] < x < w["x1"])
        if best_cross is None or crossing < best_cross:
            best_x, best_cross = x, crossing
    crossing = [w for w in words if w["x0"] < best_x < w["x1"]]
    top_band = max((w["bottom"] for w in crossing if w["top"] < height * 0.35), default=0)
    bottom_band = min((w["top"] for w in crossing if w["top"] > height * 0.85), default=height)
    middle = [w for w in crossing if top_band < w["top"] < bottom_band]
    body = [w for w in words if top_band < w["top"] < bottom_band]
    left = sum(1 for w in body if w["x1"] <= best_x)
    right = sum(1 for w in body if w["x0"] >= best_x)
    if len(middle) <= max(2, 0.01 * len(body)) and left > 40 and right > 40:
        return best_x, top_band, bottom_band
    return None


def _page_text(page, x_tolerance: float) -> tuple[str, bool]:
    """Texte d'une page, colonne par colonne si besoin. Renvoie (texte, deux_colonnes)."""
    kwargs = {"x_tolerance": x_tolerance, "y_tolerance": 3}
    words = page.extract_words(**kwargs)
    gutter = _find_gutter(page, words)
    if gutter is None:
        return page.extract_text(**kwargs) or "", False
    x, top, bottom = gutter
    # Certaines numérisations ont un cadre de page décalé (haut négatif) : on reste dans page.bbox.
    x0, y0, x1, y1 = page.bbox
    top, bottom = max(top, y0), min(bottom, y1)
    regions = []
    if top > y0:
        regions.append((x0, y0, x1, top))
    regions += [(x0, top, x, bottom), (x, top, x1, bottom)]
    if bottom < y1:
        regions.append((x0, bottom, x1, y1))
    parts = [page.crop(box).extract_text(**kwargs) or "" for box in regions]
    return "\n".join(p for p in parts if p.strip()), True


def _ocr_page(page) -> str | None:
    """OCR d'une page scannée. Nécessite pytesseract et le logiciel Tesseract."""
    try:
        import pytesseract
    except ImportError:
        return None
    windows_default = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
    if windows_default.exists():  # l'installateur Windows n'ajoute pas Tesseract au PATH
        pytesseract.pytesseract.tesseract_cmd = str(windows_default)
    try:
        image = page.to_image(resolution=300).original
        return pytesseract.image_to_string(image, lang="eng")
    except Exception:  # noqa: BLE001 - Tesseract absent ou page illisible
        return None


def _extract_pages(pdf, x_tolerance: float) -> tuple[list[str], int]:
    pages, two_cols = [], 0
    for page in pdf.pages:
        text, cols = _page_text(page, x_tolerance)
        pages.append(text)
        two_cols += cols
    return pages, two_cols


def parse_pdf(path: Path) -> dict:
    warnings: list[str] = []
    with pdfplumber.open(path) as pdf:
        pages, two_cols = _extract_pages(pdf, DEFAULT_X_TOLERANCE)
        # Espaces perdus (« Thishistoryrevolves… ») : on relit avec une tolérance plus fine.
        if cleaning.mean_word_length("\n".join(pages)) > 9:
            pages, two_cols = _extract_pages(pdf, TIGHT_X_TOLERANCE)
            warnings.append(f"espaces perdus : relu avec x_tolerance={TIGHT_X_TOLERANCE}")

        ocr_pages = 0
        for i, page in enumerate(pdf.pages):
            if len(pages[i].strip()) < MIN_CHARS_PER_PAGE and page.images:
                text = _ocr_page(page)
                if text:
                    pages[i] = text
                    ocr_pages += 1
        if ocr_pages:
            warnings.append(f"{ocr_pages} page(s) lue(s) par OCR")

    raw_chars = sum(len(p) for p in pages)
    page_lines = [p.splitlines() for p in pages]
    repeated = cleaning.find_repeated_lines(page_lines)

    units, removed = [], 0
    for number, lines in enumerate(page_lines, start=1):
        lines, n = cleaning.remove_noise_lines(lines, repeated)
        removed += n
        text = cleaning.split_paragraphs_by_layout(lines)
        text = cleaning.join_lines(cleaning.dehyphenate(text))
        text = cleaning.clean_text(text)
        if len(text) >= MIN_CHARS_PER_PAGE:
            units.append({"page": number, "section": None, "text": text})

    empty = len(pages) - len(units)
    if empty == len(pages):
        warnings.append("aucun texte extrait : PDF scanné, OCR nécessaire (installer Tesseract)")
    elif empty:
        warnings.append(f"{empty} page(s) sans texte ignorée(s)")
    if two_cols:
        warnings.append(f"{two_cols} page(s) lue(s) en deux colonnes")
    if repeated:
        warnings.append(f"{len(repeated)} en-tête(s)/pied(s) de page répété(s) supprimé(s)")

    return {
        "units": units,
        "pages_total": len(pages),
        "raw_chars": raw_chars,
        "removed_lines": removed,
        "warnings": warnings,
        "parser": "pdfplumber",
    }

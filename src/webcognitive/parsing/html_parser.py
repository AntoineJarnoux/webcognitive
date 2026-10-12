"""Extraction des pages HTML avec BeautifulSoup.

On isole le contenu principal (article) et on écarte menus, bandeaux,
scripts, liens « modifier » et appels de note de Wikipédia. Le texte est
découpé en sections d'après les intertitres h2/h3, qui servent ensuite de
« localisation » (les pages web n'ont pas de numéros de page).
"""
from __future__ import annotations

import re
from pathlib import Path

from bs4 import BeautifulSoup, Tag

from . import cleaning

# Éléments jamais utiles au moteur
NOISE_TAGS = ["script", "style", "noscript", "nav", "header", "footer", "aside", "form",
              "iframe", "svg", "button", "figure", "img", "input", "select"]
NOISE_SELECTORS = [
    ".mw-editsection", "sup.reference", ".reference", ".mw-cite-backlink", ".navbox",
    ".infobox", ".infobox_v2", ".infobox_v3", ".bandeau", ".bandeau-container", ".metadata",
    ".noprint", ".hatnote", ".homonymie", ".toc", "#toc", ".mw-jump-link", ".catlinks",
    "table.wikitable", ".sr-only", ".screen-reader-text", ".share", ".sharedaddy",
    ".comments", "#comments", ".related", ".breadcrumb", ".cookie", "[role=navigation]",
]
# Conteneurs du contenu principal, du plus précis au plus général
MAIN_SELECTORS = ["#mw-content-text .mw-parser-output", "article .entry-content", ".entry-content",
                  ".post-content", "main article", "article", "main", "[role=main]", "#content", "body"]
# Sections à ne pas garder (références, liens, appels aux dons…). Les « Notes » seules
# sont conservées : chez l'ISOC elles contiennent du contenu (la note 5 sur la rumeur nucléaire).
SKIP_HEADINGS = re.compile(
    r"^(notes et références|références|voir aussi|bibliographie|liens externes|articles connexes|"
    r"annexes|avez-vous trouvé|suivez-nous|partager|laisser un commentaire|commentaires|"
    r"related|see also|external links|references)",
    re.IGNORECASE,
)
HEADING_TAGS = ("h1", "h2", "h3", "h4")
BLOCK_TAGS = ["h1", "h2", "h3", "h4", "p", "li", "dt", "dd", "blockquote", "pre"]
WIKI_EDIT = re.compile(r"\[\s*modifier(\s*\|\s*modifier le code)?\s*\]")
NOTE_CALL = re.compile(r"\[\s*(\d+|[a-z]|réf\. nécessaire|citation nécessaire)\s*\]")


def _main_container(soup: BeautifulSoup) -> Tag:
    for selector in MAIN_SELECTORS:
        node = soup.select_one(selector)
        if node and len(node.get_text(strip=True)) > 200:
            return node
    return soup.body or soup


def _block_text(node: Tag) -> str:
    """Texte d'un bloc sans séparateur artificiel entre les balises en ligne."""
    for br in node.find_all("br"):
        br.replace_with("\n")
    text = node.get_text()
    text = WIKI_EDIT.sub("", text)
    text = NOTE_CALL.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_html(path: Path) -> dict:
    raw = path.read_bytes().decode("utf-8", errors="replace")
    soup = BeautifulSoup(raw, "lxml")
    title = soup.find("h1")
    title = _block_text(title) if title else (soup.title.get_text(strip=True) if soup.title else None)
    full_chars = len(soup.get_text(" ", strip=True))

    for tag in soup(NOISE_TAGS):
        tag.decompose()
    for selector in NOISE_SELECTORS:
        for node in soup.select(selector):
            node.decompose()
    # appels de note en exposant (« DARPA<sup>4</sup> ») : sinon ils se collent au mot
    for sup in soup.find_all("sup"):
        if re.fullmatch(r"\s*\[?\d{1,3}\]?\s*", sup.get_text()):
            sup.decompose()

    root = _main_container(soup)
    sections: list[dict] = []
    current = {"page": None, "section": title, "parts": []}
    seen: set[int] = set()
    skipping, skipped = False, []
    for node in root.find_all(BLOCK_TAGS):
        # un <p> dans un <li> déjà lu, ou un <li> imbriqué : déjà couvert par le parent
        if any(id(parent) in seen for parent in node.parents):
            continue
        seen.add(id(node))
        text = _block_text(node)
        if not text:
            continue
        if node.name in HEADING_TAGS:
            # Une section à écarter court jusqu'à l'intertitre suivant.
            skipping = bool(SKIP_HEADINGS.match(text))
            if skipping:
                skipped.append(text)
                continue
            sections.append(current)
            current = {"page": None, "section": text, "parts": []}
        elif skipping or (node.name == "li" and len(text) < 25):
            continue  # section écartée ou entrée de menu restante
        else:
            current["parts"].append(text)
    sections.append(current)

    units = []
    for sec in sections:
        text = cleaning.clean_text("\n\n".join(sec["parts"]))
        if len(text) >= 30:
            units.append({"page": None, "section": sec["section"], "text": text})

    # Repli : si la structure en blocs n'a presque rien donné, on prend tout le texte du conteneur.
    kept = sum(len(u["text"]) for u in units)
    warnings = []
    if kept < 0.3 * len(root.get_text(" ", strip=True)):
        text = cleaning.clean_text(cleaning.join_lines(root.get_text("\n")))
        units = [{"page": None, "section": title, "text": text}]
        warnings.append("structure en blocs insuffisante : texte complet du conteneur principal")
    if skipped:
        warnings.append(f"{len(skipped)} section(s) écartée(s) : {', '.join(skipped)[:80]}")
    warnings.append(f"contenu gardé : {kept * 100 // max(full_chars, 1)} % du texte de la page")

    return {
        "units": units,
        "title_detected": title,
        "pages_total": None,
        "raw_chars": len(raw),
        "removed_lines": None,
        "warnings": warnings,
        "parser": "BeautifulSoup (lxml)",
    }

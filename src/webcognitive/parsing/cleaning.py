"""Nettoyage et normalisation du texte extrait (expressions régulières).

Toutes les fonctions prennent et renvoient une chaîne : on peut les tester
séparément et les enchaîner dans l'ordre voulu par chaque parseur.
"""
from __future__ import annotations

import collections
import re
import unicodedata

# --------------------------------------------------------------------------- #
# Encodage et caractères spéciaux
# --------------------------------------------------------------------------- #
# Signe typique d'un texte UTF-8 relu en Latin-1 : « Ã© » au lieu de « é ».
MOJIBAKE = re.compile(r"Ã[\x80-\xbf]|â€[\x80-\x9f™œ]|Â[\xa0-\xbf]")

LIGATURES = {"ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl", "ﬅ": "st", "ﬆ": "st"}
SPECIAL_CHARS = {
    " ": " ",   # espace insécable
    " ": " ",   # espace fine insécable
    " ": " ",   # espace fine
    "­": "",    # trait d'union conditionnel
    "​": "",    # espace de largeur nulle
    "﻿": "",    # BOM
    "’": "'",   # apostrophe typographique
    "‘": "'",
    "–": "-",   # tiret demi-cadratin
    "‐": "-",
}


def fix_encoding(text: str) -> str:
    """Répare le texte UTF-8 décodé à tort en Latin-1 / CP1252 (« Ã© » -> « é »)."""
    if not MOJIBAKE.search(text):
        return text
    for codec in ("cp1252", "latin-1"):
        try:
            fixed = text.encode(codec).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
        if len(MOJIBAKE.findall(fixed)) < len(MOJIBAKE.findall(text)):
            return fixed
    return text


def normalize_unicode(text: str) -> str:
    """Forme NFC, ligatures typographiques et espaces spéciaux."""
    text = unicodedata.normalize("NFC", text)
    for src, dst in {**LIGATURES, **SPECIAL_CHARS}.items():
        text = text.replace(src, dst)
    # caractères de contrôle, sauf saut de ligne, tabulation et saut de page
    return re.sub(r"[\x00-\x08\x0b\x0e-\x1f\x7f]", "", text)


# --------------------------------------------------------------------------- #
# Lignes parasites (en-têtes, pieds de page, numéros de page)
# --------------------------------------------------------------------------- #
PAGE_NUMBER = re.compile(
    r"^\s*(?:page\s*)?[-–(]?\s*(?:\d{1,4}|[ivxlcIVXLC]{1,6}|[IVX]{1,4}-\d{1,3})\s*[-–)]?\s*$",
    re.IGNORECASE,
)


def line_signature(line: str) -> str:
    """Forme normalisée d'une ligne : les nombres deviennent « # » (« Page 12 » == « Page 13 »)."""
    return re.sub(r"\d+", "#", re.sub(r"\s+", " ", line.strip().lower()))


def find_repeated_lines(pages: list[list[str]], edge: int = 3, min_ratio: float = 0.3) -> set[str]:
    """Signatures des lignes qui reviennent en haut ou en bas d'une grande part des pages.

    On ne regarde que les `edge` premières et dernières lignes de chaque page :
    c'est là que se trouvent les en-têtes et pieds de page.
    """
    counter: collections.Counter[str] = collections.Counter()
    for lines in pages:
        lines = [l for l in lines if l.strip()]
        for sig in {line_signature(l) for l in lines[:edge] + lines[-edge:]}:
            if len(sig) > 3 and sig != "#":
                counter[sig] += 1
    threshold = max(3, len(pages) * min_ratio)
    return {sig for sig, n in counter.items() if n >= threshold}


def remove_noise_lines(lines: list[str], repeated: set[str]) -> tuple[list[str], int]:
    """Retire en-têtes/pieds répétés et numéros de page isolés. Renvoie (lignes, nb retirées)."""
    kept = [l for l in lines if line_signature(l) not in repeated and not PAGE_NUMBER.match(l)]
    return kept, len(lines) - len(kept)


# --------------------------------------------------------------------------- #
# Reconstitution des paragraphes
# --------------------------------------------------------------------------- #
def dehyphenate(text: str) -> str:
    """Recolle les mots coupés en fin de ligne : « pa-\\nper » -> « paper »."""
    return re.sub(r"(?<=[a-zà-ÿ])-\n\s*(?=[a-zà-ÿ])", "", text)


def join_lines(text: str) -> str:
    """Fusionne les sauts de ligne au milieu des phrases.

    Un saut de ligne simple devient une espace ; une ligne vide (double saut)
    reste une séparation de paragraphes.
    """
    paragraphs = re.split(r"\n\s*\n", text)
    return "\n\n".join(re.sub(r"\s*\n\s*", " ", p).strip() for p in paragraphs if p.strip())


def split_paragraphs_by_layout(lines: list[str]) -> str:
    """Pour les PDF (aucune ligne vide) : devine les fins de paragraphe.

    Une ligne nettement plus courte que la normale et terminée par une
    ponctuation forte clôt un paragraphe ; une ligne courte sans ponctuation
    finale qui précède une majuscule est traitée comme un intertitre.
    """
    lengths = sorted(len(l) for l in lines if len(l.strip()) > 20)
    if not lengths:
        return "\n".join(lines)
    typical = lengths[int(len(lengths) * 0.75)]
    out: list[str] = []
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        out.append(line)
        nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
        short = len(line) < 0.7 * typical
        if short and (re.search(r"[.!?:»\"]$", line) or (nxt[:1].isupper() and not line.endswith(("-", ",")))):
            out.append("")
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# Espaces et ponctuation
# --------------------------------------------------------------------------- #
def fix_spacing(text: str) -> str:
    """Espaces multiples, espaces avant la ponctuation et après les apostrophes.

    Les espaces avant « ; : ! ? » sont conservées : elles sont correctes en français.
    """
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" +([,.)\]])", r"\1", text)                 # « Postel , » -> « Postel, »
    text = re.sub(r"([(\[]) +", r"\1", text)                   # « ( Californie » -> « (Californie »
    text = re.sub(r"\b([lLdDjJnNsScCmMtT]|[qQ]u|[jJ]usqu|[lL]orsqu|[pP]uisqu)' +(?=\w)", r"\1'", text)  # « l' Internet »
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_text(text: str) -> str:
    """Chaîne de nettoyage commune, appliquée à la fin de chaque parseur."""
    text = fix_encoding(text)
    text = normalize_unicode(text)
    text = dehyphenate(text)
    return fix_spacing(text)


# --------------------------------------------------------------------------- #
# Indicateurs de qualité
# --------------------------------------------------------------------------- #
FR_WORDS = {"le", "la", "les", "des", "est", "et", "une", "dans", "pour", "que", "qui", "du", "sur", "au"}
EN_WORDS = {"the", "and", "of", "to", "is", "in", "that", "for", "with", "are", "this", "on", "by"}


def detect_language(text: str) -> str:
    """Langue majoritaire (fr/en) par comptage de mots-outils : suffisant pour deux langues."""
    words = re.findall(r"[a-zà-ÿ]+", text[:100_000].lower())
    fr = sum(w in FR_WORDS for w in words)
    en = sum(w in EN_WORDS for w in words)
    return "fr" if fr > en else "en"


def mean_word_length(text: str) -> float:
    """Longueur moyenne des mots : au-delà de ~9, les espaces ont probablement été perdus."""
    words = re.findall(r"\S+", text)
    return sum(map(len, words)) / len(words) if words else 0.0

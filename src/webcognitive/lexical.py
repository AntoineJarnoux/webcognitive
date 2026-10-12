"""Étape 4 : recherche par mots-clés (BM25), en complément de la recherche sémantique.

Pourquoi : l'évaluation de l'étape 3 montre que les questions qui citent un nom
(« selon Clark », « Saltzer et al. », « la RFC 1 ») échouent souvent avec les
embeddings seuls. Le segment qui contient la réponse ne ressemble pas assez à la
question par le sens, alors qu'il partage avec elle un mot rare.

BM25 est la formule classique des moteurs de recherche par mots-clés :
- un mot de la question compte d'autant plus qu'il est **rare dans le corpus**
  (IDF : « Mockapetris » pèse beaucoup plus que « réseau ») ;
- et qu'il est **fréquent dans le segment**, avec un effet de saturation ;
- les segments longs sont légèrement pénalisés.

Limite : BM25 ne comprend pas le sens et ne traduit pas. Une question française
retrouve mal un passage anglais, sauf pour les noms propres, les sigles et les dates.
D'où l'intérêt de combiner les deux méthodes (voir search_engine.py).
"""
from __future__ import annotations

import re
import unicodedata

import numpy as np
from rank_bm25 import BM25Okapi

TOKEN = re.compile(r"\w+")

# Mots trop fréquents pour aider à distinguer les segments (français et anglais)
STOPWORDS = """
a à au aux avec ce ces cet cette d dans de des du elle en est et été être il ils je l la le les leur lui
ma mais me même mes moi mon n ne ni nos notre nous on ou où par pas pour qu que quel quelle quelles quels qui
s sa sans se ses si son sont sur t ta te tes toi ton tu un une vos votre vous y c j m quand comment
selon quoi dont lors avait ont
the of and to in is was are were be been by for on at as with that this these those it its an or from
which who whom what when where how not but have has had do does did he she they their his her them
""".split()


def normalize(text: str) -> str:
    """Minuscules, sans accents : « Réseau » et « reseau » deviennent le même mot."""
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(ch for ch in text if not unicodedata.combining(ch))


STOPWORDS = {normalize(w) for w in STOPWORDS}  # comparés aux mots déjà normalisés


def tokenize(text: str) -> list[str]:
    return [t for t in TOKEN.findall(normalize(text)) if t not in STOPWORDS and (len(t) > 1 or t.isdigit())]


class BM25Index:
    """Index BM25 en mémoire sur les segments (construit en 1 à 2 secondes pour 5 751 segments)."""

    def __init__(self, texts: list[str]):
        self.bm25 = BM25Okapi([tokenize(t) for t in texts])

    def search(self, query: str, k: int, allowed: np.ndarray | None = None) -> list[tuple[int, float]]:
        """Les k meilleurs segments (indice, score). `allowed` : masque booléen issu des filtres."""
        tokens = tokenize(query)
        if not tokens:
            return []
        scores = self.bm25.get_scores(tokens)
        if allowed is not None:
            scores = np.where(allowed, scores, 0.0)
        top = np.argsort(-scores)[:k]
        return [(int(i), float(scores[i])) for i in top if scores[i] > 0]

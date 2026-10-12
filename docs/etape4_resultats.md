# Étape 4 : évaluation de la recherche servie par l'API

Fichier généré par `scripts/evaluate_search.py`. Mêmes questions et mêmes mesures qu'à l'étape 3 (`data/validation_questions.json`, 26 questions F et C ; succès = la réponse **et** le bon document). Explications : `docs/etape4_api.md`.

| Mode | Succès@1 | **Succès@5** | Réponse@5 | Doc@5 | MRR@10 | Temps par question |
|---|---|---|---|---|---|---|
| Sémantique (ChromaDB) | 31 % | **54 %** | 81 % | 62 % | 0.40 | 285 ms |
| Mots-clés (BM25) | 31 % | **46 %** | 69 % | 65 % | 0.38 | 17 ms |
| Hybride (fusion des rangs) | 31 % | **58 %** | 77 % | 73 % | 0.42 | 18 ms |

Accord entre ChromaDB (index HNSW, approché) et le calcul exact de l'étape 3 : **100 %** des segments du top 10 sont identiques.

## Rang de la première bonne réponse, par question

| Question | Sémantique (ChromaDB) | Mots-clés (BM25) | Hybride (fusion des rangs) |
|---|---|---|---|
| F01 | – | – | – |
| F02 | 7 | 3 | 3 |
| F03 | – | – | – |
| F04 | 2 | – | 10 |
| F05 | – | – | 7 |
| F06 | 1 | – | 5 |
| F07 | – | – | – |
| F08 | – | – | – |
| F09 | – | – | – |
| F10 | – | – | – |
| F11 | 1 | 1 | 1 |
| F12 | – | 3 | 3 |
| F13 | 1 | 1 | 1 |
| F14 | 4 | 1 | 1 |
| F15 | 1 | 1 | 1 |
| F16 | 3 | 2 | 2 |
| F17 | – | 2 | 7 |
| F18 | – | – | – |
| F19 | 2 | 9 | 3 |
| F20 | – | – | – |
| F21 | 1 | 1 | 1 |
| F22 | 1 | 1 | 1 |
| C01 | 1 | – | 2 |
| C02 | 2 | 1 | 1 |
| C03 | 5 | – | 3 |
| C04 | 1 | 1 | 1 |
| P01 | piège | piège | piège |
| P02 | piège | piège | piège |
| P03 | piège | piège | piège |

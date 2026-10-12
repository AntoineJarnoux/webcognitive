# Étape 4 : évaluation de la recherche servie par l'API

Fichier généré par `scripts/evaluate_search.py`. Mêmes questions et mêmes mesures qu'à l'étape 3 (`data/validation_questions.json`, 26 questions F et C ; succès = la réponse **et** le bon document). Explications : `docs/etape4_api.md`.

| Mode | Succès@1 | **Succès@5** | Réponse@5 | Doc@5 | MRR@10 | Temps par question |
|---|---|---|---|---|---|---|
| Mots-clés (BM25) | 31 % | **46 %** | 69 % | 65 % | 0.38 | 47 ms |

## Rang de la première bonne réponse, par question

| Question | Mots-clés (BM25) |
|---|---|
| F01 | – |
| F02 | 3 |
| F03 | – |
| F04 | – |
| F05 | – |
| F06 | – |
| F07 | – |
| F08 | – |
| F09 | – |
| F10 | – |
| F11 | 1 |
| F12 | 3 |
| F13 | 1 |
| F14 | 1 |
| F15 | 1 |
| F16 | 2 |
| F17 | 2 |
| F18 | – |
| F19 | 9 |
| F20 | – |
| F21 | 1 |
| F22 | 1 |
| C01 | – |
| C02 | 1 |
| C03 | – |
| C04 | 1 |
| P01 | piège |
| P02 | piège |
| P03 | piège |

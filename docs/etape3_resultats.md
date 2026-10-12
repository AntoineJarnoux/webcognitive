# Étape 3 : résultats de l'évaluation du chunking

Fichier généré par `scripts/evaluate_chunking.py` à partir de `data/embeddings/evaluation.json`. Questions : `data/validation_questions.json` (26 questions F et C, dont F09 impossible tant que le PDF de Baran n'est pas passé à l'OCR, et 3 pièges P). Explications : `docs/etape3_chunking_embeddings.md`.

| Configuration | Taille | Chevauch. | Segments | Tronqués | Succès@1 | **Succès@5** | Réponse@5 | Doc@5 | MRR@10 | Score moyen (vraies) | Score max (pièges) | Temps |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| minilm | 250 | 50 | 11723 | 0 % | 35 % | **38 %** | – | 46 % | 0.37 | 0.69 | 0.66 | 333 s |
| minilm | 300 | 60 | 9920 | 0 % | 27 % | **38 %** | – | 46 % | 0.32 | 0.68 | 0.63 | 375 s |
| minilm | 500 | 100 | 5751 | 0 % | 23 % | **42 %** | 54 % | 46 % | 0.31 | 0.66 | 0.61 | 417 s |
| minilm | 800 | 160 | 3266 | 3 % | 31 % | **38 %** | – | 38 % | 0.32 | 0.63 | 0.60 | 188 s |
| minilm | 1200 | 240 | 2059 | 46 % | 19 % | **27 %** | – | 38 % | 0.24 | 0.60 | 0.59 | 147 s |
| multi-minilm | 250 | 50 | 11723 | 0 % | 15 % | **42 %** | – | 62 % | 0.29 | 0.70 | 0.67 | 652 s |
| multi-minilm | 300 | 60 | 9920 | 0 % | 31 % | **46 %** | – | 69 % | 0.37 | 0.70 | 0.65 | 587 s |
| multi-minilm | 500 | 100 | 5751 | 13 % | 31 % | **54 %** | 81 % | 62 % | 0.40 | 0.69 | 0.69 | 633 s |
| multi-minilm | 800 | 160 | 3266 | 95 % | 31 % | **42 %** | – | 62 % | 0.38 | 0.68 | 0.66 | 309 s |
| multi-minilm | 1200 | 240 | 2059 | 100 % | 31 % | **46 %** | – | 54 % | 0.39 | 0.67 | 0.66 | 205 s |
| multi-minilm + en-tête | 300 | 60 | 9920 | 2 % | 23 % | **42 %** | 73 % | 73 % | 0.33 | 0.69 | 0.67 | 516 s |
| multi-minilm + en-tête | 500 | 100 | 5751 | 55 % | 31 % | **46 %** | 77 % | 73 % | 0.37 | 0.68 | 0.69 | 291 s |
| multi-minilm + en-tête + 256 tokens | 500 | 100 | 5751 | 0 % | 23 % | **38 %** | 69 % | 65 % | 0.31 | 0.68 | 0.70 | 944 s |
| e5-small | 250 | 50 | 11723 | 0 % | 31 % | **46 %** | – | 46 % | 0.37 | 0.88 | 0.84 | 684 s |
| e5-small | 300 | 60 | 9920 | 0 % | 38 % | **38 %** | – | 46 % | 0.39 | 0.87 | 0.84 | 661 s |
| e5-small | 500 | 100 | 5751 | 0 % | 35 % | **46 %** | – | 54 % | 0.40 | 0.88 | 0.84 | 455 s |
| e5-small | 800 | 160 | 3266 | 0 % | 38 % | **50 %** | 69 % | 54 % | 0.42 | 0.87 | 0.84 | 786 s |
| e5-small | 1200 | 240 | 2059 | 0 % | 38 % | **46 %** | – | 46 % | 0.42 | 0.86 | 0.84 | 329 s |
| e5-small + en-tête | 800 | 160 | 3266 | 0 % | 35 % | **50 %** | 81 % | 73 % | 0.44 | 0.87 | 0.84 | 837 s |

## Détail par question : multi-minilm, taille 500

| Question | Rang de la 1re bonne réponse (bon document) | Score du 1er segment | 1er segment |
|---|---|---|---|
| F01 | absent du top 10 | 0.648 | `txt11_0062` |
| F02 | 7 | 0.807 | `docx01_0037` |
| F03 | absent du top 10 | 0.768 | `html01_0057` |
| F04 | 2 | 0.621 | `html01_0057` |
| F05 | absent du top 10 | 0.734 | `pdf02_0087` |
| F06 | 1 | 0.595 | `pdf02_0018` |
| F07 | absent du top 10 | 0.54 | `pdf10_0131` |
| F08 | absent du top 10 | 0.578 | `pdf08_0177` |
| F09 | absent du top 10 | 0.532 | `pdf07_0163` |
| F10 | absent du top 10 | 0.792 | `pdf05_0000` |
| F11 | 1 | 0.657 | `html01_0009` |
| F12 | absent du top 10 | 0.793 | `pdf10_0123` |
| F13 | 1 | 0.778 | `html01_0030` |
| F14 | 4 | 0.741 | `pdf03_0064` |
| F15 | 1 | 0.769 | `html01_0087` |
| F16 | 3 | 0.762 | `html05_0039` |
| F17 | absent du top 10 | 0.611 | `html05_0037` |
| F18 | absent du top 10 | 0.72 | `docx07_0007` |
| F19 | 2 | 0.667 | `docx07_0007` |
| F20 | absent du top 10 | 0.579 | `txt06_0001` |
| F21 | 1 | 0.784 | `html01_0191` |
| F22 | 1 | 0.725 | `html01_0176` |
| C01 | 1 | 0.767 | `html07_0024` |
| C02 | 2 | 0.69 | `pdf03_0028` |
| C03 | 5 | 0.68 | `txt03_0082` |
| C04 | 1 | 0.698 | `docx08_0000` |
| P01 | piège | 0.585 | `docx01_0100` |
| P02 | piège | 0.301 | `docx01_0055` |
| P03 | piège | 0.692 | `pdf02_0000` |

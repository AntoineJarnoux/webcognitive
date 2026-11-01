# Étape 7 : module de dataviz et analyse exploratoire

**Objectif :** ajouter à l'application un regard **analytique** sur le corpus, à côté du mode conversationnel. L'onglet **Tableau de bord** de l'interface donne une vue d'ensemble des documents, de l'index et de l'usage de l'assistant.

```bash
python scripts/carte_vecteurs.py     # une fois : calcule la carte 2D des segments (≈ 30 s)
python scripts/serve_api.py          # puis onglet « Tableau de bord » sur http://127.0.0.1:8000/
```

## 1. Architecture

```
data/processed/ (étape 2) ──┐
ChromaDB (étapes 3-4) ──────┼──► analytics.py (Python) ──► GET /stats, /stats/questions, /stats/map ──► dashboard.js (Plotly.js)
data/logs/questions.jsonl ──┘          calcule les indicateurs          JSON déjà agrégé                    dessine les graphiques
```

- **Calcul en Python** (`src/webcognitive/analytics.py`). Les indicateurs sont calculés côté serveur une seule fois, en quelques secondes, puis gardés en cache et recalculés après une réindexation. Le navigateur reçoit des chiffres déjà agrégés, pas les 41 textes.
- **Affichage avec Plotly.** C'est la bibliothèque proposée par la fiche, utilisée ici dans sa version JavaScript, ce qui donne des graphiques interactifs : survol, zoom, clic sur la légende. Elle est **servie en local** par l'API (`/vendor/plotly.min.js`, fichier fourni par le paquet Python `plotly`) : aucune connexion Internet n'est nécessaire.
- **Journal des questions.** Chaque question posée à l'assistant est enregistrée dans `data/logs/questions.jsonl` (fichier local, ignoré par Git) avec :
  - la date ;
  - le refus éventuel ;
  - les documents cités ;
  - le temps de réponse.

## 2. Les indicateurs et leurs graphiques

| Graphique | Ce qu'il montre | Ce qu'on y lit |
|---|---|---|
| **Chiffres clés** | documents, segments, mots, période, questions posées | 41 documents, 5 751 segments, 315 525 mots, de 1964 à 2018 |
| **Documents par format** (anneau) | part des PDF, TXT, HTML et DOCX | un corpus équilibré entre les 4 formats |
| **Volume de texte par format** (barres) | mots extraits par format | les 11 RFC (TXT) pèsent 140 000 mots, les 12 pages HTML seulement 37 000 |
| **Documents par décennie** (barres empilées par langue) | répartition dans le temps | les sources anglaises datent des années 1960-1990, les françaises sont récentes ou non datées |
| **Taille des segments** (histogramme) | distribution de la longueur des 5 751 segments | médiane 443 caractères, sous la cible de 500, car la coupure se fait en fin de phrase (étape 3) |
| **Thématiques par document** (carte de chaleur) | mentions de 10 thèmes pour 10 000 mots, document par document | le thème dominant de chaque document : RFC 1034 → DNS, documents de Pouzin → Cyclades… |
| **Évolution des thèmes par décennie** | les mêmes thèmes, regroupés par décennie de publication | TCP/IP dans les années 1970, RFC et ARPANET dans les années 1980, le Web dans les années 1990 |
| **Termes les plus fréquents** (barres, français ou anglais) | 15 mots les plus fréquents, sans les mots vides | « réseau », « Minitel », « Inria » côté français ; « network », « host », « protocol » côté anglais |
| **Carte sémantique** (nuage de points) | les 5 751 vecteurs projetés en 2D (t-SNE), colorés par langue ; un document peut être mis en évidence | les segments d'un même document forment un îlot ; des passages français et anglais d'un même sujet sont voisins |
| **Questions posées** | nombre, refus, temps moyen, documents les plus cités, dernières questions | l'usage réel de l'assistant |

**Les thématiques suivies** reprennent les axes du corpus définis à l'étape 1 :
- ARPANET ;
- commutation de paquets ;
- TCP/IP ;
- datagramme ;
- Cyclades / Pouzin ;
- courrier électronique ;
- DNS ;
- Web / HTTP ;
- Minitel / Transpac ;
- RFC.

Chaque thème est repéré par une expression régulière, valable en français et en anglais (par exemple `packet switch` ou `commutation de paquets`). Les mentions sont **ramenées à 10 000 mots** : sans cela, les longs documents écraseraient les courts.

## 3. Choix de présentation
- **Une couleur suit toujours la même chose** : chaque format garde sa couleur dans tous les graphiques (PDF bleu, TXT orange, HTML vert d'eau, DOCX jaune), de même que chaque langue (français violet, anglais vert). La palette a été vérifiée avec un outil de contrôle des couleurs : elle reste lisible pour les daltoniens et assez contrastée.
- **Valeurs écrites sur les barres et l'anneau**, en plus de la couleur, et **détail au survol** de chaque élément.
- **Intensité d'une seule couleur** (du bleu clair au bleu foncé) pour les cartes de chaleur : plus c'est foncé, plus le thème est présent.
- **Deux modes dans l'interface**, comme le demande la fiche : l'**Assistant** pour une recherche précise, le **Tableau de bord** pour une vue d'ensemble.

## 4. Routes de l'API ajoutées

| Route | Contenu |
|---|---|
| `GET /stats` | totaux, répartitions par format, langue et décennie, histogramme des segments, thématiques, termes fréquents |
| `GET /stats/questions` | statistiques du journal des questions |
| `GET /stats/map` | coordonnées 2D des segments (produites par `scripts/carte_vecteurs.py`) |

## 5. Tests
`tests/test_dataviz.py` vérifie :
- les indicateurs calculés sur un petit corpus connu (bons totaux, thèmes comptés dans le bon document) ;
- le journal des questions ;
- les trois routes `/stats` ;
- la carte, absente (message d'erreur clair) ou présente ;
- le service local de Plotly.

## 6. Limites
- **15 documents sur 41 ne sont pas datés** (notes Wikipédia, pages web) : ils ne comptent pas dans l'évolution par décennie.
- **Le comptage des thèmes se fait par mots-clés.** Un thème évoqué sans son mot-clé n'est pas compté, et un mot ambigu (« web ») peut être compté à tort.
- **Le scan de Baran (`pdf04`) n'a pas de texte sans OCR** : sa ligne est vide dans la carte de chaleur.

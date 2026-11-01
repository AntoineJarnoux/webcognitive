# WebCognitive Engine : Histoire d'Internet

**Un assistant documentaire 100 % local** qui répond à des questions sur l'histoire d'Internet **uniquement à partir d'un corpus de 41 documents**, en **citant ses sources** (fichier et page). Il dit « je ne sais pas » quand l'information n'y est pas. Il comprend aussi un moteur de recherche sémantique et un tableau de bord d'analyse du corpus.

Projet individuel du cours *Techniques Informatiques et Web*, Master THYP (M2), Université Paris 8, 2026-2027. Auteur : Antoine Jarnoux.

| Recherche | Assistant (RAG) | Dataviz | Tout en local |
|---|---|---|---|
| ChromaDB + BM25 | Mistral 7B via Ollama | Plotly | aucun service cloud, aucune clé d'API |

---

## Sommaire
1. [Le projet](#1-le-projet)
2. [Fonctionnalités](#2-fonctionnalités)
3. [Architecture](#3-architecture)
4. [Structure du dépôt](#4-structure-du-dépôt)
5. [Installation pas à pas](#5-installation-pas-à-pas)
6. [Utilisation](#6-utilisation)
7. [API REST](#7-api-rest)
8. [Résultats et validation](#8-résultats-et-validation)
9. [Tests](#9-tests)
10. [Configuration](#10-configuration)
11. [Documentation détaillée](#11-documentation-détaillée)
12. [Limites et pistes](#12-limites-et-pistes)
13. [Sources et licences](#13-sources-et-licences)

---

## 1. Le projet

### 1.1 Thème et périmètre du corpus
**Thème :** l'histoire d'Internet et des réseaux informatiques, des premières idées de réseau (années 1960) à l'ouverture du World Wide Web au public (années 1990).

Axes couverts :
- **Les fondations** : Licklider, Baran (RAND), commutation de paquets.
- **ARPANET** : BBN, NCP, les premiers nœuds, les RFC.
- **TCP/IP** : Cerf et Kahn, la transition de 1983, les principes d'architecture (Clark, argument de bout en bout).
- **Les services** : DNS, courrier électronique, HTTP.
- **Le Web** : la proposition de Tim Berners-Lee au CERN (1989), le W3C.
- **La contribution française** : Cyclades, Louis Pouzin, Transpac, Minitel, l'arrivée d'Internet en France.
- **Les pionniers** : biographies et hommages (Cerf, Berners-Lee, Postel, Pouzin).

**Hors périmètre :** l'actualité récente (réseaux sociaux, IA, régulation) et les aspects commerciaux postérieurs à 2000.

### 1.2 Composition du corpus

| Format | Nombre | Nature |
|---|---|---|
| PDF | 10 | Articles académiques fondateurs, rapports officiels (dont deux scans : RAND 1964, BBN 1981) |
| TXT | 11 | RFC historiques (1, 675, 791, 793, 801, 1034, 1945…) et textes mémoriels |
| HTML | 12 | Articles de vulgarisation, entretiens, pages Wikipédia complètes (avec menus, pour tester le nettoyage) |
| DOCX | 8 | Notes de synthèse et biographies |
| **Total** | **41** | 24 en anglais, 17 en français ; de 1964 à 2018 ; 315 525 mots après nettoyage |

La liste des sources est dans [`data/sources.json`](data/sources.json), l'inventaire (taille, empreinte SHA-256) dans [`data/corpus_metadata.json`](data/corpus_metadata.json).

**Pourquoi ce corpus convient à un RAG :**
- il est hétérogène en formats et en langues ;
- il contient des faits datés et chiffrés, faciles à vérifier ;
- plusieurs documents racontent les mêmes événements, ce qui permet des questions croisées ;
- il pose de vraies difficultés d'extraction : scans, RFC en texte à largeur fixe, pages HTML chargées.

### 1.3 Contraintes et critères de réussite
- **Contraintes :**
  - tout fonctionne en local, avec des outils libres ;
  - le code est versionné avec Git, avec au moins un commit par étape.
- **Critères de réussite :**
  - au moins 80 % des questions de validation obtiennent une réponse correcte avec la bonne source ;
  - toutes les questions « pièges » (hors corpus) sont refusées.

  **Les deux sont atteints** : 81 % de succès et 100 % des pièges refusés (voir § 8).

---

## 2. Fonctionnalités

| Fonctionnalité | Description |
|---|---|
| **Ingestion automatique** | 4 formats (PDF, TXT, HTML, DOCX) → texte nettoyé + métadonnées, un JSON par document ; réindexation possible via l'API (`POST /ingest`) |
| **Recherche sémantique** | une question en langage naturel renvoie les passages les plus proches par le sens (même d'une langue à l'autre), avec filtres (langue, format, document, années) ; modes sémantique, mots-clés (BM25) ou hybride |
| **Assistant RAG local** | Mistral 7B rédige la réponse uniquement à partir des extraits trouvés, cite ses sources `[n]` et refuse les questions hors corpus |
| **Interface web** | chat avec réponse affichée au fil de l'eau, sources cliquables (fichier, page, contexte), onglet de recherche |
| **Tableau de bord** | répartition du corpus (formats, langues, décennies), taille des segments, thématiques par document et par décennie, termes fréquents, carte sémantique 2D, statistiques des questions posées |

---

## 3. Architecture

```
                         ┌──────────────────────── préparation (une fois) ─────────────────────────┐
 data/raw/  (41 fichiers) │ ① parsing + nettoyage  ② découpage + vectorisation   ③ base vectorielle  │
 PDF · TXT · HTML · DOCX ─┼─► data/processed/*.json ─► data/embeddings/ ───────────► ChromaDB        │
                         │   (pdfplumber, BS4,        (segments de 500 car.,         (cosinus, HNSW,  │
                         │    python-docx, regex)      MiniLM multilingue, 384 dim.)  métadonnées)    │
                         └──────────────────────────────────────────────────────────────────────────┘
                                                                                     │
 Navigateur ──HTTP──► FastAPI (src/webcognitive/api.py) ──► moteur de recherche ─────┤ (+ index BM25)
  interface web        /search  /ask  /documents  /stats      search_engine.py       │
  (HTML/CSS/JS)        │                                                             │
       ▲               └── /ask ──► pipeline RAG (rag.py) : 8 extraits + consigne ──► Ollama (Mistral 7B, local)
       └──────────── réponse mot à mot + sources (fichier, page) ◄────────────────────┘
```

| Brique | Technologie | Rôle |
|---|---|---|
| Extraction | pdfplumber, BeautifulSoup + lxml, python-docx, `re` | lire les 4 formats et nettoyer le texte (en-têtes, colonnes, menus, encodage) |
| Vectorisation | sentence-transformers (`paraphrase-multilingual-MiniLM-L12-v2`) | transformer chaque segment en vecteur de 384 nombres qui représente son sens |
| Base vectorielle | ChromaDB | stocker vecteurs, textes et métadonnées ; trouver les plus proches (cosinus) ; filtrer |
| Recherche par mots-clés | rank-bm25 | compléter la recherche par le sens pour les noms propres, sigles et dates |
| Back-end | FastAPI + Uvicorn | API REST, documentation interactive `/docs`, service de l'interface |
| LLM local | Ollama + Mistral 7B | rédiger une réponse sourcée à partir des extraits |
| Front-end | HTML5, CSS3, JavaScript (fetch, streaming) | chat, recherche, tableau de bord, sans framework ni compilation |
| Dataviz | Plotly (servi en local), scikit-learn (t-SNE) | graphiques interactifs, carte 2D des segments |

---

## 4. Structure du dépôt

```
webcognitive/
├── data/
│   ├── sources.json               # les 41 sources (URL, format, métadonnées)
│   ├── corpus_metadata.json       # inventaire généré (taille, SHA-256, date)
│   ├── validation_questions.json  # questions de validation, version machine
│   ├── raw/                       # documents bruts : pdf/ html/ docx/ txt/
│   ├── processed/                 # un JSON propre par document (étape 2)
│   ├── embeddings/                # segments, vecteurs (.npy régénérable, ignoré par Git), évaluation (étape 3)
│   ├── analytics/carte_2d.json    # projection 2D des vecteurs pour le tableau de bord (étape 7)
│   ├── evaluation_*.json          # résultats des évaluations (étapes 4 et 5)
│   ├── vectordb/                  # base ChromaDB (régénérable, ignorée par Git)
│   └── logs/                      # journal local des questions posées (ignoré par Git)
├── src/webcognitive/
│   ├── config.py                  # chemins et réglages retenus
│   ├── parsing/                   # un parseur par format + nettoyage (étape 2)
│   ├── chunking.py                # découpage avec chevauchement (étape 3)
│   ├── embeddings.py              # vectorisation locale (étape 3)
│   ├── indexing.py                # chaîne d'indexation (scripts et API)
│   ├── vectordb.py                # base vectorielle ChromaDB (étape 4)
│   ├── lexical.py                 # recherche BM25 (étape 4)
│   ├── search_engine.py           # recherche sémantique, mots-clés ou hybride (étape 4)
│   ├── rag.py                     # pipeline RAG et client Ollama (étape 5)
│   ├── analytics.py               # indicateurs du tableau de bord (étape 7)
│   └── api.py                     # API REST FastAPI (étapes 4 à 7)
├── frontend/                      # interface web : index.html, style.css, app.js, dashboard.js (étapes 6-7)
├── scripts/                       # points d'entrée en ligne de commande (voir § 5 et § 9)
├── tests/                         # tests automatiques (pytest)
├── installer.bat / installer.ps1  # installation automatique (Windows)
├── lancer.bat                     # démarrage de l'application (Windows)
├── install.sh / lancer.sh         # équivalents Linux / macOS
├── docs/                          # documentation de chaque étape, résultats, manuel utilisateur
├── requirements.txt
└── README.md
```

---

## 5. Installation pas à pas

### Installation automatique (recommandée)
**Windows :**
1. Récupérez le projet : `git clone https://github.com/AntoineJarnoux/webcognitive.git`, ou « Code → Download ZIP » sur GitHub, puis décompressez.
2. Double-cliquez sur **`installer.bat`**. Le script fait toutes les étapes ci-dessous :
   - il vérifie Python ;
   - il crée l'environnement virtuel et installe les dépendances ;
   - il installe Ollama (avec winget) s'il est absent, et le démarre ;
   - il télécharge Mistral ;
   - il calcule les vecteurs et remplit la base.

   On peut le relancer sans risque, il saute ce qui est déjà fait. Comptez 15 à 20 minutes la première fois, surtout pour les téléchargements et le calcul des vecteurs.
3. Ensuite, pour chaque utilisation, double-cliquez sur **`lancer.bat`** : l'application démarre et le navigateur s'ouvre sur [http://127.0.0.1:8000/](http://127.0.0.1:8000/).

**Linux / macOS :** `bash install.sh`, puis `bash lancer.sh`.

Pour un PC peu puissant, prenez un modèle plus léger :
- Windows : `installer.bat -Modele llama3.2:3b` ;
- Linux / macOS : `bash install.sh llama3.2:3b`.

Les sections suivantes décrivent les mêmes étapes **à la main**.

### 5.1 Prérequis
- **Python 3.12** (testé avec 3.12 sous Windows 11 ; 3.10 minimum) et **Git**.
- **[Ollama](https://ollama.com/download)** pour faire tourner le LLM en local.
- Environ **8 Go de RAM** libres pour Mistral 7B et **6 Go d'espace disque** (modèle compris). Pas de carte graphique nécessaire : tout tourne sur le processeur, plus lentement.

### 5.2 Récupérer le projet et créer l'environnement virtuel
```bash
git clone https://github.com/AntoineJarnoux/webcognitive.git
cd webcognitive
python -m venv .venv
.venv\Scripts\activate             # Windows (PowerShell)
# source .venv/bin/activate        # Linux / macOS
pip install -r requirements.txt
```

### 5.3 Installer le LLM local
Installez Ollama depuis [https://ollama.com/download](https://ollama.com/download). Il se lance tout seul en arrière-plan. Téléchargez ensuite le modèle, une seule fois :
```bash
ollama pull mistral                # ≈ 4,4 Go
```

### 5.4 Préparer les données
Le corpus brut (`data/raw/`) et le texte nettoyé (`data/processed/`) sont déjà dans le dépôt. Il reste à calculer les vecteurs (non versionnés) et à remplir la base :
```bash
python scripts/build_embeddings.py # étape 3 : découpage + vectorisation (télécharge le modèle d'embedding la 1re fois ; 5 à 10 min sur CPU)
python scripts/build_vectordb.py   # étape 4 : chargement dans ChromaDB (≈ 5 s)
```
Facultatif : la carte 2D du tableau de bord est déjà fournie. On la régénère avec `python scripts/carte_vecteurs.py`.

<details>
<summary>Reconstruire tout depuis zéro (téléchargement et parsing)</summary>

```bash
python scripts/download_corpus.py  # étape 1 : télécharge les 41 documents (ne réécrit pas l'existant)
python scripts/parse_corpus.py     # étape 2 : extraction + nettoyage → data/processed/
```
Le PDF de Baran (`pdf04`) est un scan sans texte. Pour le lire, installez [Tesseract](https://github.com/UB-Mannheim/tesseract/wiki), puis `pip install pytesseract`, et lancez `python scripts/parse_corpus.py --only pdf04`.
</details>

### 5.5 Lancer l'application
```bash
python scripts/serve_api.py
```
Ouvrez **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)**. Le point vert en haut à droite indique que la base, Ollama et le modèle sont prêts. La documentation interactive de l'API est sur [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

> **Windows, dossier avec accents** (ex. `D:\école\…`) : ChromaDB ne relit pas son index dans un tel chemin. La base est alors rangée automatiquement dans `%LOCALAPPDATA%\webcognitive\vectordb`.

---

## 6. Utilisation
Le mode d'emploi complet de l'interface est dans **[docs/manuel_utilisateur.md](docs/manuel_utilisateur.md)**. En bref :
- **Assistant** : posez une question (ex. « Qui a inventé le DNS ? »). La réponse s'écrit en direct ; cliquez sur `[1]`, `[2]`… pour voir l'extrait source, son fichier et sa page.
- **Recherche dans le corpus** : les passages les plus pertinents, sans LLM.
- **Tableau de bord** : la vue d'ensemble statistique du corpus et des questions posées.

En ligne de commande :
```bash
python scripts/search.py "Qui a inventé le DNS ?"     # recherche sémantique
python scripts/voir_bd.py html01_0087                 # contenu d'une entrée de la base vectorielle
```

---

## 7. API REST

| Méthode | Route | Rôle |
|---|---|---|
| GET | `/health` | état : segments indexés, modèle d'embedding, Ollama et LLM disponibles |
| GET | `/documents` | catalogue des 41 documents (filtres `format`, `lang`) |
| GET | `/documents/{id}` | un document ; `include_text=true` pour son texte nettoyé par page ou section |
| GET | `/chunks/{id}` | un segment et ses voisins (`previous`, `next`) |
| GET / POST | `/search` | recherche : `q`, `k`, `mode` (`semantic`, `lexical`, `hybrid`), filtres `lang`, `format`, `doc_id`, `year_min`, `year_max` |
| POST | `/ask` | question → réponse du LLM + sources ; `stream: true` pour un flux NDJSON (sources, morceaux de texte, fin) |
| POST / GET | `/ingest` | relance l'indexation en arrière-plan (`reembed: true` refait aussi la vectorisation) / suivi |
| GET | `/stats`, `/stats/questions`, `/stats/map` | données du tableau de bord |

Exemple :
```bash
curl -X POST http://127.0.0.1:8000/ask -H "Content-Type: application/json" -d "{\"question\": \"Qui a inventé le DNS ?\"}"
```
```json
{"answer": "Le DNS a été inventé par Paul Mockapetris, de l'USC/ISI [1].", "refused": false, "cited": [1],
 "sources": [{"number": 1, "cited": true, "filename": "isoc_bref_historique_internet_fr.html",
              "location": "§ Démontrer les idées", "text": "…", "score": 0.03}], "model": "mistral", "total_ms": 1900}
```

---

## 8. Résultats et validation

Les **29 questions de validation** de l'étape 1 ([docs/questions_validation.md](docs/questions_validation.md)) se répartissent ainsi :
- 22 questions factuelles ;
- 4 questions croisées entre plusieurs documents ;
- 3 pièges hors corpus.

Elles ont servi à régler chaque brique :

| Étape | Mesure | Résultat |
|---|---|---|
| 3. Embeddings | bonne réponse et bon document dans les 5 premiers segments | modèle de la fiche (anglais) 42 % → **modèle multilingue 54 %** |
| 4. Recherche | idem, recherche sémantique / mots-clés / hybride | 54 % / 46 % / **58 %** ; ChromaDB identique au calcul exact (100 %) |
| 5. RAG | réponse correcte **et** source qui la justifie | 73 % (sens seul, 5 extraits) → **81 %** (hybride, 8 extraits) |
| 5. RAG | questions pièges refusées | **100 %** (3/3) |
| 8. Recette | contrôles de bout en bout via l'API (`scripts/recette.py`) | voir [docs/etape8_recette.md](docs/etape8_recette.md) |

Les détails sont dans [etape3_resultats.md](docs/etape3_resultats.md), [etape4_resultats.md](docs/etape4_resultats.md) et [etape5_resultats.md](docs/etape5_resultats.md).

---

## 9. Tests

```bash
python -m pytest tests -q                   # 34 tests unitaires et d'API (sans Ollama ni modèle : faux modèles)
python scripts/recette.py --validation      # recette de bout en bout sur l'application en marche
python scripts/evaluate_rag.py              # évaluation du RAG sur les questions de validation
```

La **recette** (`scripts/recette.py`) interroge l'application en marche à travers l'API, comme le fait l'interface. Elle vérifie :
- l'état de la base et du LLM ;
- l'ingestion via `POST /ingest` ;
- le catalogue ;
- la recherche dans les 3 modes ;
- les réponses du RAG (sources, refus, streaming) ;
- les données du tableau de bord ;
- les fichiers de l'interface ;
- avec `--validation`, les 29 questions de validation.

Elle écrit un rapport dans `docs/etape8_recette.md`.

---

## 10. Configuration
Les réglages sont regroupés dans [`src/webcognitive/config.py`](src/webcognitive/config.py), chacun avec la raison de son choix :

| Réglage | Valeur | Pourquoi |
|---|---|---|
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | 500 / 100 caractères | meilleur compromis mesuré (étape 3) |
| `EMBEDDING_MODEL` | `paraphrase-multilingual-MiniLM-L12-v2` | questions en français, corpus à moitié en anglais |
| `RAG_MODE` / `RAG_K` | `hybrid` / 8 extraits | meilleur succès mesuré (étape 5) |
| `RAG_MIN_SCORE` | 0,35 | garde-fou : refus sans appeler le LLM pour les questions sans rapport |
| `LLM_TEMPERATURE` | 0,1 | réponses factuelles et stables |

Variables d'environnement :
- `WEBCOGNITIVE_LLM` : autre modèle Ollama, par exemple `llama3.2:3b`, plus léger ;
- `OLLAMA_URL` : adresse d'Ollama, par défaut `http://127.0.0.1:11434` ;
- `WEBCOGNITIVE_VECTORDB_DIR` : dossier de la base ChromaDB.

---

## 11. Documentation détaillée

| Étape | Document |
|---|---|
| 1. Cadrage et corpus | [journal_audit.md](docs/journal_audit.md), [questions_validation.md](docs/questions_validation.md) |
| 2. Parsing et nettoyage | [etape2_parsing.md](docs/etape2_parsing.md) |
| 3. Chunking et embeddings | [etape3_chunking_embeddings.md](docs/etape3_chunking_embeddings.md) |
| 4. Base vectorielle et API | [etape4_api.md](docs/etape4_api.md) |
| 5. Pipeline RAG | [etape5_rag.md](docs/etape5_rag.md) |
| 6. Interface web | [etape6_interface.md](docs/etape6_interface.md) |
| 7. Dataviz | [etape7_dataviz.md](docs/etape7_dataviz.md) |
| 8. Finalisation | [etape8_finalisation.md](docs/etape8_finalisation.md), [manuel_utilisateur.md](docs/manuel_utilisateur.md) |

---

## 12. Limites et pistes
- **La recherche est le maillon limitant.** Quand le bon passage n'est pas dans les 8 extraits, le LLM ne peut pas répondre (F08, F10). Piste : un re-classement des extraits par un modèle *cross-encoder*.
- **Le scan de Baran (`pdf04`) n'est pas lu sans OCR** (Tesseract).
- **Pas de mémoire de conversation** : chaque question est traitée seule.
- **Lenteur sur CPU** : quelques secondes par réponse avec Mistral 7B. `llama3.2:3b` est plus rapide mais moins précis.
- **15 documents non datés** (notes Wikipédia, pages web) : ils sont absents de l'évolution par décennie du tableau de bord.

---

## 13. Sources et licences
Les documents du corpus restent la propriété de leurs auteurs et éditeurs, et sont utilisés à des fins strictement pédagogiques. Les notes DOCX sont dérivées de Wikipédia (licence CC BY-SA 4.0, source indiquée en tête de chaque fichier). Les briques logicielles sont libres :
- [FastAPI](https://fastapi.tiangolo.com) ;
- [ChromaDB](https://docs.trychroma.com) ;
- [sentence-transformers](https://www.sbert.net) ;
- [Ollama](https://ollama.com) ;
- [Mistral 7B](https://mistral.ai/news/announcing-mistral-7b) (Apache 2.0) ;
- [Plotly](https://plotly.com/javascript/).

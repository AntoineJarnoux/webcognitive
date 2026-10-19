# WebCognitive Engine : Histoire d'Internet

Projet individuel du cours *Techniques Informatiques et Web* (M1 Informatique, Université Paris 8).
L'application transforme un corpus multi-formats sur l'histoire d'Internet en un moteur de recherche sémantique et un assistant conversationnel local (RAG), avec traçabilité des sources et un tableau de bord d'analyse.

---

## 1. Cahier des charges synthétique

### 1.1 Thème et périmètre du corpus
**Thème unique :** l'histoire d'Internet et des réseaux informatiques, des premières idées de réseau (années 1960) à l'ouverture du World Wide Web au public (années 1990).

Axes couverts :
- **Les fondations** : Licklider, Baran (RAND), commutation de paquets.
- **ARPANET** : BBN, NCP, les premiers nœuds, les RFC.
- **TCP/IP** : Cerf et Kahn, la transition de 1983, les principes d'architecture (Clark, argument de bout en bout).
- **Les services** : DNS, courrier électronique, HTTP.
- **Le Web** : proposition de Tim Berners-Lee au CERN (1989), W3C.
- **La contribution française** : Cyclades, Louis Pouzin, Transpac, Minitel, l'arrivée d'Internet en France.
- **Les pionniers** : biographies et hommages (Cerf, Berners-Lee, Postel, Pouzin).

**Hors périmètre :** l'actualité récente (réseaux sociaux, IA, régulation) et les aspects purement commerciaux postérieurs à 2000.

### 1.2 Composition du corpus

| Format | Nombre | Nature |
|---|---|---|
| PDF | 10 | Articles académiques fondateurs, rapports officiels (dont deux scans OCR : RAND 1964, BBN 1981) |
| TXT | 11 | Spécifications historiques (RFC 1, 675, 791, 793, 801, 1034, 1945…) et documents mémoriels |
| HTML | 12 | Articles de vulgarisation, entretiens, pages Wikipédia complètes (avec menus, utiles pour tester le nettoyage) |
| DOCX | 8 | Notes de synthèse et biographies |
| **Total** | **41** | Deux langues (FR / EN), de 1964 à 2018 |

La liste détaillée est dans [`data/sources.json`](data/sources.json). L'inventaire généré, avec la taille et le SHA-256 de chaque fichier, est dans `data/corpus_metadata.json`.

**Pourquoi ce corpus est pertinent pour un RAG :**
- il est hétérogène en formats et en langues ;
- il contient des faits datés et chiffrés, faciles à vérifier ;
- plusieurs documents racontent les mêmes événements sous des angles différents, ce qui permet des questions croisées ;
- il comporte des difficultés réelles de parsing : scans OCR, RFC en texte à largeur fixe avec en-têtes de page, pages HTML avec navigation.

### 1.3 Fonctionnalités visées (MVP)
1. **Ingestion automatique** des 4 formats vers un JSON normalisé (texte et métadonnées).
2. **Recherche sémantique** : une question en langage naturel renvoie les passages les plus proches, avec leur document et leur page.
3. **Assistant RAG local** : il répond uniquement à partir du corpus et cite ses sources. S'il ne trouve pas l'information, il répond « je ne sais pas ».
4. **Interface web** : un chat, une recherche et une consultation des sources.
5. **Tableau de bord** : répartition du corpus (formats, langues, années), termes dominants, carte 2D des embeddings, statistiques des requêtes.

### 1.4 Contraintes
- Tout fonctionne en local, avec des outils libres, sans API cloud payante.
- La stack est Python : FastAPI, ChromaDB (ou FAISS), sentence-transformers, Ollama, et Streamlit ou un front web.
- Le code est versionné avec Git, avec un commit par étape au minimum.
- La qualité est mesurée par les questions de validation de [`docs/questions_validation.md`](docs/questions_validation.md).

### 1.5 Critères de réussite
- Au moins 80 % des questions de validation obtiennent une réponse correcte et la bonne source.
- Toutes les questions « pièges » (hors corpus) obtiennent un refus explicite, sans invention.

---

## 2. Arborescence

```
webcognitive/
├── data/
│   ├── sources.json            # liste des sources (URL, format, métadonnées)
│   ├── corpus_metadata.json    # inventaire généré (taille, sha256, date)
│   ├── validation_questions.json # questions de validation, version machine (étape 3)
│   ├── raw/                    # documents bruts, jamais modifiés à la main
│   │   ├── pdf/  html/  docx/  txt/
│   ├── processed/              # un JSON propre par document (étape 2)
│   ├── embeddings/             # segments, vecteurs et évaluation (étape 3)
│   └── vectordb/               # base ChromaDB, régénérable, ignorée par Git (étape 4)
├── docs/
│   ├── questions_validation.md # questions dont la réponse est dans le corpus
│   ├── journal_audit.md        # notes de l'exploration manuelle
│   ├── etape2_parsing.md       # choix et résultats du parsing
│   ├── etape3_chunking_embeddings.md  # choix et résultats du chunking / des embeddings
│   ├── etape3_resultats.md     # tableau généré par l'évaluation
│   ├── etape4_api.md           # base vectorielle, recherche et API REST
│   ├── etape4_resultats.md     # évaluation de la recherche servie par l'API
│   ├── etape5_rag.md           # pipeline RAG, prompt, LLM local (Ollama)
│   └── etape6_interface.md     # interface web de chat avec les sources
├── scripts/
│   ├── download_corpus.py      # étape 1 : constitution reproductible du corpus
│   ├── parse_corpus.py         # étape 2 : extraction et nettoyage
│   ├── build_embeddings.py     # étape 3 : chunking et vectorisation
│   ├── evaluate_chunking.py    # étape 3 : comparaison tailles de segments / modèles
│   ├── search.py               # étape 3 : recherche sémantique de démonstration
│   ├── build_vectordb.py       # étape 4 : chargement dans ChromaDB
│   ├── serve_api.py            # étape 4 : lancement de l'API
│   ├── evaluate_search.py      # étape 4 : évaluation des modes de recherche
│   └── evaluate_rag.py         # étape 5 : évaluation des réponses du LLM
├── src/webcognitive/
│   ├── config.py               # chemins et paramètres retenus
│   ├── parsing/                # un parseur par format + nettoyage regex
│   ├── chunking.py             # découpage avec chevauchement
│   ├── embeddings.py           # vectorisation locale (sentence-transformers)
│   ├── indexing.py             # chaîne d'indexation (scripts et API)
│   ├── vectordb.py             # base vectorielle ChromaDB
│   ├── lexical.py              # recherche par mots-clés (BM25)
│   ├── search_engine.py        # recherche sémantique, mots-clés ou hybride
│   ├── rag.py                  # pipeline RAG : extraits + consigne -> LLM local (Ollama)
│   └── api.py                  # API REST (FastAPI) : /search, /ask… et service de l'interface
├── frontend/                   # interface web (étape 6) : index.html, style.css, app.js
├── tests/                      # tests automatiques (étapes 4, 5 et 6)
├── requirements.txt
└── README.md
```

## 3. Installation

```bash
python -m venv .venv
# Windows : .venv\Scripts\activate    |    Linux/macOS : source .venv/bin/activate
pip install -r requirements.txt

python scripts/download_corpus.py      # récupère les 41 documents
```

Le script n'écrase pas ce qui est déjà présent. Il signale les éventuels échecs, par exemple un site avec une protection anti-robots, et indique où déposer le fichier récupéré à la main. Relance-le ensuite : il complète l'inventaire.

```bash
python scripts/parse_corpus.py         # étape 2 : data/processed/<id>.json
python scripts/build_embeddings.py     # étape 3 : data/embeddings/ (télécharge le modèle au 1er lancement)
python scripts/search.py "Qui a inventé le DNS ?"
python scripts/evaluate_chunking.py    # étape 3 : comparaison des réglages (~15 min sur CPU)

python scripts/build_vectordb.py       # étape 4 : charge les vecteurs dans ChromaDB (data/vectordb/)
python scripts/serve_api.py            # étape 4 : API sur http://127.0.0.1:8000 (documentation : /docs)
python scripts/evaluate_search.py      # étape 4 : compare recherche sémantique, BM25 et hybride
python -m pytest tests -q              # tests automatiques
```

Exemple : http://127.0.0.1:8000/search?q=Qui%20a%20invent%C3%A9%20le%20DNS%20%3F&k=3

**LLM local (étapes 5 et 6).** Installe [Ollama](https://ollama.com/download), puis télécharge le modèle une fois :

```bash
ollama pull mistral                    # ≈ 4 Go ; plus léger : ollama pull llama3.2:3b puis WEBCOGNITIVE_LLM=llama3.2:3b
python scripts/serve_api.py            # interface web : http://127.0.0.1:8000/  (API : /docs)
python scripts/evaluate_rag.py         # étape 5 : évaluation des réponses sur les questions de validation
```

**OCR (facultatif).** Le PDF de Baran (`pdf04`) est un scan sans texte. Pour le lire, installe [Tesseract](https://github.com/UB-Mannheim/tesseract/wiki) puis `pip install pytesseract`, et relance `parse_corpus.py --only pdf04`.

## 4. Sources et licences
Les documents restent la propriété de leurs auteurs et éditeurs. Les notes DOCX sont dérivées de Wikipédia (licence CC BY-SA 4.0, source indiquée en tête de chaque fichier). Le corpus est utilisé à des fins strictement pédagogiques.

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
│   ├── raw/                    # documents bruts, jamais modifiés à la main
│   │   ├── pdf/  html/  docx/  txt/
│   └── processed/              # sorties du pipeline (étape 2)
├── docs/
│   ├── questions_validation.md # questions dont la réponse est dans le corpus
│   └── journal_audit.md        # notes de l'exploration manuelle
├── scripts/
│   └── download_corpus.py      # constitution reproductible du corpus
├── src/                        # code de l'application (étapes 2 et suivantes)
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

## 4. Sources et licences
Les documents restent la propriété de leurs auteurs et éditeurs. Les notes DOCX sont dérivées de Wikipédia (licence CC BY-SA 4.0, source indiquée en tête de chaque fichier). Le corpus est utilisé à des fins strictement pédagogiques.

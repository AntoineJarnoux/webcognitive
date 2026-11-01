# Étape 8 : finalisation, documentation et restitution

**Objectif :** consolider l'application, vérifier toute la chaîne, documenter l'installation et l'utilisation, et livrer un dépôt Git propre.

## 1. Recette : tests globaux de l'application

**Deux niveaux de tests :**

| Niveau | Outil | Ce qui est vérifié | Besoin d'Ollama ? |
|---|---|---|---|
| Tests unitaires et d'API | `python -m pytest tests -q` (34 tests) | chaque brique isolément, avec de faux modèles : découpage, base vectorielle, filtres, BM25, prompt, citations, refus, streaming, statistiques, service de l'interface | non |
| **Recette de bout en bout** | `python scripts/recette.py --validation` | l'application en marche, à travers l'API REST, comme l'utilise l'interface | oui |

**La recette** (`scripts/recette.py`) suit le parcours demandé par la fiche, de l'ingestion à la dataviz :

| Étape | Contrôles |
|---|---|
| 1. État | base remplie, Ollama répond, modèle téléchargé |
| 2. Ingestion | `POST /ingest` réindexe via l'API ; suivi jusqu'à « terminé » ; même nombre de segments ensuite |
| 3. Corpus | 41 documents, 4 formats ; texte d'un document par page ; segment et ses voisins ; 404 sur un document inconnu |
| 4. Recherche | le passage sur Mockapetris est trouvé dans les 3 modes ; les filtres sont respectés ; un paramètre invalide renvoie 422 |
| 5. RAG | réponse correcte avec sources (fichier + page/section) ; question hors corpus refusée ; flux NDJSON complet |
| 6. Dataviz | indicateurs, carte sémantique, questions comptabilisées, Plotly servi en local |
| 7. Interface | page d'accueil, `app.js`, `dashboard.js`, `style.css` |
| 8. Validation | **les 29 questions de l'étape 1** posées à l'application : succès ≥ 80 % et 100 % des pièges refusés |

Elle produit le rapport [etape8_recette.md](etape8_recette.md) : un tableau des contrôles réussis ou échoués, puis chaque question de validation avec la réponse obtenue et les sources affichées.

## 2. Précision des réponses (questions de validation)

Mesure faite avec `scripts/evaluate_rag.py` à l'étape 5 (Mistral 7B, recherche hybride, 8 extraits) :

| Mesure | Résultat | Objectif |
|---|---|---|
| Réponse correcte | 85 % | – |
| Source citée qui justifie la réponse | 81 % | – |
| **Succès (les deux)** | **81 %** | ≥ 80 % ✅ |
| **Pièges hors corpus refusés** | **100 %** | 100 % ✅ |

**Questions encore en échec :**
- **F04** : le modèle confond la date de publication (mai 1974) avec la date de réception du manuscrit (5 novembre 1973).
- **F08, F10** : le passage qui contient la réponse n'est pas parmi les 8 extraits retrouvés.
- **F07** : refusée à tort.

L'amélioration la plus utile serait donc du côté de la recherche, plutôt que du LLM.

## 3. Documentation
- **[README.md](../README.md)** : présentation du thème et du corpus, fonctionnalités, schéma d'architecture, structure du dépôt, **installation pas à pas** (environnement virtuel, dépendances, Ollama, préparation des données, lancement de FastAPI et de l'interface), API, résultats, tests, configuration, limites.
- **[manuel_utilisateur.md](manuel_utilisateur.md)** : utilisation de l'interface (assistant, sources, recherche, tableau de bord), lecture du voyant d'état, résolution des problèmes courants.
- **Une documentation par étape** (`docs/etape2_…` à `docs/etape7_…`) : les choix techniques, leur justification et les mesures.
- **Dans le code** : chaque module commence par un commentaire qui explique son rôle, et chaque réglage de `config.py` est justifié.

## 4. Nettoyage du code et du dépôt
- **Une chaîne d'indexation unique** (`indexing.py`), utilisée à la fois par les scripts et par l'API (`POST /ingest`) : pas de code en double.
- **Tous les réglages au même endroit** (`config.py`), avec la raison de chaque valeur.
- **Les fichiers régénérables ne sont pas versionnés** (`.gitignore`) :
  - les vecteurs (`embeddings.npy`) ;
  - la base ChromaDB ;
  - le journal des questions ;
  - la page autonome de la carte ;
  - l'environnement virtuel et les caches Python.
- **Le corpus brut est versionné octet pour octet** (`.gitattributes`) : les empreintes SHA-256 restent valables après un clone.
- **Les tests tournent sans service externe** : faux modèle d'embedding, faux LLM et journal temporaire.
- **Historique Git** : au moins un commit par étape, avec des messages qui décrivent le contenu.

## 5. Correspondance avec la fiche

| Demande de la fiche | Réalisation |
|---|---|
| Recette et tests globaux, de l'ingestion via l'API à la dataviz | `scripts/recette.py` (étapes 1 à 7), tests `pytest` |
| Exécuter les questions de validation de l'étape 1, mesurer la précision et la justesse des sources | `scripts/recette.py --validation`, `scripts/evaluate_rag.py` : 81 % de succès, 100 % des pièges refusés |
| README complet : thématique, architecture, installation pas à pas (venv, Ollama, FastAPI, front-end) | [README.md](../README.md), § 1 à 5 |
| Manuel d'utilisation et spécification technique en Markdown | [manuel_utilisateur.md](manuel_utilisateur.md) ; README § 3, 7 et 10, et les documents par étape |
| Nettoyage du code et engagement final sur Git | § 4 ci-dessus ; commit final poussé sur GitHub |

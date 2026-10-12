# Étape 4 : base vectorielle (ChromaDB) et API REST (FastAPI)

**Objectif :** ranger les segments vectorisés de l'étape 3 dans une vraie base de données vectorielle, puis exposer la recherche par une API REST que le front (étape 6) et le RAG (étape 5) pourront appeler.

```bash
python scripts/build_vectordb.py        # charge data/embeddings/ dans ChromaDB (≈ 5 s)
python scripts/serve_api.py             # lance l'API : http://127.0.0.1:8000/docs
python scripts/evaluate_search.py       # évalue la recherche servie par l'API (≈ 1 min)
python -m pytest tests -q               # tests automatiques (sans le modèle)
```

## 1. Architecture

```
data/embeddings/ (étape 3)                 data/processed/ (étape 2)
  chunks.jsonl + embeddings.npy                 un JSON par document
          │                                          │
          ▼  build_vectordb.py                       │
   data/vectordb/  (ChromaDB)                        │
          │                                          │
          ▼                                          ▼
   search_engine.py  ── recherche sémantique (ChromaDB) + mots-clés (BM25) + catalogue
          │
          ▼
   api.py (FastAPI)  ── /search  /documents  /chunks  /ingest  /health
```

| Fichier | Rôle |
|---|---|
| `src/webcognitive/vectordb.py` | création de la collection ChromaDB, filtres, requêtes |
| `src/webcognitive/lexical.py` | recherche par mots-clés BM25 |
| `src/webcognitive/search_engine.py` | réunit les deux recherches et le catalogue des documents |
| `src/webcognitive/indexing.py` | chaîne d'indexation, partagée par les scripts et par `POST /ingest` |
| `src/webcognitive/api.py` | les routes de l'API |
| `scripts/build_vectordb.py`, `serve_api.py`, `evaluate_search.py` | points d'entrée |
| `tests/test_api.py` | 17 tests automatiques |

## 2. La base vectorielle : ChromaDB

**Pourquoi ChromaDB plutôt que FAISS ?** FAISS ne stocke que des vecteurs : il faudrait gérer à côté les textes et les métadonnées. ChromaDB garde ensemble, pour chaque segment, son **identifiant**, son **vecteur**, son **texte** et ses **métadonnées** (document, page ou section, format, langue, année). Elle s'enregistre sur disque (`data/vectordb/`) et permet de **filtrer** sur les métadonnées pendant la recherche.

**Choix faits :**
- **On réutilise les vecteurs de l'étape 3** (`embedding_function=None`) : ChromaDB ne recalcule rien, l'indexation prend 5 secondes au lieu de 11 minutes.
- **Le manifeste de l'étape 3 est enregistré avec la collection** : l'API sait ainsi avec quel modèle vectoriser la question. Une question vectorisée avec un autre modèle ne serait pas comparable aux segments.
- **Distance cosinus** (`hnsw:space = cosine`), la mesure de l'étape 3. ChromaDB renvoie une distance `d = 1 − cosinus`, que l'on reconvertit en score.
- **Index HNSW** : ChromaDB ne compare pas la question aux 5 751 segments. Il parcourt un graphe de voisinage, ce qui est beaucoup plus rapide, mais **approché**. Test sur 200 requêtes : **99,75 %** des segments du top 10 sont les mêmes que ceux du calcul exact de l'étape 3.
- **Les valeurs absentes sont omises**, parce que ChromaDB refuse les métadonnées `None` (exemple : pas de page pour un HTML).
- **La collection est recréée à chaque indexation**, pour ne pas garder de segments d'un ancien découpage.

## 3. La recherche : trois modes

| Mode | Principe | Points forts | Limites |
|---|---|---|---|
| `semantic` (par défaut) | La question est vectorisée, puis ChromaDB renvoie les segments les plus proches | Comprend le sens, même d'une langue à l'autre | Rate les questions qui citent un nom (« selon Clark ») |
| `lexical` | **BM25** : score par mots communs ; un mot rare (« Mockapetris ») compte beaucoup plus qu'un mot courant (« réseau ») | Noms propres, sigles, dates | Ne comprend pas le sens et ne traduit pas |
| `hybrid` | On prend les 50 meilleurs de chaque méthode et on **fusionne leurs rangs** : score = Σ 1 / (60 + rang) | Combine les deux | Un peu plus lent |

**Pourquoi fusionner les rangs et non les scores ?** Un cosinus est compris entre −1 et 1, alors qu'un score BM25 n'a pas de borne. Les additionner n'aurait pas de sens. La fusion par rangs (*Reciprocal Rank Fusion*) ne regarde que les positions dans chaque liste.

Le BM25 a été ajouté parce que l'étape 3 montrait que les questions citant un auteur échouaient (F03, F05, F07, F10). Avant de comparer les mots, on passe tout en minuscules, on retire les accents et on retire les mots vides (« le », « de », « the »…).

**Filtres** (sur les métadonnées) : `doc_id`, `format`, `lang`, `year_min`, `year_max`. Exemple : `lang=fr&year_max=1990`. En sémantique, le filtre est appliqué par ChromaDB (clause `where`). En BM25, la même règle est appliquée en Python.

## 4. L'API REST (FastAPI)

FastAPI valide automatiquement les paramètres. Par exemple, `k=0` ou `lang=de` renvoient une erreur 422 qui explique le problème. FastAPI génère aussi une **documentation interactive** sur `/docs`, où l'on peut essayer chaque route.

| Méthode | Route | Rôle |
|---|---|---|
| GET | `/health` | état : nombre de segments indexés, modèle, date de l'index |
| GET | `/documents?format=&lang=` | catalogue des 41 documents, avec le nombre de segments indexés pour chacun |
| GET | `/documents/{doc_id}?include_text=true` | un document, avec son texte nettoyé par page ou section |
| GET | `/chunks/{chunk_id}` | un segment et ses voisins (`previous`, `next`) pour relire le contexte |
| GET | `/search?q=…&k=5&mode=semantic` | recherche, avec filtres possibles |
| POST | `/search` | même recherche, avec les paramètres dans un corps JSON (plus pratique pour le front) |
| POST | `/ingest` `{"reembed": false}` | relance l'indexation en **tâche de fond** (`reembed: true` refait aussi l'étape 3) |
| GET | `/ingest` | suivi de l'indexation : `running`, `done` ou `error` |

Exemple de réponse de `GET /search?q=Qui a inventé le DNS ?&k=1` :

```json
{
  "query": "Qui a inventé le DNS ?", "mode": "semantic", "k": 1, "filters": {}, "took_ms": 21.4, "count": 1,
  "results": [{
    "rank": 1, "chunk_id": "html01_0087", "score": 0.769,
    "text": "Le système Domain Name System (DNS) fut alors inventé par Paul Mockapetris de l'USC/ISI. …",
    "doc_id": "html01", "filename": "isoc_bref_historique_internet_fr.html", "format": "html",
    "title": "Bref historique de l'Internet (traduction française)", "author": "Internet Society (Leiner et al.)",
    "year": 1997, "lang": "fr", "page": null, "section": "Démontrer les idées",
    "location": "§ Démontrer les idées", "citation": "isoc_bref_historique_internet_fr.html, § Démontrer les idées"
  }]
}
```

Chaque résultat porte sa **source** (document, page ou section, citation prête à afficher). C'est ce qui permettra au RAG de l'étape 5 de citer ses sources.

**Démarrage :** au lancement, l'API charge le modèle d'embedding (quelques secondes) pour que la première question soit rapide. Si la base est vide, les routes de recherche renvoient 503 avec la commande à lancer.

## 5. Tests

`tests/test_api.py` contient 17 tests qui tournent **sans le vrai modèle**. Ils utilisent un petit corpus de 3 documents et un « faux modèle » qui vectorise les mots par hachage. Ils vérifient :
- que ChromaDB renvoie les mêmes scores que le calcul exact ;
- que les filtres sont respectés dans les trois modes ;
- que BM25 retrouve un nom propre ;
- le format des réponses, la citation, les voisins d'un segment ;
- les erreurs 404, 422 et 503 ;
- l'indexation en tâche de fond.

## 6. Résultats

Les résultats détaillés sont dans [etape4_resultats.md](etape4_resultats.md), généré par `scripts/evaluate_search.py`. On utilise les mêmes 26 questions et le même critère qu'à l'étape 3 : la réponse **et** le bon document dans les 5 premiers segments.

| Mode | Succès@5 | Réponse@5 | MRR@10 |
|---|---|---|---|
| Sémantique (étape 3, calcul exact) | 54 % | 81 % | 0,40 |
| **Sémantique (ChromaDB)** | **54 %** | **81 %** | **0,40** |
| Mots-clés (BM25) | 46 % | 69 % | 0,38 |
| Hybride (fusion des rangs) | 58 % | 77 % | 0,42 |

**Ce qu'on en retient :**
- **ChromaDB ne dégrade rien.** Sur les questions de validation, son top 10 est identique à 100 % à celui du calcul exact de l'étape 3, et les scores sont les mêmes.
- **BM25 seul est moins bon** (46 %), mais il ne réussit pas les mêmes questions : il trouve F02, F12 et F17 grâce aux mots « 1983 », « IMP » et « Mitranet ».
- **L'hybride gagne une question au critère strict** (58 % contre 54 %, MRR 0,42 contre 0,40), mais en perd une en réponse@5 (77 % contre 81 %). Avec 26 questions, un écart d'une question (4 points) **n'est pas significatif**.
- **Décision :** le mode par défaut reste `semantic`, le plus simple. Le mode `hybrid` reste disponible, et on refera la comparaison à l'étape 5 sur les réponses finales du LLM, qui sont le vrai critère du projet.

## 7. Limites et suite
- **Les pièges ne sont pas filtrés ici** : la recherche renvoie toujours les segments « les moins éloignés ». Le refus (« je ne sais pas ») viendra du LLM à l'étape 5.
- **BM25 ne traduit pas** : une question en français trouve mal un passage en anglais, sauf pour les noms propres et les dates.
- **L'index BM25 est en mémoire**, reconstruit au démarrage en 1 à 2 secondes. C'est suffisant pour 5 751 segments.
- **Étape 5 :** une route `POST /ask` prendra les k meilleurs segments de `/search` et les donnera à un LLM local (Ollama) avec la consigne de répondre uniquement à partir de ces passages et de citer leur `citation`.

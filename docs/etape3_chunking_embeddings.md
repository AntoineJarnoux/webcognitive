# Étape 3 : chunking et vectorisation locale

**Objectif :** découper le texte nettoyé de l'étape 2 en segments de taille contrôlée, avec chevauchement, puis transformer chaque segment en vecteur à l'aide d'un modèle d'embedding exécuté en local. Ces vecteurs permettront une recherche **par le sens** (recherche sémantique) et non par mots-clés.

```bash
python scripts/build_embeddings.py                      # construit l'index (≈ 10 min sur CPU)
python scripts/search.py "Qui a inventé le DNS ?"       # recherche de démonstration
python scripts/evaluate_chunking.py --sizes 300 500 800 # test des réglages
```

## 1. Le chunking (`src/webcognitive/chunking.py`)

### Pourquoi découper ?
- Une question porte sur un fait précis. Comparée à un document entier de 180 pages, elle serait noyée.
- Les modèles d'embedding ne lisent qu'une fenêtre limitée : 128 tokens pour le modèle retenu, soit environ 500 caractères. Au-delà, la fin du texte est ignorée.
- C'est le segment, et non le document, qui sera cité et donné au LLM à l'étape 5.

### L'algorithme
1. Les unités d'un document (pages ou sections, issues de l'étape 2) sont mises bout à bout. On mémorise la position de départ de chacune.
2. On avance par pas d'environ `size` = **500 caractères** :
   - on coupe de préférence **à une fin de phrase** située dans la seconde moitié du segment ;
   - sinon, on coupe **entre deux mots** ;
   - on ne coupe jamais au milieu d'un mot.
3. **Chevauchement (overlap) de 100 caractères.** Le segment suivant repart d'un **début de phrase** situé dans les 100 derniers caractères du précédent. S'il n'y en a pas, il remonte au début de phrase juste avant, avec au plus 200 caractères de chevauchement. En dernier recours, il repart d'un début de mot. Une phrase coupée à la frontière se trouve ainsi entière dans au moins un segment.
4. Les initiales et abréviations (« J.C.R. Licklider », « Fig. 1 », « et al. ») ne sont pas prises pour des fins de phrase.
5. Un dernier segment de moins de 100 caractères est rattaché au précédent, pour éviter les segments sans contexte.
6. **Chaque segment garde sa provenance** : document, page ou section de départ et de fin, positions dans le texte, titre, auteur, année et langue.

Exemple de segment (`data/embeddings/chunks.jsonl`) :
```json
{"chunk_id": "pdf06_0055", "doc_id": "pdf06", "chunk_index": 55,
 "text": "Perhaps the oldest and most widely known form of the argument concerns acknowledgement of delivery. […] The ARPANET, for example, returns a packet known as \"Request For Next Message\" (RFNM)[1] whenever it delivers a message.",
 "char_start": 16788, "char_end": 17132, "page": 5, "page_end": 5, "section": null,
 "filename": "saltzer_reed_clark_1984_end_to_end.pdf", "format": "pdf",
 "title": "End-to-End Arguments in System Design", "author": "J.H. Saltzer, D.P. Reed, D.D. Clark",
 "lang": "en", "year": 1984}
```

## 2. La vectorisation (`src/webcognitive/embeddings.py`)

- **Bibliothèque :** `sentence-transformers` (Hugging Face), exécuté **sur le CPU**. Le modèle est téléchargé une fois dans le cache local, puis tout fonctionne sans connexion.
- **Résultat :** chaque segment devient un vecteur de **384 nombres**. Des textes de sens proche donnent des vecteurs proches, même s'ils n'emploient pas les mêmes mots ou la même langue.
- **Normalisation :** les vecteurs sont ramenés à une **norme de 1**. Le produit scalaire (`matrice @ vecteur_question`, avec numpy) donne alors directement la **similarité cosinus**, entre -1 et 1.
- **Sorties :**
  - `chunks.jsonl` : les segments et leurs métadonnées, une ligne par segment ;
  - `embeddings.npy` : la matrice des vecteurs (nombre de segments × 384), dans le même ordre ;
  - `manifest.json` : le modèle et les réglages utilisés. La question doit être vectorisée exactement de la même manière que les segments.

## 3. Test et optimisation (`scripts/evaluate_chunking.py`)

### Méthode
Les 26 questions de validation de l'étape 1 sont reprises dans `data/validation_questions.json`. Pour chacune, on note les documents attendus et une expression régulière qui reconnaît la réponse (par exemple `Mockapetris`). Pour chaque réglage :
1. on découpe et on vectorise tout le corpus ;
2. on vectorise chaque question et on prend les 10 segments les plus proches ;
3. on calcule plusieurs mesures :

| Mesure | Signification |
|---|---|
| **Succès@5** | Un des 5 premiers segments contient la réponse **et** vient d'un document attendu. C'est le critère le plus strict, proche du critère de réussite du projet (« la bonne réponse avec la bonne source »). |
| Réponse@5 | Un des 5 premiers segments contient la réponse, quel que soit le document. Le corpus répète certains faits : la date de 1983 est aussi dans la note sur l'histoire d'Internet. |
| Doc@5 | Un des 5 premiers segments vient d'un document attendu. |
| MRR@10 | Moyenne de 1/rang de la première bonne réponse : 1 si elle est 1re, 0,5 si elle est 2e… |
| Score des pièges | Similarité du meilleur segment pour les questions hors corpus (P01 à P03). |

### Réglages comparés
- **Tailles de segment :** 250, 300, 500, 800 et 1 200 caractères, avec 20 % de chevauchement.
- **Trois modèles de 384 dimensions :**
  - `all-MiniLM-L6-v2` : le modèle cité dans la fiche, entraîné **sur de l'anglais** ;
  - `paraphrase-multilingual-MiniLM-L12-v2` : la même famille, **multilingue** (plus de 50 langues) ;
  - `multilingual-e5-small` : multilingue, avec les préfixes `query:` et `passage:`.
- **Deux variantes :**
  - un **en-tête contextuel** : on ajoute « titre (auteur, année) » avant chaque segment vectorisé ;
  - une **fenêtre de 256 tokens** au lieu de 128.

Les résultats complets sont dans [etape3_resultats.md](etape3_resultats.md). Résumé :

| Réglage | Succès@5 | Réponse@5 | MRR@10 |
|---|---|---|---|
| all-MiniLM-L6-v2 (fiche), 500 car. | 42 % | 54 % | 0,31 |
| all-MiniLM-L6-v2, 1 200 car. | 27 % | – | 0,24 |
| **paraphrase-multilingual-MiniLM-L12-v2, 500 car.** | **54 %** | **81 %** | **0,40** |
| même modèle, 300 car. | 46 % | – | 0,37 |
| même modèle, 800 car. | 42 % | – | 0,38 |
| même modèle, 500 car. + en-tête | 46 % | 77 % | 0,37 |
| même modèle, 500 car. + en-tête + 256 tokens | 38 % | 69 % | 0,31 |
| multilingual-e5-small, 800 car. | 50 % | 69 % | 0,42 |
| multilingual-e5-small, 800 car. + en-tête | 50 % | 81 % | 0,44 |

### Ce qu'on en retient
1. **Un modèle multilingue est nécessaire.** Les questions sont en français et 24 documents sur 41 sont en anglais. Le modèle de la fiche, entraîné sur de l'anglais, rapproche mal une question française d'un passage anglais : 42 % contre 54 % de succès@5, et 54 % contre 81 % de réponse@5.
2. **La taille de segment a un optimum autour de 500 caractères.** C'est l'effet décrit dans la fiche :
   - **segments trop petits** (250-300) : ils manquent de contexte (« *il* fut installé en 1969 ») ;
   - **segments trop grands** (800-1 200) : ils mélangent plusieurs idées et dépassent la fenêtre du modèle. Avec le modèle multilingue, 95 % des segments de 800 caractères sont **tronqués** : sa fenêtre de 128 tokens fait environ 500 caractères. Avec le modèle de la fiche, on tombe à 27 % de succès à 1 200 caractères.
3. **Élargir la fenêtre à 256 tokens dégrade les résultats.** Le modèle a été entraîné sur des textes de 128 tokens au plus : la taille de segment doit s'adapter au modèle, pas l'inverse.
4. **L'en-tête contextuel n'apporte rien de mesurable ici.** Il aide e5-small en réponse@5 (69 % → 81 %), mais pas le modèle retenu. Il reste disponible en option (`EMBEDDING_HEADER`).
5. **Un seuil de similarité ne suffira pas à refuser les questions hors corpus.** Avec le modèle retenu, la question piège sur QUIC (un protocole réseau récent) obtient 0,69, autant que la moyenne des vraies questions. La capitale de l'Australie obtient seulement 0,30. Un seuil bas éliminera les questions franchement hors sujet, mais le refus des questions proches du thème devra être assuré par le LLM à l'étape 5, avec une consigne « réponds uniquement à partir des passages fournis ».

### Réglages retenus (`src/webcognitive/config.py`)
| Paramètre | Valeur |
|---|---|
| Modèle | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384 dimensions, 128 tokens) |
| Taille des segments | 500 caractères |
| Chevauchement | 100 caractères |
| Taille minimale | 100 caractères |
| En-tête contextuel | non |

### Résultat
Index final : **40 documents → 5 751 segments** (428 caractères en moyenne, de 117 à 499), soit une matrice de **5 751 × 384**, vectorisée en 11 minutes sur CPU. Le 41e document, le scan de Baran, est vide tant qu'il n'est pas passé à l'OCR.

```
$ python scripts/search.py "Qui a inventé le DNS ?" -k 2
1. [0.769] isoc_bref_historique_internet_fr.html (§ Démontrer les idées)
   Le système Domain Name System (DNS) fut alors inventé par Paul Mockapetris de l'USC/ISI. …
2. [0.655] note_histoire_d_internet.docx (§ Network Information Center et autres autorités de coordination)
   Une solution technique apparut sous la forme de Domain Name System […], mis en place par Paul Mockapetris. …
```

## 4. Limites et pistes
- **L'évaluation est petite** : 26 questions. Un écart de 2 questions représente 8 points. Les écarts inférieurs à 10 points ne sont donc pas significatifs. Il faudrait enrichir le jeu de questions, ce qui est prévu pour l'étape 8.
- **Le critère strict pénalise les bonnes réponses trouvées ailleurs.** Plusieurs « échecs » de succès@5 sont des réponses justes trouvées dans un autre document :
  - F01 : la RFC 2555 dit que la RFC 1 a été écrite par Steve Crocker le 7 avril 1969 ;
  - F02 : la note sur l'histoire d'Internet donne le 1er janvier 1983 ;
  - F12 : le livre de Hauben cite l'installation du premier IMP à UCLA ;
  - F18 : la biographie de Berners-Lee donne le 13 mars 1989.

  Les documents attendus pourront être complétés dans `validation_questions.json`.
- **Les questions qui citent un auteur échouent souvent** (F03, F05, F07, F10 : « selon Clark », « Saltzer et al. »). Le segment qui contient la réponse ne mentionne pas l'auteur. À l'étape 4, on pourra **filtrer par document** grâce aux métadonnées, ou combiner la recherche sémantique avec une recherche par mots-clés (BM25).
- **F09 échoue forcément** tant que le PDF de Baran n'est pas passé à l'OCR (étape 2).
- **Le temps de calcul est d'environ 5 à 10 minutes** pour vectoriser tout le corpus sur CPU. Les temps du tableau de résultats sont approximatifs : certains tests ont tourné en parallèle.

## 5. Vers l'étape 4
Les fichiers `chunks.jsonl` et `embeddings.npy` seront chargés dans une base vectorielle locale (ChromaDB). Les métadonnées de chaque segment (document, page, langue, année) permettront de filtrer les recherches, et une API REST (FastAPI) exposera `/search`.

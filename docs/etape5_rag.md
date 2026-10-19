# Étape 5 : recherche sémantique et pipeline RAG avec un LLM local

**Objectif :** répondre à une question en langage naturel **uniquement à partir du corpus**, en citant les sources, et dire « je ne sais pas » quand l'information n'y est pas.

```bash
ollama pull mistral                     # une fois : télécharge le LLM (≈ 4 Go)
python scripts/serve_api.py             # l'API expose POST /ask
python scripts/evaluate_rag.py          # évaluation sur les questions de validation
```

## 1. Le principe

```
question ──► recherche (étape 4) ──► 8 extraits numérotés [1]…[8], chacun avec sa source
                                          │
       consigne + extraits + question ──► LLM local (Ollama) ──► réponse avec [1], [3]…
                                                                    │
                                     numéros cités ──► fichier + page affichés sous la réponse
```

1. **Recherche (retrieval)** : la question est vectorisée, puis on garde les **8 extraits** les plus pertinents (top-k). La recherche combine la **similarité cosinus** dans ChromaDB et les mots-clés (BM25), avec le mode `hybrid` de l'étape 4.
2. **Augmentation** : ces extraits sont insérés dans le prompt, numérotés et accompagnés de leur source.
3. **Génération** : le LLM rédige la réponse à partir de ces extraits seulement.

Code : `src/webcognitive/rag.py` (pipeline), route `POST /ask` dans `src/webcognitive/api.py`.

## 2. Le LLM local : Ollama + Mistral

- **[Ollama](https://ollama.com)** fait tourner des LLM open source sur la machine et les expose par une petite API HTTP locale (`http://127.0.0.1:11434`). Aucun service cloud, aucune clé.
- **Modèle par défaut : `mistral`** (Mistral 7B, ≈ 4 Go, environ 8 Go de RAM). Il est bon en français. Variable `WEBCOGNITIVE_LLM` pour en changer, par exemple `llama3.2:3b`, plus léger et plus rapide sur un PC modeste.
- **Réglages** (`config.py`) :
  - `temperature = 0.1` : réponses factuelles et stables, peu d'« imagination » ;
  - `num_ctx = 4096` tokens : assez pour la consigne, 8 extraits (≈ 1 100 tokens) et la question.
- La réponse est **envoyée au fil de l'eau** (streaming) : l'interface affiche les mots à mesure qu'ils sont écrits.

## 3. Le prompt (prompt engineering)

**Consigne système** (extrait) :

> Tu réponds à la question en t'appuyant UNIQUEMENT sur les extraits numérotés du CONTEXTE.
> 1. N'utilise jamais tes connaissances personnelles.
> 2. Si les extraits ne contiennent pas la réponse, réponds exactement : « Je ne sais pas : cette information n'est pas dans le corpus. »
> 3. Réponds en français, même si les extraits sont en anglais.
> 4. Après chaque information, indique entre crochets le numéro de l'extrait qui la justifie, par exemple [2].
> 5. N'affirme que ce qui est écrit explicitement dans un extrait : ne déduis pas une date, un auteur ou un lieu qui n'y figure pas.

**Message de l'utilisateur** construit par le code :

```
CONTEXTE :
[1] Source : isoc_bref_historique_internet_fr.html, § Démontrer les idées — Bref historique de l'Internet (ISOC, 1997)
Le système Domain Name System (DNS) fut alors inventé par Paul Mockapetris…
[2] Source : rfc1034_domain_names_concepts.txt, p. 1 — RFC 1034 …
…
QUESTION : Qui a inventé le DNS ?
```

**Pourquoi ces choix :**
- **Numéroter les extraits** permet au LLM de citer précisément, et au code de retrouver les sources citées (`[1]` → fichier + page).
- **Imposer une phrase de refus exacte** permet de détecter le refus automatiquement.
- **Donner la source avec chaque extrait** aide le LLM à distinguer les documents (« selon Clark »).

## 4. Trois protections contre les inventions

| Protection | Rôle |
|---|---|
| La consigne | interdit les connaissances extérieures et impose « je ne sais pas » |
| Les citations | chaque information renvoie à un extrait vérifiable ; les numéros inventés (ex. `[9]` sur 5 extraits) sont ignorés |
| Le garde-fou | si le meilleur extrait a un cosinus < 0,35, la question est hors sujet : refus **sans appeler le LLM** |

Le seuil de 0,35 vient de l'étape 3 : la plus faible des vraies questions obtient 0,53, la question « capitale de l'Australie » 0,30. Il n'arrête que les questions franchement hors sujet. Pour les questions proches du thème (QUIC : 0,69), c'est la consigne qui fait refuser.

## 5. La route `POST /ask`

```json
POST /ask
{"question": "Qui a inventé le DNS ?", "k": 8, "mode": "hybrid", "stream": false}
```

Réponse :

```json
{
  "answer": "Le DNS a été inventé par Paul Mockapetris, de l'USC/ISI [1]. …",
  "refused": false, "guard": false, "cited": [1, 2],
  "sources": [{"number": 1, "cited": true, "filename": "isoc_bref_historique_internet_fr.html",
               "location": "§ Démontrer les idées", "page": null, "text": "…", "score": 0.77}, …],
  "model": "mistral", "retrieval_ms": 25, "total_ms": 6800
}
```

Avec `"stream": true`, la réponse arrive en **NDJSON** (une ligne JSON par événement) : d'abord les sources, puis les morceaux de texte (`token`), enfin `done` avec la réponse complète et les citations. C'est ce qu'utilise l'interface de l'étape 6.

Mêmes filtres qu'à l'étape 4 (`lang`, `format`, `doc_id`, `year_min`, `year_max`). Si Ollama n'est pas lancé, l'API renvoie 503 avec la commande à exécuter. `GET /health` indique si Ollama répond et si le modèle est téléchargé.

## 6. Tests et évaluation

- **Tests automatiques** (`tests/test_rag.py`) : un « faux LLM » remplace Ollama. On vérifie la consigne, la numérotation, la lecture des citations, le refus, le garde-fou (le LLM n'est pas appelé), le streaming et l'erreur quand Ollama est absent.
- **Évaluation** (`scripts/evaluate_rag.py`) : les 29 questions de validation passent par le pipeline complet. Pour chaque question, on vérifie :
  - **réponse correcte** : la réponse contient l'information attendue (`rag_pattern` dans `data/validation_questions.json`) ;
  - **bonne source** : un extrait cité justifie la réponse, c'est-à-dire qu'il vient d'un document attendu ou contient lui-même l'information (le corpus répète certains faits : 1983 apparaît dans trois documents) ;
  - **pièges** : les 3 questions hors corpus doivent recevoir « je ne sais pas ».

Critère du projet : **au moins 80 %** de réponses correctes avec la bonne source, **100 %** des pièges refusés. Résultats complets : [etape5_resultats.md](etape5_resultats.md).

| Réglage (LLM Mistral 7B) | Réponse correcte | Bonne source | **Succès** | Pièges refusés |
|---|---|---|---|---|
| recherche par le sens, 5 extraits | 73 % | 85 % | 73 % | 100 % |
| **recherche hybride, 8 extraits (retenu)** | **85 %** | **81 %** | **81 %** | **100 %** |

**Ce qu'on en retient :**
- **Les deux critères du projet sont atteints** avec le réglage retenu : 81 % de succès (objectif 80 %) et les 3 pièges refusés.
- **La recherche limite le LLM.** Avec 5 extraits trouvés par le sens seul, le bon passage manquait pour « selon Clark » (F05), « Mitranet » (F17) ou la RFC 2468 (F20). Le mode hybride (mots-clés) et 8 extraits les retrouvent.
- **La consigne fonctionne.** Quand l'extrait manque, Mistral répond le plus souvent « je ne sais pas » (F07). Les pièges sont tous refusés : la capitale de l'Australie par le garde-fou, Google et QUIC par le LLM.
- **Erreurs restantes** :
  - une date mal lue (F04 : « mai 1974 », la date de publication, au lieu du 5 novembre 1973) ;
  - deux questions dont le passage n'est pas retrouvé (F08, F10) ;
  - F07, refusé à tort.
  Pour aller plus loin, il faudrait améliorer la recherche (re-classement des extraits) plutôt que le LLM.

## 7. Limites
- **Chaque question est traitée seule** : l'assistant ne se souvient pas de la question précédente (« et lui, quand est-il né ? » ne marche pas).
- **La qualité dépend de la recherche** : si le bon extrait n'est pas dans les 5 premiers (54 % de succès@5 à l'étape 4), le LLM ne peut pas le deviner. Il doit alors dire « je ne sais pas », mais un petit modèle peut s'en écarter.
- **Vitesse** : sur CPU, Mistral 7B met quelques secondes à quelques dizaines de secondes par réponse. `llama3.2:3b` est plus rapide mais moins précis.

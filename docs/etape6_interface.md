# Étape 6 : interface web (front-end)

**Objectif :** dialoguer avec le moteur RAG dans le navigateur, en voyant **sous chaque réponse les sources exactes** (fichier et page).

```bash
python scripts/serve_api.py     # puis ouvrir http://127.0.0.1:8000/
```

## 1. Choix technique : HTML, CSS et JavaScript, sans framework

| Option | Pour | Contre |
|---|---|---|
| Streamlit / Gradio | très rapide, 100 % Python | appelle le code Python directement, et non l'API ; mise en page peu personnalisable |
| **HTML5 + CSS3 + JavaScript (fetch)** ✅ | utilise vraiment l'API REST ; aucune dépendance ni compilation ; contrôle total sur l'affichage des sources | plus de code à écrire |

L'interface est faite de **3 fichiers statiques** dans `frontend/` (`index.html`, `style.css`, `app.js`). **FastAPI les sert lui-même** sur `/app/` (et `/` y renvoie). Comme la page et l'API ont la même adresse, il n'y a pas de problème de CORS et un seul programme à lancer.

## 2. Ce que fait l'interface

```
┌ WebCognitive Engine ─────────────────────── ● 40 documents · 5751 extraits · LLM mistral ┐
│ [Assistant]  Recherche dans le corpus                                                     │
├────────────────────────────────────────────────────┬──────────────────────────────────────┤
│                         Qui a inventé le DNS ? ▐   │ Sources                              │
│ ┌────────────────────────────────────────────┐     │ Citées dans la réponse               │
│ │ Le DNS a été inventé par Paul Mockapetris  │     │ ┃[1] isoc_bref_historique….html      │
│ │ de l'USC/ISI [1]…                          │     │ ┃ § Démontrer les idées              │
│ └────────────────────────────────────────────┘     │ ┃ « Le système DNS fut inventé… »    │
│ mistral · 2 source(s) citée(s) · 6,8 s             │ ┃ Voir le contexte                   │
│ ┌ Votre question…                   [Envoyer] ┐    │ ▸ Extraits consultés mais non cités  │
│ Recherche [par le sens]  Extraits [5]  Langue [toutes]                                    │
└────────────────────────────────────────────────────┴──────────────────────────────────────┘
```

- **Zone de dialogue** : on tape une question (Entrée pour envoyer, Maj + Entrée pour aller à la ligne), ou on clique une question d'exemple. La réponse s'écrit **mot à mot**.
- **Traçabilité** :
  - chaque `[n]` de la réponse devient un bouton qui fait défiler jusqu'à l'extrait ;
  - le panneau **Sources** affiche, pour chaque extrait cité, le **nom du fichier** et la **page** (ou la section pour un HTML ou un DOCX), le document, l'auteur, l'année et le texte ;
  - « Voir le contexte » affiche les extraits voisins, l'extrait cité étant surligné ;
  - les extraits transmis au LLM mais non cités restent consultables, repliés.
- **Refus** : « Je ne sais pas » s'affiche avec une marge orange, et le panneau explique qu'aucun extrait ne contenait la réponse.
- **Options** : mode de recherche (sens, sens + mots-clés, mots-clés), nombre d'extraits, langue des sources.
- **Onglet Recherche** : la recherche seule (`GET /search`, étape 4), sans LLM, avec le score de chaque passage.
- **État** en haut à droite (`GET /health`) : nombre d'extraits indexés, et si Ollama et le modèle sont prêts. En cas de problème, il affiche la commande à lancer.

## 3. La connexion asynchrone à l'API

| Action | Requête |
|---|---|
| poser une question | `POST /ask` avec `"stream": true` |
| voir le contexte d'un extrait | `GET /chunks/{id}`, puis ses voisins `previous` / `next` |
| onglet Recherche | `GET /search?q=…&k=10&mode=…` |
| état du système | `GET /health` |

**Le streaming** : `fetch` renvoie la réponse sous forme de flux. `app.js` le lit morceau par morceau (`response.body.getReader()`), découpe les lignes et traite chaque événement JSON :

1. `sources` : les extraits trouvés s'affichent tout de suite dans le panneau ;
2. `token` : un morceau de texte, ajouté à la réponse en cours ;
3. `done` : la réponse finale, les numéros cités et les sources marquées « citées » ;
4. `error` : par exemple si Ollama n'est pas lancé. Le message dit quoi faire.

La page ne se recharge jamais : tout est mis à jour en JavaScript.

## 4. Design
- **Thème inspiré des documents du corpus** : un en-tête façon RFC, des extraits présentés comme des fiches d'archive sur un fond rappelant le papier listing à bandes, et le bleu des cartes d'ARPANET pour les liens et les citations.
- **Lisibilité** : les réponses et les extraits sont en police à empattements, plus agréable pour lire du texte long. Les noms de fichiers sont en police à chasse fixe, comme dans un terminal.
- **Accessibilité** : navigation au clavier avec un contour de focus visible, couleurs contrastées, mise en page adaptée au téléphone (la page défile et le panneau des sources passe sous la conversation), animations coupées si le système le demande.
- **Sécurité** : tout texte venant du corpus ou du LLM est échappé avant affichage, ce qui empêche l'injection de HTML.

## 5. Tests
- `tests/test_frontend.py` : l'API sert bien la page, le CSS et le JavaScript.
- Testé dans Chromium avec un faux Ollama :
  - réponse en streaming ;
  - clic sur `[2]` ;
  - « Voir le contexte » ;
  - refus ;
  - onglet Recherche ;
  - affichage mobile (390 px).

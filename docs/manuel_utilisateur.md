# Manuel d'utilisation : WebCognitive Engine

Ce manuel s'adresse à la personne qui **utilise** l'application. Pour l'installer, voir le [README](../README.md#5-installation-pas-à-pas).

## Démarrer
1. Vérifiez qu'Ollama tourne : son icône est dans la barre des tâches. S'il est arrêté, lancez l'application Ollama.
2. Dans un terminal, depuis le dossier du projet :
   ```bash
   python scripts/serve_api.py
   ```
3. Ouvrez [http://127.0.0.1:8000/](http://127.0.0.1:8000/) dans votre navigateur.

En haut à droite, un **voyant** résume l'état du système :

| Voyant | Signification | Que faire |
|---|---|---|
| ● vert « 40 documents · 5751 extraits · LLM mistral » | tout est prêt | – |
| ● orange « Ollama non lancé » | la recherche marche, pas l'assistant | lancer Ollama |
| ● orange « Modèle absent » | Ollama ne connaît pas le modèle | `ollama pull mistral` |
| ● rouge « Base vectorielle vide » | les données ne sont pas indexées | `python scripts/build_vectordb.py` |

La première réponse peut prendre quelques secondes de plus : Ollama charge le modèle en mémoire.

## Onglet « Assistant » : poser une question
1. Tapez votre question dans la zone du bas, puis **Entrée** (Maj + Entrée pour aller à la ligne). Vous pouvez aussi cliquer sur une question d'exemple.
2. Les extraits trouvés s'affichent tout de suite à droite, puis la réponse s'écrit **mot à mot**.
3. Les numéros `[1]`, `[2]`… de la réponse indiquent d'où vient chaque information. **Cliquez dessus** : l'extrait correspondant s'affiche à droite et s'encadre.
4. Chaque extrait du panneau **Sources** indique :
   - le **nom du fichier** et la **page** (PDF, TXT) ou la **section** (HTML, DOCX) ;
   - le titre, l'auteur et l'année du document ;
   - le texte de l'extrait ; **« Voir le contexte »** affiche aussi les passages qui l'entourent, l'extrait étant surligné.
5. Les extraits que le modèle a lus sans les citer restent consultables dans « Extraits consultés mais non cités ».

**Si l'information n'est pas dans le corpus**, l'assistant répond « Je ne sais pas : cette information n'est pas dans le corpus. » avec une marge orange. C'est voulu : il ne répond qu'à partir des 41 documents.

**Options**, sous la zone de saisie :
- **Recherche** : la façon de trouver les extraits. « Sens + mots-clés » est le réglage par défaut et le plus fiable. « Par le sens » comprend les reformulations ; « mots-clés » est adapté aux noms propres.
- **Extraits** : combien de passages sont donnés au modèle (8 par défaut).
- **Langue des sources** : se limiter aux documents français ou anglais.

**Conseils pour de bonnes réponses :**
- poser une question précise, sur un seul sujet (« Qui a inventé le DNS ? » plutôt que « Parle-moi d'Internet ») ;
- citer les noms propres quand on les connaît (« selon Clark… », « la RFC 1034 ») ;
- chaque question est traitée seule : répétez le sujet plutôt que d'écrire « et lui ? ».

## Onglet « Recherche dans le corpus »
Il trouve les passages les plus pertinents **sans** passer par le modèle de langage. C'est plus rapide, et utile pour explorer les sources. Chaque résultat affiche son fichier, sa page ou section, son score et un lien « Voir le contexte ».

## Onglet « Tableau de bord »
Il donne une vue d'ensemble du corpus :
- chiffres clés ;
- documents par format, volume de texte et décennie ;
- taille des segments ;
- thématiques par document et par décennie ;
- termes les plus fréquents ;
- carte sémantique ;
- questions déjà posées.

Survolez un graphique pour voir les valeurs exactes. Molette pour zoomer, double-clic pour revenir à la vue d'ensemble. Sur la **carte sémantique**, choisissez un document dans « Mettre en évidence » pour voir où se trouvent ses passages.

## Arrêter
Dans le terminal, appuyez sur **Ctrl + C**. Ollama peut rester ouvert.

## En cas de problème

| Symptôme | Cause probable | Solution |
|---|---|---|
| « API injoignable » | le serveur n'est pas lancé | `python scripts/serve_api.py` |
| `can't open file 'scripts/serve_api.py'` | le terminal n'est pas dans le dossier du projet | `cd` vers le dossier du projet, puis relancer |
| « Impossible d'obtenir une réponse : Ollama ne répond pas » | Ollama est arrêté | lancer Ollama, puis reposer la question |
| Réponse très lente | modèle trop lourd pour la machine | `ollama pull llama3.2:3b`, puis lancer l'API avec `WEBCOGNITIVE_LLM=llama3.2:3b` (PowerShell : `$env:WEBCOGNITIVE_LLM="llama3.2:3b"`) |
| Tableau de bord : « Carte absente » | la carte 2D n'a pas été calculée | `python scripts/carte_vecteurs.py` |

# Étape 8 : recette de l'application

Rapport généré par `scripts/recette.py` le 01/11/2026 à 14:09, contre l'application en marche (http://127.0.0.1:8000), en 46 s. Chaque contrôle passe par l'API REST, comme l'interface web.

**30 contrôles réussis sur 31.**

| Étape | Contrôle | Résultat | Détail |
|---|---|---|---|
| 1. État | base vectorielle remplie | ✅ | 5751 segments |
| 1. État | Ollama répond | ✅ | mistral |
| 1. État | modèle LLM téléchargé | ✅ | mistral |
| 2. Ingestion | POST /ingest accepté | ✅ | running |
| 2. Ingestion | indexation terminée | ✅ | 5751 segments en 4.1 s |
| 2. Ingestion | même nombre de segments après réindexation | ✅ | 5751 |
| 3. Corpus | catalogue complet | ✅ | 41 documents |
| 3. Corpus | 4 formats présents | ✅ | docx, html, pdf, txt |
| 3. Corpus | texte d'un document consultable (pdf02, par page) | ✅ | 10 pages |
| 3. Corpus | segment consultable avec ses voisins | ✅ | isoc_bref_historique_internet_fr.html, § Publié 1997 |
| 3. Corpus | document inconnu → 404 | ✅ |  |
| 4. Recherche | mode semantic : passage sur Mockapetris dans le top 5 | ✅ | isoc_bref_historique_internet_fr.html, § Démontrer les idées (15.4 ms) |
| 4. Recherche | mode lexical : passage sur Mockapetris dans le top 5 | ✅ | isoc_bref_historique_internet_fr.html, § Démontrer les idées (248.3 ms) |
| 4. Recherche | mode hybrid : passage sur Mockapetris dans le top 5 | ✅ | isoc_bref_historique_internet_fr.html, § Démontrer les idées (17.1 ms) |
| 4. Recherche | filtres langue + format respectés | ✅ |  |
| 4. Recherche | paramètre invalide → 422 | ✅ |  |
| 5. RAG | réponse correcte (Mockapetris) | ✅ | Le DNS a été inventé par Paul Mockapetris de l'USC/ISI [1, 3]. |
| 5. RAG | sources citées avec fichier et page/section | ✅ | isoc_bref_historique_internet_fr.html, § Démontrer les idées; leiner_et_al_brief_history_internet.pdf, p. 5 |
| 5. RAG | question hors corpus refusée | ✅ | Je ne sais pas : cette information n'est pas dans le corpus. |
| 5. RAG | flux NDJSON : sources, morceaux de texte, fin | ✅ | 30 morceaux |
| 6. Dataviz | indicateurs du corpus | ✅ | 315525 mots, 10 thématiques |
| 6. Dataviz | carte sémantique disponible | ✅ | 5751 points |
| 6. Dataviz | questions posées comptabilisées | ✅ | 3 questions |
| 6. Dataviz | Plotly servi en local | ❌ | 0 Ko |
| 7. Interface | / redirige vers l'interface | ✅ |  |
| 7. Interface | page d'accueil | ✅ |  |
| 7. Interface | ressource app.js | ✅ |  |
| 7. Interface | ressource dashboard.js | ✅ |  |
| 7. Interface | ressource style.css | ✅ |  |
| 8. Validation | succès ≥ 80 % (réponse correcte + bonne source) | ✅ | 21/26 = 81% |
| 8. Validation | pièges hors corpus refusés (100 %) | ✅ | 3/3 |

## Questions de validation (étape 1), posées à l'application

| Question | Succès | Réponse | Sources citées |
|---|---|---|---|
| F01 | ✅ | Steve Crocker a écrit la RFC 1 et à la date du 7 avril 1969 [4]. | rfc2555_30_years_of_rfcs.txt, p. 9 |
| F02 | ✅ | Le 1er janvier 1983 ([1], [2], [5], [6]). | leiner_et_al_brief_history_internet.pdf, p. 5<br>note_histoire_d_internet.docx, § Protocole TCP/IP<br>historyofinformation_cerf_kahn_tcp.html, § Cerf & Kahn Publish TCP: A Protocol for Packet Network Communication |
| F03 | ✅ | Les auteurs Vinton Cerf et Robert Kahn ont publié leur protocole, le Transmission Control Protocol (TCP), dans la revue IEEE Transactions on Communications, dans le volume COM-22, V 5, en mai 1974 [1]… | historyofinformation_cerf_kahn_tcp.html, § Cerf & Kahn Publish TCP: A Protocol for Packet Network Communication |
| F04 | ❌ | Le manuscrit de Cerf et Kahn a été reçu par l'éditeur en mai 1974 [2]. | historyofinformation_cerf_kahn_tcp.html, § Cerf & Kahn Publish TCP: A Protocol for Packet Network Communication |
| F05 | ✅ | L'objectif de premier niveau de l'architecture Internet, selon Clark (1988), est de développer une technique efficace pour l'utilisation multiplexée des réseaux existants interconnectés [2, 7]. | clark_1988_design_philosophy_darpa.pdf, p. 1 |
| F06 | ✅ | Le premier des objectifs de second niveau listés par Clark est "Internet communication must continue despite loss of networks or gateways" [5, 1]. | inria_code_source_1988_1997.pdf, p. 15<br>clark_1988_design_philosophy_darpa.pdf, p. 2 |
| F07 | ❌ | Je ne sais pas : cette information n'est pas dans le corpus. [6] | – |
| F08 | ❌ | Je ne sais pas : cette information n'est pas dans le corpus. | – |
| F09 | ✅ | Paul Baran a publié le mémorandum RM-3420 en août 1964 pour la Rand Corporation. [1] | bbn_1981_history_arpanet_first_decade.pdf, p. 49 |
| F10 | ❌ | La réunion technique tenue via un ordinateur a été permise par l'idée avancée par Licklider et Taylor (1968) d'un réseau de tels ordinateurs connectés les uns aux autres par des lignes de télécommunic… | licklider_taylor_1968_computer_communication_device.pdf, p. 22 |
| F11 | ✅ | Licklider a écrit ses mémos sur le « réseau galactique » en août 1962 [2]. | isoc_bref_historique_internet_fr.html, § Origines de l’Internet |
| F12 | ❌ | Le premier IMP a été installé à l'UCLA le 2 septembre 1969 [2]. | bbn_1981_history_arpanet_first_decade.pdf, p. 95-96 |
| F13 | ✅ | Le premier logiciel de courrier électronique a été écrit par Ray Tomlinson en mars 1972 [1]. | isoc_bref_historique_internet_fr.html, § Origines de l’Internet |
| F14 | ✅ | Dans le modèle initial, les 32 bits d'une adresse IP se répartissaient de la manière suivante : les 8 premiers bits signifiaient le réseau et les 24 bits restants désignaient l'hôte sur ce réseau [1, … | isoc_bref_historique_internet_fr.html, § Les concepts initiaux de l’interréseautage<br>leiner_et_al_brief_history_internet.pdf, p. 4 |
| F15 | ✅ | Le DNS a été inventé par Paul Mockapetris de l'USC/ISI [1, 3]. | isoc_bref_historique_internet_fr.html, § Démontrer les idées<br>leiner_et_al_brief_history_internet.pdf, p. 5 |
| F16 | ✅ | Le réseau de transmission de paquets de Cyclades a été surnommé « Cigale » [2]. Ce surnom a été choisi car chaque fois qu'un paquet passait dans le modem, le bruit ressemblait au grésillement des ciga… | interstices_louis_pouzin_tete_dans_les_reseaux.html, § Louis Pouzin, la tête dans les réseaux |
| F17 | ✅ | Mitranet ([7]) | wikipedia_fr_cyclades_reseau.html, § Cyclades (réseau) |
| F18 | ✅ | Le 13 mars 1989 ([1], [3]). | note_bio_tim_berners_lee.docx, § L'invention du World Wide Web<br>wikipedia_fr_world_wide_web.html, § Chronologie |
| F19 | ✅ | Tim Berners-Lee a écrit un programme intitulé "Enquire-Within-Upon-Everything" au CERN en 1980 [3]. | w3c_little_history_www.html, § A Little History of the World Wide Web |
| F20 | ✅ | La RFC 2468 a été écrite par Vint Cerf [2]. Elle rend hommage à Jon Postel [2]. | note_bio_jon_postel.docx, § Hommages |
| F21 | ✅ | Le Federal Networking Council (FNC) a adopté sa définition du mot « Internet » le 24 octobre 1995 [1, 2, 3, 4]. | isoc_bref_historique_internet_fr.html, § Histoire de l’avenir<br>leiner_et_al_brief_history_internet.pdf, p. 9 |
| F22 | ✅ | Il y avait 50 entreprises et 5 000 visiteurs au premier salon Interop, en septembre 1988 [1, 3]. | isoc_bref_historique_internet_fr.html, § Commercialisation de la technologie<br>leiner_et_al_brief_history_internet.pdf, p. 9 |
| C01 | ✅ | Le réseau Cyclades a eu une influence reconnue sur le protocole TCP, car ses travaux ont été cités par Vint Cerf dans une de ses premières spécifications du protocole de transport d'Internet TCP [8]. … | interstices_louis_pouzin_tete_dans_les_reseaux.html, § Louis Pouzin, la tête dans les réseaux<br>wikipedia_fr_louis_pouzin.html, § Louis Pouzin |
| C02 | ✅ | L'idée qu'ARPANET a été conçu pour résister à une guerre nucléaire est une rumeur ([1], [4], [7], [8]). En effet, aucun document officiel ne soutient cette légende. Seule l'étude sans rapport de RAND … | isoc_bref_historique_internet_fr.html, § Notes<br>note_arpanet.docx, § Note de synthèse : ARPANET<br>note_histoire_d_internet.docx, § Répartition et commutation de paquets de données |
| C03 | ✅ | Les deux concepts sont liés car l'argument de bout en bout est un principe de conception de système qui stipule que certaines fonctions doivent être implémentées à l'application plutôt qu'au niveau in… | isoc_bref_historique_internet_fr.html, § Les concepts initiaux de l’interréseautage<br>interstices_louis_pouzin_tete_dans_les_reseaux.html, § Louis Pouzin, la tête dans les réseaux<br>saltzer_reed_clark_1984_end_to_end.pdf, p. 7-8 |
| C04 | ✅ | Jon Postel était un informaticien américain, né le 6 août 1943 à Altadena (Californie) et mort le 16 octobre 1998 à Santa Monica (Californie) [1]. Il est connu pour être l'un des principaux contribute… | note_bio_jon_postel.docx, § Note de synthèse : Jon Postel<br>note_histoire_d_internet.docx, § Network Information Center et autres autorités de coordination<br>rfc2555_30_years_of_rfcs.txt, p. 11 |
| P01 | ✅ | Je ne sais pas : cette information n'est pas dans le corpus. | – |
| P02 | ✅ | Je ne sais pas : cette information n'est pas dans le corpus. | – |
| P03 | ✅ | Je ne sais pas : cette information n'est pas dans le corpus. | – |

# Étape 5 : évaluation de l'assistant RAG

Fichier généré par `scripts/evaluate_rag.py` (une ligne par réglage mesuré). Critère du projet : **succès** = réponse correcte **et** extrait cité qui la justifie, objectif 80 % ; pièges refusés, objectif 100 %. Explications : `docs/etape5_rag.md`.

| LLM | Recherche | k | Réponse correcte | Bonne source | **Succès** | Pièges refusés | Refus à tort | s/question |
|---|---|---|---|---|---|---|---|---|
| mistral | semantic | 5 | 73 % | 85 % | **73 %** | 100 % | 2 | 1.9 |
| mistral | hybrid | 8 | 85 % | 81 % | **81 %** | 100 % | 1 | 2.1 |

## Détail du meilleur réglage : mistral, recherche hybrid, k = 8

| Question | Succès | Réponse | Documents cités |
|---|---|---|---|
| F01 | ✅ | Steve Crocker a écrit la RFC 1 et à la date du 7 avril 1969 [4]. | txt11 |
| F02 | ✅ | Le 1er janvier 1983 ([1], [2], [5], [6]). | docx01, html08, pdf03 |
| F03 | ✅ | Les auteurs Vinton Cerf et Robert Kahn ont publié leur protocole en 1974 dans la revue IEEE Transactions on Communications, dans le volume COM-22, V 5, pages 627-641 [3 et 7]. | html01, html08 |
| F04 | ❌ | Le manuscrit de Cerf et Kahn a été reçu par l'éditeur en mai 1974 [2]. | html08 |
| F05 | ✅ | L'objectif de premier niveau de l'architecture Internet, selon Clark (1988), est de développer une technique efficace pour la multiplexation de l'utilisation de réseaux existants interconnectés [2]. | pdf02 |
| F06 | ✅ | Le premier des objectifs de second niveau listés par Clark est "Internet communication must continue despite loss of networks or gateways" [5, 1]. | pdf02, pdf09 |
| F07 | ❌ | Je ne sais pas : cette information n'est pas dans le corpus. [6] | – |
| F08 | ❌ | Le paquet d'accusé de réception renvoyé par l'ARPANET, cité par Saltzer et al., n'est pas spécifiquement nommé dans les extraits fournis. [2] et [4] mentionnent que chaque ACK (Accusé de réception) renvoyé est cumulé pou… | html01 |
| F09 | ✅ | Paul Baran a publié le mémorandum RM-3420 en août 1964 pour la RAND Corporation. [1] | pdf07 |
| F10 | ❌ | La réunion technique tenue via un ordinateur a été permise par l'idée avancée par Licklider et Taylor (1968) de « réseaux de tels [ordinateurs], connectés les uns aux autres par des lignes de télécommunications large ban… | – |
| F11 | ✅ | Licklider a écrit ses mémos sur le « réseau galactique » en août 1962 [2]. | html01 |
| F12 | ❌ | Le premier IMP a été installé à l'UCLA le 2 septembre 1969 [2]. | pdf07 |
| F13 | ✅ | Le premier logiciel de courrier électronique a été écrit par Ray Tomlinson en mars 1972 [1]. | html01 |
| F14 | ✅ | Dans le modèle initial, les 32 bits d'une adresse IP se répartissaient de la manière suivante : les 8 premiers bits signifiaient le réseau et les 24 bits restants désignaient l'hôte sur ce réseau [1, 3]. | html01, pdf03 |
| F15 | ✅ | Le DNS a été inventé par Paul Mockapetris de l'USC/ISI [1, 3]. | html01, pdf03 |
| F16 | ✅ | Le réseau de transmission de paquets de Cyclades a été surnommé « Cigale » [2]. Le nom a été choisi car chaque fois qu'un paquet passait dans le modem, le bruit ressemblait au grésillement des cigales ! [2] | html05 |
| F17 | ✅ | Mitranet ([7]) | html09 |
| F18 | ✅ | Le 13 mars 1989 ([1], [3]). | docx07, html11 |
| F19 | ✅ | Tim Berners-Lee a écrit un programme intitulé "Enquire-Within-Upon-Everything" au CERN en 1980 [3]. | html02 |
| F20 | ✅ | La RFC 2468 a été écrite par Vint Cerf [2]. Elle rend hommage à Jon Postel [2]. | docx08 |
| F21 | ✅ | Le Federal Networking Council (FNC) a adopté sa définition du mot « Internet » le 24 octobre 1995 [1, 2]. | html01, pdf03 |
| F22 | ✅ | Il y avait 50 entreprises et 5 000 visiteurs au premier salon Interop, en septembre 1988 [1, 3]. | html01, pdf03 |
| C01 | ✅ | Le réseau Cyclades a eu une influence reconnue sur le protocole de communication TCP, car ses travaux ont été cités par Vint Cerf dans une de ses premières spécifications du protocole de transport d'Internet TCP [8]. De … | html05, html10 |
| C02 | ✅ | L'idée selon laquelle ARPANET a été conçu pour résister à une guerre nucléaire est une rumeur ([1], [4], [6], [8]). En effet, aucun document officiel ne soutient cette légende, et seule une étude sans rapport de RAND por… | docx02, html01, pdf03, pdf09 |
| C03 | ✅ | Les deux concepts sont liés car l'argument de bout en bout est un principe de conception de système qui stipule que certaines fonctions doivent être implémentées à l'application plutôt qu'au niveau inférieur du protocole… | pdf06 |
| C04 | ✅ | Jon Postel était un informaticien américain, né le 6 août 1943 à Altadena (Californie) et mort le 16 octobre 1998 à Santa Monica (Californie) [1]. Il est considéré comme l'un des principaux contributeurs à la création de… | docx01, docx08, html01 |
| P01 | ✅ | Je ne sais pas : cette information n'est pas dans le corpus. | – |
| P02 | ✅ | Je ne sais pas : cette information n'est pas dans le corpus. | – |
| P03 | ✅ | Je ne sais pas : cette information n'est pas dans le corpus. | – |

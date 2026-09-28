# Questions de validation

Ces questions servent de **jeu de test** pour le moteur (recherche, puis RAG) jusqu'à la soutenance. Chaque réponse se trouve explicitement dans un document du corpus.

Les localisations ont été **retrouvées par recherche automatique dans le texte extrait** le 28/09/2026. Pour chaque question, ouvre le document, vérifie la réponse à l'endroit indiqué et coche « Vérifié ». Ajoute aussi quelques questions de ton cru.

Pour les PDF et les TXT, « p. » est la page du fichier. Pour les HTML, « § » est l'intertitre de la page.

Types de questions :
- **F** : fait simple, un seul document.
- **C** : question croisée, qui exige plusieurs documents.
- **P** : piège, hors corpus. Le moteur doit refuser de répondre.

## A. Faits simples (F)

| # | Question | Réponse attendue | Document | Localisation | Vérifié |
|---|---|---|---|---|---|
| F01 | Qui a écrit la RFC 1 et à quelle date ? | Steve Crocker, 7 avril 1969 | `txt/rfc0001_host_software.txt` | en-tête, p. 1 | ☐ |
| F02 | À quelle date la transition d'ARPANET de NCP vers TCP/IP a-t-elle eu lieu ? | 1er janvier 1983 | `html/isoc_bref_historique_internet_fr.html`, `txt/rfc0801_ncp_tcp_transition_plan.txt` | ISOC : § Transition vers une infrastructure à grande échelle ; RFC 801 : § The General Plan, p. 2 (date *prévue* : « by 1 January 1983 ») | ☐ |
| F03 | Dans quelle revue et quel numéro Cerf et Kahn ont-ils publié leur protocole en 1974 ? | IEEE Transactions on Communications, vol. COM-22, n° 5, mai 1974 | `pdf/cerf_kahn_1974_protocol_packet_network.pdf` | bandeau en bas de chaque page (p. 1) | ☐ |
| F04 | Quand le manuscrit de Cerf et Kahn a-t-il été reçu par l'éditeur ? | 5 novembre 1973 | idem | p. 1, note de bas de page (« Manuscript received November 5, 1973 ») | ☐ |
| F05 | Selon Clark (1988), quel est l'objectif de premier niveau de l'architecture Internet ? | Développer une technique efficace pour le multiplexage des réseaux interconnectés existants | `pdf/clark_1988_design_philosophy_darpa.pdf` | § 2 « Fundamental Goal », p. 1 | ☐ |
| F06 | Quel est le premier des objectifs de second niveau listés par Clark ? | La survivabilité : la communication doit continuer malgré la perte de réseaux ou de passerelles | idem | § 3 « Second Level Goals », p. 2 (liste, point 1) | ☐ |
| F07 | Dans l'article de Saltzer, Reed et Clark, à quelle fréquence la passerelle défectueuse du MIT inversait-elle une paire d'octets ? | Environ une fois par million d'octets | `pdf/saltzer_reed_clark_1984_end_to_end.pdf` | § « A too-real example », p. 3-4 | ☐ |
| F08 | Comment s'appelle le paquet d'accusé de réception renvoyé par l'ARPANET, cité par Saltzer et al. ? | RFNM, « Request For Next Message » | idem | § « Delivery guarantees », p. 5 | ☐ |
| F09 | Quand et pour qui Paul Baran a-t-il publié le mémorandum RM-3420 ? | Août 1964, RAND Corporation, pour l'US Air Force | `pdf/baran_1964_rand_rm3420_distributed_communications.pdf` | page de titre ⚠️ **à vérifier à l'œil** : le PDF est un scan sans texte, le moteur ne pourra pas répondre sans OCR | ☐ |
| F10 | Selon Licklider et Taylor (1968), qu'a permis la réunion technique tenue via un ordinateur ? | Faire en deux jours ce qui aurait normalement pris une semaine | `pdf/licklider_taylor_1968_computer_communication_device.pdf` | p. 2, début de l'article | ☐ |
| F11 | Quand Licklider a-t-il écrit ses mémos sur le « réseau galactique » ? | Août 1962 | `html/isoc_bref_historique_internet_fr.html` | § Origines de l'Internet | ☐ |
| F12 | Où et quand le premier IMP a-t-il été installé ? | À UCLA, en septembre 1969, par BBN | idem | § Origines de l'Internet | ☐ |
| F13 | Qui a écrit le premier logiciel de courrier électronique, et quand ? | Ray Tomlinson (BBN), mars 1972 | idem | § Origines de l'Internet | ☐ |
| F14 | Dans le modèle initial, comment se répartissaient les 32 bits d'une adresse IP ? | 8 bits pour le réseau, 24 bits pour l'hôte | idem | § Les concepts initiaux de l'interréseautage | ☐ |
| F15 | Qui a inventé le DNS ? | Paul Mockapetris (USC/ISI) | idem et `txt/rfc1034_domain_names_concepts.txt` | ISOC : § Transition vers une infrastructure à grande échelle ; RFC 1034 : en-tête, p. 1 | ☐ |
| F16 | Comment l'équipe de Cyclades avait-elle surnommé son réseau de transmission de paquets, et pourquoi ? | « Cigale » : le bruit des paquets dans le modem rappelait le grésillement des cigales | `html/interstices_louis_pouzin_tete_dans_les_reseaux.html` | fin de l'article, paragraphe sur Cyclades (pas dans le chapeau) | ☐ |
| F17 | Quel surnom portait Cyclades à ses débuts ? | « Mitranet », parce qu'il était basé sur le mini-ordinateur Mitra 15 | `html/wikipedia_fr_cyclades_reseau.html` | introduction (avant § Genèse) | ☐ |
| F18 | Quand Tim Berners-Lee a-t-il écrit « Information Management: A Proposal » ? | Mars 1989 | `html/w3c_little_history_www.html`, `html/berners_lee_1989_information_management_proposal.html` | W3C : entrée 1989 ; proposition : en-tête (« March 1989, May 1990 ») | ☐ |
| F19 | Quel programme Tim Berners-Lee a-t-il écrit au CERN en 1980 ? | ENQUIRE (« Enquire-Within-Upon-Everything ») | `html/w3c_little_history_www.html` | entrée 1980 | ☐ |
| F20 | Qui a écrit la RFC 2468, et en hommage à qui ? | Vint Cerf, en hommage à Jon Postel (17 octobre 1998) | `txt/rfc2468_i_remember_iana.txt` | en-tête et 1er paragraphe, p. 1 | ☐ |
| F21 | À quelle date le Federal Networking Council a-t-il adopté sa définition du mot « Internet » ? | 24 octobre 1995 | `html/isoc_bref_historique_internet_fr.html` | § Histoire de l'avenir | ☐ |
| F22 | Combien d'entreprises et de visiteurs y avait-il au premier salon Interop, en septembre 1988 ? | 50 entreprises et 5 000 ingénieurs | idem | § Commercialisation de la technologie | ☐ |

## B. Questions croisées (C)

| # | Question | Réponse attendue | Documents | Localisation | Vérifié |
|---|---|---|---|---|---|
| C01 | Quel lien existe-t-il entre Cyclades et TCP ? | Les idées de Cyclades (Pouzin, Zimmermann, Le Lann, Elie) ont influencé la conception de TCP : Cerf et Kahn citent CYCLADES et Pouzin dans leur article de 1974 | `pdf/cerf_kahn_1974…`, `html/wikipedia_fr_louis_pouzin.html`, `html/signal_biographie_pouzin_cyclades.html` | Cerf-Kahn : p. 7 (fenêtre « similar to that used by the French CYCLADES system ») et p. 12 (remerciements, réf. [2] Pouzin) ; Wikipédia : introduction ; Signal : § Cyclades et TCP/IP | ☐ |
| C02 | Pourquoi l'idée qu'ARPANET a été conçu pour résister à une guerre nucléaire est-elle une rumeur ? | Seule l'étude RAND de Baran portait sur la survie aux attaques ; ARPANET ne visait pas cet objectif | `html/isoc_bref_historique_internet_fr.html`, `pdf/baran_1964…` | ISOC : note 5 (en fin de page) et § Origines ; Baran : scan sans texte ⚠️ | ☐ |
| C03 | Quel point commun y a-t-il entre l'argument de bout en bout et le choix du datagramme dans IP ? | Placer les fonctions (fiabilité, ordre) aux extrémités plutôt que dans le réseau | `pdf/saltzer_reed_clark_1984…`, `pdf/clark_1988…` | Saltzer : résumé, p. 1 ; Clark : § 1 (p. 1) et discussion du datagramme, p. 3 | ☐ |
| C04 | Qui était Jon Postel, et quels rôles a-t-il tenus ? | Éditeur des RFC et gestionnaire des numéros de protocole (IANA), décédé le 16 octobre 1998 | `txt/rfc2468…`, `docx/note_bio_jon_postel.docx`, `html/isoc_…` | RFC 2468 : p. 1 ; note Postel : 1er paragraphe et § Biographie ; ISOC : § Le rôle de la documentation | ☐ |

## C. Pièges, hors corpus (P) : réponse attendue « information absente du corpus »

| # | Question |
|---|---|
| P01 | Quel est le chiffre d'affaires de Google en 2024 ? |
| P02 | Quelle est la capitale de l'Australie ? |
| P03 | Qui a inventé le protocole QUIC ? |

## Corrections apportées lors de la vérification

- **F02** : la RFC 801 donne la date *prévue* de la transition ; c'est le texte de l'ISOC qui confirme qu'elle a eu lieu le 1er janvier 1983.
- **F16** : la phrase sur « Cigale » n'est pas dans le chapeau mais à la fin de l'article.
- **C01** : l'article de Cerf et Kahn ne cite pas « l'IRIA » mais CYCLADES et L. Pouzin ; réponse reformulée.
- **F09 et C02** : le PDF de Baran n'a pas de couche texte. Soit on ajoute un OCR à l'étape 2, soit on remplace ces questions.

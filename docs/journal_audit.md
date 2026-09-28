# Journal d'audit du corpus (exploration manuelle)

Une ligne par document. C'est la trace demandée par la fiche de l'étape 1 : on vérifie que le contenu est riche et exploitable avant d'écrire du code.

Les colonnes « Pages / taille », « Qualité du texte » et « Pièges pour le parsing » ont été **pré-remplies par une extraction automatique** (pdfplumber, BeautifulSoup, python-docx) le 28/09/2026. Elles doivent être **vérifiées en ouvrant chaque document** : coche la colonne « Vérifié » au fur et à mesure, complète « Passages / chiffres repérés » et décide de « Garder ? ».

Elles serviront directement à l'étape 2 (parsing et nettoyage).

## PDF (10)

| ID | Fichier | Pages / taille | Qualité du texte | Pièges pour le parsing | Passages / chiffres repérés | Garder ? | Vérifié |
|---|---|---|---|---|---|---|---|
| pdf01 | cerf_kahn_1974_protocol_packet_network.pdf | 13 p., 174 Ko, ~10 500 mots, EN | Texte natif, bon | 2 colonnes mélangées à l'extraction ; bandeau « © 1974 IEEE. Reprinted… » répété en bas de chaque page ; césures (« pa- per ») | Manuscrit reçu le 5 nov. 1973 (p. 1) ; IEEE Trans. on Comms, vol. COM-22, n° 5, mai 1974 ; cite CYCLADES (p. 7) et Pouzin (réf. [2], p. 12) | | ☐ |
| pdf02 | clark_1988_design_philosophy_darpa.pdf | 10 p., 58 Ko, ~8 000 mots, EN | Texte natif, très bon | 2 colonnes mélangées ; pied de page « ACM SIGCOMM -n- Computer Communication Review » | § 2 « Fundamental Goal » (p. 1) ; § 3 « Second Level Goals » et § 4 « Survivability » (p. 2) | | ☐ |
| pdf03 | leiner_et_al_brief_history_internet.pdf | 10 p., 681 Ko, ~3 500 mots, EN | Natif mais **mots collés** (« Thishistoryrevolvesaround… ») | Espaces perdus : régler `x_tolerance` de pdfplumber ; 2 colonnes ; appels de note collés (« 50kbps6 ») ; en-tête ACM répété | Version anglaise de html01 (même texte ISOC) | | ☐ |
| pdf04 | baran_1964_rand_rm3420_distributed_communications.pdf | 51 p., 1,5 Mo, **0 caractère extrait** | **Scan sans couche texte** | OCR obligatoire (Tesseract) à l'étape 2, sinon document inutilisable | | | ☐ |
| pdf05 | licklider_taylor_1968_computer_communication_device.pdf | 22 p., 126 Ko, ~7 400 mots, EN | Texte natif, bon | Numéros de page isolés ; césures ; mise en page 2 colonnes détectée | Réunion par ordinateur : 2 jours au lieu d'une semaine (p. 2) | | ☐ |
| pdf06 | saltzer_reed_clark_1984_end_to_end.pdf | 10 p., 36 Ko, ~6 300 mots, EN | Texte natif, très bon | En-tête « SALTZER ET AL. End-to-End Arguments in System Design n » répété | Exemple MIT : inversion d'octets 1 fois par million (p. 3-4) ; RFNM (p. 5) | | ☐ |
| pdf07 | bbn_1981_history_arpanet_first_decade.pdf | 183 p., 7,4 Mo, ~34 000 mots, EN | Scan avec OCR correct, erreurs ponctuelles (« botn », « DepartmeTrt », lettres isolées) | En-tête « Report No. 4799 Bolt Beranek and Newman Inc. » sur chaque page ; numéros « II-3 » ; document le plus long du corpus | | | ☐ |
| pdf08 | dca_1985_arpanet_information_brochure.pdf | 59 p., 4,5 Mo, ~13 500 mots, EN | Numérisation DTIC, texte lisible (~2,6 % de mots douteux) | 1 page vide ; numéros de page isolés | | | ☐ |
| pdf09 | inria_code_source_1988_1997.pdf | 20 p., 8,3 Mo, ~21 000 mots, **FR** | Texte natif, bon | Mise en page journal (colonnes, encadrés) ; fichier lourd (images) | | | ☐ |
| pdf10 | hauben_netizens_ch7_behind_the_net.pdf | 14 p., 105 Ko, ~7 000 mots, EN | Texte natif, bon | Pied de page « Page n » | | | ☐ |

## TXT (11)

Pièges communs à toutes les RFC : en-tête « RFC n  Titre  Date » et pied « Auteur  [Page n] » sur chaque page, sauts de page `\f`, lignes coupées à 72 caractères, schémas en ASCII.

| ID | Fichier | Pages / taille | Qualité du texte | Pièges pour le parsing | Passages / chiffres repérés | Garder ? | Vérifié |
|---|---|---|---|---|---|---|---|
| txt01 | rfc0001_host_software.txt | 12 p., 20 Ko, ~2 500 mots, EN | Bon | 11 pieds de page ; sommaire en tête | Steve Crocker, UCLA, 7 avril 1969 (en-tête, p. 1) | | ☐ |
| txt02 | rfc0675_tcp_specification_1974.txt | 71 p., 153 Ko, ~18 700 mots, EN | Bon | 70 pieds de page ; nombreux schémas ASCII | | | ☐ |
| txt03 | rfc0791_internet_protocol.txt | 52 p., 92 Ko, ~11 000 mots, EN | Bon | 45 pieds de page ; schémas d'en-tête IP en ASCII | | | ☐ |
| txt04 | rfc0793_transmission_control_protocol.txt | 92 p., 168 Ko, ~22 000 mots, EN | Bon | 85 pieds de page ; schémas ASCII (en-tête TCP, automate d'états) | | | ☐ |
| txt05 | rfc0801_ncp_tcp_transition_plan.txt | 22 p., 39 Ko, ~5 300 mots, EN | Bon | 21 pieds de page | Bascule NCP → TCP/IP prévue « by 1 January 1983 » (§ The General Plan, p. 2) | | ☐ |
| txt06 | rfc1000_rfc_reference_guide.txt | 150 p., 307 Ko, ~40 000 mots, EN | Bon | 149 pieds de page ; **surtout une liste de références** : peu de texte narratif, risque de polluer la recherche | | | ☐ |
| txt07 | rfc1034_domain_names_concepts.txt | 56 p., 123 Ko, ~17 900 mots, EN | Bon | 55 pieds de page | Auteur P. Mockapetris, ISI (en-tête) | | ☐ |
| txt08 | rfc1945_http_1_0.txt | 61 p., 134 Ko, ~19 500 mots, EN | Bon | 60 pieds de page ; grammaire BNF | | | ☐ |
| txt09 | rfc2235_hobbes_internet_timeline.txt | 23 p., 42 Ko, ~5 700 mots, EN | Bon | 22 pieds de page ; format chronologie (lignes courtes) | | | ☐ |
| txt10 | rfc2468_i_remember_iana.txt | 5 p., 8 Ko, ~1 300 mots, EN | Bon | 4 pieds de page | Vint Cerf, 17 octobre 1998, hommage à Jon Postel (en-tête) | | ☐ |
| txt11 | rfc2555_30_years_of_rfcs.txt | 19 p., 41 Ko, ~6 700 mots, EN | Bon | 18 pieds de page | | | ☐ |

## HTML (12)

« Contenu utile » : part du texte de la page qui se trouve dans le contenu principal (`<main>`, `<article>` ou corps de l'article Wikipédia), le reste étant des menus et bandeaux.

| ID | Fichier | Pages / taille | Qualité du texte | Pièges pour le parsing | Passages / chiffres repérés | Garder ? | Vérifié |
|---|---|---|---|---|---|---|---|
| html01 | isoc_bref_historique_internet_fr.html | 258 Ko, ~10 800 mots, FR, contenu utile 97 % | Très bon, riche | 128 balises script/style ; menus ; appels de note sous forme de chiffres collés (« DARPA 4 , ») ; notes en fin de page | Mémos Licklider août 1962, 1er IMP à UCLA sept. 1969, Tomlinson mars 1972 (§ Origines) ; adresse 8 + 24 bits (§ Concepts initiaux) ; DNS Mockapetris, NCP → TCP/IP 1er janv. 1983 (§ Transition) ; Interop sept. 1988 (§ Commercialisation) ; FNC 24 oct. 1995 (§ Histoire de l'avenir) ; rumeur nucléaire (note 5) | | ☐ |
| html02 | w3c_little_history_www.html | 12 Ko, ~1 300 mots, EN, contenu utile 100 % | Bon | Pas de `<main>` : prendre tout le `<body>` ; structure en années (h2) | ENQUIRE (1980) ; « Information Management: A Proposal », mars 1989 | | ☐ |
| html03 | berners_lee_1989_information_management_proposal.html | 33 Ko, ~4 900 mots, EN, contenu utile 100 % | Bon | Pas de `<main>` ; diagrammes en image absents | Daté « March 1989, May 1990 » (en-tête) | | ☐ |
| html04 | cern_birth_of_the_web.html | 247 Ko, **~220 mots**, EN, contenu utile 42 % | **Pauvre** : page vitrine | Plus de la moitié du texte est du menu ; 110 balises script/style | Logiciel du Web dans le domaine public le 30 avril 1993 | ⚠️ à remplacer ? | ☐ |
| html05 | interstices_louis_pouzin_tete_dans_les_reseaux.html | 126 Ko, ~3 500 mots, FR, contenu utile 95 % | Très bon | Métadonnées en tête (« Publié le », « Niveau ») ; bibliographie en fin | Surnom « Cigale » (texte extrait, l. 95) ; Cyclades abandonné en 1978 | | ☐ |
| html06 | cigref_datagramme_louis_pouzin.html | 60 Ko, ~870 mots, FR, contenu utile 61 % | Correct mais court | 17 blocs nav/header/footer | | | ☐ |
| html07 | signal_biographie_pouzin_cyclades.html | 45 Ko, ~2 300 mots, FR, contenu utile 97 % | Bon | Blog : commentaires et barre latérale | Vint Cerf s'inspire de Cyclades dès 1972-1973 (§ Cyclades et TCP/IP) | | ☐ |
| html08 | historyofinformation_cerf_kahn_tcp.html | 21 Ko, **~480 mots**, EN, contenu utile 99 % | Court | Pas de `<main>` ; 21 balises script/style | | | ☐ |
| html09 | wikipedia_fr_cyclades_reseau.html | 215 Ko, ~3 500 mots, FR, contenu utile 92 % | Bon | Wikipédia : « [ modifier \| modifier le code ] », appels « [ 1 ] », infobox, sections Notes / Références / Liens externes à couper | Surnom « Mitranet », Mitra 15 (introduction) | | ☐ |
| html10 | wikipedia_fr_louis_pouzin.html | 257 Ko, ~3 900 mots, FR, contenu utile 93 % | Bon | Idem Wikipédia | Influence de Zimmermann, Le Lann, Elie reconnue par Vint Cerf (introduction) | | ☐ |
| html11 | wikipedia_fr_world_wide_web.html | 510 Ko, ~9 800 mots, FR, contenu utile 96 % | Bon | Idem Wikipédia ; nombreux tableaux | | | ☐ |
| html12 | wikipedia_fr_internet_en_france.html | 462 Ko, ~5 300 mots, FR, contenu utile 94 % | Bon | Idem Wikipédia | | | ☐ |

## DOCX (8)

Les 8 notes ont été générées par `download_corpus.py` à partir d'articles Wikipédia : les styles Word sont propres (Title, Heading 1-3, List Bullet), sans tableau.

| ID | Fichier | Pages / taille | Qualité du texte | Pièges pour le parsing | Passages / chiffres repérés | Garder ? | Vérifié |
|---|---|---|---|---|---|---|---|
| docx01 | note_histoire_d_internet.docx | 52 Ko, 114 §, ~6 900 mots, FR | Bon | Espaces avant la ponctuation (« Postel , ») hérités du HTML ; ligne « Source / licence » en tête | | | ☐ |
| docx02 | note_arpanet.docx | 40 Ko, 39 §, ~1 700 mots, FR | Bon | Idem ; 15 puces | | | ☐ |
| docx03 | note_minitel.docx | 54 Ko, 203 §, ~8 000 mots, FR | Bon | Idem ; 72 puces | | | ☐ |
| docx04 | note_transpac.docx | 40 Ko, 25 §, ~1 700 mots, FR | Bon | Idem | | | ☐ |
| docx05 | note_commutation_de_paquets.docx | 39 Ko, 22 §, ~1 300 mots, FR | Bon | Idem | | | ☐ |
| docx06 | note_bio_vint_cerf.docx | 38 Ko, 23 §, ~750 mots, FR | Court | Idem | | | ☐ |
| docx07 | note_bio_tim_berners_lee.docx | 46 Ko, 76 §, ~4 300 mots, FR | Bon | Idem ; 29 puces | | | ☐ |
| docx08 | note_bio_jon_postel.docx | 37 Ko, 17 §, **~400 mots**, FR | Court | Idem | Né le 6 août 1943, mort le 16 octobre 1998 ; directeur de l'IANA ; principe de robustesse | | ☐ |

## Constats généraux

- **Langues :** 24 documents en anglais (9 PDF, 11 TXT, 4 HTML) et 17 en français (1 PDF, 8 HTML, 8 DOCX). Le modèle d'embeddings devra être multilingue.
- **Documents problématiques :**
  - `pdf04` (Baran) : scan sans texte. Il faut soit ajouter un OCR à l'étape 2 (Tesseract), soit remplacer la source. Les questions F09 et C02 en dépendent.
  - `html04` (CERN) : environ 220 mots utiles seulement.
  - `txt06` (RFC 1000) : surtout une liste de références, peu de texte narratif.
  - `html08`, `docx06` et `docx08` : courts, mais exploitables.
  - `pdf03` reprend en anglais le même texte que `html01` : doublon partiel, utile pour tester le multilingue.
- **Idées pour le nettoyage (étape 2) :**
  - PDF : extraction en colonnes (`pdf.pages[i].crop(...)` par moitié de page), réglage de `x_tolerance` pour `pdf03`, suppression des en-têtes et pieds répétés (lignes identiques sur plus de 30 % des pages), recollage des césures (`-\n`).
  - RFC : regex sur `^RFC \d+ .*\d{4}$` et `\[Page \d+\]$`, découpage sur `\f`.
  - HTML : garder `<main>` / `<article>` / `#mw-content-text`, retirer `script`, `style`, `nav`, `footer`, les « [ modifier ] » et les appels de note `\[ ?\d+ ?\]`, couper à partir de « Notes et références ».
  - DOCX : supprimer l'espace avant la ponctuation (`\s+([,.;:)])`), ignorer la ligne source/licence.

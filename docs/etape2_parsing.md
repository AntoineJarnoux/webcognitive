# Étape 2 : pipeline de parsing et de prétraitement

**Objectif :** extraire automatiquement le texte des 41 documents (4 formats), le nettoyer, puis l'exporter dans un format unique : un fichier JSON par document, avec ses métadonnées.

```bash
python scripts/parse_corpus.py                  # tout le corpus (≈ 1 min)
python scripts/parse_corpus.py --only pdf03     # un seul document
```

## 1. Architecture

```
src/webcognitive/
├── config.py                  chemins du projet
└── parsing/
    ├── cleaning.py            fonctions de nettoyage (regex), communes à tous les formats
    ├── pdf_parser.py          PDF  -> pdfplumber
    ├── txt_parser.py          TXT  -> lecture brute (RFC)
    ├── html_parser.py         HTML -> BeautifulSoup + lxml
    ├── docx_parser.py         DOCX -> python-docx
    └── pipeline.py            choisit le parseur selon le format, assemble le JSON final
scripts/parse_corpus.py        point d'entrée : lit l'inventaire, écrit data/processed/
```

Chaque parseur renvoie la même structure : une liste d'**unités**. Une unité correspond à une page pour les PDF et les TXT, et à une section (intertitre) pour les HTML et les DOCX. Le pipeline n'a donc pas besoin de connaître le format. Pour ajouter un format, il suffit d'ajouter un parseur dans `PARSERS` (`pipeline.py`).

Ces unités servent à **localiser** les réponses : à l'étape 3, chaque segment garde sa page ou sa section, ce qui permettra au moteur de citer « Clark 1988, p. 2 » ou « ISOC, § Origines de l'Internet ».

## 2. Format de sortie

`data/processed/<id>.json` :

```json
{
  "id": "pdf02",
  "filename": "clark_1988_design_philosophy_darpa.pdf",
  "format": "pdf",
  "title": "The Design Philosophy of the DARPA Internet Protocols",
  "author": "David D. Clark", "year": 1988, "lang": "en",
  "url": "...", "source_path": "data/raw/pdf/...", "sha256": "...",
  "retrieved_at": "...", "parsed_at": "...", "parser": "pdfplumber",
  "units": [ {"page": 1, "section": null, "text": "..."}, ... ],
  "text": "texte complet, paragraphes séparés par une ligne vide",
  "stats": {"raw_chars": 49514, "clean_chars": 49221, "words": 7931, "units": 10, ...},
  "warnings": ["10 page(s) lue(s) en deux colonnes", "..."]
}
```

`data/processed/_rapport.json` récapitule les statistiques et avertissements de tous les documents.

## 3. Traitements par format

### PDF (`pdf_parser.py`, pdfplumber)
| Problème repéré à l'étape 1 | Traitement |
|---|---|
| Mise en page sur 2 colonnes : les lignes des deux colonnes se mélangent | Recherche de la **gouttière** : on cherche, entre 35 % et 65 % de la largeur, la position verticale que traverse le moins de mots. Le titre et le pied de page peuvent la traverser : on les isole en bandeaux pleine largeur. On lit ensuite la colonne gauche, puis la droite. |
| Mots collés dans `pdf03` (« Thishistoryrevolves… ») | Si la longueur moyenne des mots dépasse 9 caractères, on relit le PDF avec une tolérance horizontale plus fine (`x_tolerance=1.5` au lieu de 3). |
| En-têtes et pieds de page répétés (« © 1974 IEEE… », « Report No. 4799… ») | On repère les lignes présentes en haut ou en bas d'au moins 30 % des pages (nombres remplacés par `#` pour comparer « Page 3 » et « Page 4 »), puis on les supprime. |
| Numéros de page isolés (« 12 », « - 3 - », « II-3 », « iv ») | Expression régulière `PAGE_NUMBER`. |
| Mots coupés en fin de ligne (« pa-\nper ») | Recollage par regex. |
| Lignes coupées au milieu des phrases | Une ligne nettement plus courte que la normale et terminée par un point marque une fin de paragraphe ; les autres sauts de ligne deviennent des espaces. |
| Cadre de page décalé (`pdf07`, `pdf08`) | Les zones découpées restent à l'intérieur de `page.bbox`. |
| PDF scanné sans texte (`pdf04`, Baran) | OCR prévu (pytesseract), mais **inactif tant que Tesseract n'est pas installé**. Le document est signalé et reste vide. |

### TXT (`txt_parser.py`, RFC)
- Découpage en pages sur le saut de page `\f`.
- Suppression des en-têtes `RFC 791  Internet Protocol  September 1981` et des pieds `Postel  [Page 3]` (y compris `[Page iii]`).
- Suppression des lignes de sommaire (`3.1 Format ........ 11`) et des schémas ASCII (lignes avec moins de 40 % de lettres et au moins 3 symboles `+-|`).
- Les paragraphes sont séparés par des lignes vides : on recolle les lignes à l'intérieur de chaque paragraphe.

### HTML (`html_parser.py`, BeautifulSoup)
- Suppression des balises inutiles (`script`, `style`, `nav`, `header`, `footer`, `aside`, `form`, `figure`…) et des éléments de Wikipédia (liens « modifier », infobox, bandeaux, sommaire, tableaux).
- Recherche du conteneur principal, du plus précis au plus général : `#mw-content-text`, `.entry-content`, `article`, `main`… et `body` en dernier recours.
- Lecture bloc par bloc (`p`, `li`, `h2`…) sans insérer d'espace entre les balises en ligne : on évite ainsi « Postel , ».
- Les intertitres `h1` à `h4` ouvrent une nouvelle section. Les sections « Notes et références », « Voir aussi », « Liens externes », ainsi que l'appel aux dons de l'ISOC, sont écartées. Les « Notes » de l'ISOC sont **gardées** : la note 5 sert à la question C02.
- Suppression des appels de note (`[12]`, `<sup>4</sup>`).

### DOCX (`docx_parser.py`, python-docx)
- Les styles Word donnent la structure : `Title` et `Heading n` ouvrent une section.
- La ligne « Source : … » en tête des notes est ignorée : c'est une métadonnée.
- Les tableaux éventuels sont lus ligne par ligne.

### Nettoyage commun (`cleaning.py`, module `re`)
Appliqué à la fin de chaque parseur, dans cet ordre :
1. `fix_encoding` : répare le texte UTF-8 mal décodé (`Ã©` → `é`).
2. `normalize_unicode` : forme NFC, ligatures (`ﬁ` → `fi`), espaces insécables, trait d'union conditionnel, apostrophes typographiques.
3. `dehyphenate` : recolle les mots coupés en fin de ligne.
4. `fix_spacing` : espaces multiples, espace avant `,` `.` `)`, espace après une élision (`l' Internet` → `l'Internet`). Les espaces avant `; : ! ?` sont conservées, car elles sont correctes en français.

## 4. Résultats

| Format | Documents | Caractères en entrée | Caractères après nettoyage | Mots |
|---|---|---|---|---|
| PDF | 10 | 705 935 (texte extrait) | 698 423 | 114 779 |
| TXT | 11 | 1 159 893 | 840 669 (−28 %) | 140 443 |
| HTML | 12 | 2 283 049 (code source) | 223 913 (−90 %) | 36 571 |
| DOCX | 8 | 149 934 | 145 913 | 23 732 |
| **Total** | **41** | | **1 908 918** | **315 525** |

- **Langues détectées :** 24 documents en anglais et 17 en français, ce qui correspond à l'audit de l'étape 1.
- **Le HTML diminue de 90 %** : la plus grande partie d'une page web est du code et des menus.
- **Le TXT perd 28 %** : il s'agit des en-têtes, pieds de page, sommaires et schémas des RFC.

## 5. Limites connues

- **`pdf04` (Baran) : 0 mot.** Il faut installer Tesseract pour que l'OCR prenne le relais (voir le README). En attendant, la question F09 ne peut pas réussir.
- **`pdf07` (BBN) :** la page de garde, numérisée par le DTIC, contient du bruit d'OCR (« AMOVED&Y'CFl… »). Le reste du rapport est propre.
- **`html04` (CERN) :** seulement 184 mots utiles. C'est un candidat au remplacement.
- **Abréviations :** certaines abréviations ou cas particuliers peuvent encore produire de faux débuts de paragraphe dans les PDF. C'est sans effet notable sur la recherche.

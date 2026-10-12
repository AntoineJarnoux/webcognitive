"""Chemins et paramètres partagés par tout le projet."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
EMBEDDINGS_DIR = DATA_DIR / "embeddings"
METADATA_FILE = DATA_DIR / "corpus_metadata.json"
VALIDATION_FILE = DATA_DIR / "validation_questions.json"

# Étape 3 : valeurs retenues après l'évaluation (voir docs/etape3_chunking_embeddings.md)
CHUNK_SIZE = 500        # caractères
CHUNK_OVERLAP = 100     # caractères partagés entre deux segments consécutifs
CHUNK_MIN_SIZE = 100    # un dernier segment plus court est fusionné avec le précédent
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_HEADER = False         # « titre (auteur, année) » avant chaque segment : testé, n'améliore pas ce modèle
EMBEDDING_MAX_SEQ_LENGTH = None  # tokens lus par le modèle (None : 128, sa valeur d'entraînement ; 256 testé, moins bon)
QUERY_PREFIX = ""                # préfixes exigés par certains modèles (e5 : « query: » / « passage: »)
PASSAGE_PREFIX = ""

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

# Étape 4 : base vectorielle (ChromaDB) et API REST (FastAPI)
VECTORDB_DIR = DATA_DIR / "vectordb"  # base ChromaDB enregistrée sur disque (régénérable, ignorée par Git)
COLLECTION_NAME = "corpus"
SEARCH_K = 5             # nombre de segments renvoyés par défaut
SEARCH_K_MAX = 50
HYBRID_CANDIDATES = 50   # recherche hybride : candidats pris de chaque côté avant la fusion
RRF_K = 60               # constante de la fusion par rangs (Reciprocal Rank Fusion), valeur usuelle
API_HOST = "127.0.0.1"
API_PORT = 8000

"""Chemins et paramètres partagés par tout le projet."""
import os
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


def _vectordb_dir() -> Path:
    """Dossier de la base ChromaDB (régénérable, ignoré par Git).

    Sous Windows, ChromaDB n'arrive pas à relire son index HNSW si le chemin contient
    des accents (ex. « D:\\école\\… »). Dans ce cas, la base est rangée dans
    %LOCALAPPDATA%\\webcognitive\\vectordb. La variable d'environnement
    WEBCOGNITIVE_VECTORDB_DIR permet de choisir un autre dossier.
    """
    if os.environ.get("WEBCOGNITIVE_VECTORDB_DIR"):
        return Path(os.environ["WEBCOGNITIVE_VECTORDB_DIR"])
    default = DATA_DIR / "vectordb"
    if os.name == "nt" and not str(default).isascii():
        return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "webcognitive" / "vectordb"
    return default


VECTORDB_DIR = _vectordb_dir()  # base ChromaDB enregistrée sur disque
COLLECTION_NAME = "corpus"
SEARCH_K = 5             # nombre de segments renvoyés par défaut
SEARCH_K_MAX = 50
HYBRID_CANDIDATES = 50   # recherche hybride : candidats pris de chaque côté avant la fusion
RRF_K = 60               # constante de la fusion par rangs (Reciprocal Rank Fusion), valeur usuelle
API_HOST = "127.0.0.1"
API_PORT = 8000

# Étape 5 : RAG avec un LLM local (Ollama)
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
LLM_MODEL = os.environ.get("WEBCOGNITIVE_LLM", "mistral")  # autre choix plus léger : llama3.2:3b
LLM_TEMPERATURE = 0.1    # proche de 0 : réponses factuelles et stables, peu d'« imagination »
LLM_NUM_CTX = 4096       # tokens que le LLM peut lire (consigne + extraits + question)
LLM_TIMEOUT = 300        # secondes (le premier appel charge le modèle en mémoire)
RAG_K = 8                # extraits donnés au LLM (8 : meilleur résultat que 5, voir docs/etape5_resultats.md)
RAG_MODE = "hybrid"      # sens + mots-clés : retrouve mieux les noms propres (« selon Clark », « Mitranet »)
RAG_MIN_SCORE = 0.35     # garde-fou : sous ce cosinus, la question est jugée hors sujet sans appeler le LLM

# Étape 7 : dataviz
QUESTION_LOG = DATA_DIR / "logs" / "questions.jsonl"   # questions posées à l'assistant (local, ignoré par Git)
MAP_FILE = DATA_DIR / "analytics" / "carte_2d.json"     # projection 2D des vecteurs (scripts/carte_vecteurs.py)

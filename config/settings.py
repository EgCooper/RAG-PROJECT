from dotenv import load_dotenv
import os
load_dotenv()

# API Keys
GROQ_API_KEY    = os.getenv("GROQ_API_KEY")
MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY")

# LLM - provider: "minimax" or "groq"
LLM_PROVIDER      = os.getenv("LLM_PROVIDER", "minimax")
MINIMAX_BASE_URL  = "https://api.minimax.io/v1"
MINIMAX_LLM_MODEL = os.getenv("MINIMAX_LLM_MODEL", "MiniMax-M2.7")
GROQ_LLM_MODEL    = os.getenv("GROQ_LLM_MODEL", "llama-3.3-70b-versatile")

# Modelos
EMBEDDING_MODEL = "BAAI/bge-m3"

# Chunking
CHUNK_SIZE       = 1000
CHUNK_OVERLAP    = 300
MIN_CHUNK_CHARS  = 30
TABLE_CHUNK_SIZE = 800

# Weaviate
WEAVIATE_HOST       = "localhost"
WEAVIATE_PORT       = 8080
WEAVIATE_COLLECTION = "Documento"

# PostgreSQL
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://rag:rag@localhost:5432/rag_ach",
)
DEFAULT_USER_NAME = os.getenv("DEFAULT_USER_NAME", "default")


UPLOAD_MAX_MB = int(os.getenv("UPLOAD_MAX_MB", "50"))
PENDING_UPLOAD_DIR = os.getenv("PENDING_UPLOAD_DIR", "uploads/pending")
ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".csv", ".docx", ".md", ".ppt", ".pptx"}
UPLOAD_BATCH_MAX_FILES = int(os.getenv("UPLOAD_BATCH_MAX_FILES", "100"))

# Retrieval
TOP_K_CHUNKS         = 16
HYBRID_ALPHA         = 0.3
TABLE_QUERY_MAX      = 80
RERANK_ENABLED       = os.getenv("RERANK_ENABLED", "false").lower() == "true"
RERANK_MODEL         = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-v2-m3")
RERANK_CANDIDATES    = int(os.getenv("RERANK_CANDIDATES", "30"))
DEDUP_ENABLED = os.getenv("DEDUP_ENABLED", "true").lower() == "true"

# LLM
TEMPERATURE       = 0.1
MAX_TOKENS        = 4000
TOP_P             = 0.9
FREQUENCY_PENALTY = 0.1
PRESENCE_PENALTY  = 0.1

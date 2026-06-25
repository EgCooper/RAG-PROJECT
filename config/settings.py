from dotenv import load_dotenv

import os

load_dotenv()

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Modelos
EMBEDDING_MODEL = "BAAI/bge-m3"
LLM_MODEL       = "llama-3.3-70b-versatile"

# Chunking
CHUNK_SIZE    = 1000
CHUNK_OVERLAP = 100

# Weaviate
WEAVIATE_HOST       = "localhost"
WEAVIATE_PORT       = 8080
WEAVIATE_COLLECTION = "Documento"

# Retrieval
TOP_K_CHUNKS = 5

# LLM
TEMPERATURE       = 0.1
MAX_TOKENS        = 1000
TOP_P             = 0.9
FREQUENCY_PENALTY = 0.1
PRESENCE_PENALTY  = 0.1

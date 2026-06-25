# Asistente RAG - Progreso del Proyecto

## Stack Tecnológico

| Etapa | Herramienta | Detalle |
|---|---|---|
| Extracción PDF | unstructured | strategy="hi_res", languages=["spa", "eng"] |
| Chunking | langchain-text-splitters | RecursiveCharacterTextSplitter |
| Embeddings | BGE-M3 (BAAI/bge-m3) | 1024 dimensiones, 8192 tokens máx |
| Base de datos vectorial | Weaviate | Docker con volumen persistente |
| LLM | Groq (llama-3.3-70b-versatile) | temperature=0.1 |
| Orquestación | LangChain | Pipeline RAG completo |

---

## Configuración

### Parámetros definidos (config/settings.py)

```python
EMBEDDING_MODEL     = "BAAI/bge-m3"
LLM_MODEL           = "llama-3.3-70b-versatile"
CHUNK_SIZE          = 1000
CHUNK_OVERLAP       = 100
WEAVIATE_HOST       = "localhost"
WEAVIATE_PORT       = 8080
WEAVIATE_COLLECTION = "Documento"
TOP_K_CHUNKS        = 5
TEMPERATURE         = 0.1
MAX_TOKENS          = 1000
TOP_P               = 0.9
FREQUENCY_PENALTY   = 0.1
PRESENCE_PENALTY    = 0.1
```

### Variables de entorno (.env)
```
GROQ_API_KEY=tu_api_key_aqui
```

---

## Estructura del Proyecto

```
Asistente/
│
├── data/                          # PDFs fuente
│
├── src/
│   ├── ingestion/
│   │   ├── extractor.py           # extracción con unstructured
│   │   ├── chunker.py             # chunking con langchain
│   │   └── embedder.py            # embeddings con BGE-M3
│   │
│   ├── storage/
│   │   └── weaviate_client.py     # conexión y operaciones Weaviate
│   │
│   ├── retrieval/
│   │   └── retriever.py           # búsqueda semántica en Weaviate
│   │
│   ├── llm/
│   │   ├── groq_client.py         # conexión Groq
│   │   └── prompt.py              # templates de prompts
│   │
│   └── rag/
│       └── pipeline.py            # une todo el flujo
│
├── config/
│   └── settings.py                # configuración centralizada
│
├── scripts/
│   ├── index_documents.py         # indexar PDFs
│   └── query.py                   # consultas por terminal
│
├── tests/
│   └── test_pipeline.py
│
├── docker-compose.yml             # Weaviate con persistencia
├── requirements.txt
├── .env
└── .gitignore
```

---

## Dependencias

### Python
```
unstructured[all-docs]
langchain-text-splitters
langchain-huggingface
sentence-transformers
weaviate-client
groq
python-dotenv
unstructured-inference
```

### Sistema (Fedora)
```bash
sudo dnf install poppler-utils tesseract tesseract-langpack-spa tesseract-langpack-eng
```

---

## Docker - Weaviate

```yaml
version: '3.8'
services:
  weaviate:
    image: cr.weaviate.io/semitechnologies/weaviate:latest
    ports:
      - "8080:8080"
      - "50051:50051"
    volumes:
      - weaviate_data:/var/lib/weaviate
    environment:
      AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: "true"
      PERSISTENCE_DATA_PATH: "/var/lib/weaviate"
      DEFAULT_VECTORIZER_MODULE: "none"
    restart: unless-stopped
volumes:
  weaviate_data:
```

### Comandos Docker
```bash
# Levantar
docker-compose up -d

# Apagar
docker-compose down

# Limpiar base de datos
curl -X DELETE http://localhost:8080/v1/schema/Documento
```

---

## Comandos de uso

```bash
# Indexar PDFs
cd /home/vpinto/Documents/Cooper/Asistente
python scripts/index_documents.py

# Consultar por terminal
python scripts/query.py
```

---

## Estado actual

- [x] Extracción de PDFs con unstructured
- [x] Chunking con RecursiveCharacterTextSplitter
- [x] Embeddings con BGE-M3
- [x] Almacenamiento en Weaviate con persistencia
- [x] LLM con Groq
- [x] Prompt optimizado para documentación técnica
- [x] Pipeline RAG completo end-to-end
- [x] Consultas por terminal interactiva
- [x] Script de indexación masiva
- [ ] Interfaz Streamlit
- [ ] Refinamiento de respuestas

---

## Pendiente

1. **Interfaz Streamlit** — UI web para usuarios finales
2. **Refinamiento de respuestas** — mejorar calidad del RAG
3. **Subir a GitHub** — repositorio del proyecto

---

## Notas importantes

- Los PDFs van en la carpeta `data/`
- El `.env` nunca debe subirse al repo (está en `.gitignore`)
- Weaviate debe estar corriendo antes de indexar o consultar
- BGE-M3 se descarga la primera vez (~2.27GB), luego queda en caché
- Ejecutar siempre desde la raíz del proyecto

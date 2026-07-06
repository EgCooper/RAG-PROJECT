# Setup — Asistente RAG ACH

Guía para levantar el proyecto en Windows (Linux/macOS: mismos pasos, rutas distintas).

## Requisitos

| Componente | Versión | Para qué |
|------------|---------|----------|
| Python | 3.12 | Runtime |
| Docker | reciente | Weaviate |
| Tesseract OCR | 5.x + `spa` | PDFs con `hi_res` |
| Poppler | reciente | Render PDF en unstructured |

## 1. Clonar e instalar

```powershell
cd RAG-PROJECT
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 2. Dependencias de sistema

**Tesseract (Windows):** instalar desde [UB-Mannheim](https://github.com/UB-Mannheim/tesseract/wiki) e incluir en PATH. Paquete de idioma `spa`.

**Poppler:** descargar binarios y agregar `bin` al PATH.

**Weaviate:**

```powershell
docker compose up -d
```

## 3. Configuración

```powershell
copy .env.example .env
```

Editar `.env` con tu API key (MiniMax o Groq).

Variables opcionales:

| Variable | Default | Descripción |
|----------|---------|-------------|
| `RERANK_ENABLED` | `true` | Reranking cross-encoder |
| `DEDUP_ENABLED` | `true` | Quitar chunks duplicados |
| `RERANK_CANDIDATES` | `30` | Candidatos antes del rerank |

## 4. Verificar entorno

```powershell
python scripts/health_check.py
python scripts/health_check.py --skip-llm
```

## 5. Indexar PDFs

Colocar PDFs en `data/` y ejecutar:

```powershell
python scripts/index_documents.py
```

Reindexar el mismo PDF **reemplaza** chunks previos (no duplica).

## 6. Consultar

```powershell
python scripts/query.py
```

Cada pregunta es independiente (sin historial de conversación en el servidor).

## 8. API + Frontend (chat web)

**Terminal 1 — API (puerto 8000):**

```powershell
pip install fastapi uvicorn
uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 — Frontend (puerto 5173):**

```powershell
cd frontend
npm install
npm run dev
```

Abrir http://localhost:5173

Requisitos: Weaviate corriendo, PDFs indexados, `.env` con API key LLM.

## 9. Evaluar calidad

```powershell
python scripts/eval_rag.py --solo-retrieval
python scripts/eval_rag.py --output eval/resultados.json
```

## Tablas ACH soportadas (`tabla_id`)

| ID | Documento típico | Consulta ejemplo |
|----|------------------|------------------|
| `excepciones` | Manual Operación | `lista todos los códigos de excepción` |
| `abonabilidad` | Especificación Webservices | `lista códigos de abonabilidad` |
| `parametros` | Manual Operación | `lista parámetros COD_ACH` |
| `jobs` | Manual Operación | `lista jobs del scheduler` |

Tras cambios en `config/tables_ach.py` o `chunker.py`, **reindexar**.

## Filtro por documento

Si la pregunta menciona el documento, el retrieval filtra automáticamente:

- *"en el manual…"* → Manual Operación
- *"en la guía…"* → Guía implementación
- *"webservice / especificación…"* → Especificación Webservices

## Estructura

```
data/           PDFs fuente
eval/           Dataset y resultados de evaluación
scripts/        index_documents, query, eval_rag, health_check
src/ingestion/  extracción, chunking, embeddings
src/retrieval/  retriever, reranker, dedup
src/storage/    Weaviate
src/llm/        MiniMax / Groq
config/         settings, tablas ACH, validación env
src/api/          FastAPI
frontend/         React (Vite)
```

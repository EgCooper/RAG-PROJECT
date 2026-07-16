# Setup — Asistente RAG (multi-proyecto)

Guía para levantar el proyecto en Windows (Linux/macOS: mismos pasos, rutas distintas).

## Requisitos

| Componente | Versión | Para qué |
|------------|---------|----------|
| Python | 3.12 | Runtime |
| Docker | reciente | Weaviate + PostgreSQL |
| Tesseract OCR | 5.x + `spa` | PDFs con `hi_res` |
| Poppler | reciente | Render PDF en unstructured |

## Proyectos

El asistente aísla **chats**, **documentos** e **índice Weaviate** por proyecto:

| slug | Nombre | Notas |
|------|--------|--------|
| `ach` | ACH | Default; tablas ACH / prompt ACH |
| `feel` | FEEL | Corpus propio |
| `banca` | BANCA | Corpus propio |

- UI: selector en el sidebar.
- API: header `X-Proyecto-Slug: ach`.
- Weaviate: multi-tenancy (`tenant = slug`).
- Tras migrar a multi-tenant: **reindexar** (la colección se recrea).

## 1. Clonar e instalar

```powershell
cd RAG-PROJECT
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 2. Infraestructura

```powershell
docker compose up -d
copy .env.example .env
```

Editar `.env` con tu API key (MiniMax o Groq).

```powershell
python scripts/init_db.py
python scripts/health_check.py --skip-llm
```

## 3. Indexar (por proyecto)

```powershell
python scripts/index_documents.py --proyecto ach --todos
python scripts/index_documents.py --proyecto feel --todos
python scripts/index_documents.py --proyecto banca --todos
python scripts/index_documents.py --proyecto ach --archivo manual.pdf --forzar
```

También desde la UI (Documentos) con el proyecto activo en el sidebar.

## 4. API + Frontend

```powershell
uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000
```

```powershell
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

Abrir http://localhost:5173 y elegir proyecto en el sidebar.

## 5. CLI / eval

```powershell
python scripts/query.py --proyecto ach
python eval/run_eval.py --proyecto ach --limit 5
```

## 6. Crear otro proyecto

```powershell
curl -X POST http://localhost:8000/api/proyectos ^
  -H "Content-Type: application/json" ^
  -d "{\"nombre\":\"Mi Sistema\",\"slug\":\"mi-sistema\"}"
```

## Modelo

```
proyectos
 ├── documents
 └── chat_sessions → chat_messages
```

Weaviate colección `Documento` + tenant por `proyecto.slug`.

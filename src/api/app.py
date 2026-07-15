from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import (
    CORS_ORIGIN_REGEX,
    CORS_ORIGINS,
    UPLOAD_BATCH_MAX_FILES,
    UPLOAD_MAX_MB,
)
from src.api.deps import set_pipeline
from src.api.routes import chat, documents, projects, sessions
from src.db.bootstrap import inicializar_db
from src.db.engine import SessionLocal, verificar_conexion
from src.db import projects_repository as proy_repo
from src.ingestion.index_queue import obtener_cola_indexacion, recuperar_trabajos_pendientes
from src.llm.llm_factory import info_proveedor
from src.rag.pipeline import RAGPipeline


@asynccontextmanager
async def lifespan(app: FastAPI):
    inicializar_db()
    pipeline = RAGPipeline()
    set_pipeline(pipeline)
    with SessionLocal() as db:
        for proy in proy_repo.listar_proyectos(db, solo_activos=True):
            try:
                pipeline.asegurar_tenant_proyecto(proy.slug)
            except Exception as e:
                print(f"AVISO: no se pudo crear tenant '{proy.slug}': {e}")
    obtener_cola_indexacion()
    recuperar_trabajos_pendientes()
    yield
    obtener_cola_indexacion().detener()
    if pipeline:
        pipeline.cerrar()


app = FastAPI(title="RAG Multi-Proyecto API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(sessions.router)
app.include_router(chat.router)
app.include_router(documents.router)


@app.get("/api/health")
def health():
    db_status = "ok"
    try:
        verificar_conexion()
    except Exception:
        db_status = "error"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "llm": info_proveedor(),
        "postgres": db_status,
        "upload_max_mb": UPLOAD_MAX_MB,
        "upload_batch_max_files": UPLOAD_BATCH_MAX_FILES,
    }

import os
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.rag.pipeline import RAGPipeline
from src.llm.llm_factory import info_proveedor

_pipeline: RAGPipeline | None = None


def _serializar_chunks(chunks):
    return [
        {
            "fuente": os.path.basename(c.get("fuente", "")),
            "pagina": c.get("pagina", 0),
        }
        for c in chunks
    ]


class ChatRequest(BaseModel):
    pregunta: str = Field(..., min_length=1)
    session_id: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    respuesta: str
    chunks: list[dict]


class SessionRequest(BaseModel):
    session_id: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _pipeline
    _pipeline = RAGPipeline()
    yield
    if _pipeline:
        _pipeline.cerrar()


app = FastAPI(title="RAG ACH API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "llm": info_proveedor(),
    }


@app.post("/api/chat", response_model=ChatResponse)
def chat(body: ChatRequest):
    if not _pipeline:
        raise HTTPException(503, "Pipeline no inicializado")

    session_id = body.session_id or str(uuid.uuid4())

    try:
        respuesta, chunks = _pipeline.consultar(body.pregunta.strip())
    except Exception as e:
        raise HTTPException(500, f"Error al consultar: {e}") from e

    return ChatResponse(
        session_id=session_id,
        respuesta=respuesta,
        chunks=_serializar_chunks(chunks),
    )


@app.post("/api/chat/limpiar")
def limpiar_chat(body: SessionRequest):
    """Sin historial en servidor; el front resetea la UI con este endpoint."""
    return {"ok": True, "session_id": body.session_id}

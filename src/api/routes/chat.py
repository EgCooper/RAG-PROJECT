import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.deps import get_db, get_default_user, get_pipeline
from src.db import repository
from src.db.models import User
from src.db.schemas import ChatRequest, ChatResponse
from src.rag.pipeline import RAGPipeline

router = APIRouter(prefix="/api", tags=["chat"])


def _serializar_chunks(chunks):
    return [
        {
            "fuente": os.path.basename(c.get("fuente", "")),
            "pagina": c.get("pagina", 0),
        }
        for c in chunks
    ]


@router.post("/chat", response_model=ChatResponse)
def chat(
    body: ChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_default_user),
    pipeline: RAGPipeline = Depends(get_pipeline),
):
    sesion = repository.obtener_o_crear_sesion(db, user.id, body.session_id)
    es_primera = len(sesion.messages) == 0
    pregunta = body.pregunta.strip()

    repository.agregar_mensaje(db, sesion.id, "user", pregunta)

    try:
        respuesta, chunks = pipeline.consultar(pregunta)
    except Exception as e:
        raise HTTPException(500, f"Error al consultar: {e}") from e

    chunks_api = _serializar_chunks(chunks)
    repository.agregar_mensaje(db, sesion.id, "assistant", respuesta, chunks_api)
    repository.actualizar_sesion_tras_mensaje(
        db,
        sesion,
        primera_pregunta=pregunta if es_primera else None,
    )

    return ChatResponse(
        session_id=sesion.id,
        respuesta=respuesta,
        chunks=chunks_api,
    )


@router.post("/chat/limpiar")
def limpiar_chat(
    db: Session = Depends(get_db),
    user: User = Depends(get_default_user),
):
    """Compatibilidad: crea una sesión nueva (el front ya no depende del id anterior)."""
    sesion = repository.crear_sesion(db, user.id)
    return {"ok": True, "session_id": str(sesion.id)}

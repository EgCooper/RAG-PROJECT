import json
import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from src.api.deps import get_db, get_default_user, get_pipeline, get_proyecto_activo
from src.db import documents_repository as doc_repo
from src.db import repository
from src.db.engine import SessionLocal
from src.db.models import Proyecto, User
from src.db.schemas import ChatRequest, ChatResponse
from src.rag.pipeline import RAGPipeline
from src.rag.errors import IndiceVectorialError
from src.retrieval.attribution import marcar_chunks_usados

router = APIRouter(prefix="/api", tags=["chat"])


def _serializar_chunks(chunks, nombres_fuentes=None):
    nombres_fuentes = nombres_fuentes or {}
    resultado = []
    for c in chunks:
        fuente = c.get("fuente", "")
        visible = nombres_fuentes.get(fuente) or os.path.basename(fuente)
        resultado.append({
            "fuente": visible,
            "pagina": c.get("pagina", 0),
            "usada": bool(c.get("usada", False)),
        })
    return resultado


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/chat", response_model=ChatResponse)
def chat(
    body: ChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_default_user),
    proyecto: Proyecto = Depends(get_proyecto_activo),
    pipeline: RAGPipeline = Depends(get_pipeline),
):
    sesion = repository.obtener_o_crear_sesion(
        db, proyecto.id, body.session_id, user_id=user.id
    )
    es_primera = len(sesion.messages) == 0
    pregunta = body.pregunta.strip()

    repository.agregar_mensaje(db, sesion.id, "user", pregunta)

    fuentes = doc_repo.resolver_fuentes_filtro_chat(db, proyecto.id, body.filtro)

    try:
        respuesta, chunks = pipeline.consultar(
            pregunta, proyecto, fuentes_permitidas=fuentes
        )
    except IndiceVectorialError as e:
        raise HTTPException(503, str(e)) from e
    except Exception as e:
        raise HTTPException(500, "Error inesperado al consultar. Intentá de nuevo.") from e

    chunks = marcar_chunks_usados(respuesta, chunks)
    nombres = doc_repo.nombres_por_fuentes(
        db, proyecto.id, [c.get("fuente", "") for c in chunks]
    )
    chunks_api = _serializar_chunks(chunks, nombres)
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
        proyecto_slug=proyecto.slug,
    )


@router.post("/chat/stream")
def chat_stream(
    body: ChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_default_user),
    proyecto: Proyecto = Depends(get_proyecto_activo),
    pipeline: RAGPipeline = Depends(get_pipeline),
):
    """SSE: meta → token* → done | error. El prompt RAG no cambia."""
    sesion = repository.obtener_o_crear_sesion(
        db, proyecto.id, body.session_id, user_id=user.id
    )
    es_primera = len(sesion.messages) == 0
    pregunta = body.pregunta.strip()
    session_id = sesion.id
    proyecto_id = proyecto.id
    proyecto_slug = proyecto.slug
    primera_pregunta = pregunta if es_primera else None

    repository.agregar_mensaje(db, session_id, "user", pregunta)
    db.commit()

    fuentes = doc_repo.resolver_fuentes_filtro_chat(db, proyecto_id, body.filtro)

    try:
        token_iter, chunks, respuesta_fija = pipeline.consultar_stream(
            pregunta, proyecto, fuentes_permitidas=fuentes
        )
    except IndiceVectorialError as e:
        raise HTTPException(503, str(e)) from e
    except Exception:
        raise HTTPException(500, "Error inesperado al consultar. Intentá de nuevo.") from e

    def evento_gen():
        yield _sse({
            "type": "meta",
            "session_id": str(session_id),
            "proyecto_slug": proyecto_slug,
        })

        partes: list[str] = []
        try:
            if respuesta_fija is not None:
                partes.append(respuesta_fija)
                yield _sse({"type": "token", "text": respuesta_fija})
            elif token_iter is not None:
                for token in token_iter:
                    partes.append(token)
                    yield _sse({"type": "token", "text": token})

            respuesta = "".join(partes)
            chunks_marcados = marcar_chunks_usados(respuesta, list(chunks or []))

            db_local = SessionLocal()
            try:
                nombres = doc_repo.nombres_por_fuentes(
                    db_local,
                    proyecto_id,
                    [c.get("fuente", "") for c in chunks_marcados],
                )
                chunks_api = _serializar_chunks(chunks_marcados, nombres)
                repository.agregar_mensaje(
                    db_local, session_id, "assistant", respuesta, chunks_api
                )
                sesion_local = repository.obtener_sesion(
                    db_local, session_id, proyecto_id
                )
                if sesion_local:
                    repository.actualizar_sesion_tras_mensaje(
                        db_local,
                        sesion_local,
                        primera_pregunta=primera_pregunta,
                    )
            finally:
                db_local.close()

            yield _sse({
                "type": "done",
                "session_id": str(session_id),
                "respuesta": respuesta,
                "chunks": chunks_api,
                "proyecto_slug": proyecto_slug,
            })
        except Exception as e:
            yield _sse({
                "type": "error",
                "detail": str(e) or "Error durante el streaming",
            })

    return StreamingResponse(
        evento_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/chat/limpiar")
def limpiar_chat(
    db: Session = Depends(get_db),
    user: User = Depends(get_default_user),
    proyecto: Proyecto = Depends(get_proyecto_activo),
):
    """Compatibilidad: crea una sesión nueva en el proyecto activo."""
    sesion = repository.crear_sesion(db, proyecto.id, user_id=user.id)
    return {"ok": True, "session_id": str(sesion.id)}

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.deps import get_db, get_default_user
from src.db import repository
from src.db.models import User
from src.db.schemas import SessionCreateResponse, SessionDetail, SessionSummary

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("", response_model=list[SessionSummary])
def listar_sesiones(db: Session = Depends(get_db), user: User = Depends(get_default_user)):
    return repository.listar_sesiones(db, user.id)


@router.post("", response_model=SessionCreateResponse)
def crear_sesion(db: Session = Depends(get_db), user: User = Depends(get_default_user)):
    sesion = repository.crear_sesion(db, user.id)
    return sesion


@router.delete("")
def eliminar_todas_sesiones(
    db: Session = Depends(get_db),
    user: User = Depends(get_default_user),
):
    eliminados = repository.eliminar_todas_sesiones(db, user.id)
    return {"ok": True, "eliminados": eliminados}


@router.get("/{session_id}", response_model=SessionDetail)
def obtener_sesion(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_default_user),
):
    sesion = repository.obtener_sesion(db, session_id, user.id)
    if not sesion:
        raise HTTPException(404, "Sesión no encontrada")

    return SessionDetail(
        id=sesion.id,
        titulo=sesion.titulo,
        creado_en=sesion.creado_en,
        actualizado_en=sesion.actualizado_en,
        mensajes=[
            {
                "id": m.id,
                "rol": m.rol,
                "texto": m.texto,
                "chunks": m.chunks,
                "creado_en": m.creado_en,
            }
            for m in sesion.messages
        ],
    )


@router.delete("/{session_id}")
def eliminar_sesion(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_default_user),
):
    if not repository.eliminar_sesion(db, session_id, user.id):
        raise HTTPException(404, "Sesión no encontrada")
    return {"ok": True}

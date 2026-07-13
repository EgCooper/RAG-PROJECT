import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from config.settings import DEFAULT_USER_NAME
from src.db.models import ChatMessage, ChatSession, User

_TITULO_MAX = 80


def _ahora():
    return datetime.now(timezone.utc)


def _truncar_titulo(texto: str) -> str:
    limpio = " ".join(texto.split())
    if len(limpio) <= _TITULO_MAX:
        return limpio
    return limpio[: _TITULO_MAX - 1] + "…"


def obtener_o_crear_usuario_default(db: Session) -> User:
    usuario = db.scalar(select(User).where(User.nombre == DEFAULT_USER_NAME))
    if usuario:
        return usuario
    usuario = User(nombre=DEFAULT_USER_NAME)
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


def listar_sesiones(db: Session, user_id: uuid.UUID) -> list[ChatSession]:
    return list(
        db.scalars(
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.actualizado_en.desc())
        )
    )


def crear_sesion(db: Session, user_id: uuid.UUID) -> ChatSession:
    sesion = ChatSession(user_id=user_id)
    db.add(sesion)
    db.commit()
    db.refresh(sesion)
    return sesion


def obtener_sesion(db: Session, session_id: uuid.UUID, user_id: uuid.UUID) -> ChatSession | None:
    return db.scalar(
        select(ChatSession)
        .options(joinedload(ChatSession.messages))
        .where(ChatSession.id == session_id, ChatSession.user_id == user_id)
    )


def eliminar_sesion(db: Session, session_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    sesion = db.scalar(
        select(ChatSession)
        .options(joinedload(ChatSession.messages))
        .where(ChatSession.id == session_id, ChatSession.user_id == user_id)
    )
    if not sesion:
        return False
    db.delete(sesion)
    db.commit()
    return True


def eliminar_todas_sesiones(db: Session, user_id: uuid.UUID) -> int:
    sesiones = db.scalars(
        select(ChatSession)
        .options(selectinload(ChatSession.messages))
        .where(ChatSession.user_id == user_id)
    ).all()
    for sesion in sesiones:
        db.delete(sesion)
    db.commit()
    return len(sesiones)


def agregar_mensaje(
    db: Session,
    session_id: uuid.UUID,
    rol: str,
    texto: str,
    chunks: list[dict] | None = None,
) -> ChatMessage:
    mensaje = ChatMessage(
        session_id=session_id,
        rol=rol,
        texto=texto,
        chunks=chunks,
    )
    db.add(mensaje)
    db.commit()
    db.refresh(mensaje)
    return mensaje


def actualizar_sesion_tras_mensaje(
    db: Session,
    sesion: ChatSession,
    primera_pregunta: str | None = None,
) -> ChatSession:
    sesion.actualizado_en = _ahora()
    if primera_pregunta and sesion.titulo == "Nueva conversación":
        sesion.titulo = _truncar_titulo(primera_pregunta)
    db.commit()
    db.refresh(sesion)
    return sesion


def obtener_o_crear_sesion(
    db: Session, user_id: uuid.UUID, session_id: uuid.UUID | None
) -> ChatSession:
    if session_id:
        sesion = obtener_sesion(db, session_id, user_id)
        if sesion:
            return sesion
    return crear_sesion(db, user_id)

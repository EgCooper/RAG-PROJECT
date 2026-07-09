import os
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from config.settings import ALLOWED_UPLOAD_EXTENSIONS, DATA_DIR
from src.db.models import Document
from src.ingestion.index_registry import cargar_registro, normalizar_clave
from src.storage.weaviate_client import listar_fuentes_indexadas, normalizar_fuente


def _ahora():
    return datetime.now(timezone.utc)


def listar_documentos(db: Session, user_id: uuid.UUID) -> list[Document]:
    return list(
        db.scalars(
            select(Document)
            .where(Document.user_id == user_id)
            .order_by(Document.actualizado_en.desc())
        )
    )


def obtener_documento(db: Session, doc_id: uuid.UUID, user_id: uuid.UUID) -> Document | None:
    return db.scalar(
        select(Document).where(Document.id == doc_id, Document.user_id == user_id)
    )


def obtener_por_ruta(db: Session, ruta: str) -> Document | None:
    norm = normalizar_fuente(ruta)
    return db.scalar(select(Document).where(Document.ruta == norm))


def crear_documento(
    db: Session,
    user_id: uuid.UUID,
    nombre: str,
    ruta: str,
    extension: str,
    tamano_bytes: int,
    estado: str = "indexando",
) -> Document:
    doc = Document(
        user_id=user_id,
        nombre=nombre,
        ruta=normalizar_fuente(ruta),
        extension=extension,
        tamano_bytes=tamano_bytes,
        estado=estado,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def actualizar_tras_indexar(
    db: Session,
    doc: Document,
    *,
    ok: bool,
    perfil: str = "",
    chunks: int = 0,
    error: str | None = None,
) -> Document:
    doc.estado = "indexado" if ok else "error"
    doc.perfil = perfil
    doc.chunks = chunks
    doc.error = error
    doc.actualizado_en = _ahora()
    db.commit()
    db.refresh(doc)
    return doc


def eliminar_documento_db(db: Session, doc: Document) -> None:
    db.delete(doc)
    db.commit()


def _archivos_en_disco():
    if not os.path.isdir(DATA_DIR):
        return []
    archivos = []
    for nombre in os.listdir(DATA_DIR):
        if nombre.startswith("."):
            continue
        ext = os.path.splitext(nombre)[1].lower()
        if ext not in ALLOWED_UPLOAD_EXTENSIONS:
            continue
        ruta = os.path.join(DATA_DIR, nombre)
        if os.path.isfile(ruta):
            archivos.append(ruta)
    return archivos


def sincronizar_desde_disco(db: Session, user_id: uuid.UUID, cliente_weaviate) -> None:
    """Registra en Postgres PDFs/CSV en data/ que aún no están en la tabla."""
    fuentes = {normalizar_fuente(f) for f in listar_fuentes_indexadas(cliente_weaviate)}
    registro = cargar_registro()

    for ruta in _archivos_en_disco():
        norm = normalizar_fuente(ruta)
        if obtener_por_ruta(db, norm):
            continue

        nombre = os.path.basename(ruta)
        ext = os.path.splitext(nombre)[1].lower()
        tamano = os.path.getsize(ruta)
        en_indice = norm in fuentes
        entrada = registro.get(normalizar_clave(ruta), {})
        chunks = entrada.get("chunks", 0) if en_indice else 0

        doc = Document(
            user_id=user_id,
            nombre=nombre,
            ruta=norm,
            extension=ext,
            tamano_bytes=tamano,
            perfil="",
            chunks=chunks,
            estado="indexado" if en_indice else "pendiente",
        )
        db.add(doc)

    db.commit()

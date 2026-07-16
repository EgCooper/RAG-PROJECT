import uuid
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.orm import Session, joinedload

from config.documentos import SECCION_DEFAULT, normalizar_seccion
from src.db.models import Document
from src.storage.weaviate_client import normalizar_fuente

FUENTE_PREFIX = "doc/"


def _ahora():
    return datetime.now(timezone.utc)


def fuente_documento(doc_id: uuid.UUID) -> str:
    return f"{FUENTE_PREFIX}{doc_id}"


def id_desde_fuente(fuente: str) -> uuid.UUID | None:
    if not fuente or not fuente.startswith(FUENTE_PREFIX):
        return None
    try:
        return uuid.UUID(fuente[len(FUENTE_PREFIX) :])
    except ValueError:
        return None


def migrar_schema_documentos(engine) -> None:
    with engine.begin() as conn:
        col = conn.execute(
            text("""
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'documents' AND column_name = 'seccion'
            """)
        ).scalar()
        if not col:
            conn.execute(
                text(
                    "ALTER TABLE documents ADD COLUMN seccion VARCHAR(20) "
                    f"NOT NULL DEFAULT '{SECCION_DEFAULT}'"
                )
            )


def listar_documentos(
    db: Session, proyecto_id: uuid.UUID, seccion: str | None = None
) -> list[Document]:
    q = select(Document).where(Document.proyecto_id == proyecto_id)
    if seccion:
        q = q.where(Document.seccion == normalizar_seccion(seccion))
    q = q.order_by(Document.actualizado_en.desc())
    return list(db.scalars(q))


def obtener_documento(
    db: Session, doc_id: uuid.UUID, proyecto_id: uuid.UUID
) -> Document | None:
    return db.scalar(
        select(Document).where(Document.id == doc_id, Document.proyecto_id == proyecto_id)
    )


def obtener_documento_por_id(db: Session, doc_id: uuid.UUID) -> Document | None:
    return db.scalar(
        select(Document)
        .options(joinedload(Document.proyecto))
        .where(Document.id == doc_id)
    )


def obtener_por_nombre(
    db: Session, proyecto_id: uuid.UUID, nombre: str
) -> Document | None:
    return db.scalar(
        select(Document).where(
            Document.proyecto_id == proyecto_id,
            Document.nombre == nombre,
        )
    )


def nombres_por_fuentes(
    db: Session, proyecto_id: uuid.UUID, fuentes: list[str]
) -> dict[str, str]:
    ids = []
    for fuente in fuentes:
        doc_id = id_desde_fuente(fuente)
        if doc_id:
            ids.append(doc_id)
    if not ids:
        return {}

    docs = db.scalars(
        select(Document).where(
            Document.proyecto_id == proyecto_id,
            Document.id.in_(ids),
        )
    )
    return {fuente_documento(d.id): d.nombre for d in docs}


def fuentes_por_seccion(
    db: Session, proyecto_id: uuid.UUID, seccion: str
) -> list[str]:
    seccion_n = normalizar_seccion(seccion)
    docs = db.scalars(
        select(Document).where(
            Document.proyecto_id == proyecto_id,
            Document.seccion == seccion_n,
            Document.estado == "indexado",
        )
    )
    return [normalizar_fuente(d.ruta) for d in docs]


def fuentes_por_ids(
    db: Session, proyecto_id: uuid.UUID, document_ids: list[uuid.UUID]
) -> list[str]:
    if not document_ids:
        return []
    docs = db.scalars(
        select(Document).where(
            Document.proyecto_id == proyecto_id,
            Document.id.in_(document_ids),
            Document.estado == "indexado",
        )
    )
    return [normalizar_fuente(d.ruta) for d in docs]


def resolver_fuentes_filtro_chat(
    db: Session,
    proyecto_id: uuid.UUID,
    filtro: str,
) -> list[str] | None:
    """
    None = sin filtro (todos).
    Lista (puede estar vacía) = restringir retrieval a esas fuentes.
    """
    modo = (filtro or "todos").lower()
    if modo == "todos":
        return None
    if modo in ("documentos", "manuales"):
        return fuentes_por_seccion(db, proyecto_id, "manual")
    if modo == "informes":
        return fuentes_por_seccion(db, proyecto_id, "informe")
    return None


def crear_documento(
    db: Session,
    proyecto_id: uuid.UUID,
    nombre: str,
    extension: str,
    tamano_bytes: int,
    estado: str = "pendiente",
    user_id: uuid.UUID | None = None,
    seccion: str = SECCION_DEFAULT,
) -> Document:
    doc_id = uuid.uuid4()
    doc = Document(
        id=doc_id,
        proyecto_id=proyecto_id,
        user_id=user_id,
        nombre=nombre,
        ruta=normalizar_fuente(fuente_documento(doc_id)),
        extension=extension,
        tamano_bytes=tamano_bytes,
        seccion=normalizar_seccion(seccion),
        estado=estado,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def actualizar_seccion(db: Session, doc: Document, seccion: str) -> Document:
    doc.seccion = normalizar_seccion(seccion)
    doc.actualizado_en = _ahora()
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


def eliminar_todos_documentos_db(
    db: Session, proyecto_id: uuid.UUID, seccion: str | None = None
) -> int:
    docs = listar_documentos(db, proyecto_id, seccion=seccion)
    for doc in docs:
        db.delete(doc)
    db.commit()
    return len(docs)

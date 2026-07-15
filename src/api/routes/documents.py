import os
import re
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from config.settings import ALLOWED_UPLOAD_EXTENSIONS, UPLOAD_MAX_MB
from src.api.deps import get_db, get_default_user, get_pipeline, get_proyecto_activo
from src.db import documents_repository as doc_repo
from src.db.models import Proyecto, User
from src.db.schemas import DocumentOut, DocumentUploadResponse, IndexStatsOut
from src.ingestion.index_queue import obtener_cola_indexacion, ruta_pendiente
from src.rag.errors import IndiceVectorialError, traducir_error_weaviate
from src.rag.pipeline import RAGPipeline
from src.storage.weaviate_client import eliminar_chunks_por_fuente, estadisticas_indice

router = APIRouter(prefix="/api/documents", tags=["documents"])

_UNSAFE_NAME = re.compile(r"[^\w.\- áéíóúÁÉÍÓÚñÑ]")


def _sanitizar_nombre(nombre: str) -> str:
    base = os.path.basename(nombre).strip()
    if not base:
        raise HTTPException(400, "Nombre de archivo inválido")
    limpio = _UNSAFE_NAME.sub("_", base)
    return limpio.replace(" ", "_")


@router.get("", response_model=list[DocumentOut])
def listar_documentos(
    db: Session = Depends(get_db),
    proyecto: Proyecto = Depends(get_proyecto_activo),
):
    return doc_repo.listar_documentos(db, proyecto.id)


@router.get("/index-stats", response_model=IndexStatsOut)
def estadisticas_indice_vectorial(
    db: Session = Depends(get_db),
    proyecto: Proyecto = Depends(get_proyecto_activo),
    pipeline: RAGPipeline = Depends(get_pipeline),
):
    try:
        docs = doc_repo.listar_documentos(db, proyecto.id)
        catalogo = {d.ruta for d in docs}
        return estadisticas_indice(
            pipeline.cliente_weaviate, proyecto.slug, catalogo
        )
    except Exception as exc:
        traducido = traducir_error_weaviate(exc)
        if isinstance(traducido, IndiceVectorialError):
            raise HTTPException(503, str(traducido)) from exc
        raise


@router.delete("")
def eliminar_todos_documentos(
    db: Session = Depends(get_db),
    proyecto: Proyecto = Depends(get_proyecto_activo),
    pipeline: RAGPipeline = Depends(get_pipeline),
):
    docs = doc_repo.listar_documentos(db, proyecto.id)
    for doc in docs:
        ruta_tmp = ruta_pendiente(doc.id, doc.extension)
        if os.path.isfile(ruta_tmp):
            os.remove(ruta_tmp)
        eliminar_chunks_por_fuente(pipeline.cliente_weaviate, doc.ruta, proyecto.slug)

    eliminados = doc_repo.eliminar_todos_documentos_db(db, proyecto.id)
    return {"ok": True, "eliminados": eliminados}


@router.post("/upload", response_model=DocumentUploadResponse)
async def subir_documento(
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_default_user),
    proyecto: Proyecto = Depends(get_proyecto_activo),
    pipeline: RAGPipeline = Depends(get_pipeline),
):
    if not archivo.filename:
        raise HTTPException(400, "Archivo sin nombre")

    nombre = _sanitizar_nombre(archivo.filename)
    ext = os.path.splitext(nombre)[1].lower()
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(400, f"Formato no permitido. Use: {', '.join(ALLOWED_UPLOAD_EXTENSIONS)}")

    contenido = await archivo.read()
    max_bytes = UPLOAD_MAX_MB * 1024 * 1024
    if len(contenido) > max_bytes:
        raise HTTPException(400, f"Archivo demasiado grande (máx. {UPLOAD_MAX_MB} MB)")

    existente = doc_repo.obtener_por_nombre(db, proyecto.id, nombre)
    if existente and existente.estado in ("pendiente", "indexando", "indexado"):
        raise HTTPException(409, f"Ya existe un documento con el nombre '{nombre}'")
    if existente:
        eliminar_chunks_por_fuente(
            pipeline.cliente_weaviate, existente.ruta, proyecto.slug
        )
        ruta_vieja = ruta_pendiente(existente.id, existente.extension)
        if os.path.isfile(ruta_vieja):
            os.remove(ruta_vieja)
        doc_repo.eliminar_documento_db(db, existente)

    doc = doc_repo.crear_documento(
        db,
        proyecto.id,
        nombre,
        ext,
        len(contenido),
        estado="pendiente",
        user_id=user.id,
    )

    ruta_tmp = ruta_pendiente(doc.id, ext)
    with open(ruta_tmp, "wb") as f:
        f.write(contenido)

    obtener_cola_indexacion().encolar(doc.id, ruta_tmp)

    return DocumentUploadResponse(
        documento=doc,
        mensaje="Archivo recibido. La indexación continúa en segundo plano.",
    )


@router.delete("/{document_id}")
def eliminar_documento(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    proyecto: Proyecto = Depends(get_proyecto_activo),
    pipeline: RAGPipeline = Depends(get_pipeline),
):
    doc = doc_repo.obtener_documento(db, document_id, proyecto.id)
    if not doc:
        raise HTTPException(404, "Documento no encontrado")

    ruta_tmp = ruta_pendiente(doc.id, doc.extension)
    if os.path.isfile(ruta_tmp):
        os.remove(ruta_tmp)

    eliminar_chunks_por_fuente(pipeline.cliente_weaviate, doc.ruta, proyecto.slug)
    doc_repo.eliminar_documento_db(db, doc)
    return {"ok": True, "id": str(document_id)}

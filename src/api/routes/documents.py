import os
import re
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from config.settings import ALLOWED_UPLOAD_EXTENSIONS, DATA_DIR, UPLOAD_MAX_MB
from src.api.deps import get_db, get_default_user, get_pipeline
from src.db import documents_repository as doc_repo
from src.db.models import User
from src.db.schemas import DocumentOut, DocumentUploadResponse
from src.ingestion.index_registry import eliminar_del_registro, registrar_indexacion, cargar_registro, guardar_registro
from src.rag.pipeline import RAGPipeline
from src.storage.weaviate_client import eliminar_chunks_por_fuente

router = APIRouter(prefix="/api/documents", tags=["documents"])

_UNSAFE_NAME = re.compile(r"[^\w.\- áéíóúÁÉÍÓÚñÑ]")


def _sanitizar_nombre(nombre: str) -> str:
    base = os.path.basename(nombre).strip()
    if not base:
        raise HTTPException(400, "Nombre de archivo inválido")
    limpio = _UNSAFE_NAME.sub("_", base)
    return limpio.replace(" ", "_")


def _ruta_destino(nombre: str) -> str:
    os.makedirs(DATA_DIR, exist_ok=True)
    return os.path.join(DATA_DIR, nombre)


@router.get("", response_model=list[DocumentOut])
def listar_documentos(
    db: Session = Depends(get_db),
    user: User = Depends(get_default_user),
    pipeline: RAGPipeline = Depends(get_pipeline),
):
    doc_repo.sincronizar_desde_disco(db, user.id, pipeline.cliente_weaviate)
    return doc_repo.listar_documentos(db, user.id)


@router.post("/upload", response_model=DocumentUploadResponse)
async def subir_documento(
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_default_user),
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

    ruta = _ruta_destino(nombre)
    norm = os.path.normpath(ruta).replace("\\", "/")

    existente = doc_repo.obtener_por_ruta(db, norm)
    if existente and existente.estado != "error":
        raise HTTPException(409, f"Ya existe un documento con el nombre '{nombre}'")
    if existente:
        if os.path.isfile(ruta):
            os.remove(ruta)
        doc_repo.eliminar_documento_db(db, existente)

    with open(ruta, "wb") as f:
        f.write(contenido)

    doc = doc_repo.crear_documento(
        db, user.id, nombre, norm, ext, len(contenido), estado="indexando"
    )

    resultado = pipeline.indexar(norm)
    if resultado["ok"]:
        registro = cargar_registro()
        registrar_indexacion(registro, norm, resultado["chunks"])
        guardar_registro(registro)
        doc = doc_repo.actualizar_tras_indexar(
            db,
            doc,
            ok=True,
            perfil=resultado.get("perfil", ""),
            chunks=resultado["chunks"],
        )
        mensaje = f"Indexado: {resultado['chunks']} chunks"
    else:
        doc = doc_repo.actualizar_tras_indexar(
            db,
            doc,
            ok=False,
            error=resultado.get("error", "Error desconocido"),
        )
        mensaje = "Error al indexar"

    return DocumentUploadResponse(documento=doc, mensaje=mensaje)


@router.delete("/{document_id}")
def eliminar_documento(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_default_user),
    pipeline: RAGPipeline = Depends(get_pipeline),
):
    doc = doc_repo.obtener_documento(db, document_id, user.id)
    if not doc:
        raise HTTPException(404, "Documento no encontrado")

    eliminar_chunks_por_fuente(pipeline.cliente_weaviate, doc.ruta)
    eliminar_del_registro(doc.ruta)

    ruta_disco = doc.ruta
    if not os.path.isabs(ruta_disco):
        ruta_disco = os.path.normpath(ruta_disco)
    if os.path.isfile(ruta_disco):
        os.remove(ruta_disco)

    doc_repo.eliminar_documento_db(db, doc)
    return {"ok": True, "id": str(document_id)}

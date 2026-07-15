"""Cola de indexación en background (un hilo, trabajos en serie)."""

import os
import queue
import threading
import uuid

from sqlalchemy import select

from config.settings import PENDING_UPLOAD_DIR
from src.api.deps import get_pipeline
from src.db import documents_repository as doc_repo
from src.db.engine import SessionLocal
from src.db.models import Document
from src.storage.weaviate_client import eliminar_chunks_por_fuente


def ruta_pendiente(doc_id: uuid.UUID, extension: str) -> str:
    os.makedirs(PENDING_UPLOAD_DIR, exist_ok=True)
    ext = extension if extension.startswith(".") else f".{extension}"
    return os.path.join(PENDING_UPLOAD_DIR, f"{doc_id}{ext}")


def _limpiar_archivo(ruta: str | None) -> None:
    if ruta and os.path.isfile(ruta):
        try:
            os.remove(ruta)
        except OSError:
            pass


def _procesar_trabajo(doc_id: uuid.UUID, tmp_path: str) -> None:
    db = SessionLocal()
    try:
        doc = doc_repo.obtener_documento_por_id(db, doc_id)
        if not doc:
            _limpiar_archivo(tmp_path)
            return

        tenant = doc.proyecto.slug if doc.proyecto else None
        if not tenant:
            doc_repo.actualizar_tras_indexar(
                db, doc, ok=False, error="Documento sin proyecto asociado"
            )
            return

        doc.estado = "indexando"
        doc.error = None
        db.commit()

        pipeline = get_pipeline()
        resultado = pipeline.indexar(tmp_path, fuente=doc.ruta, tenant=tenant)

        doc = doc_repo.obtener_documento_por_id(db, doc_id)
        if not doc:
            if not resultado["ok"]:
                eliminar_chunks_por_fuente(
                    pipeline.cliente_weaviate, resultado["fuente"], tenant
                )
            return

        if resultado["ok"]:
            doc_repo.actualizar_tras_indexar(
                db,
                doc,
                ok=True,
                perfil=resultado.get("perfil", ""),
                chunks=resultado["chunks"],
            )
        else:
            eliminar_chunks_por_fuente(pipeline.cliente_weaviate, doc.ruta, tenant)
            doc_repo.actualizar_tras_indexar(
                db,
                doc,
                ok=False,
                error=resultado.get("error", "Error desconocido"),
            )
    except Exception as e:
        doc = doc_repo.obtener_documento_por_id(db, doc_id)
        if doc:
            try:
                pipeline = get_pipeline()
                tenant = doc.proyecto.slug if doc.proyecto else None
                if tenant:
                    eliminar_chunks_por_fuente(
                        pipeline.cliente_weaviate, doc.ruta, tenant
                    )
            except Exception:
                pass
            doc_repo.actualizar_tras_indexar(db, doc, ok=False, error=str(e))
    finally:
        _limpiar_archivo(tmp_path)
        db.close()


class IndexQueue:
    def __init__(self):
        self._cola: queue.Queue = queue.Queue()
        self._hilo: threading.Thread | None = None
        self._detener = threading.Event()

    def iniciar(self) -> None:
        if self._hilo and self._hilo.is_alive():
            return
        self._detener.clear()
        self._hilo = threading.Thread(target=self._worker, name="index-queue", daemon=True)
        self._hilo.start()
        print("Cola de indexación iniciada")

    def detener(self) -> None:
        self._detener.set()
        if self._hilo:
            self._hilo.join(timeout=5)

    def encolar(self, doc_id: uuid.UUID, tmp_path: str) -> None:
        self._cola.put((doc_id, tmp_path))

    def _worker(self) -> None:
        while not self._detener.is_set():
            try:
                doc_id, tmp_path = self._cola.get(timeout=1)
            except queue.Empty:
                continue
            try:
                _procesar_trabajo(doc_id, tmp_path)
            finally:
                self._cola.task_done()


_cola: IndexQueue | None = None


def obtener_cola_indexacion() -> IndexQueue:
    global _cola
    if _cola is None:
        _cola = IndexQueue()
        _cola.iniciar()
    return _cola


def recuperar_trabajos_pendientes() -> None:
    """Reencola documentos pendientes tras reinicio del servidor."""
    db = SessionLocal()
    cola = obtener_cola_indexacion()
    try:
        docs = db.scalars(
            select(Document).where(Document.estado.in_(("pendiente", "indexando")))
        )
        for doc in docs:
            ruta = ruta_pendiente(doc.id, doc.extension)
            if os.path.isfile(ruta):
                doc.estado = "pendiente"
                doc.error = None
                db.commit()
                cola.encolar(doc.id, ruta)
            else:
                doc_repo.actualizar_tras_indexar(
                    db,
                    doc,
                    ok=False,
                    error="Archivo no encontrado tras reinicio del servidor",
                )
    finally:
        db.close()

from fastapi import Depends
from sqlalchemy.orm import Session

from src.db.engine import get_db as _get_db
from src.db import repository
from src.db.models import User
from src.rag.pipeline import RAGPipeline

_pipeline: RAGPipeline | None = None


def set_pipeline(pipeline: RAGPipeline | None):
    global _pipeline
    _pipeline = pipeline


def get_pipeline() -> RAGPipeline:
    if not _pipeline:
        raise RuntimeError("Pipeline no inicializado")
    return _pipeline


def get_db():
    yield from _get_db()


def get_default_user(db: Session = Depends(get_db)) -> User:
    return repository.obtener_o_crear_usuario_default(db)

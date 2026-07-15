from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from src.db.engine import get_db as _get_db
from src.db import repository
from src.db import projects_repository as proy_repo
from src.db.models import Proyecto, User
from src.rag.pipeline import RAGPipeline
from config.proyectos import DEFAULT_PROYECTO_SLUG

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


def get_proyecto_activo(
    x_proyecto_slug: str | None = Header(default=None, alias="X-Proyecto-Slug"),
    db: Session = Depends(get_db),
) -> Proyecto:
    slug = (x_proyecto_slug or DEFAULT_PROYECTO_SLUG).strip().lower()
    proy = proy_repo.obtener_por_slug(db, slug)
    if not proy or not proy.activo:
        raise HTTPException(404, f"Proyecto '{slug}' no encontrado o inactivo")
    return proy

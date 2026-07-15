from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.api.deps import get_db, get_pipeline
from src.db import projects_repository as proy_repo
from src.db.schemas import ProyectoCreate, ProyectoOut
from src.rag.pipeline import RAGPipeline

router = APIRouter(prefix="/api/proyectos", tags=["proyectos"])


@router.get("", response_model=list[ProyectoOut])
def listar_proyectos(db: Session = Depends(get_db)):
    return proy_repo.listar_proyectos(db, solo_activos=True)


@router.post("", response_model=ProyectoOut)
def crear_proyecto(
    body: ProyectoCreate,
    db: Session = Depends(get_db),
    pipeline: RAGPipeline = Depends(get_pipeline),
):
    try:
        proy = proy_repo.crear_proyecto(
            db,
            nombre=body.nombre,
            slug=body.slug,
            descripcion=body.descripcion or "",
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e

    try:
        pipeline.asegurar_tenant_proyecto(proy.slug)
    except Exception as e:
        raise HTTPException(503, f"Proyecto creado pero tenant Weaviate falló: {e}") from e

    return proy

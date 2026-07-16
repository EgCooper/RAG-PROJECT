"""Repositorio de proyectos."""

import re
import uuid

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from config.proyectos import (
    DEFAULT_PROYECTO_SLUG,
    PROYECTOS_OBSOLETOS,
    PROYECTOS_SEED,
)
from src.db.models import Proyecto

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def slugify(nombre: str) -> str:
    s = nombre.strip().lower()
    s = re.sub(r"[áàä]", "a", s)
    s = re.sub(r"[éèë]", "e", s)
    s = re.sub(r"[íìï]", "i", s)
    s = re.sub(r"[óòö]", "o", s)
    s = re.sub(r"[úùü]", "u", s)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "proyecto"


def listar_proyectos(db: Session, solo_activos: bool = True) -> list[Proyecto]:
    q = select(Proyecto).order_by(Proyecto.nombre)
    if solo_activos:
        q = q.where(Proyecto.activo.is_(True))
    return list(db.scalars(q))


def obtener_por_slug(db: Session, slug: str) -> Proyecto | None:
    return db.scalar(select(Proyecto).where(Proyecto.slug == slug))


def obtener_por_id(db: Session, proyecto_id: uuid.UUID) -> Proyecto | None:
    return db.get(Proyecto, proyecto_id)


def obtener_default(db: Session) -> Proyecto:
    proy = obtener_por_slug(db, DEFAULT_PROYECTO_SLUG)
    if proy:
        return proy
    activos = listar_proyectos(db, solo_activos=True)
    if activos:
        return activos[0]
    raise RuntimeError("No hay proyectos configurados")


def crear_proyecto(
    db: Session,
    *,
    nombre: str,
    slug: str | None = None,
    descripcion: str = "",
    config: dict | None = None,
) -> Proyecto:
    slug_final = (slug or slugify(nombre)).lower().strip()
    if not _SLUG_RE.match(slug_final):
        raise ValueError(
            "Slug inválido. Usá minúsculas, números y guiones (ej: ach, feel, banca)."
        )
    if obtener_por_slug(db, slug_final):
        raise ValueError(f"Ya existe un proyecto con slug '{slug_final}'")

    proy = Proyecto(
        slug=slug_final,
        nombre=nombre.strip(),
        descripcion=descripcion.strip(),
        activo=True,
        config=config or {"dominio": slug_final, "usa_tablas_ach": slug_final == "ach"},
    )
    db.add(proy)
    db.commit()
    db.refresh(proy)
    return proy


def seed_proyectos(db: Session) -> list[Proyecto]:
    creados = []
    for data in PROYECTOS_SEED:
        existente = obtener_por_slug(db, data["slug"])
        if existente:
            # Asegura nombres/config actuales y que quede activo
            existente.nombre = data["nombre"]
            existente.descripcion = data.get("descripcion", "")
            existente.config = data.get("config")
            existente.activo = True
            creados.append(existente)
            continue
        proy = Proyecto(
            id=uuid.uuid4(),
            slug=data["slug"],
            nombre=data["nombre"],
            descripcion=data.get("descripcion", ""),
            activo=True,
            config=data.get("config"),
        )
        db.add(proy)
        creados.append(proy)

    for slug in PROYECTOS_OBSOLETOS:
        viejo = obtener_por_slug(db, slug)
        if viejo and viejo.activo:
            viejo.activo = False

    db.commit()
    for p in creados:
        db.refresh(p)
    return creados


def migrar_schema_proyectos(engine) -> None:
    """Añade tabla/columnas de proyecto si la DB ya existía sin ellas."""
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS proyectos (
                id UUID PRIMARY KEY,
                slug VARCHAR(64) NOT NULL UNIQUE,
                nombre VARCHAR(120) NOT NULL,
                descripcion VARCHAR(255) DEFAULT '',
                activo BOOLEAN NOT NULL DEFAULT TRUE,
                config JSONB,
                creado_en TIMESTAMPTZ DEFAULT NOW()
            )
        """))

        # chat_sessions.proyecto_id
        col = conn.execute(text("""
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'chat_sessions' AND column_name = 'proyecto_id'
        """)).scalar()
        if not col:
            conn.execute(text(
                "ALTER TABLE chat_sessions ADD COLUMN proyecto_id UUID"
            ))

        # documents.proyecto_id
        col = conn.execute(text("""
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'documents' AND column_name = 'proyecto_id'
        """)).scalar()
        if not col:
            conn.execute(text(
                "ALTER TABLE documents ADD COLUMN proyecto_id UUID"
            ))

        # user_id nullable
        try:
            conn.execute(text(
                "ALTER TABLE chat_sessions ALTER COLUMN user_id DROP NOT NULL"
            ))
        except Exception:
            pass
        try:
            conn.execute(text(
                "ALTER TABLE documents ALTER COLUMN user_id DROP NOT NULL"
            ))
        except Exception:
            pass

from sqlalchemy import select, text

from config.settings import DEFAULT_USER_NAME
from config.proyectos import DEFAULT_PROYECTO_SLUG
from src.db.engine import Base, SessionLocal, engine
from src.db import repository
from src.db import projects_repository as proy_repo
from src.db import documents_repository as doc_repo
from src.db.models import ChatSession, Document


def _backfill_proyecto_id(db) -> None:
    ach = proy_repo.obtener_por_slug(db, DEFAULT_PROYECTO_SLUG)
    if not ach:
        return

    sessions_sin = db.scalars(
        select(ChatSession).where(ChatSession.proyecto_id.is_(None))
    ).all()
    for s in sessions_sin:
        s.proyecto_id = ach.id

    docs_sin = db.scalars(
        select(Document).where(Document.proyecto_id.is_(None))
    ).all()
    for d in docs_sin:
        d.proyecto_id = ach.id

    db.commit()

    with engine.begin() as conn:
        for table in ("chat_sessions", "documents"):
            fk_name = f"{table}_proyecto_id_fkey"
            existe = conn.execute(
                text("""
                SELECT 1 FROM information_schema.table_constraints
                WHERE table_name = :t AND constraint_name = :c
            """),
                {"t": table, "c": fk_name},
            ).scalar()
            if not existe:
                try:
                    conn.execute(
                        text(f"""
                        ALTER TABLE {table}
                        ADD CONSTRAINT {fk_name}
                        FOREIGN KEY (proyecto_id) REFERENCES proyectos(id)
                    """)
                    )
                except Exception:
                    pass
            try:
                conn.execute(
                    text(f"ALTER TABLE {table} ALTER COLUMN proyecto_id SET NOT NULL")
                )
            except Exception:
                pass

        try:
            conn.execute(
                text("""
                ALTER TABLE documents
                ADD CONSTRAINT uq_documents_proyecto_nombre
                UNIQUE (proyecto_id, nombre)
            """)
            )
        except Exception:
            pass


def inicializar_db():
    Base.metadata.create_all(bind=engine)
    proy_repo.migrar_schema_proyectos(engine)
    doc_repo.migrar_schema_documentos(engine)

    with SessionLocal() as db:
        repository.obtener_o_crear_usuario_default(db)
        proy_repo.seed_proyectos(db)
        _backfill_proyecto_id(db)

    print(
        f"PostgreSQL listo (usuario: {DEFAULT_USER_NAME}, "
        f"proyecto default: {DEFAULT_PROYECTO_SLUG})"
    )

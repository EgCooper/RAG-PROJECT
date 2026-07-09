from config.settings import DEFAULT_USER_NAME
from src.db.engine import Base, SessionLocal, engine
from src.db import repository


def inicializar_db():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        repository.obtener_o_crear_usuario_default(db)
    print(f"PostgreSQL listo (usuario: {DEFAULT_USER_NAME})")

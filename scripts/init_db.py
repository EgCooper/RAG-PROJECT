import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.bootstrap import inicializar_db
from src.db.engine import verificar_conexion


def main():
    print("Inicializando PostgreSQL...")
    try:
        verificar_conexion()
    except Exception as e:
        print(f"ERROR: no se pudo conectar a PostgreSQL: {e}")
        print("¿Está corriendo docker compose up -d?")
        sys.exit(1)

    inicializar_db()
    print("Tablas, proyectos (ACH / FEEL BANCA) y usuario default listos.")


if __name__ == "__main__":
    main()

"""
Verifica dependencias del sistema antes de indexar o consultar.

Uso:
  python scripts/health_check.py
  python scripts/health_check.py --skip-llm
"""

import argparse
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import WEAVIATE_HOST, WEAVIATE_PORT, LLM_PROVIDER
from config.validate_env import validar_env


def _ok(msg):
    print(f"  OK  {msg}")


def _fail(msg):
    print(f"  FAIL {msg}")
    return msg


def verificar_tesseract():
    if shutil.which("tesseract"):
        _ok("Tesseract instalado")
        return None
    return _fail("Tesseract no encontrado en PATH (requerido para hi_res)")


def verificar_weaviate():
    try:
        import weaviate
        client = weaviate.connect_to_local(host=WEAVIATE_HOST, port=WEAVIATE_PORT)
        client.is_ready()
        client.close()
        _ok(f"Weaviate en {WEAVIATE_HOST}:{WEAVIATE_PORT}")
        return None
    except Exception as e:
        return _fail(f"Weaviate no disponible: {e}")


def verificar_postgres():
    try:
        from src.db.engine import verificar_conexion
        verificar_conexion()
        _ok("PostgreSQL conectado")
        return None
    except Exception as e:
        return _fail(f"PostgreSQL no disponible: {e}")


def main():
    parser = argparse.ArgumentParser(description="Health check del asistente RAG")
    parser.add_argument("--skip-llm", action="store_true", help="No validar API keys LLM")
    parser.add_argument("--skip-postgres", action="store_true", help="No validar PostgreSQL")
    args = parser.parse_args()

    print("=== Health check RAG ===\n")
    fallos = []

    print("Entorno:")
    try:
        validar_env(requiere_llm=not args.skip_llm)
        _ok(f"LLM_PROVIDER={LLM_PROVIDER}")
    except SystemExit:
        fallos.append("Variables de entorno incompletas")

    print("\nDependencias sistema:")
    t = verificar_tesseract()
    if t:
        fallos.append(t)

    print("\nServicios:")
    w = verificar_weaviate()
    if w:
        fallos.append(w)

    p = None
    if not args.skip_postgres:
        p = verificar_postgres()
        if p:
            fallos.append(p)

    print()
    if fallos:
        print(f"Resultado: {len(fallos)} problema(s) encontrado(s)")
        sys.exit(1)
    print("Resultado: todo OK")
    sys.exit(0)


if __name__ == "__main__":
    main()

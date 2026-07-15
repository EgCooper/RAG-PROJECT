import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.proyectos import DEFAULT_PROYECTO_SLUG
from src.db.bootstrap import inicializar_db
from src.db.engine import SessionLocal
from src.db import projects_repository as proy_repo
from src.rag.pipeline import RAGPipeline


def mostrar_chunks(chunks):
    print(f"\nChunks recuperados ({len(chunks)}):")
    for i, c in enumerate(chunks, 1):
        fuente = os.path.basename(c.get("fuente", "?"))
        score = c.get("score")
        score_txt = f"{score:.4f}" if score is not None else "n/a"
        preview = c["texto"][:200].replace("\n", " ")
        print(f"  [{i}] score={score_txt} | {fuente} p.{c.get('pagina', '?')}")
        print(f"      {preview}{'...' if len(c['texto']) > 200 else ''}")


def main():
    parser = argparse.ArgumentParser(description="Consultar el asistente RAG (CLI)")
    parser.add_argument(
        "--proyecto",
        default=DEFAULT_PROYECTO_SLUG,
        help=f"Slug del proyecto (default: {DEFAULT_PROYECTO_SLUG})",
    )
    args = parser.parse_args()

    inicializar_db()
    with SessionLocal() as db:
        proy = proy_repo.obtener_por_slug(db, args.proyecto)
        if not proy or not proy.activo:
            print(f"ERROR: proyecto '{args.proyecto}' no encontrado")
            sys.exit(1)
        # detach attrs we need
        slug = proy.slug
        nombre = proy.nombre

    pipeline = RAGPipeline()
    pipeline.asegurar_tenant_proyecto(slug)

    print(f"\n=== Asistente RAG [{nombre} / {slug}] ===")
    print("Escribe 'salir' para terminar\n")

    try:
        with SessionLocal() as db:
            while True:
                pregunta = input("Pregunta: ").strip()

                if pregunta.lower() == "salir":
                    print("Cerrando asistente...")
                    break

                if not pregunta:
                    continue

                proyecto = proy_repo.obtener_por_slug(db, slug)
                respuesta, chunks = pipeline.consultar(pregunta, proyecto)
                mostrar_chunks(chunks)
                print(f"\nRespuesta: {respuesta}\n")
                print("-" * 50)
    finally:
        pipeline.cerrar()


if __name__ == "__main__":
    main()

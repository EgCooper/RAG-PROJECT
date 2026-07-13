import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.rag.pipeline import RAGPipeline
from src.storage.weaviate_client import listar_fuentes_indexadas, normalizar_fuente
from src.ingestion.index_registry import (
    cargar_registro,
    guardar_registro,
    necesita_indexar,
    registrar_indexacion,
)

DATA_DIR = "data"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Indexar PDFs en Weaviate (por defecto solo nuevos o modificados).",
    )
    parser.add_argument(
        "--todos",
        action="store_true",
        help="Reindexar todos los PDFs en data/",
    )
    parser.add_argument(
        "--archivo",
        metavar="PDF",
        help="Indexar solo este PDF (nombre en data/ o ruta)",
    )
    parser.add_argument(
        "--forzar",
        action="store_true",
        help="Reindexar aunque el archivo no haya cambiado",
    )
    return parser.parse_args()


def listar_pdfs(archivo=None):
    if archivo:
        return [resolver_archivo(archivo)]

    if not os.path.isdir(DATA_DIR):
        return []

    return sorted(
        os.path.join(DATA_DIR, f)
        for f in os.listdir(DATA_DIR)
        if f.lower().endswith((".pdf", ".csv", ".docx", ".md", ".ppt", ".pptx"))
    )


def resolver_archivo(archivo):
    candidatos = [archivo]
    if not os.path.isabs(archivo):
        candidatos.append(os.path.join(DATA_DIR, archivo))

    for ruta in candidatos:
        if os.path.isfile(ruta) and ruta.lower().endswith((".pdf", ".csv", ".docx", ".md", ".ppt", ".pptx")):
            return os.path.normpath(ruta)

    print(f"ERROR: no se encontró archivo indexable: {archivo}")
    sys.exit(1)


def resolver_pdf(archivo):
    return resolver_archivo(archivo)


def main():
    args = parse_args()
    pdfs = listar_pdfs(args.archivo)

    if not pdfs:
        print("No se encontraron PDFs/CSV en la carpeta data/")
        sys.exit(0)

    pipeline = RAGPipeline(requiere_llm=False)
    fuentes_weaviate = listar_fuentes_indexadas(pipeline.cliente_weaviate)
    registro = cargar_registro()

    a_indexar = []
    omitidos = []

    for ruta in pdfs:
        if args.todos or args.forzar:
            a_indexar.append(ruta)
            continue

        if necesita_indexar(ruta, fuentes_weaviate, registro):
            a_indexar.append(ruta)
        else:
            omitidos.append(ruta)

    print(f"PDFs en data/: {len(pdfs)}")
    if omitidos:
        print(f"Omitidos (sin cambios): {len(omitidos)}")
    print(f"A indexar: {len(a_indexar)}\n")

    for ruta in omitidos:
        print(f"  Omitido: {os.path.basename(ruta)}")

    if omitidos and a_indexar:
        print()

    exitos = []
    fallos = []

    for i, ruta in enumerate(a_indexar, 1):
        pdf = os.path.basename(ruta)
        print(f"[{i}/{len(a_indexar)}] Procesando: {pdf}")
        resultado = pipeline.indexar(ruta)
        if resultado["ok"]:
            registrar_indexacion(registro, ruta, resultado["chunks"])
            fuentes_weaviate.add(normalizar_fuente(ruta))
            exitos.append(resultado)
        else:
            fallos.append(resultado)

    guardar_registro(registro)

    print(f"\n{'=' * 50}")
    print(f"Resumen: {len(exitos)}/{len(a_indexar)} indexados correctamente")
    if omitidos:
        print(f"Omitidos: {len(omitidos)}")

    if exitos:
        print("\nExitosos:")
        for r in exitos:
            print(f"  - {os.path.basename(r['fuente'])} ({r['chunks']} chunks)")

    if fallos:
        print("\nFallidos:")
        for r in fallos:
            print(f"  - {os.path.basename(r['fuente'])} [{r['etapa']}]: {r['error']}")

    pipeline.cerrar()

    if fallos:
        sys.exit(1)


if __name__ == "__main__":
    main()

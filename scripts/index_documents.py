import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.rag.pipeline import RAGPipeline

DATA_DIR = "data"

pipeline = RAGPipeline()

pdfs = [f for f in os.listdir(DATA_DIR) if f.lower().endswith(".pdf")]

if not pdfs:
    print("No se encontraron PDFs en la carpeta data/")
    sys.exit(0)

print(f"PDFs encontrados: {len(pdfs)}\n")

exitos = []
fallos = []

for i, pdf in enumerate(pdfs, 1):
    ruta = os.path.join(DATA_DIR, pdf)
    print(f"[{i}/{len(pdfs)}] Procesando: {pdf}")
    resultado = pipeline.indexar(ruta)
    if resultado["ok"]:
        exitos.append(resultado)
    else:
        fallos.append(resultado)

print(f"\n{'=' * 50}")
print(f"Resumen: {len(exitos)}/{len(pdfs)} indexados correctamente")

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

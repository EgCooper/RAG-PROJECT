import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.rag.pipeline import RAGPipeline

DATA_DIR = "data"

pipeline = RAGPipeline()

pdfs = [f for f in os.listdir(DATA_DIR) if f.endswith(".pdf")]

if not pdfs:
    print("No se encontraron PDFs en la carpeta data/")
    sys.exit(0)

print(f"PDFs encontrados: {len(pdfs)}\n")

for i, pdf in enumerate(pdfs, 1):
    ruta = os.path.join(DATA_DIR, pdf)
    print(f"[{i}/{len(pdfs)}] Procesando: {pdf}")
    pipeline.indexar(ruta)

print(f"\nIndexación completa. {len(pdfs)} PDFs procesados.")
pipeline.cerrar()

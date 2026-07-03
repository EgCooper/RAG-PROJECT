import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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


pipeline = RAGPipeline()

print("\n=== Asistente RAG ===")
print("Comandos: 'salir' | 'limpiar' (nueva conversación)\n")

try:
    while True:
        pregunta = input("Pregunta: ").strip()

        if pregunta.lower() == "salir":
            print("Cerrando asistente...")
            break

        if pregunta.lower() in ("limpiar", "nuevo", "reset"):
            pipeline.limpiar_historial()
            print("Historial limpiado. Nueva conversación.\n")
            continue

        if not pregunta:
            continue

        respuesta, chunks = pipeline.consultar(pregunta)
        mostrar_chunks(chunks)
        print(f"\nRespuesta: {respuesta}\n")
        print("-" * 50)
finally:
    pipeline.cerrar()

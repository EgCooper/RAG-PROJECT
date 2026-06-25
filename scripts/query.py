import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.rag.pipeline import RAGPipeline

pipeline = RAGPipeline()

print("\n=== Asistente RAG ===")
print("Escribe 'salir' para terminar\n")
  
while True:
    pregunta = input("Pregunta: ").strip()
  
    if pregunta.lower() == "salir":
        print("Cerrando asistente...")
        break
  
    if not pregunta:
        continue

    respuesta = pipeline.consultar(pregunta)
    print(f"\nRespuesta: {respuesta}\n")
    print("-" * 50)

pipeline.cerrar()
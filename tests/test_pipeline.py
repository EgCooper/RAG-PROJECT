import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.rag.pipeline import RAGPipeline

pipeline = RAGPipeline()
pipeline.indexar("data/service.pdf")

pregunta = "¿Instalacion de wildfly como servicio?"
respuesta = pipeline.consultar(pregunta)

print(f"Pregunta: {pregunta}")
print(f"Respuesta: {respuesta}")

pipeline.cerrar()
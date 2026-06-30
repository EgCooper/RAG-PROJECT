from src.ingestion.extractor import extraer_pdf
from src.ingestion.chunker import dividir_chunks
from src.ingestion.embedder import cargar_modelo, generar_embeddings
from src.storage.weaviate_client import conectar, crear_collection, almacenar_chunks
from src.retrieval.retriever import buscar_chunks
from src.llm.llm_factory import crear_cliente, generar_respuesta, info_proveedor
from src.llm.prompt import SYSTEM_PROMPT, construir_prompt


class RAGPipeline:

    def __init__(self):
        print(f"Iniciando pipeline RAG... (LLM: {info_proveedor()})")
        self.modelo_embeddings = cargar_modelo()
        self.cliente_weaviate  = conectar()
        self.cliente_llm       = crear_cliente()
        crear_collection(self.cliente_weaviate)
        print("Pipeline listo.")

    def indexar(self, ruta_pdf):
        print(f"Indexando: {ruta_pdf}")
        elementos = extraer_pdf(ruta_pdf)
        chunks    = dividir_chunks(elementos)
        vectores  = generar_embeddings(chunks, self.modelo_embeddings)
        almacenar_chunks(self.cliente_weaviate, chunks, vectores, ruta_pdf)
        print(f"Indexación completa: {len(chunks)} chunks almacenados")

    def consultar(self, pregunta):
        vector_pregunta = self.modelo_embeddings.embed_query(pregunta)
        chunks          = buscar_chunks(self.cliente_weaviate, pregunta, vector_pregunta)
        prompt          = construir_prompt(pregunta, chunks)
        respuesta       = generar_respuesta(self.cliente_llm, SYSTEM_PROMPT, prompt)
        return respuesta, chunks

    def cerrar(self):
        self.cliente_weaviate.close()

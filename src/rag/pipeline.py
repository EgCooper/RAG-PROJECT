from src.ingestion.extractor import extraer_pdf
from src.ingestion.chunker import dividir_chunks
from src.ingestion.embedder import cargar_modelo, generar_embeddings
from src.storage.weaviate_client import conectar, crear_collection, almacenar_chunks
from src.retrieval.retriever import buscar_chunks
from src.retrieval.reranker import cargar_reranker
from src.llm.llm_factory import crear_cliente, generar_respuesta, info_proveedor
from src.llm.prompt import SYSTEM_PROMPT, construir_prompt
from src.chat.historial import HistorialChat
from config.settings import RERANK_ENABLED, RERANK_MODEL
from config.validate_env import validar_env


class RAGPipeline:

    def __init__(self, requiere_llm=True):
        validar_env(requiere_llm=requiere_llm)
        print(f"Iniciando pipeline RAG... (LLM: {info_proveedor()})")
        self.modelo_embeddings = cargar_modelo()
        self.cliente_weaviate  = conectar()
        self.cliente_llm       = crear_cliente()
        self.reranker          = None
        self.historial         = HistorialChat()
        crear_collection(self.cliente_weaviate)
        if RERANK_ENABLED:
            print(f"Reranker: {RERANK_MODEL} (se carga al consultar)")
        print("Pipeline listo.")

    def indexar(self, ruta_pdf):
        print(f"Indexando: {ruta_pdf}")
        etapa = "extraccion"
        try:
            elementos = extraer_pdf(ruta_pdf)
            etapa = "chunking"
            chunks    = dividir_chunks(elementos)
            etapa = "embeddings"
            vectores  = generar_embeddings(chunks, self.modelo_embeddings)
            etapa = "almacenamiento"
            almacenar_chunks(self.cliente_weaviate, chunks, vectores, ruta_pdf)
            print(f"Indexación completa: {len(chunks)} chunks almacenados")
            return {"ok": True, "fuente": ruta_pdf, "chunks": len(chunks)}
        except Exception as e:
            print(f"ERROR en {ruta_pdf} ({etapa}): {e}")
            return {"ok": False, "fuente": ruta_pdf, "etapa": etapa, "error": str(e)}

    def consultar(self, pregunta, usar_historial=True):
        if RERANK_ENABLED and self.reranker is None:
            print(f"Cargando reranker: {RERANK_MODEL}...")
            self.reranker = cargar_reranker()

        pregunta_busqueda = (
            self.historial.pregunta_para_retrieval(pregunta)
            if usar_historial
            else pregunta
        )
        if pregunta_busqueda != pregunta:
            print(f"Búsqueda enriquecida: {pregunta_busqueda}")

        vector_pregunta = self.modelo_embeddings.embed_query(pregunta_busqueda)
        chunks          = buscar_chunks(
            self.cliente_weaviate, pregunta_busqueda, vector_pregunta, self.reranker
        )
        historial_texto = (
            self.historial.formatear_para_prompt() if usar_historial else None
        )
        prompt          = construir_prompt(pregunta, chunks, historial_texto)
        respuesta       = generar_respuesta(self.cliente_llm, SYSTEM_PROMPT, prompt)

        if usar_historial:
            self.historial.agregar(pregunta, respuesta)

        return respuesta, chunks

    def limpiar_historial(self):
        self.historial.limpiar()

    def cerrar(self):
        self.cliente_weaviate.close()

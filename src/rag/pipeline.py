from src.ingestion.index_router import construir_chunks
from src.ingestion.embedder import cargar_modelo, generar_embeddings
from src.storage.weaviate_client import conectar, crear_collection, almacenar_chunks
from src.retrieval.retriever import buscar_chunks
from src.retrieval.reranker import cargar_reranker
from src.llm.llm_factory import crear_cliente, generar_respuesta, info_proveedor
from src.llm.prompt import SYSTEM_PROMPT, construir_prompt
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
        crear_collection(self.cliente_weaviate)
        if RERANK_ENABLED:
            print(f"Reranker: {RERANK_MODEL} (se carga al consultar)")
        print("Pipeline listo.")

    def indexar(self, ruta_archivo):
        print(f"Indexando: {ruta_archivo}")
        etapa = "extraccion"
        try:
            chunks, info = construir_chunks(ruta_archivo)
            perfil = info["perfil"]
            print(f"Perfil: {perfil} | chunks: {len(chunks)}")
            if info["validacion"].get("advertencias"):
                for adv in info["validacion"]["advertencias"]:
                    print(f"  Advertencia: {adv}")
            etapa = "embeddings"
            vectores  = generar_embeddings(chunks, self.modelo_embeddings)
            etapa = "almacenamiento"
            almacenar_chunks(self.cliente_weaviate, chunks, vectores, ruta_archivo)
            print(f"Indexación completa: {len(chunks)} chunks almacenados")
            return {
                "ok": True,
                "fuente": ruta_archivo,
                "chunks": len(chunks),
                "perfil": perfil,
            }
        except Exception as e:
            print(f"ERROR en {ruta_archivo} ({etapa}): {e}")
            return {"ok": False, "fuente": ruta_archivo, "etapa": etapa, "error": str(e)}

    def consultar(self, pregunta):
        if RERANK_ENABLED and self.reranker is None:
            print(f"Cargando reranker: {RERANK_MODEL}...")
            self.reranker = cargar_reranker()

        vector_pregunta = self.modelo_embeddings.embed_query(pregunta)
        chunks          = buscar_chunks(
            self.cliente_weaviate, pregunta, vector_pregunta, self.reranker
        )
        prompt          = construir_prompt(pregunta, chunks)
        respuesta       = generar_respuesta(self.cliente_llm, SYSTEM_PROMPT, prompt)
        return respuesta, chunks

    def cerrar(self):
        self.cliente_weaviate.close()

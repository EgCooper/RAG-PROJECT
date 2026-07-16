from src.ingestion.index_router import construir_chunks
from src.ingestion.embedder import cargar_modelo, generar_embeddings
from src.storage.weaviate_client import (
    conectar,
    crear_collection,
    almacenar_chunks,
    asegurar_tenant,
)
from src.retrieval.retriever import buscar_chunks
from src.retrieval.reranker import cargar_reranker
from src.llm.llm_factory import (
    crear_cliente,
    generar_respuesta,
    generar_respuesta_stream,
    info_proveedor,
)
from src.llm.prompt import construir_prompt
from config.proyectos import system_prompt_para, usa_tablas_ach
from config.settings import RERANK_ENABLED, RERANK_MODEL
from config.validate_env import validar_env
from src.rag.errors import MENSAJE_FILTRO_SIN_DOCS, MENSAJE_INDICE_VACIO


class RAGPipeline:

    def __init__(self, requiere_llm=True):
        validar_env(requiere_llm=requiere_llm)
        print(f"Iniciando pipeline RAG... (LLM: {info_proveedor()})")
        self.modelo_embeddings = cargar_modelo()
        self.cliente_weaviate = conectar()
        self.cliente_llm = crear_cliente() if requiere_llm else None
        self.reranker = None
        crear_collection(self.cliente_weaviate)
        if RERANK_ENABLED:
            print(f"Reranker: {RERANK_MODEL} (se carga al consultar)")
        print("Pipeline listo.")

    def asegurar_tenant_proyecto(self, slug: str) -> None:
        asegurar_tenant(self.cliente_weaviate, slug)

    def indexar(self, ruta_archivo, fuente=None, tenant: str | None = None):
        if not tenant:
            raise ValueError("tenant (slug de proyecto) es obligatorio para indexar")
        clave_fuente = fuente or ruta_archivo
        print(f"Indexando [{tenant}]: {ruta_archivo} → {clave_fuente}")
        etapa = "extraccion"
        try:
            chunks, info = construir_chunks(ruta_archivo)
            perfil = info["perfil"]
            print(f"Perfil: {perfil} | chunks: {len(chunks)}")
            if info["validacion"].get("advertencias"):
                for adv in info["validacion"]["advertencias"]:
                    print(f"  Advertencia: {adv}")
            etapa = "embeddings"
            vectores = generar_embeddings(chunks, self.modelo_embeddings)
            etapa = "almacenamiento"
            almacenar_chunks(
                self.cliente_weaviate, chunks, vectores, clave_fuente, tenant=tenant
            )
            print(f"Indexación completa [{tenant}]: {len(chunks)} chunks almacenados")
            return {
                "ok": True,
                "fuente": clave_fuente,
                "chunks": len(chunks),
                "perfil": perfil,
                "tenant": tenant,
            }
        except Exception as e:
            print(f"ERROR en {ruta_archivo} ({etapa}): {e}")
            return {
                "ok": False,
                "fuente": clave_fuente,
                "etapa": etapa,
                "error": str(e),
                "tenant": tenant,
            }

    def _retrieve(self, pregunta, proyecto, fuentes_permitidas=None):
        if RERANK_ENABLED and self.reranker is None:
            print(f"Cargando reranker: {RERANK_MODEL}...")
            self.reranker = cargar_reranker()

        tenant = proyecto.slug
        vector_pregunta = self.modelo_embeddings.embed_query(pregunta)
        return buscar_chunks(
            self.cliente_weaviate,
            pregunta,
            vector_pregunta,
            self.reranker,
            tenant=tenant,
            usa_tablas_ach=usa_tablas_ach(proyecto),
            fuentes_permitidas=fuentes_permitidas,
        )

    def consultar(self, pregunta, proyecto, fuentes_permitidas=None):
        chunks = self._retrieve(pregunta, proyecto, fuentes_permitidas)
        if not chunks:
            if fuentes_permitidas is not None:
                return MENSAJE_FILTRO_SIN_DOCS, []
            return MENSAJE_INDICE_VACIO, []

        prompt = construir_prompt(pregunta, chunks)
        system = system_prompt_para(proyecto)
        respuesta = generar_respuesta(self.cliente_llm, system, prompt)
        return respuesta, chunks

    def consultar_stream(self, pregunta, proyecto, fuentes_permitidas=None):
        """
        Prepara retrieval y devuelve (token_iterator | None, chunks, respuesta_fija | None).

        Si no hay chunks: (None, [], mensaje).
        Si hay chunks: (iterator de tokens, chunks, None).
        """
        chunks = self._retrieve(pregunta, proyecto, fuentes_permitidas)
        if not chunks:
            mensaje = (
                MENSAJE_FILTRO_SIN_DOCS
                if fuentes_permitidas is not None
                else MENSAJE_INDICE_VACIO
            )
            return None, [], mensaje

        prompt = construir_prompt(pregunta, chunks)
        system = system_prompt_para(proyecto)
        stream = generar_respuesta_stream(self.cliente_llm, system, prompt)
        return stream, chunks, None

    def cerrar(self):
        self.cliente_weaviate.close()

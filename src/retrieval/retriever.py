import re

import weaviate.classes.query as wq
from weaviate.classes.query import Filter

from config.settings import (
    TOP_K_CHUNKS,
    HYBRID_ALPHA,
    TABLE_QUERY_MAX,
    RERANK_ENABLED,
    RERANK_CANDIDATES,
    DEDUP_ENABLED,
)
from config.tables_ach import (
    TABLA_KEYWORDS_CONSULTA,
    inferir_tabla_id_consulta,
    inferir_filtro_fuente,
)
from src.retrieval.reranker import rerank_chunks
from src.retrieval.dedup import deduplicar_chunks
from src.storage.weaviate_client import crear_collection
from src.storage.weaviate_client import collection_tenant, normalizar_fuente
from src.rag.errors import traducir_error_weaviate

_LISTA_TABLA_KEYWORDS = (
    "listar", "lista", "todos", "todas", "completa", "completo",
    "enumera", "cuales son", "cuáles son", "tabla completa", "tabla de",
)

_CODIGO_ESPECIFICO = re.compile(
    r"\b(?:ERRORES_ORDEN\s+[A-Z0-9]+|ERROR_\w+|\d{4}|(?:X|RA|EC|D|RC)\d{2})\b",
    re.I,
)


def _objeto_a_chunk(obj, score=None):
    return {
        "texto":  obj.properties["texto"],
        "tipo":   obj.properties["tipo"],
        "fuente": obj.properties["fuente"],
        "pagina": obj.properties.get("pagina", 0),
        "tabla_id": obj.properties.get("tabla_id", ""),
        "score":  score,
    }


def _es_consulta_tabla(pregunta):
    p = pregunta.lower()
    return any(k in p for k in TABLA_KEYWORDS_CONSULTA)


def _tiene_codigo_especifico(pregunta):
    return _CODIGO_ESPECIFICO.search(pregunta) is not None


def _es_consulta_listar_tabla(pregunta):
    if not _es_consulta_tabla(pregunta):
        return False
    if _tiene_codigo_especifico(pregunta):
        return False
    p = pregunta.lower()
    if any(k in p for k in _LISTA_TABLA_KEYWORDS):
        return True
    if "tabla" in p:
        return True
    return False


def _filtro_fuente_like(patron):
    if not patron:
        return None
    return Filter.by_property("fuente").like(f"*{patron}*")


def _filtro_fuentes_exactas(fuentes: list[str] | None):
    if not fuentes:
        return None
    claves = [normalizar_fuente(f) for f in fuentes if f]
    if not claves:
        return None
    if len(claves) == 1:
        return Filter.by_property("fuente").equal(claves[0])
    return Filter.by_property("fuente").contains_any(claves)


def _combinar_filtros(*filtros):
    vivos = [f for f in filtros if f is not None]
    if not vivos:
        return None
    resultado = vivos[0]
    for f in vivos[1:]:
        resultado = resultado & f
    return resultado


def _aplicar_dedup(chunks):
    if not DEDUP_ENABLED:
        return chunks
    return deduplicar_chunks(chunks)


def _buscar_hibrido(
    collection,
    pregunta,
    vector_pregunta,
    limit,
    filtro_fuente=None,
    fuentes_permitidas=None,
):
    filtros = _combinar_filtros(
        _filtro_fuente_like(filtro_fuente),
        _filtro_fuentes_exactas(fuentes_permitidas),
    )
    resultados = collection.query.hybrid(
        query=pregunta,
        vector=vector_pregunta,
        alpha=HYBRID_ALPHA,
        limit=limit,
        filters=filtros,
        return_metadata=wq.MetadataQuery(score=True),
    )
    return [
        _objeto_a_chunk(obj, obj.metadata.score)
        for obj in resultados.objects
    ]


def _buscar_tabla_completa(collection, tabla_id, filtro_fuente=None, fuentes_permitidas=None):
    filtros = _combinar_filtros(
        Filter.by_property("tabla_id").equal(tabla_id),
        _filtro_fuente_like(filtro_fuente),
        _filtro_fuentes_exactas(fuentes_permitidas),
    )

    resultados = collection.query.fetch_objects(
        filters=filtros,
        limit=TABLE_QUERY_MAX,
    )
    chunks = [_objeto_a_chunk(obj) for obj in resultados.objects]
    chunks.sort(key=lambda c: (c["pagina"], c["texto"][:80]))
    return _aplicar_dedup(chunks)


def _aplicar_rerank(pregunta, chunks, reranker):
    if not (RERANK_ENABLED and reranker and chunks):
        return chunks
    return rerank_chunks(pregunta, chunks, reranker)


def buscar_chunks(
    client,
    pregunta,
    vector_pregunta,
    reranker=None,
    *,
    tenant: str,
    usa_tablas_ach: bool = False,
    fuentes_permitidas: list[str] | None = None,
):
    # Lista vacía explícita: el filtro no matchea ningún documento indexado
    if fuentes_permitidas is not None and len(fuentes_permitidas) == 0:
        return []

    try:
        crear_collection(client)
        collection = collection_tenant(client, tenant)
    except Exception as e:
        raise traducir_error_weaviate(e) from e

    filtro_fuente = inferir_filtro_fuente(pregunta) if usa_tablas_ach else None

    try:
        if usa_tablas_ach and _es_consulta_listar_tabla(pregunta):
            tabla_id = inferir_tabla_id_consulta(pregunta)
            if tabla_id:
                chunks = _buscar_tabla_completa(
                    collection,
                    tabla_id,
                    filtro_fuente,
                    fuentes_permitidas,
                )
                if chunks:
                    return chunks
            return _buscar_hibrido(
                collection,
                pregunta,
                vector_pregunta,
                TABLE_QUERY_MAX,
                filtro_fuente,
                fuentes_permitidas,
            )

        limit = RERANK_CANDIDATES if RERANK_ENABLED and reranker else TOP_K_CHUNKS
        chunks = _buscar_hibrido(
            collection,
            pregunta,
            vector_pregunta,
            limit,
            filtro_fuente,
            fuentes_permitidas,
        )
        chunks = _aplicar_dedup(chunks)
        return _aplicar_rerank(pregunta, chunks, reranker)
    except Exception as e:
        raise traducir_error_weaviate(e) from e

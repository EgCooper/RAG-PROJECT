import re

import weaviate.classes.query as wq
from weaviate.classes.query import Filter

from config.settings import (
    WEAVIATE_COLLECTION,
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


def _filtro_fuente(patron):
    if not patron:
        return None
    return Filter.by_property("fuente").like(f"*{patron}*")


def _aplicar_dedup(chunks):
    if not DEDUP_ENABLED:
        return chunks
    return deduplicar_chunks(chunks)


def _buscar_hibrido(collection, pregunta, vector_pregunta, limit, filtro_fuente=None):
    filtros = _filtro_fuente(filtro_fuente)
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


def _buscar_tabla_completa(collection, tabla_id, filtro_fuente=None):
    filtros = Filter.by_property("tabla_id").equal(tabla_id)
    fuente_filtro = _filtro_fuente(filtro_fuente)
    if fuente_filtro is not None:
        filtros = filtros & fuente_filtro

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


def buscar_chunks(client, pregunta, vector_pregunta, reranker=None):
    collection = client.collections.get(WEAVIATE_COLLECTION)
    filtro_fuente = inferir_filtro_fuente(pregunta)

    if _es_consulta_listar_tabla(pregunta):
        tabla_id = inferir_tabla_id_consulta(pregunta)
        chunks = _buscar_tabla_completa(collection, tabla_id, filtro_fuente)
        if chunks:
            return chunks
        return _buscar_hibrido(
            collection, pregunta, vector_pregunta, TABLE_QUERY_MAX, filtro_fuente
        )

    limit = RERANK_CANDIDATES if RERANK_ENABLED and reranker else TOP_K_CHUNKS
    chunks = _buscar_hibrido(
        collection, pregunta, vector_pregunta, limit, filtro_fuente
    )
    chunks = _aplicar_dedup(chunks)
    return _aplicar_rerank(pregunta, chunks, reranker)

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
)
from src.retrieval.reranker import rerank_chunks

_TABLA_KEYWORDS = (
    "codigo", "código", "codigos", "códigos",
    "excepcion", "excepción", "excepciones",
    "mensaje", "mensajes", "error_exception",
    "abonabilidad",
)

_LISTA_TABLA_KEYWORDS = (
    "listar", "lista", "todos", "todas", "completa", "completo",
    "enumera", "cuales son", "cuáles son", "tabla completa", "tabla de",
)

# Códigos ACH concretos: ERROR_*, 4 dígitos, X99/RA01/EC10/D01, etc.
_CODIGO_ESPECIFICO = re.compile(
    r"\b(?:ERROR_\w+|\d{4}|(?:X|RA|EC|D)\d{2})\b",
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
    return any(k in p for k in _TABLA_KEYWORDS)


def _tiene_codigo_especifico(pregunta):
    return _CODIGO_ESPECIFICO.search(pregunta) is not None


def _inferir_tabla_id(pregunta):
    p = pregunta.lower()
    if "abonabilidad" in p:
        return "abonabilidad"
    return "excepciones"


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


def _buscar_hibrido(collection, pregunta, vector_pregunta, limit):
    resultados = collection.query.hybrid(
        query=pregunta,
        vector=vector_pregunta,
        alpha=HYBRID_ALPHA,
        limit=limit,
        return_metadata=wq.MetadataQuery(score=True),
    )
    return [
        _objeto_a_chunk(obj, obj.metadata.score)
        for obj in resultados.objects
    ]


def _buscar_tabla_completa(collection, tabla_id):
    resultados = collection.query.fetch_objects(
        filters=Filter.by_property("tabla_id").equal(tabla_id),
        limit=TABLE_QUERY_MAX,
    )
    chunks = [_objeto_a_chunk(obj) for obj in resultados.objects]
    chunks.sort(key=lambda c: (c["pagina"], c["texto"][:80]))
    return chunks


def _aplicar_rerank(pregunta, chunks, reranker):
    if not (RERANK_ENABLED and reranker and chunks):
        return chunks
    return rerank_chunks(pregunta, chunks, reranker)


def buscar_chunks(client, pregunta, vector_pregunta, reranker=None):
    collection = client.collections.get(WEAVIATE_COLLECTION)

    if _es_consulta_listar_tabla(pregunta):
        tabla_id = _inferir_tabla_id(pregunta)
        chunks = _buscar_tabla_completa(collection, tabla_id)
        if chunks:
            return chunks
        if tabla_id == "abonabilidad":
            return _buscar_hibrido(collection, pregunta, vector_pregunta, TABLE_QUERY_MAX)

    limit = RERANK_CANDIDATES if RERANK_ENABLED and reranker else TOP_K_CHUNKS
    chunks = _buscar_hibrido(collection, pregunta, vector_pregunta, limit)
    return _aplicar_rerank(pregunta, chunks, reranker)

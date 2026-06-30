import re

import weaviate.classes.query as wq
from weaviate.classes.query import Filter

from config.settings import (
    WEAVIATE_COLLECTION,
    TOP_K_CHUNKS,
    HYBRID_ALPHA,
    TABLE_QUERY_MAX,
)

_TABLA_KEYWORDS = (
    "codigo", "código", "codigos", "códigos",
    "excepcion", "excepción", "excepciones",
    "mensaje", "mensajes", "error_exception",
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


def _es_consulta_tabla_completa(pregunta):
    if not _es_consulta_tabla(pregunta):
        return False
    if re.search(r"\b\d{4}\b", pregunta):
        return False
    if re.search(r"ERROR_\w+", pregunta, re.I):
        return False
    return True


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


def buscar_chunks(client, pregunta, vector_pregunta):
    collection = client.collections.get(WEAVIATE_COLLECTION)

    if _es_consulta_tabla_completa(pregunta):
        chunks = _buscar_tabla_completa(collection, "excepciones")
        if chunks:
            return chunks

    return _buscar_hibrido(collection, pregunta, vector_pregunta, TOP_K_CHUNKS)

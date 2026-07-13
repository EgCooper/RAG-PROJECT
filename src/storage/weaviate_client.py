import os

import weaviate
from weaviate.classes.aggregate import GroupByAggregate
from weaviate.classes.config import Configure, Property, DataType
from weaviate.classes.query import Filter

from config.settings import WEAVIATE_HOST, WEAVIATE_PORT, WEAVIATE_COLLECTION


def conectar():
    return weaviate.connect_to_local(
        host=WEAVIATE_HOST,
        port=WEAVIATE_PORT,
    )


def crear_collection(client):
    if not client.collections.exists(WEAVIATE_COLLECTION):
        client.collections.create(
            name=WEAVIATE_COLLECTION,
            vectorizer_config=Configure.Vectorizer.none(),
            properties=[
                Property(name="texto",    data_type=DataType.TEXT),
                Property(name="tipo",     data_type=DataType.TEXT),
                Property(name="fuente",   data_type=DataType.TEXT),
                Property(name="pagina",   data_type=DataType.INT),
                Property(name="tabla_id", data_type=DataType.TEXT),
            ],
        )


def normalizar_fuente(ruta):
    return os.path.normpath(ruta).replace("\\", "/")


def _fuentes_equivalentes(ruta):
    """Claves de fuente usadas en indexaciones previas (p. ej. barras en Windows)."""
    norm = os.path.normpath(ruta)
    return {normalizar_fuente(ruta), norm}


def listar_fuentes_indexadas(client):
    if not client.collections.exists(WEAVIATE_COLLECTION):
        return set()

    collection = client.collections.get(WEAVIATE_COLLECTION)
    resultado = collection.aggregate.over_all(
        group_by=GroupByAggregate(prop="fuente"),
    )

    fuentes = set()
    for grupo in resultado.groups or []:
        valor = grupo.grouped_by.value
        if valor:
            fuentes.add(normalizar_fuente(valor))
    return fuentes


def estadisticas_indice(client, fuentes_catalogo: set[str] | None = None):
    """Totales del índice vectorial y chunks huérfanos (fuente no está en Postgres)."""
    vacio = {
        "coleccion_existe": False,
        "total_chunks": 0,
        "fuentes": 0,
        "chunks_en_catalogo": 0,
        "huerfanos_chunks": 0,
        "huerfanos": [],
    }
    if not client.collections.exists(WEAVIATE_COLLECTION):
        return vacio

    collection = client.collections.get(WEAVIATE_COLLECTION)
    total_res = collection.aggregate.over_all(total_count=True)
    total_chunks = int(total_res.total_count or 0)

    grouped = collection.aggregate.over_all(
        group_by=GroupByAggregate(prop="fuente"),
    )

    catalogo = {normalizar_fuente(f) for f in (fuentes_catalogo or set())}
    chunks_en_catalogo = 0
    huerfanos: list[dict] = []
    fuentes_count = 0

    for grupo in grouped.groups or []:
        raw = grupo.grouped_by.value
        if not raw:
            continue
        fuentes_count += 1
        fuente = normalizar_fuente(raw)
        count = int(grupo.total_count or 0)
        if catalogo and fuente in catalogo:
            chunks_en_catalogo += count
        else:
            huerfanos.append({"fuente": fuente, "chunks": count})

    return {
        "coleccion_existe": True,
        "total_chunks": total_chunks,
        "fuentes": fuentes_count,
        "chunks_en_catalogo": chunks_en_catalogo,
        "huerfanos_chunks": sum(h["chunks"] for h in huerfanos),
        "huerfanos": sorted(huerfanos, key=lambda x: -x["chunks"]),
    }


def eliminar_chunks_por_fuente(client, fuente):
    if not client.collections.exists(WEAVIATE_COLLECTION):
        return 0

    collection = client.collections.get(WEAVIATE_COLLECTION)
    eliminados = 0

    for clave in _fuentes_equivalentes(fuente):
        result = collection.data.delete_many(
            where=Filter.by_property("fuente").equal(clave),
        )
        eliminados += result.successful

    return eliminados


def almacenar_chunks(client, chunks, vectores, fuente):
    fuente = normalizar_fuente(fuente)
    crear_collection(client)
    previos = eliminar_chunks_por_fuente(client, fuente)
    if previos:
        print(f"Reemplazando índice: {previos} chunks previos eliminados de {fuente}")

    collection = client.collections.get(WEAVIATE_COLLECTION)

    with collection.batch.dynamic() as batch:
        for chunk, vector in zip(chunks, vectores):
            batch.add_object(
                properties={
                    "texto":    chunk["texto"],
                    "tipo":     chunk["tipo"],
                    "fuente":   fuente,
                    "pagina":   chunk.get("pagina", 0),
                    "tabla_id": chunk.get("tabla_id", ""),
                },
                vector=vector,
            )

    print(f"Almacenados: {len(chunks)} chunks de {fuente}")

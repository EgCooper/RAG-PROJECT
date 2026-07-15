"""Cliente Weaviate con multi-tenancy (un tenant por proyecto.slug)."""

import os

import weaviate
from weaviate.classes.aggregate import GroupByAggregate
from weaviate.classes.config import Configure, Property, DataType
from weaviate.classes.query import Filter
from weaviate.classes.tenants import Tenant

from config.settings import WEAVIATE_HOST, WEAVIATE_PORT, WEAVIATE_COLLECTION


def conectar():
    return weaviate.connect_to_local(
        host=WEAVIATE_HOST,
        port=WEAVIATE_PORT,
    )


def _multi_tenancy_enabled(client) -> bool:
    if not client.collections.exists(WEAVIATE_COLLECTION):
        return False
    try:
        cfg = client.collections.get(WEAVIATE_COLLECTION).config.get()
        mt = getattr(cfg, "multi_tenancy_config", None)
        return bool(mt and getattr(mt, "enabled", False))
    except Exception:
        return False


def crear_collection(client, recreate_si_sin_tenants: bool = True):
    """
    Crea la colección Documento con multi-tenancy.
    Si existe una colección antigua sin tenants, la recrea (pierde vectores previos).
    """
    if client.collections.exists(WEAVIATE_COLLECTION):
        if _multi_tenancy_enabled(client):
            return
        if not recreate_si_sin_tenants:
            raise RuntimeError(
                f"La colección {WEAVIATE_COLLECTION} existe sin multi-tenancy. "
                "Reindexá tras recrearla."
            )
        print(
            f"AVISO: recreando colección {WEAVIATE_COLLECTION} con multi-tenancy "
            "(los vectores previos se pierden; reindexá por proyecto)."
        )
        client.collections.delete(WEAVIATE_COLLECTION)

    client.collections.create(
        name=WEAVIATE_COLLECTION,
        vectorizer_config=Configure.Vectorizer.none(),
        multi_tenancy_config=Configure.multi_tenancy(enabled=True),
        properties=[
            Property(name="texto", data_type=DataType.TEXT),
            Property(name="tipo", data_type=DataType.TEXT),
            Property(name="fuente", data_type=DataType.TEXT),
            Property(name="pagina", data_type=DataType.INT),
            Property(name="tabla_id", data_type=DataType.TEXT),
        ],
    )


def asegurar_tenant(client, tenant: str) -> None:
    if not tenant:
        raise ValueError("tenant (slug de proyecto) requerido")
    crear_collection(client)
    collection = client.collections.get(WEAVIATE_COLLECTION)
    # tenants.get() -> Dict[str, Tenant]; .exists(name) es la API correcta en client 4.x
    try:
        ya_existe = collection.tenants.exists(tenant)
    except Exception:
        raw = collection.tenants.get()
        if isinstance(raw, dict):
            ya_existe = tenant in raw
        else:
            ya_existe = tenant in {
                (t if isinstance(t, str) else getattr(t, "name", str(t)))
                for t in (raw or [])
            }
    if not ya_existe:
        collection.tenants.create([Tenant(name=tenant)])
        print(f"Tenant Weaviate creado: {tenant}")


def collection_tenant(client, tenant: str):
    asegurar_tenant(client, tenant)
    return client.collections.get(WEAVIATE_COLLECTION).with_tenant(tenant)


def normalizar_fuente(ruta):
    return os.path.normpath(ruta).replace("\\", "/")


def _fuentes_equivalentes(ruta):
    """Claves de fuente usadas en indexaciones previas (p. ej. barras en Windows)."""
    norm = os.path.normpath(ruta)
    return {normalizar_fuente(ruta), norm}


def listar_fuentes_indexadas(client, tenant: str):
    if not client.collections.exists(WEAVIATE_COLLECTION):
        return set()
    if not _multi_tenancy_enabled(client):
        return set()

    collection = collection_tenant(client, tenant)
    resultado = collection.aggregate.over_all(
        group_by=GroupByAggregate(prop="fuente"),
    )

    fuentes = set()
    for grupo in resultado.groups or []:
        valor = grupo.grouped_by.value
        if valor:
            fuentes.add(normalizar_fuente(valor))
    return fuentes


def estadisticas_indice(client, tenant: str, fuentes_catalogo: set[str] | None = None):
    """Totales del índice vectorial del tenant y chunks huérfanos."""
    vacio = {
        "coleccion_existe": False,
        "total_chunks": 0,
        "fuentes": 0,
        "chunks_en_catalogo": 0,
        "huerfanos_chunks": 0,
        "huerfanos": [],
        "tenant": tenant,
    }
    if not client.collections.exists(WEAVIATE_COLLECTION):
        return vacio
    if not _multi_tenancy_enabled(client):
        return vacio

    collection = collection_tenant(client, tenant)
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
        "tenant": tenant,
    }


def eliminar_chunks_por_fuente(client, fuente, tenant: str):
    if not client.collections.exists(WEAVIATE_COLLECTION):
        return 0
    if not _multi_tenancy_enabled(client):
        return 0

    collection = collection_tenant(client, tenant)
    eliminados = 0

    for clave in _fuentes_equivalentes(fuente):
        result = collection.data.delete_many(
            where=Filter.by_property("fuente").equal(clave),
        )
        eliminados += result.successful

    return eliminados


def almacenar_chunks(client, chunks, vectores, fuente, tenant: str):
    fuente = normalizar_fuente(fuente)
    asegurar_tenant(client, tenant)
    previos = eliminar_chunks_por_fuente(client, fuente, tenant)
    if previos:
        print(f"Reemplazando índice [{tenant}]: {previos} chunks previos eliminados de {fuente}")

    collection = collection_tenant(client, tenant)

    with collection.batch.dynamic() as batch:
        for chunk, vector in zip(chunks, vectores):
            batch.add_object(
                properties={
                    "texto": chunk["texto"],
                    "tipo": chunk["tipo"],
                    "fuente": fuente,
                    "pagina": chunk.get("pagina", 0),
                    "tabla_id": chunk.get("tabla_id", ""),
                },
                vector=vector,
            )

    print(f"Almacenados [{tenant}]: {len(chunks)} chunks de {fuente}")

import weaviate.classes.query as wq
from config.settings import WEAVIATE_COLLECTION, TOP_K_CHUNKS

def buscar_chunks(client, vector_pregunta):
    collection = client.collections.get(WEAVIATE_COLLECTION)

    resultados = collection.query.near_vector(
        near_vector=vector_pregunta,
        limit=TOP_K_CHUNKS,
        return_metadata=wq.MetadataQuery(distance=True)
    )

    chunks = []
    for obj in resultados.objects:
        chunks.append({
            "texto":    obj.properties["texto"],
            "tipo":     obj.properties["tipo"],
            "fuente":   obj.properties["fuente"],
            "distancia": obj.metadata.distance
        })

    return chunks

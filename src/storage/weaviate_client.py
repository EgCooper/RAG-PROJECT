#librearie for connection whit database weaviate
import weaviate
# importing variables from settings for determine the host, port and collection 
from weaviate.classes.config import Configure, Property, DataType
# importing variables from settings for determine the host, port and collection
from config.settings import WEAVIATE_HOST, WEAVIATE_PORT, WEAVIATE_COLLECTION

def conectar():
    return weaviate.connect_to_local(
        host=WEAVIATE_HOST,
        port=WEAVIATE_PORT
    )

def crear_collection(client):
    if not client.collections.exists(WEAVIATE_COLLECTION):
        client.collections.create(
            name=WEAVIATE_COLLECTION,
            vectorizer_config=Configure.Vectorizer.none(),
            properties=[
                Property(name="texto",  data_type=DataType.TEXT),
                Property(name="tipo",   data_type=DataType.TEXT),
                Property(name="fuente", data_type=DataType.TEXT),
            ]
        )

def almacenar_chunks(client, chunks, vectores, fuente):
    collection = client.collections.get(WEAVIATE_COLLECTION)

    with collection.batch.dynamic() as batch:
        for chunk, vector in zip(chunks, vectores):
            batch.add_object(
                properties={
                    "texto":  chunk["texto"],
                    "tipo":   chunk["tipo"],
                    "fuente": fuente
                },
                vector=vector
            )

    print(f"Almacenados: {len(chunks)} chunks de {fuente}")

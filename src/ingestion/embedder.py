# importing library for embedding models
from langchain_huggingface import HuggingFaceEmbeddings
# importing variables from settings for determine the embedding model
from config.settings import EMBEDDING_MODEL

def cargar_modelo():
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

def generar_embeddings(chunks, modelo):
    textos = [c["texto"] for c in chunks]
    vectores = modelo.embed_documents(textos)
    return vectores

# Librarie for dividing chunks
from langchain_text_splitters import RecursiveCharacterTextSplitter
# importing variables from settings for determine the chunk size and overlap
from config.settings import CHUNK_SIZE, CHUNK_OVERLAP

def dividir_chunks(elementos):

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP
    )

    chunks = []

    for elemento in elementos:
        tipo = type(elemento).__name__

        if tipo == "Table":
            chunks.append({
                "texto": elemento.text,
                "tipo": "tabla"
            })
        elif elemento.text:
            for parte in splitter.split_text(elemento.text):
                chunks.append({
                    "texto": parte,
                    "tipo": tipo
                })

    return chunks

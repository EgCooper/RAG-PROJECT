from sentence_transformers import CrossEncoder

from config.settings import RERANK_MODEL, TOP_K_CHUNKS


def cargar_reranker():
    return CrossEncoder(RERANK_MODEL)


def rerank_chunks(pregunta, chunks, modelo, top_k=TOP_K_CHUNKS):
    if not chunks:
        return chunks

    pares = [(pregunta, c["texto"]) for c in chunks]
    scores = modelo.predict(pares)

    for chunk, score in zip(chunks, scores):
        chunk["score"] = float(score)

    ordenados = sorted(chunks, key=lambda c: c["score"], reverse=True)
    return ordenados[:top_k]

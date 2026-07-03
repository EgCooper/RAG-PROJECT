"""Elimina chunks duplicados o casi idénticos del contexto de retrieval."""


def _clave_chunk(chunk, prefijo=200):
    texto = " ".join(chunk.get("texto", "").lower().split())
    return (
        chunk.get("fuente", ""),
        chunk.get("pagina", 0),
        chunk.get("tabla_id", ""),
        texto[:prefijo],
    )


def deduplicar_chunks(chunks, prefijo=200):
    if not chunks:
        return chunks

    vistos = set()
    unicos = []
    for chunk in chunks:
        clave = _clave_chunk(chunk, prefijo)
        if clave in vistos:
            continue
        vistos.add(clave)
        unicos.append(chunk)
    return unicos

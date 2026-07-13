"""Errores de consulta RAG con mensajes para el usuario."""


class IndiceVacioError(Exception):
    """No hay chunks indexados para responder."""


class IndiceVectorialError(Exception):
    """Weaviate no disponible o error al consultar el índice."""


MENSAJE_INDICE_VACIO = (
    "No hay documentos indexados. Subí archivos en la sección Documentos "
    "para que el asistente pueda responder."
)

MENSAJE_INDICE_NO_DISPONIBLE = (
    "El índice de documentos no está disponible. Verificá que Weaviate esté "
    "corriendo (docker compose up) y volvé a subir tus documentos."
)


def traducir_error_weaviate(exc: Exception) -> Exception:
    texto = str(exc).lower()
    if "could not find class" in texto or "schema" in texto and "not find" in texto:
        return IndiceVacioError(MENSAJE_INDICE_VACIO)
    if any(k in texto for k in ("connection refused", "unavailable", "failed to connect", "leader not found")):
        return IndiceVectorialError(MENSAJE_INDICE_NO_DISPONIBLE)
    return IndiceVectorialError(
        "No se pudo consultar el índice de documentos. Intentá de nuevo en unos segundos."
    )

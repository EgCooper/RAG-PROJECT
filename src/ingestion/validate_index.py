"""Validación de chunks antes de indexar en Weaviate."""

import re
import unicodedata

_CODIGO_EN_TEXTO = re.compile(r"\bERRORES_ORDEN\s+[A-Z0-9]+\b", re.I)
_SOLO_CODIGOS = re.compile(r"^(?:ERRORES_ORDEN\s+[A-Z0-9]+\s*)+$", re.I)
_CAMPOS_DESCRIPCION = (
    "descripcion", "mensaje", "message", "valor", "nombre", "detalle", "texto",
)


def _sin_acentos(texto):
    normalizado = unicodedata.normalize("NFD", texto)
    return "".join(c for c in normalizado if unicodedata.category(c) != "Mn").lower()


def validar_chunks(chunks, perfil="default"):
    errores = []
    advertencias = []

    if not chunks:
        errores.append("No se generó ningún chunk.")
        return _resultado(perfil, errores, advertencias, chunks)

    if perfil == "pdf_tabular":
        _validar_tabular(chunks, errores, advertencias)
    elif perfil == "csv":
        _validar_tabular(chunks, errores, advertencias)
    else:
        _validar_narrativo(chunks, advertencias)

    return _resultado(perfil, errores, advertencias, chunks)


def _resultado(perfil, errores, advertencias, chunks):
    return {
        "ok": len(errores) == 0,
        "perfil": perfil,
        "chunks": len(chunks),
        "errores": errores,
        "advertencias": advertencias,
    }


def _validar_tabular(chunks, errores, advertencias):
    sin_descripcion = 0
    solo_codigo = 0

    for chunk in chunks:
        texto = chunk.get("texto", "")
        texto_norm = _sin_acentos(texto)
        if not any(campo in texto_norm for campo in _CAMPOS_DESCRIPCION):
            sin_descripcion += 1
        if _SOLO_CODIGOS.match(texto.strip()):
            solo_codigo += 1

    if sin_descripcion > len(chunks) * 0.1:
        errores.append(
            f"{sin_descripcion}/{len(chunks)} filas sin descripción "
            "(posible desalineación de columnas)."
        )

    if solo_codigo > 0:
        errores.append(f"{solo_codigo} chunks contienen solo códigos, sin descripción.")

    codigos = sum(1 for c in chunks if _CODIGO_EN_TEXTO.search(c.get("texto", "")))
    if codigos == 0 and any(c.get("tabla_id") == "errores_orden" for c in chunks):
        advertencias.append("Ningún chunk contiene patrón ERRORES_ORDEN.")


def _validar_narrativo(chunks, advertencias):
    muy_cortos = sum(1 for c in chunks if len(c.get("texto", "")) < 30)
    if muy_cortos > len(chunks) * 0.5:
        advertencias.append(f"{muy_cortos} chunks muy cortos (< 30 caracteres).")

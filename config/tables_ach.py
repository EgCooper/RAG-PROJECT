"""Registro de tablas ACH: detección en chunking e inferencia en consultas."""

import re

# Palabras clave de consulta por tabla (listar / routing)
TABLAS_CONSULTA = {
    "errores_orden": (
        "errores_orden", "errores orden",
        "codigo error orden", "códigos error orden",
        "codigos error orden", "codigoerrororden",
    ),
    "excepciones": (
        "excepcion", "excepción", "excepciones",
        "error_exception", "mensaje", "mensajes",
    ),
    "abonabilidad": ("abonabilidad",),
    "parametros": (
        "parametro", "parámetro", "parametros", "parámetros",
        "dominio nombre valor",
    ),
    "jobs": ("job", "jobs", "scheduler", "tarea programada", "reintento"),
}

TABLA_KEYWORDS_CONSULTA = tuple(
    kw for keywords in TABLAS_CONSULTA.values() for kw in keywords
) + ("codigo", "código", "codigos", "códigos")

# Filtro de fuente por documento (consulta → substring en path/fuente)
FUENTE_CONSULTA = (
    ("manual de operacion", "Manual Operacion"),
    ("manual operacion", "Manual Operacion"),
    ("manual", "Manual Operacion"),
    ("guia implementacion", "Guia implementacion"),
    ("guía implementacion", "Guia implementacion"),
    ("guia", "Guia implementacion"),
    ("especificacion webservice", "Especificacion.Webservices"),
    ("especificación webservice", "Especificacion.Webservices"),
    ("webservice", "Especificacion.Webservices"),
    ("especificacion", "Especificacion.Webservices"),
)

_CODIGOS_ABONABILIDAD = re.compile(r"\b(?:RA|RC|X)\d{2}\b|\b0000\b", re.I)
_ES_INDICE = re.compile(r"\.{4,}")


def detectar_tabla_id(texto):
    """Etiqueta tablas reconocibles para recuperarlas completas."""
    if not texto or not texto.strip():
        return ""

    lower = texto.lower()

    if re.search(r"\bERRORES_ORDEN\s+[A-Z0-9]+\b", texto, re.I):
        return "errores_orden"

    if texto.count("ERROR_EXCEPTION") >= 2:
        return "excepciones"
    if "códigos y mensajes de excepciones" in lower:
        return "excepciones"
    if "codigos y mensajes de excepciones" in lower:
        return "excepciones"

    if "abonabilidad" in lower:
        if not _ES_INDICE.search(texto):
            return "abonabilidad"

    if ("codigo descripcion" in lower or "código descripción" in lower) and _CODIGOS_ABONABILIDAD.search(texto):
        return "abonabilidad"

    if "dominio nombre valor" in lower or (
        "parameter" in lower and re.search(r"\bCOD_", texto, re.I)
    ):
        return "parametros"

    if re.search(r"codigo job descripci", lower) or "codigo job descripción" in lower:
        return "jobs"

    return ""


def inferir_tabla_id_consulta(pregunta):
    """Infiere tabla_id a partir de la pregunta (listado completo)."""
    p = pregunta.lower()
    for tabla_id, keywords in TABLAS_CONSULTA.items():
        if any(k in p for k in keywords):
            return tabla_id
    return "excepciones"


def inferir_filtro_fuente(pregunta):
    """Infiere filtro de fuente si la pregunta menciona un documento concreto."""
    p = pregunta.lower()
    for keyword, patron in FUENTE_CONSULTA:
        if keyword in p:
            return patron
    return None

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
    "abonabilidad": (
        "abonabilidad", "cargo", "cargos", "abono", "express",
        "codigos de respuesta", "códigos de respuesta",
        "codigo de respuesta", "código de respuesta",
    ),
    "parametros": (
        "parametro", "parámetro", "parametros", "parámetros",
        "dominio nombre valor",
    ),
    "jobs": ("job", "jobs", "scheduler", "tarea programada", "reintento"),
}

TABLA_KEYWORDS_CONSULTA = tuple(
    kw for keywords in TABLAS_CONSULTA.values() for kw in keywords
) + ("codigo", "código", "codigos", "códigos")

# Filtro de fuente por documento (consulta → substring en path/fuente).
# Solo se usan nombres de documento suficientemente específicos: keywords de un
# solo término genérico ("manual", "guia", "webservice", "especificacion")
# causaban misrouting porque el dato podía vivir en otro documento.
FUENTE_CONSULTA = (
    ("manual de operacion", "Manual Operacion"),
    ("manual operacion", "Manual Operacion"),
    ("manual de operación", "Manual Operacion"),
    ("guia implementacion", "Guia implementacion"),
    ("guía implementacion", "Guia implementacion"),
    ("guia de implementacion", "Guia implementacion"),
    ("guía de implementación", "Guia implementacion"),
    ("especificacion webservice", "Especificacion.Webservices"),
    ("especificación webservice", "Especificacion.Webservices"),
    ("especificacion de webservice", "Especificacion.Webservices"),
    ("especificación de webservice", "Especificacion.Webservices"),
)

_CODIGOS_ABONABILIDAD = re.compile(r"\b(?:RA|RC|X)\d{2}\b|\b0000\b", re.I)
# Códigos que identifican SOLO la tabla de abonabilidad (RA/RC/X), sin el 0000
# ambiguo que aparece también en texto narrativo de flujos.
_CODIGOS_RARCX = re.compile(r"\b(?:RA|RC|X)\d{2}\b", re.I)
_PARECE_PARAMETROS = re.compile(r"\bPARAMETER\b|\bCOD_|dominio nombre valor", re.I)
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

    # Continuación de la tabla de abonabilidad: fragmentos sin encabezado
    # (p. ej. RA07-RA09 en la página siguiente) que igual contienen varias
    # filas RA/RC/X. Se excluye texto que parece de la tabla de parámetros.
    if (
        not _ES_INDICE.search(texto)
        and not _PARECE_PARAMETROS.search(texto)
        and len(_CODIGOS_RARCX.findall(texto)) >= 2
    ):
        return "abonabilidad"

    if "dominio nombre valor" in lower or (
        "parameter" in lower and re.search(r"\bCOD_", texto, re.I)
    ):
        return "parametros"

    if re.search(r"codigo job descripci", lower) or "codigo job descripción" in lower:
        return "jobs"

    return ""


def inferir_tabla_id_consulta(pregunta):
    """Infiere tabla_id a partir de la pregunta (listado completo).

    Devuelve "" si no reconoce la tabla, para que el retriever caiga a
    búsqueda híbrida en vez de forzar una tabla equivocada.
    """
    p = pregunta.lower()
    for tabla_id, keywords in TABLAS_CONSULTA.items():
        if any(k in p for k in keywords):
            return tabla_id
    return ""


def inferir_filtro_fuente(pregunta):
    """Infiere filtro de fuente si la pregunta menciona un documento concreto."""
    p = pregunta.lower()
    for keyword, patron in FUENTE_CONSULTA:
        if keyword in p:
            return patron
    return None

"""Perfiles de documentos ACH para el router de indexación."""

import os
import re
import unicodedata

# Perfiles tabulares: detección por nombre de archivo y marcadores en el PDF
PERFILES_TABULARES = {
    "errores_orden": {
        "nombres": (
            "codigoerrororden",
            "codigoserror",
            "erroresorden",
            "errores",
        ),
        "marcadores": (
            "COD_DOMINIO",
            "ERRORES_ORDEN",
        ),
    },
    "abonabilidad": {
        "nombres": ("abonabilidad",),
        "marcadores": (
            "abonabilidad",
            "codigo descripcion",
            "código descripción",
            "RA00",
            "RC00",
        ),
    },
    "excepciones": {
        "nombres": (
            "excepcion",
            "excepciones",
            "exception",
            "error_exception",
        ),
        "marcadores": (
            "ERROR_EXCEPTION",
            "codigos y mensajes de excepciones",
            "códigos y mensajes de excepciones",
        ),
    },
    "parametros": {
        "nombres": (
            "parametro",
            "parametros",
            "cod_ach",
        ),
        "marcadores": (
            "dominio nombre valor",
            "DOMINIO NOMBRE VALOR",
            "COD_ACH",
            "Parameter",
        ),
    },
    "jobs": {
        "nombres": (
            "job",
            "jobs",
            "scheduler",
        ),
        "marcadores": (
            "codigo job",
            "código job",
            "CODIGO JOB",
            "job descripcion",
            "job descripción",
        ),
    },
}

# Límites X (puntos PDF) para perfil errores_orden multi-columna
PDF_TABULAR_COLUMNAS_ERRORES_ORDEN = {
    "dominio_max": 120,
    "valor_min": 120,
    "valor_max": 155,
    "descripcion_min": 155,
    "descripcion_max": 490,
    "extensa_min": 490,
}

# Alias retrocompatible
PDF_TABULAR_COLUMNAS_DEFAULT = PDF_TABULAR_COLUMNAS_ERRORES_ORDEN

# Patrones de fila por perfil (extracción por líneas de texto)
_FILA_ABONABILIDAD = re.compile(r"\b(?:RA|RC|X)\d{2}\b|\b0000\b", re.I)
_FILA_EXCEPCION = re.compile(r"\bERROR_EXCEPTION\b|\b\d{3,5}\b", re.I)
_FILA_PARAMETRO = re.compile(r"\bCOD_ACH[_\w]*\b", re.I)
_FILA_JOB = re.compile(r"\b(?:job|codigo\s*job|código\s*job)\b", re.I)

_FILA_POR_PERFIL = {
    "abonabilidad": _FILA_ABONABILIDAD,
    "excepciones": _FILA_EXCEPCION,
    "parametros": _FILA_PARAMETRO,
    "jobs": _FILA_JOB,
}

# Detección tabla_id en CSV por columnas
_CSV_COLUMNAS_TABLA = {
    "errores_orden": ("cod_dominio", "valor", "errores_orden"),
    "abonabilidad": ("codigo", "código", "abonabilidad"),
    "excepciones": ("error_exception", "mensaje", "codigo", "código"),
    "parametros": ("dominio", "nombre", "valor", "cod_ach", "parameter"),
    "jobs": ("codigo job", "código job", "job", "descripcion", "descripción"),
}


def _normalizar_nombre(ruta):
    return os.path.basename(ruta).lower().replace(" ", "").replace("_", "")


def _sin_acentos(texto):
    normalizado = unicodedata.normalize("NFD", texto)
    return "".join(c for c in normalizado if unicodedata.category(c) != "Mn").lower()


def _coincide_nombre_perfil(ruta, perfil):
    nombre = _normalizar_nombre(ruta)
    return any(p in nombre for p in PERFILES_TABULARES[perfil]["nombres"])


def _coincide_marcador(texto, perfil):
    texto_norm = _sin_acentos(texto)
    for marcador in PERFILES_TABULARES[perfil]["marcadores"]:
        if _sin_acentos(marcador) in texto_norm:
            return True
    return False


def muestra_es_tabular(ruta, paginas=2):
    """Lee las primeras páginas buscando marcadores de cualquier perfil tabular."""
    import pdfplumber

    with pdfplumber.open(ruta) as pdf:
        for page in pdf.pages[:paginas]:
            texto = page.extract_text() or ""
            for perfil in PERFILES_TABULARES:
                if _coincide_marcador(texto, perfil):
                    return True
    return False


def detectar_perfil_tabular_pdf(ruta):
    """Retorna tabla_id del perfil tabular o None si es narrativo."""
    for perfil in PERFILES_TABULARES:
        if _coincide_nombre_perfil(ruta, perfil):
            return perfil

    try:
        import pdfplumber

        with pdfplumber.open(ruta) as pdf:
            for page in pdf.pages[:2]:
                texto = page.extract_text() or ""
                for perfil in PERFILES_TABULARES:
                    if _coincide_marcador(texto, perfil):
                        return perfil
    except Exception:
        pass

    return None


def es_pdf_tabular(ruta):
    return detectar_perfil_tabular_pdf(ruta) is not None


def coincide_nombre_tabular(ruta):
    return es_pdf_tabular(ruta)


def es_fila_tabular_perfil(linea, perfil):
    if perfil == "errores_orden":
        return "ERRORES_ORDEN" in linea.upper()
    patron = _FILA_POR_PERFIL.get(perfil)
    return patron.search(linea) is not None if patron else False


def detectar_tabla_id_archivo(nombre_archivo, columnas=None):
    """Detecta tabla_id por nombre de archivo y/o columnas CSV."""
    nombre = nombre_archivo.lower()
    cols = {_sin_acentos(c) for c in (columnas or [])}

    for perfil, cfg in PERFILES_TABULARES.items():
        if any(p in _normalizar_nombre(nombre_archivo) for p in cfg["nombres"]):
            return perfil

    if nombre.startswith("errores"):
        return "errores_orden"

    for perfil, hints in _CSV_COLUMNAS_TABLA.items():
        if any(h in cols for h in hints):
            return perfil

    return ""

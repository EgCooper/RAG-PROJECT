"""Extracción de PDFs tabulares multi-columna (coordenadas o líneas por perfil)."""

from collections import defaultdict

import pdfplumber

from config.documents_ach import (
    PDF_TABULAR_COLUMNAS_ERRORES_ORDEN,
    detectar_perfil_tabular_pdf,
    es_fila_tabular_perfil,
)

_TOL_FILA = 2.5


def _agrupar_filas(words, tol=_TOL_FILA):
    filas = defaultdict(list)
    for word in words:
        clave = round(word["top"] / tol) * tol
        filas[clave].append(word)
    return [(top, sorted(palabras, key=lambda w: w["x0"])) for top, palabras in sorted(filas.items())]


def _texto_columna(palabras, x_min, x_max):
    return " ".join(w["text"] for w in palabras if x_min <= w["x0"] < x_max).strip()


def _es_fila_encabezado(dominio, valor, descripcion):
    return dominio == "COD_DOMINIO" or valor == "VALOR" or descripcion == "Descripcion"


def _formatear_fila_errores(codigo, descripcion, descripcion_extensa):
    partes = [codigo]
    if descripcion:
        partes.append(f"Descripcion: {descripcion}")
    if descripcion_extensa and descripcion_extensa != descripcion:
        partes.append(f"Descripcion_extensa: {descripcion_extensa}")
    return "\n".join(partes)


def _extraer_errores_orden(ruta_pdf, columnas=None):
    cols = columnas or PDF_TABULAR_COLUMNAS_ERRORES_ORDEN
    chunks = []

    with pdfplumber.open(ruta_pdf) as pdf:
        for numero_pagina, page in enumerate(pdf.pages, start=1):
            palabras = page.extract_words() or []
            for _top, fila in _agrupar_filas(palabras):
                dominio = _texto_columna(fila, 0, cols["dominio_max"])
                valor = _texto_columna(fila, cols["valor_min"], cols["valor_max"])
                descripcion = _texto_columna(fila, cols["descripcion_min"], cols["descripcion_max"])
                extensa = _texto_columna(fila, cols["extensa_min"], 10_000)

                if _es_fila_encabezado(dominio, valor, descripcion):
                    continue
                if not dominio.startswith("ERRORES_ORDEN") or not valor:
                    continue

                codigo = f"{dominio} {valor}"
                texto = _formatear_fila_errores(codigo, descripcion, extensa)
                if not texto.strip():
                    continue

                chunks.append({
                    "texto": texto,
                    "tipo": "tabla_fila",
                    "pagina": numero_pagina,
                    "tabla_id": "errores_orden",
                })

    return chunks


def _extraer_por_lineas(ruta_pdf, perfil):
    """Extrae filas reconocibles por perfil desde texto de página."""
    chunks = []

    with pdfplumber.open(ruta_pdf) as pdf:
        for numero_pagina, page in enumerate(pdf.pages, start=1):
            texto = page.extract_text() or ""
            for indice, linea in enumerate(texto.splitlines(), start=1):
                linea = linea.strip()
                if len(linea) < 4 or not es_fila_tabular_perfil(linea, perfil):
                    continue
                chunks.append({
                    "texto": linea,
                    "tipo": "tabla_fila",
                    "pagina": numero_pagina * 1000 + indice,
                    "tabla_id": perfil,
                })

    return chunks


def extraer_pdf_tabular(ruta_pdf, perfil=None):
    """
    Agrupa palabras por fila (Y) y columnas (X) o por líneas según perfil.
    Devuelve chunks listos para indexar (1 fila = 1 chunk).
    """
    perfil = perfil or detectar_perfil_tabular_pdf(ruta_pdf) or "errores_orden"

    if perfil == "errores_orden":
        chunks = _extraer_errores_orden(ruta_pdf)
        if chunks:
            return chunks

    return _extraer_por_lineas(ruta_pdf, perfil)

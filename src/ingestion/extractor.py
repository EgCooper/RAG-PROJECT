"""Extracción de PDFs narrativos (manuales, guías) con unstructured."""

from unstructured.partition.pdf import partition_pdf

from src.ingestion.cleaning import limpiar_elementos

_PDF_LANGUAGES = ["spa", "eng"]


def extraer_pdf(ruta_pdf):
    elementos = partition_pdf(
        ruta_pdf,
        strategy="hi_res",
        languages=_PDF_LANGUAGES,
    )
    return limpiar_elementos(elementos)

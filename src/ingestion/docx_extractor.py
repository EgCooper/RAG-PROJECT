"""Extracción de DOCX narrativos con unstructured."""

from unstructured.partition.docx import partition_docx

from src.ingestion.cleaning import limpiar_elementos


def extraer_docx(ruta):
    elementos = partition_docx(ruta)
    return limpiar_elementos(elementos)

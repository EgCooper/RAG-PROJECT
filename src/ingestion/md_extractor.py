"""Extracción de Markdown (.md) con unstructured."""

from unstructured.partition.md import partition_md

from src.ingestion.cleaning import limpiar_elementos


def extraer_md(ruta):
    elementos = partition_md(filename=ruta)
    return limpiar_elementos(elementos)

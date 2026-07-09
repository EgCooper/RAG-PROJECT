"""Router de indexación: elige extractor según tipo y perfil del archivo."""

import os

from config.documents_ach import es_pdf_tabular
from src.ingestion.chunker import dividir_chunks
from src.ingestion.csv_extractor import extraer_csv
from src.ingestion.docx_extractor import extraer_docx
from src.ingestion.extractor import extraer_pdf
from src.ingestion.pdf_tabular import extraer_pdf_tabular
from src.ingestion.pptx_extractor import extraer_presentacion
from src.ingestion.validate_index import validar_chunks

_FORMATOS = {
    ".pdf": "pdf",
    ".csv": "csv",
    ".docx": "docx",
    ".ppt": "ppt",
    ".pptx": "pptx",
}


def detectar_perfil(ruta):
    extension = os.path.splitext(ruta)[1].lower()
    if extension not in _FORMATOS:
        return None

    if extension == ".pdf":
        return "pdf_tabular" if es_pdf_tabular(ruta) else "pdf_narrativo"
    if extension == ".csv":
        return "csv"
    return extension.lstrip(".")


def construir_chunks(ruta, validar=True):
    """
    Extrae y valida chunks listos para embeddear.
    Retorna (chunks, info) donde info incluye perfil y resultado de validación.
    """
    extension = os.path.splitext(ruta)[1].lower()
    if extension not in _FORMATOS:
        raise ValueError(f"Formato no soportado: {extension}")

    perfil = detectar_perfil(ruta)

    if perfil == "pdf_tabular":
        from config.documents_ach import detectar_perfil_tabular_pdf
        chunks = extraer_pdf_tabular(ruta)
        perfil = f"pdf_tabular:{detectar_perfil_tabular_pdf(ruta) or 'errores_orden'}"
    elif perfil == "pdf_narrativo":
        elementos = extraer_pdf(ruta)
        chunks = dividir_chunks(elementos)
    elif perfil == "docx":
        elementos = extraer_docx(ruta)
        chunks = dividir_chunks(elementos)
    elif perfil == "csv":
        chunks = extraer_csv(ruta)
    elif perfil in ("ppt", "pptx"):
        elementos = extraer_presentacion(ruta)
        chunks = dividir_chunks(elementos)
    else:
        raise ValueError(f"Perfil desconocido para {ruta}")

    if perfil.startswith("pdf_tabular"):
        validacion = validar_chunks(chunks, perfil="pdf_tabular")
    else:
        validacion = validar_chunks(chunks, perfil=perfil)

    if validar and not validacion["ok"]:
        mensaje = "; ".join(validacion["errores"])
        raise ValueError(f"Validación de indexación falló: {mensaje}")

    info = {
        "perfil": perfil,
        "validacion": validacion,
    }
    return chunks, info

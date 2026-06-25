# Librarie for extracting text from pdf
from unstructured.partition.pdf import partition_pdf

def extraer_pdf(ruta_pdf):
    elementos = partition_pdf(
        ruta_pdf,
        strategy="hi_res",
        languages=["spa", "eng"]
    )
    return elementos

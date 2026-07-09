"""Extracción de archivos CSV para indexación (1 fila = 1 chunk)."""

import csv
import io
import os

from config.documents_ach import detectar_tabla_id_archivo

_ENCODINGS = ("utf-8-sig", "cp1252", "latin-1")


def _leer_csv(ruta_csv):
    """Intenta leer el CSV probando encodings comunes (UTF-8, Windows)."""
    ultimo_error = None
    for encoding in _ENCODINGS:
        try:
            with open(ruta_csv, encoding=encoding, newline="") as archivo:
                return archivo.read(), encoding
        except UnicodeDecodeError as e:
            ultimo_error = e
    raise ValueError(
        "No se pudo leer el CSV: encoding no reconocido. "
        "Guarde el archivo como UTF-8 o Windows-1252 (Excel en español)."
    ) from ultimo_error


def _detectar_delimitador(contenido):
    muestra = contenido[:8192]
    try:
        dialect = csv.Sniffer().sniff(muestra, delimiters=";,\t")
        return dialect.delimiter
    except csv.Error:
        primera = muestra.splitlines()[0] if muestra else ""
        if primera.count(";") >= primera.count(","):
            return ";"
        return ","


def _normalizar_celda(valor):
    if valor is None:
        return ""
    if isinstance(valor, list):
        partes = [_normalizar_celda(v) for v in valor]
        return " ".join(p for p in partes if p)
    return str(valor).strip()


def _fila_a_texto(fila):
    return "\n".join(f"{clave}: {valor}" for clave, valor in fila.items() if valor)


def extraer_csv(ruta_csv):
    chunks = []
    nombre = os.path.basename(ruta_csv)

    contenido, _encoding = _leer_csv(ruta_csv)
    delimitador = _detectar_delimitador(contenido)
    lector = csv.DictReader(io.StringIO(contenido), delimiter=delimitador)
    if not lector.fieldnames:
        return chunks

    columnas = [c.strip() for c in lector.fieldnames if c and c.strip()]
    tabla_id = detectar_tabla_id_archivo(nombre, columnas)

    for indice, fila in enumerate(lector, start=1):
        fila_limpia = {
            (k or "").strip(): _normalizar_celda(v)
            for k, v in fila.items()
            if k is not None and str(k).strip()
        }
        texto = _fila_a_texto(fila_limpia)
        if not texto:
            continue
        chunks.append({
            "texto": texto,
            "tipo": "tabla_fila",
            "pagina": indice,
            "tabla_id": tabla_id,
        })

    return chunks

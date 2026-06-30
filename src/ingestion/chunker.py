from collections import defaultdict

from langchain_text_splitters import RecursiveCharacterTextSplitter

from config.settings import (
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    MIN_CHUNK_CHARS,
    TABLE_CHUNK_SIZE,
)


def _detectar_tabla_id(texto):
    """Etiqueta tablas reconocibles para recuperarlas completas."""
    if texto.count("ERROR_EXCEPTION") >= 2:
        return "excepciones"
    lower = texto.lower()
    if "códigos y mensajes de excepciones" in lower:
        return "excepciones"
    if "codigos y mensajes de excepciones" in lower:
        return "excepciones"
    return ""


def _merge_tablas_consecutivas(elementos):
    """Une tablas consecutivas del PDF (p. ej. una tabla que ocupa varias páginas)."""
    tablas = []
    textos = []
    pagina_inicio = None

    for elemento in elementos:
        if type(elemento).__name__ == "Table":
            texto = (elemento.text or "").strip()
            if not texto:
                continue
            pagina = getattr(elemento.metadata, "page_number", None) or 0
            if not textos:
                pagina_inicio = pagina
            textos.append(texto)
        else:
            if textos:
                tablas.append((pagina_inicio, "\n".join(textos)))
                textos = []
                pagina_inicio = None

    if textos:
        tablas.append((pagina_inicio, "\n".join(textos)))

    return tablas


def _dividir_tabla(texto, pagina, tabla_id):
    """Divide tablas largas por filas, repitiendo el encabezado en cada fragmento."""
    if len(texto) <= TABLE_CHUNK_SIZE:
        return [(texto, pagina, tabla_id)]

    lineas = [linea for linea in texto.splitlines() if linea.strip()]
    if len(lineas) <= 1:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=TABLE_CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
        )
        return [(parte, pagina, tabla_id) for parte in splitter.split_text(texto)]

    encabezado = lineas[0]
    filas = lineas[1:]
    partes = []
    buffer = [encabezado]
    buffer_len = len(encabezado)

    for fila in filas:
        extra = len(fila) + 1
        if buffer_len + extra > TABLE_CHUNK_SIZE and len(buffer) > 1:
            partes.append(( "\n".join(buffer), pagina, tabla_id))
            buffer = [encabezado, fila]
            buffer_len = len(encabezado) + extra
        else:
            buffer.append(fila)
            buffer_len += extra

    if buffer:
        partes.append(("\n".join(buffer), pagina, tabla_id))

    return partes


def dividir_chunks(elementos):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )

    por_pagina = defaultdict(list)
    chunks = []

    for pagina, texto_tabla in _merge_tablas_consecutivas(elementos):
        tabla_id = _detectar_tabla_id(texto_tabla)
        for parte, pag, tid in _dividir_tabla(texto_tabla, pagina, tabla_id):
            parte = parte.strip()
            if len(parte) >= MIN_CHUNK_CHARS:
                chunks.append({
                    "texto": parte,
                    "tipo": "tabla",
                    "pagina": pag,
                    "tabla_id": tid,
                })

    for elemento in elementos:
        if type(elemento).__name__ == "Table":
            continue
        if not elemento.text:
            continue
        pagina = getattr(elemento.metadata, "page_number", None) or 0
        por_pagina[pagina].append(elemento.text.strip())

    for pagina in sorted(por_pagina.keys()):
        texto_pagina = "\n".join(por_pagina[pagina])
        for parte in splitter.split_text(texto_pagina):
            parte = parte.strip()
            if len(parte) < MIN_CHUNK_CHARS:
                continue
            chunks.append({
                "texto": parte,
                "tipo": "pagina",
                "pagina": pagina,
                "tabla_id": _detectar_tabla_id(parte),
            })

    return chunks

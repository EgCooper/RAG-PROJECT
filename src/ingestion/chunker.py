from collections import defaultdict

from langchain_text_splitters import RecursiveCharacterTextSplitter

from config.settings import (
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    MIN_CHUNK_CHARS,
    TABLE_CHUNK_SIZE,
)
from config.tables_ach import detectar_tabla_id


def _es_page_break(elemento) -> bool:
    nombre = type(elemento).__name__
    categoria = getattr(elemento, "category", None) or getattr(elemento, "type", None)
    return nombre == "PageBreak" or categoria == "PageBreak"


def _pagina_de(elemento, pagina_actual: int) -> int:
    """Lee page_number del metadata; si falta, usa el contador por PageBreak."""
    meta = getattr(elemento, "metadata", None)
    raw = None
    if meta is not None:
        raw = getattr(meta, "page_number", None)
        if raw is None and isinstance(meta, dict):
            raw = meta.get("page_number")
    try:
        if raw is not None and int(raw) > 0:
            return int(raw)
    except (TypeError, ValueError):
        pass
    return pagina_actual if pagina_actual > 0 else 1


def _merge_tablas_consecutivas(elementos):
    """Une tablas consecutivas del PDF (p. ej. una tabla que ocupa varias páginas)."""
    tablas = []
    textos = []
    pagina_inicio = None
    pagina_actual = 1

    for elemento in elementos:
        if _es_page_break(elemento):
            pagina_actual += 1
            continue
        if type(elemento).__name__ == "Table":
            texto = (elemento.text or "").strip()
            if not texto:
                continue
            pagina = _pagina_de(elemento, pagina_actual)
            pagina_actual = max(pagina_actual, pagina)
            if not textos:
                pagina_inicio = pagina
            textos.append(texto)
        else:
            if textos:
                tablas.append((pagina_inicio, "\n".join(textos)))
                textos = []
                pagina_inicio = None
            if not _es_page_break(elemento):
                pagina_actual = max(pagina_actual, _pagina_de(elemento, pagina_actual))

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
            partes.append(("\n".join(buffer), pagina, tabla_id))
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
    pagina_actual = 1

    for pagina, texto_tabla in _merge_tablas_consecutivas(elementos):
        tabla_id = detectar_tabla_id(texto_tabla)
        for parte, pag, tid in _dividir_tabla(texto_tabla, pagina, tabla_id):
            parte = parte.strip()
            if len(parte) >= MIN_CHUNK_CHARS:
                chunks.append({
                    "texto": parte,
                    "tipo": "tabla",
                    "pagina": pag if pag and pag > 0 else 1,
                    "tabla_id": tid,
                })

    for elemento in elementos:
        if _es_page_break(elemento):
            pagina_actual += 1
            continue
        if type(elemento).__name__ == "Table":
            continue
        if not getattr(elemento, "text", None):
            continue
        pagina = _pagina_de(elemento, pagina_actual)
        pagina_actual = max(pagina_actual, pagina)
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
                "pagina": pagina if pagina and pagina > 0 else 1,
                "tabla_id": detectar_tabla_id(parte),
            })

    return chunks

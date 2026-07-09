"""
Inspecciona la extracción de un PDF (elementos, chunks y códigos detectados).

Uso:
  python scripts/dump_extraction.py data/CódigosErrorOrdenACH.pdf
  python scripts/dump_extraction.py data/archivo.pdf --strategy hi_res
  python scripts/dump_extraction.py data/archivo.pdf --compare
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unstructured.partition.pdf import partition_pdf

from src.ingestion.cleaning import limpiar_elementos
from src.ingestion.chunker import dividir_chunks
from src.ingestion.index_router import construir_chunks, detectar_perfil

_PDF_LANGUAGES = ["spa", "eng"]

_STRICT_ERROR = re.compile(r"\bERROR_[A-Z0-9_]+\b", re.I)
_STRICT_PREFIJO = re.compile(r"\b(?:X|RA|EC|D|RC)\d{2}\b", re.I)
_STRICT_4DIG = re.compile(r"\b\d{4}\b")

_LOOSE_ERROR = re.compile(r"\bERROR_[A-Z0-9_O]+\b", re.I)
_LOOSE_PREFIJO = re.compile(r"\b(?:X|RA|EC|D|RC)[0-9O]{2}\b", re.I)

_AMBIGUO_CHARS = re.compile(r"[0O]")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Volcar extracción de PDF para validar códigos y tablas.",
    )
    parser.add_argument(
        "pdf",
        help="Ruta al PDF (p. ej. data/CódigosErrorOrdenACH.pdf)",
    )
    parser.add_argument(
        "--strategy",
        choices=("fast", "hi_res"),
        default="fast",
        help="Estrategia unstructured (default: fast)",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Comparar fast vs hi_res y escribir diff de códigos",
    )
    parser.add_argument(
        "--output",
        help="Carpeta de salida (default: data/debug/<nombre_pdf>/)",
    )
    return parser.parse_args()


def resolver_pdf(ruta):
    if not os.path.isfile(ruta):
        candidato = os.path.join("data", ruta)
        if os.path.isfile(candidato):
            return os.path.normpath(candidato)
        print(f"ERROR: no se encontró PDF: {ruta}")
        sys.exit(1)
    return os.path.normpath(ruta)


def extraer_con_estrategia(ruta_pdf, strategy):
    elementos = partition_pdf(
        ruta_pdf,
        strategy=strategy,
        languages=_PDF_LANGUAGES,
    )
    return limpiar_elementos(elementos)


def _pagina(elemento):
    return getattr(elemento.metadata, "page_number", None) or 0


def _tipo(elemento):
    return type(elemento).__name__


def _es_codigo_estricto(token):
    return (
        _STRICT_ERROR.fullmatch(token)
        or _STRICT_PREFIJO.fullmatch(token)
        or _STRICT_4DIG.fullmatch(token)
    )


def _es_codigo_suelto(token):
    return _LOOSE_ERROR.fullmatch(token) or _LOOSE_PREFIJO.fullmatch(token)


def extraer_codigos(texto):
    """Devuelve (estrictos, sospechosos) en el texto."""
    estrictos = set()
    sospechosos = []

    candidatos = set()
    for patron in (_LOOSE_ERROR, _LOOSE_PREFIJO, _STRICT_4DIG):
        candidatos.update(patron.findall(texto))

    for token in sorted(candidatos, key=str.upper):
        if _es_codigo_estricto(token):
            estrictos.add(token.upper())
            continue
        if _es_codigo_suelto(token) and _AMBIGUO_CHARS.search(token):
            sospechosos.append({
                "token": token,
                "motivo": "Contiene O/0 en posición ambigua (no pasa validación estricta)",
            })

    return estrictos, sospechosos


def agrupar_por_pagina(elementos):
    por_pagina = defaultdict(list)
    for elemento in elementos:
        if not elemento.text or not elemento.text.strip():
            continue
        por_pagina[_pagina(elemento)].append(elemento)
    return por_pagina


def volcar_elementos(elementos, out_dir):
    por_pagina = agrupar_por_pagina(elementos)

    raw_path = os.path.join(out_dir, "raw_por_pagina.txt")
    tablas_path = os.path.join(out_dir, "tablas_por_pagina.txt")
    elementos_path = os.path.join(out_dir, "elementos.json")

    registros = []
    with open(raw_path, "w", encoding="utf-8") as raw_f, open(
        tablas_path, "w", encoding="utf-8"
    ) as tablas_f:
        for pagina in sorted(por_pagina.keys()):
            raw_f.write(f"\n{'=' * 72}\nPÁGINA {pagina}\n{'=' * 72}\n")
            for elemento in por_pagina[pagina]:
                tipo = _tipo(elemento)
                texto = elemento.text.strip()
                raw_f.write(f"\n--- {tipo} ---\n{texto}\n")
                registros.append({
                    "pagina": pagina,
                    "tipo": tipo,
                    "chars": len(texto),
                    "texto": texto,
                })
                if tipo == "Table":
                    tablas_f.write(f"\n{'=' * 72}\nPÁGINA {pagina}\n{'=' * 72}\n")
                    tablas_f.write(f"{texto}\n")

    with open(elementos_path, "w", encoding="utf-8") as f:
        json.dump(registros, f, ensure_ascii=False, indent=2)

    return raw_path, tablas_path, elementos_path


def volcar_chunks(chunks, out_dir):
    chunks_path = os.path.join(out_dir, "chunks_preview.json")
    preview_path = os.path.join(out_dir, "chunks_preview.txt")

    datos = []
    with open(preview_path, "w", encoding="utf-8") as txt_f:
        for i, chunk in enumerate(chunks, 1):
            registro = {
                "n": i,
                "tipo": chunk.get("tipo"),
                "pagina": chunk.get("pagina"),
                "tabla_id": chunk.get("tabla_id", ""),
                "chars": len(chunk.get("texto", "")),
                "texto": chunk.get("texto", ""),
            }
            datos.append(registro)
            txt_f.write(f"\n{'─' * 72}\n")
            txt_f.write(
                f"CHUNK {i} | tipo={registro['tipo']} | p.{registro['pagina']}"
                f" | tabla_id={registro['tabla_id'] or '-'} | {registro['chars']} chars\n"
            )
            txt_f.write(f"{'─' * 72}\n")
            txt_f.write(f"{registro['texto']}\n")

    with open(chunks_path, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)

    return chunks_path, preview_path


def volcar_codigos(elementos, chunks, out_dir):
    codigos_path = os.path.join(out_dir, "codigos_detectados.txt")
    sospechosos_path = os.path.join(out_dir, "codigos_sospechosos.txt")

    todo_texto = []
    for elemento in elementos:
        if elemento.text:
            todo_texto.append(elemento.text)
    for chunk in chunks:
        todo_texto.append(chunk["texto"])

    texto_completo = "\n".join(todo_texto)
    estrictos, sospechosos = extraer_codigos(texto_completo)

    lineas_sospechosas = []
    for linea in texto_completo.splitlines():
        _, sosp = extraer_codigos(linea)
        for item in sosp:
            lineas_sospechosas.append({
                "linea": linea.strip(),
                **item,
            })

    with open(codigos_path, "w", encoding="utf-8") as f:
        f.write(f"Códigos válidos (patrón estricto): {len(estrictos)}\n\n")
        for codigo in sorted(estrictos):
            f.write(f"  {codigo}\n")

    with open(sospechosos_path, "w", encoding="utf-8") as f:
        f.write(f"Tokens sospechosos (posible confusión 0/O): {len(lineas_sospechosas)}\n\n")
        vistos = set()
        for item in lineas_sospechosas:
            clave = (item["token"], item["linea"])
            if clave in vistos:
                continue
            vistos.add(clave)
            f.write(f"  TOKEN: {item['token']}\n")
            f.write(f"  MOTIVO: {item['motivo']}\n")
            f.write(f"  LÍNEA: {item['linea']}\n\n")

    return codigos_path, sospechosos_path, estrictos, lineas_sospechosas


def volcar_router(ruta, out_dir):
    """Chunks que produciría el router de indexación (pipeline real)."""
    perfil = detectar_perfil(ruta)
    chunks, info = construir_chunks(ruta, validar=False)
    router_dir = os.path.join(out_dir, "router")
    os.makedirs(router_dir, exist_ok=True)

    preview_path = os.path.join(router_dir, "chunks_preview.txt")
    json_path = os.path.join(router_dir, "chunks_preview.json")

    datos = []
    with open(preview_path, "w", encoding="utf-8") as txt_f:
        txt_f.write(f"Perfil router: {perfil}\n")
        txt_f.write(f"Chunks: {len(chunks)}\n")
        for i, chunk in enumerate(chunks, 1):
            registro = {
                "n": i,
                "tipo": chunk.get("tipo"),
                "pagina": chunk.get("pagina"),
                "tabla_id": chunk.get("tabla_id", ""),
                "chars": len(chunk.get("texto", "")),
                "texto": chunk.get("texto", ""),
            }
            datos.append(registro)
            txt_f.write(f"\n{'─' * 72}\n")
            txt_f.write(
                f"CHUNK {i} | tipo={registro['tipo']} | p.{registro['pagina']}"
                f" | tabla_id={registro['tabla_id'] or '-'} | {registro['chars']} chars\n"
            )
            txt_f.write(f"{'─' * 72}\n")
            txt_f.write(f"{registro['texto']}\n")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"perfil": perfil, "validacion": info["validacion"], "chunks": datos}, f, ensure_ascii=False, indent=2)

    return preview_path, json_path, perfil


def procesar_pdf(ruta_pdf, strategy, out_dir):
    os.makedirs(out_dir, exist_ok=True)

    print(f"Extrayendo ({strategy}): {ruta_pdf}")
    elementos = extraer_con_estrategia(ruta_pdf, strategy)
    chunks = dividir_chunks(elementos)

    raw_path, tablas_path, elementos_path = volcar_elementos(elementos, out_dir)
    chunks_json, chunks_txt = volcar_chunks(chunks, out_dir)
    codigos_path, sospechosos_path, estrictos, sospechosos = volcar_codigos(
        elementos, chunks, out_dir
    )

    router_preview, router_json, perfil_router = volcar_router(ruta_pdf, out_dir)

    resumen = {
        "pdf": ruta_pdf,
        "strategy": strategy,
        "perfil_router": perfil_router,
        "elementos": len(elementos),
        "chunks": len(chunks),
        "codigos_estrictos": len(estrictos),
        "lineas_sospechosas": len(sospechosos),
        "archivos": {
            "raw_por_pagina": raw_path,
            "tablas_por_pagina": tablas_path,
            "elementos": elementos_path,
            "chunks_preview": chunks_json,
            "chunks_preview_txt": chunks_txt,
            "codigos_detectados": codigos_path,
            "codigos_sospechosos": sospechosos_path,
            "router_chunks_preview": router_preview,
            "router_chunks_json": router_json,
        },
    }

    resumen_path = os.path.join(out_dir, "resumen.json")
    with open(resumen_path, "w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=2)

    return resumen


def comparar_estrategias(ruta_pdf, base_out):
    fast_dir = os.path.join(base_out, "fast")
    hi_res_dir = os.path.join(base_out, "hi_res")

    r_fast = procesar_pdf(ruta_pdf, "fast", fast_dir)
    r_hi_res = procesar_pdf(ruta_pdf, "hi_res", hi_res_dir)

    with open(os.path.join(fast_dir, "codigos_detectados.txt"), encoding="utf-8") as f:
        fast_codigos = {
            line.strip()
            for line in f.readlines()[2:]
            if line.strip() and not line.startswith("Códigos")
        }
    with open(os.path.join(hi_res_dir, "codigos_detectados.txt"), encoding="utf-8") as f:
        hi_res_codigos = {
            line.strip()
            for line in f.readlines()[2:]
            if line.strip() and not line.startswith("Códigos")
        }

    solo_fast = sorted(fast_codigos - hi_res_codigos)
    solo_hi_res = sorted(hi_res_codigos - fast_codigos)
    en_ambos = sorted(fast_codigos & hi_res_codigos)

    diff_path = os.path.join(base_out, "compare_codigos.txt")
    with open(diff_path, "w", encoding="utf-8") as f:
        f.write("COMPARACIÓN fast vs hi_res\n\n")
        f.write(f"En ambos ({len(en_ambos)}):\n")
        for c in en_ambos:
            f.write(f"  {c}\n")
        f.write(f"\nSolo en fast ({len(solo_fast)}):\n")
        for c in solo_fast:
            f.write(f"  {c}\n")
        f.write(f"\nSolo en hi_res ({len(solo_hi_res)}):\n")
        for c in solo_hi_res:
            f.write(f"  {c}\n")
        f.write("\nSospechosos fast: ")
        f.write(f"{r_fast['lineas_sospechosas']}\n")
        f.write("Sospechosos hi_res: ")
        f.write(f"{r_hi_res['lineas_sospechosas']}\n")

    print(f"\nComparación guardada en: {diff_path}")
    return diff_path


def main():
    args = parse_args()
    ruta_pdf = resolver_pdf(args.pdf)
    nombre = os.path.splitext(os.path.basename(ruta_pdf))[0]
    base_out = args.output or os.path.join("data", "debug", nombre)

    if args.compare:
        comparar_estrategias(ruta_pdf, base_out)
        print(f"\nSalida en: {base_out}/")
        return

    out_dir = os.path.join(base_out, args.strategy)
    resumen = procesar_pdf(ruta_pdf, args.strategy, out_dir)

    print(f"\nElementos (unstructured): {resumen['elementos']}")
    print(f"Chunks (unstructured): {resumen['chunks']}")
    print(f"Perfil router: {resumen['perfil_router']}")
    print(f"Códigos estrictos: {resumen['codigos_estrictos']}")
    print(f"Líneas sospechosas (0/O): {resumen['lineas_sospechosas']}")
    print(f"\nArchivos en: {out_dir}/")
    for etiqueta, path in resumen["archivos"].items():
        print(f"  {etiqueta}: {path}")
    print("\nRevisá router/chunks_preview.txt para ver lo que indexará el pipeline.")


if __name__ == "__main__":
    main()

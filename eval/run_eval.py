"""Corre el dataset de evaluacion contra el RAGPipeline y genera un reporte.

Uso:
    python eval/run_eval.py                  # corre todas las preguntas
    python eval/run_eval.py --regla 6-sin-info
    python eval/run_eval.py --tipo fuera_contexto
    python eval/run_eval.py --ids resp_ra05,lista_ra
    python eval/run_eval.py --limit 5
    python eval/run_eval.py --out eval/report.json

Para cada pregunta reporta:
  - RECUPERACION: si los chunks traidos contienen las keywords_contexto esperadas.
  - RESPUESTA: si la respuesta del LLM contiene las keywords_respuesta esperadas.
  - DIAGNOSTICO: separa fallos de PROMPT (recupero bien pero respondio mal)
    de fallos de RECUPERACION (no trajo el contexto correcto).
"""

import argparse
import json
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.rag.pipeline import RAGPipeline
from src.llm.prompt import _NO_INFO_RESPONSE

DATASET = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dataset.json")


def quitar_think(texto):
    """Elimina el razonamiento <think>...</think> y deja solo la respuesta final.

    Los modelos de razonamiento anteponen su cadena de pensamiento, que NO es la
    respuesta al usuario. Evaluar sobre ella genera falsos positivos y negativos.
    """
    if not texto:
        return ""
    cierre = texto.rfind("</think>")
    if cierre != -1:
        return texto[cierre + len("</think>"):].strip()
    return re.sub(r"</?think>", "", texto, flags=re.I).strip()


def norm(texto):
    """Minusculas + sin acentos, para comparar de forma robusta."""
    if not texto:
        return ""
    t = unicodedata.normalize("NFKD", str(texto))
    t = "".join(c for c in t if not unicodedata.combining(c))
    return t.lower()


def keywords_presentes(keywords, texto):
    """Devuelve (encontradas, faltantes) de keywords dentro de texto."""
    tn = norm(texto)
    encontradas = [k for k in keywords if norm(k) in tn]
    faltantes = [k for k in keywords if norm(k) not in tn]
    return encontradas, faltantes


def es_no_info(respuesta):
    """True si la respuesta es el mensaje fijo de 'no hay informacion'."""
    r = norm(respuesta)
    return norm(_NO_INFO_RESPONSE) in r or "no encontre informacion" in r


def tiene_tabla_markdown(respuesta):
    """Heuristica: detecta tablas markdown."""
    lineas = respuesta.splitlines()
    for ln in lineas:
        if ln.count("|") >= 2:
            return True
        if set(ln.strip()) <= {"-", "|", ":", " "} and "-" in ln and "|" in ln:
            return True
    return False


def evaluar_item(item, respuesta, chunks):
    tipo = item.get("tipo")
    respuesta_cruda = respuesta
    respuesta = quitar_think(respuesta)
    texto_chunks = "\n".join(c.get("texto", "") for c in chunks)

    kw_ctx = item.get("keywords_contexto", []) or []
    _, ctx_faltantes = keywords_presentes(kw_ctx, texto_chunks)
    recuperacion_ok = len(ctx_faltantes) == 0 if kw_ctx else None

    if tipo == "fuera_contexto":
        respuesta_ok = es_no_info(respuesta)
        resp_faltantes = [] if respuesta_ok else ["<mensaje 'no info' esperado>"]
    else:
        kw_resp = item.get("keywords_respuesta", []) or []
        _, resp_faltantes = keywords_presentes(kw_resp, respuesta)
        respuesta_ok = len(resp_faltantes) == 0 if kw_resp else None

    problemas_formato = []
    # Formato enriquecido permitido: solo avisamos si un código puntual vino como tabla grande
    if tipo == "codigo_especifico" and tiene_tabla_markdown(respuesta):
        lineas_tabla = sum(1 for ln in respuesta.splitlines() if ln.count("|") >= 2)
        if lineas_tabla >= 4:
            problemas_formato.append(
                "tabla markdown demasiado extensa para un solo código"
            )

    if respuesta_ok:
        diagnostico = "OK"
    elif tipo == "fuera_contexto":
        diagnostico = "PROMPT (alucino en vez de negar)"
    elif recuperacion_ok is False:
        diagnostico = "RECUPERACION (los chunks no traian la info)"
    elif recuperacion_ok is True:
        diagnostico = "PROMPT (recupero bien pero respondio mal)"
    else:
        diagnostico = "REVISAR"

    return {
        "id": item.get("id"),
        "tipo": tipo,
        "regla": item.get("regla"),
        "pregunta": item.get("pregunta"),
        "respuesta": respuesta,
        "respuesta_cruda": respuesta_cruda,
        "respuesta_esperada": item.get("respuesta_esperada"),
        "recuperacion_ok": recuperacion_ok,
        "ctx_faltantes": ctx_faltantes,
        "respuesta_ok": bool(respuesta_ok),
        "resp_faltantes": resp_faltantes,
        "problemas_formato": problemas_formato,
        "diagnostico": diagnostico,
    }


def parse_args():
    p = argparse.ArgumentParser(description="Evaluar el RAG contra eval/dataset.json")
    p.add_argument("--ids", help="Solo estos ids (separados por coma)")
    p.add_argument("--tipo", help="Filtrar por tipo (ej: fuera_contexto)")
    p.add_argument("--regla", help="Filtrar por regla (ej: 6-sin-info)")
    p.add_argument("--limit", type=int, help="Correr solo las primeras N preguntas")
    p.add_argument("--out", default="eval/report.json", help="Ruta del reporte JSON")
    p.add_argument("--quiet", action="store_true", help="No imprimir cada respuesta completa")
    return p.parse_args()


def cargar_dataset(args):
    with open(DATASET, encoding="utf-8") as f:
        items = json.load(f)

    if args.ids:
        wanted = {i.strip() for i in args.ids.split(",")}
        items = [it for it in items if it.get("id") in wanted]
    if args.tipo:
        items = [it for it in items if it.get("tipo") == args.tipo]
    if args.regla:
        items = [it for it in items if it.get("regla") == args.regla]
    if args.limit:
        items = items[: args.limit]
    return items


def main():
    args = parse_args()
    items = cargar_dataset(args)
    if not items:
        print("No hay preguntas que coincidan con el filtro.")
        sys.exit(0)

    print(f"\nEvaluando {len(items)} preguntas...\n")
    pipeline = RAGPipeline()
    resultados = []

    try:
        for i, item in enumerate(items, 1):
            pregunta = item["pregunta"]
            respuesta, chunks = pipeline.consultar(pregunta)
            r = evaluar_item(item, respuesta, chunks)
            resultados.append(r)

            estado = "PASS" if r["respuesta_ok"] and not r["problemas_formato"] else "FAIL"
            print(f"[{i}/{len(items)}] {estado}  {r['id']}  ({r['regla']})")
            print(f"    Q: {pregunta}")
            if not args.quiet:
                print(f"    R: {r['respuesta'][:300]}")
            if estado == "FAIL":
                if r["diagnostico"] != "OK":
                    print(f"    -> {r['diagnostico']}")
                if r["resp_faltantes"]:
                    print(f"    -> faltan en respuesta: {r['resp_faltantes']}")
                if r["recuperacion_ok"] is False:
                    print(f"    -> faltan en chunks: {r['ctx_faltantes']}")
                for pf in r["problemas_formato"]:
                    print(f"    -> formato: {pf}")
            print()
    finally:
        pipeline.cerrar()

    resumen(resultados, args.out)


def resumen(resultados, out_path):
    total = len(resultados)
    passed = sum(1 for r in resultados if r["respuesta_ok"] and not r["problemas_formato"])
    fallos_prompt = [r for r in resultados if "PROMPT" in r["diagnostico"]]
    fallos_recup = [r for r in resultados if "RECUPERACION" in r["diagnostico"]]
    fallos_formato = [r for r in resultados if r["problemas_formato"]]

    print("=" * 60)
    print(f"RESULTADO: {passed}/{total} correctas")
    print(f"  Fallos de PROMPT:       {len(fallos_prompt)}")
    print(f"  Fallos de RECUPERACION: {len(fallos_recup)}")
    print(f"  Problemas de FORMATO:   {len(fallos_formato)}")

    por_regla = {}
    for r in resultados:
        regla = r["regla"] or "sin-regla"
        d = por_regla.setdefault(regla, {"total": 0, "ok": 0})
        d["total"] += 1
        if r["respuesta_ok"] and not r["problemas_formato"]:
            d["ok"] += 1

    print("\nPor regla del prompt:")
    for regla, d in sorted(por_regla.items()):
        print(f"  {regla:24s} {d['ok']}/{d['total']}")

    if fallos_prompt:
        print("\nFallos de PROMPT (arreglables ajustando SYSTEM_PROMPT):")
        for r in fallos_prompt:
            print(f"  - {r['id']} ({r['regla']}): {r['diagnostico']}")

    if fallos_recup:
        print("\nFallos de RECUPERACION (el prompt NO los arregla, es el retriever):")
        for r in fallos_recup:
            print(f"  - {r['id']}: faltan chunks {r['ctx_faltantes']}")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)
    print(f"\nReporte detallado guardado en: {out_path}")


if __name__ == "__main__":
    main()

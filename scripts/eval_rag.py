"""
Evalúa retrieval y respuestas del RAG contra eval/dataset.json.

Uso:
  python scripts/eval_rag.py                  # retrieval + LLM
  python scripts/eval_rag.py --solo-retrieval # solo chunks (sin API LLM)
  python scripts/eval_rag.py --limit 3        # primeras N preguntas
  python scripts/eval_rag.py --output eval/resultados.json
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import RERANK_ENABLED, RERANK_MODEL, TOP_K_CHUNKS
from src.retrieval.reranker import cargar_reranker
from src.retrieval.retriever import buscar_chunks
from src.ingestion.embedder import cargar_modelo
from src.storage.weaviate_client import conectar, crear_collection
from src.llm.llm_factory import crear_cliente, generar_respuesta
from src.llm.prompt import SYSTEM_PROMPT, construir_prompt
from config.validate_env import validar_env

DATASET_DEFAULT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "eval",
    "dataset.json",
)


def _normalizar(texto):
    return " ".join((texto or "").lower().split())


def _contiene(haystack, needle):
    return _normalizar(needle) in _normalizar(haystack)


def _cargar_dataset(ruta):
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def _contexto_combinado(chunks):
    return "\n".join(c["texto"] for c in chunks)


def _evaluar_keywords(texto, keywords):
    if not keywords:
        return True, []
    faltantes = [k for k in keywords if not _contiene(texto, k)]
    return not faltantes, faltantes


def _evaluar_retrieval(caso, chunks):
    fuente_ok = True
    pagina_ok = True
    rank_fuente = None
    rank_pagina = None

    fuente_esperada = caso.get("fuente")
    pagina_esperada = caso.get("pagina")

    for i, chunk in enumerate(chunks, 1):
        basename = os.path.basename(chunk.get("fuente", ""))
        if fuente_esperada and _contiene(basename, fuente_esperada):
            if rank_fuente is None:
                rank_fuente = i
        if pagina_esperada is not None and chunk.get("pagina") == pagina_esperada:
            if rank_pagina is None:
                rank_pagina = i

    if fuente_esperada:
        fuente_ok = rank_fuente is not None
    if pagina_esperada is not None:
        pagina_ok = rank_pagina is not None

    ctx_ok, ctx_faltantes = _evaluar_keywords(
        _contexto_combinado(chunks),
        caso.get("keywords_contexto", []),
    )

    hit = fuente_ok and pagina_ok and ctx_ok
    mrr = 0.0
    if rank_fuente:
        mrr = 1.0 / rank_fuente
    elif rank_pagina:
        mrr = 1.0 / rank_pagina

    return {
        "hit": hit,
        "fuente_ok": fuente_ok,
        "pagina_ok": pagina_ok,
        "contexto_ok": ctx_ok,
        "contexto_faltantes": ctx_faltantes,
        "rank_fuente": rank_fuente,
        "rank_pagina": rank_pagina,
        "mrr": round(mrr, 4),
        "num_chunks": len(chunks),
    }


def _evaluar_respuesta(caso, respuesta):
    ok, faltantes = _evaluar_keywords(respuesta, caso.get("keywords_respuesta", []))
    return {"ok": ok, "faltantes": faltantes}


def _icono(ok):
    return "OK" if ok else "FAIL"


def _imprimir_fila(caso, ret, resp=None):
    linea = (
        f"  [{_icono(ret['hit'])}] {caso['id']:<22} "
        f"ctx={_icono(ret['contexto_ok'])} "
        f"fuente={_icono(ret['fuente_ok'])} "
        f"rank={ret['rank_fuente'] or '-'}"
    )
    if resp is not None:
        linea += f"  resp={_icono(resp['ok'])}"
    print(linea)
    if not ret["contexto_ok"]:
        print(f"       contexto faltante: {ret['contexto_faltantes']}")
    if resp and not resp["ok"]:
        print(f"       respuesta faltante: {resp['faltantes']}")


def _resumir(resultados, incluir_respuesta):
    n = len(resultados)
    if n == 0:
        return {}

    hit = sum(1 for r in resultados if r["retrieval"]["hit"])
    ctx = sum(1 for r in resultados if r["retrieval"]["contexto_ok"])
    fuente = sum(1 for r in resultados if r["retrieval"]["fuente_ok"])
    mrr = sum(r["retrieval"]["mrr"] for r in resultados) / n

    resumen = {
        "total": n,
        "retrieval_hit": hit,
        "retrieval_hit_pct": round(100 * hit / n, 1),
        "contexto_ok": ctx,
        "contexto_ok_pct": round(100 * ctx / n, 1),
        "fuente_ok": fuente,
        "fuente_ok_pct": round(100 * fuente / n, 1),
        "mrr_promedio": round(mrr, 4),
    }

    if incluir_respuesta:
        resp_ok = sum(1 for r in resultados if r.get("respuesta", {}).get("ok"))
        resumen["respuesta_ok"] = resp_ok
        resumen["respuesta_ok_pct"] = round(100 * resp_ok / n, 1)

    return resumen


def main():
    parser = argparse.ArgumentParser(description="Evaluar retrieval y respuestas RAG")
    parser.add_argument("--dataset", default=DATASET_DEFAULT, help="Ruta al JSON de casos")
    parser.add_argument("--solo-retrieval", action="store_true", help="No llamar al LLM")
    parser.add_argument("--limit", type=int, default=0, help="Máximo de casos a evaluar")
    parser.add_argument("--output", default="", help="Guardar resultados en JSON")
    args = parser.parse_args()

    casos = _cargar_dataset(args.dataset)
    if args.limit > 0:
        casos = casos[: args.limit]

    print(f"Dataset: {args.dataset} ({len(casos)} casos)")
    print(f"Rerank: {'activo' if RERANK_ENABLED else 'desactivado'} | TOP_K={TOP_K_CHUNKS}")
    print()

    print("Cargando modelos...")
    modelo = cargar_modelo()
    cliente = conectar()
    crear_collection(cliente)
    reranker = None
    if RERANK_ENABLED:
        print(f"Cargando reranker: {RERANK_MODEL}...")
        reranker = cargar_reranker()

    cliente_llm = None
    if not args.solo_retrieval:
        validar_env(requiere_llm=True)
        print("Cargando LLM...")
        cliente_llm = crear_cliente()

    resultados = []
    print()
    print(f"{'ID':<24} {'retrieval':^10} {'ctx':^5} {'fuente':^7} {'rank':^5} {'resp':^5}")
    print("-" * 62)

    for caso in casos:
        pregunta = caso["pregunta"]
        vector = modelo.embed_query(pregunta)
        chunks = buscar_chunks(cliente, pregunta, vector, reranker)
        ret = _evaluar_retrieval(caso, chunks)

        resp = None
        if not args.solo_retrieval:
            prompt = construir_prompt(pregunta, chunks)
            respuesta = generar_respuesta(cliente_llm, SYSTEM_PROMPT, prompt)
            resp = _evaluar_respuesta(caso, respuesta)
        else:
            respuesta = None

        _imprimir_fila(caso, ret, resp)

        resultados.append({
            "id": caso["id"],
            "pregunta": pregunta,
            "tipo": caso.get("tipo", ""),
            "retrieval": ret,
            "respuesta": resp,
            "top_chunk": {
                "fuente": os.path.basename(chunks[0]["fuente"]) if chunks else None,
                "pagina": chunks[0].get("pagina") if chunks else None,
                "score": chunks[0].get("score") if chunks else None,
            },
            "respuesta_texto": respuesta,
        })

    resumen = _resumir(resultados, not args.solo_retrieval)

    print()
    print("=" * 62)
    print(f"Retrieval hit@{TOP_K_CHUNKS}: {resumen['retrieval_hit']}/{resumen['total']} ({resumen['retrieval_hit_pct']}%)")
    print(f"Contexto OK:           {resumen['contexto_ok']}/{resumen['total']} ({resumen['contexto_ok_pct']}%)")
    print(f"Fuente OK:             {resumen['fuente_ok']}/{resumen['total']} ({resumen['fuente_ok_pct']}%)")
    print(f"MRR promedio:          {resumen['mrr_promedio']}")
    if not args.solo_retrieval:
        print(f"Respuesta OK:          {resumen['respuesta_ok']}/{resumen['total']} ({resumen['respuesta_ok_pct']}%)")

    if args.output:
        salida = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "dataset": args.dataset,
            "solo_retrieval": args.solo_retrieval,
            "rerank_enabled": RERANK_ENABLED,
            "resumen": resumen,
            "resultados": resultados,
        }
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(salida, f, ensure_ascii=False, indent=2)
        print(f"\nResultados guardados en: {args.output}")

    cliente.close()
    sys.exit(0 if resumen.get("retrieval_hit") == resumen.get("total") else 1)


if __name__ == "__main__":
    main()

"""Atribuye qué chunks del retrieval respaldan de verdad la respuesta del LLM."""

import re

from src.llm.prompt import _NO_INFO_RESPONSE
from src.rag.errors import MENSAJE_INDICE_VACIO

_TOKEN = re.compile(r"[a-záéíóúñü0-9]{2,}", re.IGNORECASE)
_MD_NOISE = re.compile(r"[*_`#|>\[\]()]+")
# Tokens muy frecuentes en respuestas ACH / español que no discriminan fuente
_STOP = frozenset({
    "el", "la", "los", "las", "un", "una", "de", "del", "en", "al", "a",
    "y", "o", "que", "se", "por", "para", "con", "su", "sus", "es", "son",
    "no", "si", "como", "más", "mas", "esta", "este", "estos", "estas",
    "también", "tambien", "según", "segun", "indica", "código", "codigo",
    "error", "descripción", "descripcion", "tabla", "documento", "manual",
    "página", "pagina", "the", "and", "for", "with",
})

_RESPUESTAS_SIN_FUENTE = frozenset({
    _NO_INFO_RESPONSE.strip(),
    MENSAJE_INDICE_VACIO.strip(),
})


def _normalizar(texto: str) -> str:
    limpio = _MD_NOISE.sub(" ", texto or "")
    return " ".join(limpio.lower().split())


def _tokens(texto: str) -> set[str]:
    return {
        t for t in _TOKEN.findall(_normalizar(texto))
        if t not in _STOP and len(t) >= 2
    }


def _score_overlap(respuesta_tokens: set[str], chunk_tokens: set[str]) -> float:
    if not respuesta_tokens or not chunk_tokens:
        return 0.0
    inter = respuesta_tokens & chunk_tokens
    if not inter:
        return 0.0
    # Jaccard sesgado a cobertura de la respuesta (qué tanto del answer está en el chunk)
    cobertura = len(inter) / len(respuesta_tokens)
    jaccard = len(inter) / len(respuesta_tokens | chunk_tokens)
    return 0.7 * cobertura + 0.3 * jaccard


def marcar_chunks_usados(
    respuesta: str,
    chunks: list[dict],
    *,
    umbral_relativo: float = 0.55,
    max_usadas: int = 3,
    score_minimo: float = 0.08,
) -> list[dict]:
    """
    Marca chunks que mejor respaldan la respuesta (usada=True).

    - Si la respuesta es la de "sin información", ninguna usada.
    - Siempre marca el de mayor score si supera score_minimo.
    - Marca siguientes si score >= umbral_relativo * max_score (hasta max_usadas).
    """
    if not chunks:
        return chunks

    for c in chunks:
        c["usada"] = False
        c["attribution_score"] = 0.0

    texto = (respuesta or "").strip()
    if not texto or texto in _RESPUESTAS_SIN_FUENTE:
        return chunks

    resp_tokens = _tokens(texto)
    if not resp_tokens:
        return chunks

    scored = []
    for c in chunks:
        score = _score_overlap(resp_tokens, _tokens(c.get("texto", "")))
        c["attribution_score"] = score
        scored.append((score, c))

    scored.sort(key=lambda x: x[0], reverse=True)
    mejor = scored[0][0]
    if mejor < score_minimo:
        return chunks

    marcadas = 0
    for score, c in scored:
        if marcadas >= max_usadas:
            break
        if score < score_minimo:
            break
        if score < mejor * umbral_relativo:
            break
        c["usada"] = True
        marcadas += 1

    return chunks

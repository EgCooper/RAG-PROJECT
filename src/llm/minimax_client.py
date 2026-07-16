from openai import OpenAI

from config.settings import (
    MINIMAX_API_KEY,
    MINIMAX_BASE_URL,
    MINIMAX_LLM_MODEL,
    TEMPERATURE,
    MAX_TOKENS,
    TOP_P,
)


def crear_cliente():
    return OpenAI(
        base_url=MINIMAX_BASE_URL,
        api_key=MINIMAX_API_KEY,
    )


def generar_respuesta(client, system_prompt, prompt_usuario):
    respuesta = client.chat.completions.create(
        model=MINIMAX_LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": prompt_usuario},
        ],
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
        top_p=TOP_P,
    )

    return respuesta.choices[0].message.content


def generar_respuesta_stream(client, system_prompt, prompt_usuario):
    """Genera tokens de la respuesta (sync iterator)."""
    stream = client.chat.completions.create(
        model=MINIMAX_LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt_usuario},
        ],
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
        top_p=TOP_P,
        stream=True,
    )
    for evento in stream:
        try:
            delta = evento.choices[0].delta
            texto = getattr(delta, "content", None) or ""
        except (IndexError, AttributeError):
            continue
        if texto:
            yield texto

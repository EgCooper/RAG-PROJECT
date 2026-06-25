from groq import Groq
from config.settings import (
    GROQ_API_KEY,
    LLM_MODEL,
    TEMPERATURE,
    MAX_TOKENS,
    TOP_P,
    FREQUENCY_PENALTY,
    PRESENCE_PENALTY
)

def crear_cliente():
    return Groq(api_key=GROQ_API_KEY)

def generar_respuesta(client, system_prompt, prompt_usuario):
    respuesta = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": prompt_usuario}
        ],
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
        top_p=TOP_P,
        frequency_penalty=FREQUENCY_PENALTY,
        presence_penalty=PRESENCE_PENALTY
    )

    return respuesta.choices[0].message.content

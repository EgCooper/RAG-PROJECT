from config.settings import LLM_PROVIDER, GROQ_LLM_MODEL, MINIMAX_LLM_MODEL


def _modelo_activo():
    if LLM_PROVIDER == "minimax":
        return MINIMAX_LLM_MODEL
    return GROQ_LLM_MODEL


def crear_cliente():
    if LLM_PROVIDER == "minimax":
        from src.llm.minimax_client import crear_cliente as _crear
    else:
        from src.llm.groq_client import crear_cliente as _crear
    return _crear()


def generar_respuesta(client, system_prompt, prompt_usuario):
    if LLM_PROVIDER == "minimax":
        from src.llm.minimax_client import generar_respuesta as _generar
    else:
        from src.llm.groq_client import generar_respuesta as _generar
    return _generar(client, system_prompt, prompt_usuario)


def info_proveedor():
    return f"{LLM_PROVIDER} ({_modelo_activo()})"

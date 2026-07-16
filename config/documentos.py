"""Secciones de documento (manuales vs informes) para filtrar el chat."""

SECCIONES = ("manual", "informe")
SECCION_DEFAULT = "manual"

FILTROS_CHAT = ("todos", "documentos", "informes")
FILTRO_CHAT_DEFAULT = "todos"

ETIQUETAS_SECCION = {
    "manual": "Documento",
    "informe": "Informe",
}


def normalizar_seccion(valor: str | None) -> str:
    s = (valor or SECCION_DEFAULT).strip().lower()
    if s in ("manuales",):
        return "manual"
    if s in ("informes",):
        return "informe"
    if s in SECCIONES:
        return s
    return SECCION_DEFAULT

"""Configuración por proyecto (prompt / dominio)."""

from src.llm.prompt import construir_system_prompt

# Seeds por defecto al bootstrap (solo estos 3)
PROYECTOS_SEED = (
    {
        "slug": "ach",
        "nombre": "ACH",
        "descripcion": "Sistema ACH — documentación técnica",
        "config": {"dominio": "ach", "usa_tablas_ach": True},
    },
    {
        "slug": "feel",
        "nombre": "FEEL",
        "descripcion": "Sistema FEEL — documentación técnica",
        "config": {"dominio": "feel", "usa_tablas_ach": False},
    },
    {
        "slug": "banca",
        "nombre": "BANCA",
        "descripcion": "Sistema BANCA — documentación técnica",
        "config": {"dominio": "banca", "usa_tablas_ach": False},
    },
)

# Slugs antiguos que ya no deben aparecer en la UI
PROYECTOS_OBSOLETOS = ("feel-banca",)

DEFAULT_PROYECTO_SLUG = "ach"


def system_prompt_para(proyecto) -> str:
    """Resuelve el system prompt según slug/config del proyecto."""
    config = proyecto.config or {}
    nombre = proyecto.nombre or proyecto.slug
    dominio = config.get("dominio") or proyecto.slug
    return construir_system_prompt(nombre_sistema=nombre, dominio=dominio)


def usa_tablas_ach(proyecto) -> bool:
    config = proyecto.config or {}
    if "usa_tablas_ach" in config:
        return bool(config["usa_tablas_ach"])
    return (proyecto.slug or "").lower() == "ach"

"""Validación de variables de entorno requeridas."""

import os
import sys

from config.settings import LLM_PROVIDER, GROQ_API_KEY, MINIMAX_API_KEY


def validar_env(requiere_llm=True):
    """Valida configuración mínima. Sale con código 1 si falta algo crítico."""
    errores = []

    if requiere_llm:
        if LLM_PROVIDER == "minimax":
            if not MINIMAX_API_KEY or MINIMAX_API_KEY.startswith("YOUR_"):
                errores.append("MINIMAX_API_KEY no configurada en .env")
        elif LLM_PROVIDER == "groq":
            if not GROQ_API_KEY or GROQ_API_KEY.startswith("YOUR_"):
                errores.append("GROQ_API_KEY no configurada en .env")
        else:
            errores.append(f"LLM_PROVIDER inválido: {LLM_PROVIDER!r} (usa minimax o groq)")

    if errores:
        print("Error de configuración:", file=sys.stderr)
        for e in errores:
            print(f"  - {e}", file=sys.stderr)
        print("\nCopia .env.example a .env y completa las API keys.", file=sys.stderr)
        sys.exit(1)

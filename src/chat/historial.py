import re

from config.settings import CHAT_HISTORY_MAX

_SEGUIMIENTO = re.compile(
    r"^(y |también|tambien|ese |esa |eso |el otro|la otra|más |mas |"
    r"explica|amplía|amplia|detalla|qué más|que más|cuál era|cual era)",
    re.I,
)
_CODIGO_EN_PREGUNTA = re.compile(
    r"\b(?:ERROR_\w+|\d{4}|(?:X|RA|EC|D|RC)\d{2})\b",
    re.I,
)


class HistorialChat:
    def __init__(self, max_turnos=CHAT_HISTORY_MAX):
        self.max_turnos = max_turnos
        self._turnos = []

    def agregar(self, pregunta, respuesta):
        self._turnos.append({"pregunta": pregunta, "respuesta": respuesta})
        if len(self._turnos) > self.max_turnos:
            self._turnos = self._turnos[-self.max_turnos:]

    def limpiar(self):
        self._turnos.clear()

    def turnos(self):
        return list(self._turnos)

    def vacio(self):
        return not self._turnos

    def es_seguimiento(self, pregunta):
        p = pregunta.strip()
        if not p or not self._turnos:
            return False
        if _SEGUIMIENTO.search(p):
            return True
        if _CODIGO_EN_PREGUNTA.search(p):
            return False
        return len(p.split()) <= 5

    def pregunta_para_retrieval(self, pregunta):
        if not self.es_seguimiento(pregunta):
            return pregunta
        anterior = self._turnos[-1]["pregunta"]
        return f"{anterior} {pregunta}"

    def formatear_para_prompt(self):
        if not self._turnos:
            return ""
        lineas = []
        for i, turno in enumerate(self._turnos, 1):
            lineas.append(f"Turno {i}:")
            lineas.append(f"Usuario: {turno['pregunta']}")
            lineas.append(f"Asistente: {turno['respuesta']}")
        return "\n".join(lineas)

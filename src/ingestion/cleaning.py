from unstructured.cleaners.core import clean_extra_whitespace


def limpiar_elementos(elementos):
    for elemento in elementos:
        if elemento.text:
            elemento.text = clean_extra_whitespace(elemento.text)
    return elementos

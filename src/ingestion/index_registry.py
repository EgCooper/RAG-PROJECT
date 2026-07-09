import json
import os

REGISTRY_PATH = os.path.join("data", ".index_registry.json")


def normalizar_clave(ruta):
    return os.path.normpath(ruta).replace("\\", "/")


def cargar_registro():
    if not os.path.isfile(REGISTRY_PATH):
        return {}
    try:
        with open(REGISTRY_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def guardar_registro(registro):
    os.makedirs(os.path.dirname(REGISTRY_PATH), exist_ok=True)
    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(registro, f, indent=2, ensure_ascii=False)
        f.write("\n")


def huella_archivo(ruta):
    stat = os.stat(ruta)
    return {"mtime": stat.st_mtime, "size": stat.st_size}


def _huella_coincide(actual, guardada):
    return (
        guardada is not None
        and actual["mtime"] == guardada.get("mtime")
        and actual["size"] == guardada.get("size")
    )


def registrar_indexacion(registro, ruta, chunks):
    clave = normalizar_clave(ruta)
    entrada = huella_archivo(ruta)
    entrada["chunks"] = chunks
    registro[clave] = entrada


def sincronizar_registro(registro, ruta, chunks=None):
    """Marca el archivo como indexado sin reindexar (p. ej. tras migración sin registro)."""
    clave = normalizar_clave(ruta)
    entrada = huella_archivo(ruta)
    if chunks is not None:
        entrada["chunks"] = chunks
    elif clave in registro and "chunks" in registro[clave]:
        entrada["chunks"] = registro[clave]["chunks"]
    registro[clave] = entrada


def eliminar_entrada(registro, ruta):
    clave = normalizar_clave(ruta)
    if clave in registro:
        del registro[clave]


def eliminar_del_registro(ruta):
    registro = cargar_registro()
    eliminar_entrada(registro, ruta)
    guardar_registro(registro)


def necesita_indexar(ruta, fuentes_weaviate, registro):
    clave = normalizar_clave(ruta)
    en_weaviate = clave in fuentes_weaviate
    actual = huella_archivo(ruta)
    guardada = registro.get(clave)

    if not en_weaviate:
        return True

    if guardada is None:
        sincronizar_registro(registro, ruta)
        return False

    return not _huella_coincide(actual, guardada)

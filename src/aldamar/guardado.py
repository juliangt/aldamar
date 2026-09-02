"""El esquema de las partidas guardadas: versión, migración y validación.

Dentro de un `partida.json` hay ahora un campo `version` que dice qué
esquema trae. Cargar es siempre el mismo camino: leer → validar las
claves que cualquier versión necesita → rechazar las versiones futuras
→ migrar paso a paso hasta la actual → validar el esquema completo.

Los guardados de antes del versionado se tratan como versión 0 y
migran solos; los de una versión más nueva se rechazan con un mensaje
claro, sin traceback (issue 15). Sumar un cambio de esquema = escribir
su paso `_de_N_a_M` y anotarlo en `_PASOS`: cada versión tiene su
camino de migración explícito, y ninguna partida se rompe en silencio.
"""

from __future__ import annotations

import json
from typing import Callable

# La versión del esquema que escribe esta edición del juego.
VERSION = 1


class PartidaInvalida(ValueError):
    """El archivo de partida no sirve: versión del futuro o esquema roto."""


# Claves que cualquier versión del esquema necesita para poder migrarse:
# sin ellas ni se sabe qué partida es.
_BASE = (
    "aventura",
    "dificultad",
    "nombre",
    "vida",
    "monedas",
    "corrupcion",
    "inventario",
    "companeros",
    "lugar",
    "lugar_previo",
    "flags",
    "enemigos",
    "tomados",
    "monedas_tomadas",
)

# El esquema completo de la versión actual (`_BASE` más lo que añadieron
# las versiones posteriores y las de siempre con valor opcional).
_ESQUEMA = _BASE + ("version", "experiencia", "nivel", "equipado", "derrotados", "visitados", "final")


def _de_0_a_1(estado: dict) -> dict:
    """Pre-versionado → 1: progresión, equipo puesto y huella del viaje.

    El héroe de entonces va a nivel 1, sin experiencia y con la grieta
    del viaje por delante (`derrotados` y `visitados` empiezan aquí).
    `equipado: None` significa «vestía siempre lo mejor del inventario»:
    el motor lo traduce a autoequiparse al cargar.
    """
    estado["experiencia"] = 0
    estado["nivel"] = 1
    estado["equipado"] = None
    estado["derrotados"] = []
    estado["visitados"] = [estado["lugar"]]
    estado["version"] = 1
    return estado


# El camino de migración: de cada versión, su paso. `migrar` los aplica
# en orden hasta llegar a `VERSION`.
_PASOS: dict[int, Callable[[dict], dict]] = {
    0: _de_0_a_1,
}


def migrar(estado: dict, desde: int) -> dict:
    """Lleva un estado de la versión `desde` a la actual, paso a paso."""
    for paso in range(desde, VERSION):
        siguiente = _PASOS.get(paso)
        if siguiente is None:
            raise PartidaInvalida(
                f"no hay camino de migración del esquema {paso} al {VERSION}: "
                f"falta el paso en guardado._PASOS"
            )
        estado = siguiente(estado)
    return estado


def preparar(estado: dict, ruta: str = "<partida>") -> dict:
    """Valida un estado leído y lo deja en el esquema actual.

    `ruta` es solo para el parte de culpa: los errores nombran el
    archivo y el campo, al nivel del cargador de aventuras.
    """
    if not isinstance(estado, dict):
        raise PartidaInvalida(f"{ruta}: la partida no es un objeto JSON")
    # la versión se mira antes que nada: una partida del futuro tiene un
    # esquema que no conocemos, y el mensaje útil es el de la versión
    version = estado.get("version", 0)  # sin campo: esquema pre-versionado
    if isinstance(version, bool) or not isinstance(version, int) or version < 0:
        raise PartidaInvalida(
            f"{ruta}: el campo 'version' debe ser un entero a partir de 0 (llegó {version!r})"
        )
    if version > VERSION:
        raise PartidaInvalida(
            f"{ruta}: esta partida viene de una versión más nueva de Aldamar "
            f"(esquema {version}; esta edición entiende hasta el {VERSION})."
        )
    faltan = [c for c in _BASE if c not in estado]
    if faltan:
        raise PartidaInvalida(
            f"{ruta}: faltan campos obligatorios: {', '.join(faltan)}"
        )
    estado = migrar(estado, version)
    faltan = [c for c in _ESQUEMA if c not in estado]
    if faltan:
        raise PartidaInvalida(
            f"{ruta}: el esquema {VERSION} queda incompleto, faltan campos: {', '.join(faltan)}"
        )
    return estado


def cargar(ruta: str) -> dict:
    """Lee un archivo de partida y lo devuelve en el esquema actual."""
    try:
        with open(ruta, encoding="utf-8") as f:
            estado = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise PartidaInvalida(f"No se pudo leer la partida {ruta}: {e}") from e
    return preparar(estado, ruta)

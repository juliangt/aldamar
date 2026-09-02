"""El legado de la serie: lo que cruza de una aventura a la siguiente.

Junto a `partida.json` vive `legado.json`: las banderas canónicas que
cada aventura deja escritas al terminar (evento `final`) y, si la
aventura lo declara, el nombre y el rasgo del héroe. Al empezar otra
aventura de la serie, el motor lee el legado y enciende las banderas
que aquella importa — los eventos ya saben leerlas, así que lo que
hiciste antes colorea esta historia sin tocar el balance: ni
inventario, ni niveles, ni monedas.

El archivo es un adorno opcional: si falta o está roto, se juega igual,
solo que sin memoria.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # solo anotaciones
    from .aventura import Aventura
    from .juego import Juego

ARCHIVO_LEGADO = "legado.json"

# El gesto del prólogo cuando el legado trae fama (cada aventura puede
# traer el suyo en `legado.texto_fama`).
FAMA = (
    "Tu fama te precede: hay un cantar nuevo en las posadas, y en él "
    "anda alguien que camina como tú."
)


def leer(ruta: str = ARCHIVO_LEGADO) -> dict | None:
    """El legado escrito, o None si no hay (o está roto): nunca estorba."""
    try:
        with open(ruta, encoding="utf-8") as f:
            datos = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    return datos if isinstance(datos, dict) else None


def escribir(av: "Aventura", juego: "Juego", ruta: str = ARCHIVO_LEGADO) -> dict:
    """Escribe el legado que esta aventura exporta al terminar.

    Cada aventura gestiona solo sus banderas canónicas: las enciende si
    su bandera local lo está y las apaga si no, pero respeta lo que las
    demás escribieron — el mundo recuerda la cadena entera, no la última
    faena. Con `heroe`, viajan también el nombre puesto por el jugador
    y el rasgo del héroe. Devuelve lo escrito.
    """
    legado = dict(leer(ruta) or {})
    legado["aventura"] = av.id
    for canonica, local in av.legado.exporta.items():
        if juego.flags.get(local):
            legado[canonica] = True
        else:
            legado.pop(canonica, None)
    if av.legado.heroe:
        legado["nombre"] = juego.jugador.nombre
        ficha = av.personajes[juego.personaje]
        if ficha.rasgos:
            legado["rasgo"] = ficha.rasgos[0]
        else:
            legado.pop("rasgo", None)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(legado, f, ensure_ascii=False, indent=2)
    return legado


def enciende(flags: dict[str, bool], importa: list[str], legado: dict | None) -> None:
    """Enciende en `flags` las banderas canónicas que el legado traiga.

    Las banderas importadas quedan bajo su nombre canónico: los
    `condicion` de los eventos y los `requiere_flag` de los finales las
    leen igual que las locales.
    """
    if not legado:
        return
    for canonica in importa:
        if legado.get(canonica):
            flags[canonica] = True

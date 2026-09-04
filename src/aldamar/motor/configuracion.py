"""Preferencias del jugador: el archivo configuracion.json.

Vive en el directorio donde se corre el juego, como partida.json y
compañía, y nace con valores por defecto la primera vez que se juega
de verdad (nunca en tests ni tuberías). La precedencia de toda
preferencia es siempre la misma: flag de CLI > variable de entorno >
este archivo > valores por defecto.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, fields

ARCHIVO_CONFIGURACION = "configuracion.json"


@dataclass
class Configuracion:
    """Lo que el jugador puede prender y apagar sin tocar el comando."""

    audio: bool = True  # el jingle de la presentación y del cierre
    debug: bool = False  # conservar lo que el lanzador escribió (como --debug)
    color: bool = True  # códigos ANSI (como --sin-color, al revés)
    flechas: bool = True  # menús navegables con ↑/↓ (como --sin-flechas, al revés)
    splash: bool = True  # pantalla de presentación con el sello y su jingle
    semilla: int | None = None  # semilla de cada partida, si se quiere repetible
    modelo_viva: str | None = None  # modelo del modo «Aventura Viva» (issue 22);
    # si falta, manda ALDAMAR_MODELO y, sin ella, el primero instalado
    contexto_viva: int | None = None  # num_ctx del modelo vivo (16384 por
    # defecto); bajarlo (p. ej. 8192) alivia máquinas sin GPU


def defecto() -> Configuracion:
    return Configuracion()


def cargar(ruta: str = ARCHIVO_CONFIGURACION) -> Configuracion:
    """Lee el archivo; si falta, está roto o trae basura, valores por defecto.

    Las claves desconocidas se ignoran (que no paren la partida) y los
    valores con tipo equivocado vuelven a su default, campo por campo.
    """
    try:
        with open(ruta, encoding="utf-8") as f:
            datos = json.load(f)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return defecto()
    if not isinstance(datos, dict):
        return defecto()
    config = defecto()
    for campo in fields(Configuracion):
        if campo.name not in datos:
            continue
        valor = datos[campo.name]
        if campo.name == "semilla":
            if valor is None or (isinstance(valor, int) and not isinstance(valor, bool)):
                config.semilla = valor
        elif campo.name == "modelo_viva":
            if valor is None or isinstance(valor, str):
                config.modelo_viva = valor
        elif campo.name == "contexto_viva":
            if valor is None or (isinstance(valor, int) and not isinstance(valor, bool)):
                config.contexto_viva = valor
        elif isinstance(valor, bool):
            setattr(config, campo.name, valor)
    return config


def guardar(config: Configuracion, ruta: str = ARCHIVO_CONFIGURACION) -> None:
    """Escribe el archivo completo, listo para editar a mano."""
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(asdict(config), f, indent=2, ensure_ascii=False)
        f.write("\n")


def asegurar(ruta: str = ARCHIVO_CONFIGURACION) -> bool:
    """Crea el archivo con valores por defecto si todavía no existe.

    Devuelve si lo creó. Quien llama decide cuándo toca escribir: solo
    en sesiones de verdad (ver main en juego.py), nunca en tests.
    """
    if os.path.exists(ruta):
        return False
    guardar(defecto(), ruta)
    return True

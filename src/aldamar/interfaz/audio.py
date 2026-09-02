"""El jingle de Aldamar: dos segundos de chiptune, todos estándar.

La melodía se genera al vuelo con el módulo `wave` (ondas cuadradas,
como las del 8-bit de toda la vida) y suena con el reproductor que
cada sistema traiga: afplay en macOS, paplay/aplay/ffplay en Linux y
winsound en Windows. Es la misma pieza en la presentación y en la
pantalla de cierre. Sin reproductor o sin terminal de verdad, silencio:
el juego sigue igual, sin quejarse nunca.

La nota de derechos manda también aquí: la pieza es original y nace de
este archivo, no de ninguna melodía ajena.
"""

from __future__ import annotations

import io
import math
import os
import subprocess
import sys
import tempfile
import threading
import wave
from functools import lru_cache

from .opciones import _es_interactivo

FRECUENCIA_MUESTREO = 22050  # suficiente para un jingle, archivo chico
VOLUMEN = 96  # pico de la onda (sobre 127): presente, sin saturar
ARTICULACION = 0.92  # cada nota suelta un hueco al final: sonido chiptune

# (frecuencia en Hz, duración en segundos); 0 es un respiro. La fanfarria
# sube do-mi-sol-do, respira, y remata con una escala que se apoya en el
# do final: dos segundos justos.
_MELODIA = [
    (523.25, 0.15),  # do
    (659.25, 0.15),  # mi
    (783.99, 0.15),  # sol
    (1046.50, 0.20),  # do alto
    (0.0, 0.05),
    (783.99, 0.15),  # sol
    (880.00, 0.15),  # la
    (987.77, 0.15),  # si
    (1046.50, 0.85),  # do final, con caída larga
]


def _muestras() -> bytes:
    """La melodía como PCM de 8 bits sin signo, mono."""
    muestras = bytearray()
    for frecuencia, duracion in _MELODIA:
        total = max(1, int(FRECUENCIA_MUESTREO * duracion))
        sonante = int(total * ARTICULACION) if frecuencia else 0
        for i in range(total):
            if i >= sonante:
                muestras.append(128)  # el hueco entre notas
                continue
            t = i / FRECUENCIA_MUESTREO
            onda = 1.0 if math.sin(2 * math.pi * frecuencia * t) >= 0 else -1.0
            caida = math.exp(-3.0 * i / total)  # la nota se apaga sola
            muestras.append(128 + int(onda * caida * VOLUMEN))
    return bytes(muestras)


@lru_cache(maxsize=1)
def bytes_jingle() -> bytes:
    """El jingle completo como archivo WAV en memoria (siempre igual)."""
    archivo = io.BytesIO()
    with wave.open(archivo, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(1)  # 8 bits, el sonido de la época
        w.setframerate(FRECUENCIA_MUESTREO)
        w.writeframes(_muestras())
    return archivo.getvalue()


def duracion() -> float:
    """Cuánto dura el jingle, en segundos (según sus propias muestras)."""
    return len(_muestras()) / FRECUENCIA_MUESTREO


def _reproductores_posix() -> list[list[str]]:
    if sys.platform == "darwin":
        return [["afplay"]]
    return [
        ["paplay"],
        ["aplay", "-q"],
        ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"],
    ]


def _sonar() -> None:
    if os.name == "nt":
        import winsound

        winsound.PlaySound(
            bytes_jingle(), winsound.SND_MEMORY | winsound.SND_ASYNC
        )
        return
    descriptor, ruta = tempfile.mkstemp(suffix=".wav", prefix="aldamar-")
    with os.fdopen(descriptor, "wb") as f:
        f.write(bytes_jingle())
    for comando in _reproductores_posix():
        try:
            subprocess.Popen(
                [*comando, ruta],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError:
            continue  # este sistema no trae ese reproductor: el siguiente
        # el archivo se borra cuando el reproductor ya lo abrió
        threading.Timer(15, lambda: os.unlink(ruta) if os.path.exists(ruta) else None).start()
        return
    os.unlink(ruta)  # no había reproductor alguno: silencio


def reproducir(*, entrada=input, salida=print) -> None:
    """Hace sonar el jingle una vez, sin esperar y sin quejarse jamás.

    Solo en sesiones de verdad: en tests y tuberías esta función es un
    bloque sin efecto, como los menús con flechas.
    """
    if not _es_interactivo(entrada, salida):
        return
    try:
        _sonar()
    except Exception:  # noqa: BLE001  (el audio jamás corta una partida)
        pass

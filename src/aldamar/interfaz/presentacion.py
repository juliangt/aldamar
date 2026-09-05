"""La presentación: el sello de Aldamar, su jingle y una tecla.

Como el resto de la interfaz, solo existe con teclado y pantalla
reales: en tests y tuberías la presentación no pinta nada y no espera
nada, y el arranque sigue como siempre.
"""

from __future__ import annotations

from .. import __version__
from . import audio as modulo_audio
from .opciones import DIM, LIMPIAR, TITULO, _c, _es_interactivo, _leer_tecla

# El héroe de la historia: el guerrero que despierta al amuleto, con el
# Corazón de Ceniza al pecho y la espada clavada a su costado, esperando
# a quien tome su lugar.
_SELO = r"""
         .-'''''-.
        /  _   _  \
       |  (o) (o)  |
       |     __    |
        \ '~~~~~~' /
         '-.____.-'
       ___|      |___
      /   |  (✦)  |   \
     |    |       |    \
     |    |       |     \
      \   |      |       o
       \  |      |      /=\
        \ |      |       |
         \|      |       |
          |      |       |
          |      |     ✦ |
         _|      |_       |
        (_|      |_)______|
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  ###  #     ####   ###  #   #  ###  ####
 #   # #     #   # #   # ## ## #   # #   #
 ##### #     #   # ##### # # # ##### ####
 #   # #     #   # #   # #   # #   # #  #
 #   # #####  ####  #   # #   # #   # #   #
"""

# El lema, en partes, al costado del casco: el dibujo deja libre la
# pantalla a su derecha, y así ningún renglón propio se lleva puesto
# la cabeza del guerrero en terminales chicas.
_LEMA = ("el amuleto que durmió", "veinte generaciones", "acaba de despertar")

_COSTADO = 33  # columna donde arrancan el lema y la versión


def _cartel(color: bool) -> str:
    """El sello completo: arte con el lema al costado y la versión en el suelo."""
    lineas = _SELO.strip("\n").splitlines()
    for i, parte in enumerate(_LEMA):
        lineas[i] = _c(lineas[i].ljust(_COSTADO), color, TITULO) + _c(parte, color, DIM)
    version = _c(f"  · v{__version__}", color, DIM)
    lineas[18] = _c(lineas[18], color, TITULO) + version  # el suelo de tildes
    return "\x1b[H" + "\n".join(lineas)


def presentar(*, entrada, salida, color: bool = False, sonar: bool = True) -> None:
    """Muestra el sello, hace sonar el jingle y espera una tecla.

    El jingle suena mientras el sello está en pantalla; cualquier tecla
    lo corta o lo deja terminar, y la pantalla queda limpia para el menú.
    """
    if not _es_interactivo(entrada, salida):
        return
    salida(LIMPIAR)
    salida(_cartel(color))
    if sonar:
        modulo_audio.reproducir(entrada=entrada, salida=salida)
    salida("\n" + _c("  Presiona cualquier tecla para comenzar…", color, DIM))
    _leer_tecla()
    salida(LIMPIAR)  # al continuar, lo que sigue se ve solo

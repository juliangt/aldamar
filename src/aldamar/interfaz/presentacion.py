"""La presentación: el sello de Aldamar, su jingle y una tecla.

Como el resto de la interfaz, solo existe con teclado y pantalla
reales: en tests y tuberías la presentación no pinta nada y no espera
nada, y el arranque sigue como siempre.
"""

from __future__ import annotations

from .. import __version__
from . import audio as modulo_audio
from .opciones import DIM, LIMPIAR, TITULO, _c, _es_interactivo, _leer_tecla

# El Corazón de Ceniza colgado de su cordón: la gema tallada, el brillo
# y el resplandor del amuleto que durmió veinte generaciones.
_SELO = """
      ✦          ·
            ╲ ╱
             ◇
            ╱╲
           ╱  ╲
          ╱    ╲
         ═══✦═══
          ╲    ╱
           ╲  ╱
            ╲╱

  ###  #     ####   ###  #   #  ###  ####
 #   # #     #   # #   # ## ## #   # #   #
 ##### #     #   # ##### # # # ##### ####
 #   # #     #   # #   # #   # #   # #  #
 #   # #####  ####  #   # #   # #   # #   #
"""

_LEMA = "el amuleto que durmió veinte generaciones acaba de despertar"


def _cartel(color: bool) -> str:
    """El sello completo: arte, título, lema y versión."""
    lema = _c(f"\n  {_LEMA}", color, DIM)
    version = _c(f" · v{__version__}\n", color, DIM)
    return "\x1b[H" + _c(_SELO, color, TITULO) + lema + version


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

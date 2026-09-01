"""Paquete de aventuras conocidas.

Importar un módulo de aquí lo autorregistra en
`aldamar.aventura.AVENTURAS`. Sumar una aventura al juego = crear su
módulo e importarlo en esta lista.
"""

from ..aventura import AVENTURAS

from . import corazon_ceniza  # noqa: F401  (se registra al importarse)

__all__ = ["corazon_ceniza", "AVENTURAS"]

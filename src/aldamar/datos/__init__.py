"""Los datos del juego, fuera del código: rasgos y aventuras en JSON.

Al importar el paquete, `cargar_todas` (en `aldamar.contenido.cargador`)
descubre los `*.json` de `datos/aventuras/`, los valida y los registra
solos. Sumar una aventura al juego = soltar su JSON ahí; aparece en el
menú sin tocar nada más.
"""

from ..contenido.aventura import AVENTURAS
from ..contenido.cargador import cargar_todas

cargar_todas()

__all__ = ["AVENTURAS"]

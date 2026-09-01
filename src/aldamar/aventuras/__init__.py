"""Paquete de aventuras: cada `*.json` de este directorio es una aventura.

Al importar el paquete, `cargar_todas` (en `aldamar.cargador`) descubre
los archivos, los valida y los registra solos. Sumar una aventura al
juego = soltar su JSON aquí; aparece en el menú sin tocar nada más.
"""

from ..aventura import AVENTURAS
from ..cargador import cargar_todas

cargar_todas()

__all__ = ["AVENTURAS"]

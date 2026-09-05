"""Carga y validación de aventuras definidas en archivos JSON.

Cada aventura de Aldamar es un `*.json` dentro de `aldamar.datos.aventuras`:
este paquete lo lee, valida el contrato —campos obligatorios, tipos y
referencias entre secciones, además del vocabulario de eventos de
`eventos.py`— y arma el objeto `Aventura` que el motor consume. El
trabajo vive repartido en tres módulos:

- `campos`: las primitivas de validación (textos, enteros, booleanos…)
- `secciones`: la validación y el armado de cada sección del JSON
- `carga`: la aventura completa, los fragmentos sueltos y el descubrimiento

Sumar una aventura al juego = soltar su JSON en `datos/aventuras/`: el
descubrimiento (`cargar_todas`) es automático y el orden de registro —
el del menú— lo fija el campo opcional `orden` (a igualdad o ausencia,
alfabético por nombre de archivo). Ante un archivo roto, el error
`AventuraInvalida` nombra el archivo y el campo de la culpa.

La superficie pública no cambia: `from aldamar.contenido.cargador
import cargar_aventura_dict` sigue siendo el camino (motor vivo y
tests dependen de él).
"""

from .campos import AventuraInvalida
from .carga import cargar_aventura, cargar_aventura_dict, cargar_todas, valida_fragmento

__all__ = [
    "AventuraInvalida",
    "cargar_aventura",
    "cargar_aventura_dict",
    "cargar_todas",
    "valida_fragmento",
]

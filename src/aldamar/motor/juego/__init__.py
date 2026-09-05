"""Bucle principal de Aldamar: comandos, combate, guardado y finales.

El juego es una sola clase, `Juego` (`nucleo.py`), cuyo estado crea
`__init__` y cuyo comportamiento vive repartido en módulos por
responsabilidad, ensamblado aquí como métodos:

- `salida`: colores, marcos de terminal, prólogo y pantalla de cierre
- `equipo`: lo puesto, sus bonus y los modificadores de rasgos
- `combate`: duelos por turnos, habilidades enemigas y experiencia
- `acciones`: los verbos del mundo —mirar, tomar, hablar, viajar…—
- `navegacion`: menús con flechas, submenús y despacho de órdenes
- `persistencia`: guardar y cargar el estado en JSON
- `arranque`: `main`, argparse y el bucle de sesión del ejecutable

El motor es agnóstico de la aventura: todo el contenido llega en el
objeto `Aventura` y el balance en la `Dificultad` elegida. Los eventos
narrativos de cada lugar y el golpe especial de combate son efectos del
vocabulario declarativo (`eventos.py`) que cada aventura declara en su
JSON (que `cargador.py` valida y convierte en funciones).

Este paquete reexporta la superficie pública: `from aldamar.motor.juego
import Juego, main` sigue siendo el camino (tests, modo vivo y el entry
point de consola dependen de él).
"""

from ...interfaz import audio as modulo_audio  # noqa: F401  (parche del jingle en tests)
from .arranque import _escribir_legado, main
from .combate import ayuda_combate
from .constantes import COMPRAR, ESCRIBIR, HABLAR, IR, OTRAS, RECLUTAR, TOMAR, USAR
from .nucleo import Juego
from .persistencia import _aventura_del_guardado

__all__ = [
    "COMPRAR",
    "ESCRIBIR",
    "HABLAR",
    "IR",
    "OTRAS",
    "RECLUTAR",
    "TOMAR",
    "USAR",
    "Juego",
    "_aventura_del_guardado",
    "_escribir_legado",
    "ayuda_combate",
    "main",
]

"""El modo «Aventura Viva»: una historia generada al vuelo (issue 22).

Import perezoso garantizado: este paquete solo se carga cuando el
jugador entra al modo (menú principal → «Aventura Viva…»); sin él, el
juego arranca exactamente igual que siempre. Dentro:

- `cronista`: el cliente del modelo local (Ollama, stdlib).
- `prompts` (+ `canon.md`): lo que se le pide, y cómo.
- `director`: tablas + RNG que deciden toda la mecánica.
- `memoria`: hilo rodante y hechos atómicos de la sesión.
- `sesion`: el orquestador (única puerta del contenido generado).
- `interfaz`: las pantallas del modo.
"""

from .sesion import SesionViva

__all__ = ["SesionViva"]

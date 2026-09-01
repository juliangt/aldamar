"""Dificultades: perfiles de balance que se aplican sin tocar el motor.

Una Dificultad es solo un juego de multiplicadores sobre el balance con
el que se escribió el contenido de cada aventura (1.0 = tal cual). Sumar
una dificultad nueva = agregar una entrada a DIFICULTADES.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Dificultad:
    clave: str
    nombre: str
    descripcion: str
    vida_jugador: float = 1.0
    ataque_jugador: float = 1.0
    monedas: float = 1.0
    vida_enemigos: float = 1.0
    ataque_enemigos: float = 1.0
    corrupcion: float = 1.0
    curacion: float = 1.0


DIFICULTADES: dict[str, Dificultad] = {
    "paseo": Dificultad(
        clave="paseo",
        nombre="Paseo por el huerto",
        descripcion="Para disfrutar la historia: más vida y monedas, enemigos flojos, corrupción lenta.",
        vida_jugador=1.3,
        ataque_jugador=1.15,
        monedas=1.4,
        vida_enemigos=0.75,
        ataque_enemigos=0.7,
        corrupcion=0.6,
        curacion=1.25,
    ),
    "camino": Dificultad(
        clave="camino",
        nombre="El camino",
        descripcion="El balance con el que se escribió la aventura. Ni más ni menos.",
    ),
    "ceniza": Dificultad(
        clave="ceniza",
        nombre="Yermos de Ceniza",
        descripcion="Para quien ya conoce el camino: menos vida, enemigos duros y corrupción ávida.",
        vida_jugador=0.8,
        monedas=0.8,
        vida_enemigos=1.35,
        ataque_enemigos=1.25,
        corrupcion=1.25,
        curacion=0.85,
    ),
}

DIFICULTAD_POR_DEFECTO = "camino"


def ajusta(valor: int, multiplicador: float) -> int:
    """Escala un valor de balance y lo devuelve como entero razonable."""
    return max(1, round(valor * multiplicador))


def obtener_dificultad(clave: str | None = None) -> Dificultad:
    """Resuelve una dificultad por clave; None devuelve la por defecto."""
    if clave is None:
        clave = DIFICULTAD_POR_DEFECTO
    if clave not in DIFICULTADES:
        raise KeyError(
            f"No existe la dificultad {clave!r}; válidas: {', '.join(DIFICULTADES)}"
        )
    return DIFICULTADES[clave]

"""Helpers compartidos por los tests: un Juego con entrada/salida falsas."""

from __future__ import annotations

import pytest

from aldamar.juego import Juego


class EntradaTipeada:
    """Simula el teclado: entrega líneas y lanza EOFError al agotarse."""

    def __init__(self, lineas: list[str]) -> None:
        self.lineas = list(lineas)
        self.i = 0

    def __call__(self, prompt: str = "") -> str:
        if self.i >= len(self.lineas):
            raise EOFError
        linea = self.lineas[self.i]
        self.i += 1
        return linea


@pytest.fixture
def fabrica():
    """Devuelve una función (lineas, semilla) -> (juego, salida)."""

    def hacer(lineas: list[str], semilla: int = 7) -> tuple[Juego, list[str]]:
        salida: list[str] = []
        juego = Juego(
            semilla=semilla,
            entrada=EntradaTipeada(lineas),
            salida=salida.append,
            color=False,
        )
        return juego, salida

    return hacer

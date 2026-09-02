"""Primitivas de mundo: lugares, conexiones y utilidades de texto.

El mapa concreto de cada aventura vive en su JSON de contenido
(`aventuras/*.json`); aquí solo está la geometría genérica.
"""

from __future__ import annotations

import unicodedata

from dataclasses import dataclass, field


@dataclass
class Lugar:
    id: str
    nombre: str
    descripcion: str
    salidas: dict[str, str] = field(default_factory=dict)  # palabra -> id destino
    objetos: list[str] = field(default_factory=list)  # claves de Aventura.items
    monedas: int = 0
    enemigos: list[str] = field(default_factory=list)  # claves de Aventura.enemigos
    npcs: dict[str, str] = field(default_factory=dict)  # nombre visible -> clave diálogo
    tienda: bool = False
    descanso: bool = False
    eventos: list[str] = field(default_factory=list)  # claves de Aventura.eventos, en orden; el evento "final" se dispara al limpiar el lugar
    requiere: str | None = None  # clave de item necesaria para entrar
    requiere_texto: str = ""


def nuevo_lugar(
    id_: str,
    nombre: str,
    descripcion: str,
    *,
    salidas: dict[str, str] | None = None,
    **kw,
) -> Lugar:
    return Lugar(id=id_, nombre=nombre, descripcion=descripcion, salidas=salidas or {}, **kw)


def normaliza(texto: str) -> str:
    """Minúsculas sin tildes, para comparar lo que escribe el jugador."""
    sin = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in sin if not unicodedata.combining(c)).strip()


def alcanzables(lugares: dict[str, Lugar], desde: str) -> set[str]:
    """Conjunto de lugares alcanzables desde `desde` (sin mirar requisitos)."""
    vistos = {desde}
    pila = [desde]
    while pila:
        actual = pila.pop()
        for destino in lugares[actual].salidas.values():
            if destino not in vistos:
                vistos.add(destino)
                pila.append(destino)
    return vistos

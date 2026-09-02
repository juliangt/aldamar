"""Estadísticas de partida para el playtesting (issue 21).

La partida ya lo sabe todo: aquí solo se apunta. Mientras se juega, el
motor deja en `Estadisticas` lo que no se puede derivar del estado final
— los combates uno a uno con sus turnos y su daño, el gasto, las
compras — y al terminar `--stats` escribe el informe completo en JSON:
lugares visitados, tiendas cruzadas, corrupción final, decisiones.

Todo local, todo opcional, todo en modo explícito: sin la bandera no se
escribe nada y el recolector cuesta unas listas. El informe cubre desde
que empieza (o se carga) la partida hasta su final: es la sesión, no la
historia entera.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # solo anotaciones
    from .juego import Juego

ARCHIVO_ESTADISTICAS = "estadisticas.json"


class Estadisticas:
    """Lo que la partida va sabiendo de sí misma, para el balance."""

    def __init__(self) -> None:
        self.combates: list[dict] = []  # un dict por duelo, en orden
        self.dano_infligido = 0
        self.dano_recibido = 0
        self.monedas_gastadas = 0
        self.monedas_recogidas = 0
        self.compras: list[str] = []  # claves de item comprado, con repeticiones
        self._en_curso: dict | None = None

    # ── combate ──────────────────────────────────────────────────────
    def empieza_combate(self, lugar: str, enemigo_clave: str, nombre: str) -> None:
        self._en_curso = {
            "lugar": lugar,
            "enemigo": enemigo_clave,
            "nombre": nombre,
            "turnos": 0,
            "dano_infligido": 0,
            "dano_recibido": 0,
            "resultado": "",
        }

    def cuenta_turno(self) -> None:
        """Una pasada del duelo: acción del jugador y respuesta."""
        if self._en_curso is not None:
            self._en_curso["turnos"] += 1

    def golpe_infligido(self, dano: int) -> None:
        if dano <= 0:
            return
        self.dano_infligido += dano
        if self._en_curso is not None:
            self._en_curso["dano_infligido"] += dano

    def golpe_recibido(self, dano: int) -> None:
        if dano <= 0:
            return
        self.dano_recibido += dano
        if self._en_curso is not None:
            self._en_curso["dano_recibido"] += dano

    def cierra_combate(self, resultado: str) -> None:
        if self._en_curso is None:
            return
        self._en_curso["resultado"] = resultado
        self.combates.append(self._en_curso)
        self._en_curso = None

    # ── economía ─────────────────────────────────────────────────────
    def gasta(self, precio: int, item: str) -> None:
        self.monedas_gastadas += precio
        self.compras.append(item)

    def recoge(self, monedas: int) -> None:
        self.monedas_recogidas += monedas

    # ── el informe ───────────────────────────────────────────────────
    def resumen(self, juego: "Juego") -> dict:
        """El informe completo de la sesión: lo contado aquí más lo que
        el estado final de la partida ya sabía por sí solo."""
        j = juego.jugador
        av = juego.av
        tiendas = [lid for lid in juego.visitados if av.lugares[lid].tienda]
        return {
            "aventura": av.id,
            "dificultad": juego.dificultad.clave,
            "personaje": juego.personaje,
            "heroe": {
                "nombre": j.nombre,
                "nivel": j.nivel,
                "experiencia": j.experiencia,
                "vida": j.vida,
                "vida_max": j.vida_max,
                "corrupcion": j.corrupcion,
                "monedas": j.monedas,
            },
            "final": juego.final,
            "lugares_visitados": list(juego.visitados),
            "tiendas_visitadas": tiendas,
            "decisiones": sorted(juego.flags),
            "companeros_caidos": [c.nombre for c in j.companeros if not c.viva],
            "combates": list(self.combates),
            "totales": {
                "combates": len(self.combates),
                "turnos_de_combate": sum(c["turnos"] for c in self.combates),
                "dano_infligido": self.dano_infligido,
                "dano_recibido": self.dano_recibido,
                "monedas_recogidas": self.monedas_recogidas,
                "monedas_gastadas": self.monedas_gastadas,
                "compras": list(self.compras),
            },
        }

    def escribir(self, juego: "Juego", ruta: str = ARCHIVO_ESTADISTICAS) -> dict:
        """Escribe el informe en JSON y devuelve lo escrito."""
        informe = self.resumen(juego)
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(informe, f, ensure_ascii=False, indent=2)
        return informe

"""Guardar y cargar partidas: el estado de `Juego` a JSON y de vuelta.

El esquema lo lleva `motor/guardado.py` (versión y migraciones); aquí
solo se arma y se aplica el estado. La aventura viva viaja dentro del
guardado y se reconstruye sin modelo instalado. Ensambla `nucleo.Juego`.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from ...contenido.aventura import Aventura, obtener_aventura
from ...contenido.personajes import Companero
from ...interfaz.menu import ARCHIVO_PARTIDA
from .. import guardado
from ..dificultad import obtener_dificultad
from ..guardado import PartidaInvalida

if TYPE_CHECKING:
    from .nucleo import Juego


def _aventura_del_guardado(estado: dict, ruta: str) -> Aventura:
    """La aventura que trae un guardado: la registrada, o la viva reconstruida.

    Una partida viva lleva su aventura generada dentro del
    propio archivo: `cargar_aventura_dict` sobre lo acumulado basta, sin
    modelo instalado y sin depender del registro de aventuras.
    """
    if estado.get("viva"):
        from ...viva.sesion import SesionViva

        return SesionViva.aventura_de_estado(estado["viva"], ruta)
    return obtener_aventura(estado.get("aventura"))


def _guardar(self: Juego, arg: str = "") -> None:
    ruta = arg.strip() or ARCHIVO_PARTIDA
    # la primera clave es la versión del esquema: guardado.py la lee
    # al cargar y sabe migrar (o rechazar con nombre y apellido)
    estado = {
        "version": guardado.VERSION,
        "aventura": self.av.id,
        "dificultad": self.dificultad.clave,
        "personaje": self.personaje,
        "nombre": self.jugador.nombre,
        "vida": self.jugador.vida,
        "monedas": self.jugador.monedas,
        "corrupcion": self.jugador.corrupcion,
        "experiencia": self.jugador.experiencia,
        "nivel": self.jugador.nivel,
        "inventario": self.jugador.inventario,
        "equipado": dict(self.jugador.equipado),
        "companeros": [
            {"clave": c.clave, "vida": c.vida, "viva": c.viva} for c in self.jugador.companeros
        ],
        "lugar": self.lugar,
        "lugar_previo": self.lugar_previo,
        "flags": self.flags,
        "enemigos": self.enemigos,
        "tomados": sorted("|".join(t) for t in self.tomados),
        "monedas_tomadas": sorted(self.monedas_tomadas),
        "derrotados": self.derrotados,
        "visitados": self.visitados,
        "final": self.final,
        # la sesión viva (dict acumulado, memoria, rellenados) o None
        "viva": self.viva.estado() if self.viva is not None else None,
    }
    try:
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(estado, f, ensure_ascii=False, indent=2)
        self.exito(f"Partida guardada en {ruta}.")
    except OSError as e:
        self.peligro(f"No se pudo guardar: {e}")


def _aplicar_estado(self: Juego, estado: dict, ruta: str) -> None:
    viva_estado = estado.get("viva")
    if viva_estado:
        # la aventura viva viaja dentro del guardado: se reconstruye
        # desde su dict (sin modelo instalado) y la sesión despierta
        from ...viva.sesion import SesionViva

        self.av = _aventura_del_guardado(estado, ruta)
        self.viva = SesionViva.desde_estado(viva_estado)
    else:
        self.av = obtener_aventura(estado.get("aventura"))
        self.viva = None
    self.dificultad = obtener_dificultad(estado.get("dificultad"))
    self.personaje = estado.get("personaje") or self.av.jugador_inicial
    self.jugador = self.av.crear_jugador(self.personaje, self.dificultad)
    j = self.jugador
    j.nombre = estado["nombre"]
    j.vida = estado["vida"]
    j.monedas = estado["monedas"]
    j.corrupcion = estado["corrupcion"]
    # el estado ya pasó por guardado.preparar: viene en el esquema
    # actual (la migración 0→1 deja `equipado` en None)
    j.experiencia = estado["experiencia"]
    j.nivel = estado["nivel"]
    j.inventario = list(estado["inventario"])
    puesto = estado["equipado"]
    j.equipado = {t: k for t, k in (puesto or {}).items() if k in j.inventario}
    if puesto is None:  # «vestía siempre lo mejor del inventario»
        self._autoequipar()
    j.companeros = []
    for c in estado["companeros"]:
        base = self.av.reclutas[c["clave"]]
        j.companeros.append(Companero(**{**base.__dict__, "vida": c["vida"], "viva": c["viva"]}))
    self.lugar = estado["lugar"]
    self.lugar_previo = estado["lugar_previo"]
    self.flags = dict(estado["flags"])
    # un guardado de una edición anterior del juego puede traer menos
    # lugares que la aventura de hoy: los faltantes recuperan sus
    # enemigos originales (esto es evolución del contenido, no del
    # esquema, y por eso no lo lleva la migración)
    guardados = {k: list(v) for k, v in estado["enemigos"].items()}
    self.enemigos = {
        lid: guardados.get(lid, list(lugar.enemigos)) for lid, lugar in self.av.lugares.items()
    }
    self.tomados = {tuple(t.split("|", 1)) for t in estado["tomados"]}
    self.monedas_tomadas = set(estado["monedas_tomadas"])
    self.derrotados = list(estado["derrotados"])
    self.visitados = list(estado["visitados"]) or [self.lugar]
    self.epilogo = None
    self.fin = False
    self.final = estado.get("final")
    self.reanudada = True
    self.exito(f"Partida cargada de {ruta}. De nuevo en {self.aqui().nombre}.")


def _cargar(self: Juego, arg: str = "") -> None:
    ruta = arg.strip() or ARCHIVO_PARTIDA
    try:
        estado = guardado.cargar(ruta)
    except PartidaInvalida as e:
        self.peligro(str(e))
        return
    self._aplicar_estado(estado, ruta)

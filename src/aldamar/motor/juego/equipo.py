"""El equipo del héroe: lo puesto, sus bonus y la gestión del inventario.

Las piezas derivadas (bonus de arma y armadura, ataque total) y los
modificadores del vocabulario de rasgos salen de aquí; el resto del
motor los consulta. Ensambla `nucleo.Juego`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...contenido.mundo import normaliza
from ...contenido.personajes import Combatiente
from ...contenido.rasgos import RASGOS

if TYPE_CHECKING:
    from .nucleo import Juego


def _item_equipado(self: Juego, tipo: str) -> dict | None:
    """La pieza puesta en ese sitio (arma/armadura), si la sigues llevando."""
    clave = self.jugador.equipado.get(tipo)
    if clave and clave in self.jugador.inventario:
        return self.av.items[clave]
    self.jugador.equipado.pop(tipo, None)
    return None


def bonus_arma(self: Juego) -> int:
    arma = self._item_equipado("arma")
    return arma["bonus"] if arma else 0


def bonus_armadura(self: Juego) -> int:
    armadura = self._item_equipado("armadura")
    return armadura["bonus"] if armadura else 0


def ataque_total(self: Juego) -> int:
    return self.jugador.ataque + self.bonus_arma()


def _modificador(self: Juego, campo: str, objetivo: Combatiente | None = None) -> int:
    """La suma de un modificador del vocabulario de rasgos sobre los
    dones del héroe: el único camino por el que un don toca la
    mecánica. Cada don aporta el valor que declaró en `rasgos.json`
    mientras cumpla su condición (`cond_vida_enemigo` compara la
    vida del objetivo del golpe con un porcentaje de su vida_max).
    """
    total = 0
    for clave in self.jugador.rasgos:
        rasgo = RASGOS[clave]
        valor = getattr(rasgo, campo)
        if not valor:
            continue
        if rasgo.cond_vida_enemigo is not None and (
            objetivo is None
            or objetivo.vida <= objetivo.vida_max * rasgo.cond_vida_enemigo / 100
        ):
            continue
        total += valor
    return total


def _autoequipar(self: Juego) -> None:
    """Viste lo mejor que haya, sin decisión: al empezar y al cargar
    un guardado viejo —que vestía siempre lo mejor del inventario—.
    A partir de ahí, equiparse es un comando, no un efecto automático."""
    for tipo in ("arma", "armadura"):
        if self.jugador.equipado.get(tipo):
            continue
        candidatos = [k for k in self.jugador.inventario if self.av.items[k]["tipo"] == tipo]
        mejor = max(candidatos, key=lambda k: self.av.items[k]["bonus"], default=None)
        if mejor is not None:
            self.jugador.equipado[tipo] = mejor


def adquirir(self: Juego, clave: str) -> None:
    """Suma un objeto al inventario. Si es equipo y su sitio está
    vacío, se pone solo (con aviso): la primera pieza sirve como
    siempre; decidir entre dos ya es asunto del jugador."""
    self.jugador.inventario.append(clave)
    item = self.av.items[clave]
    tipo = item["tipo"]
    if tipo in ("arma", "armadura") and not self.jugador.equipado.get(tipo):
        self.jugador.equipado[tipo] = clave
        if tipo == "arma":
            self.aviso(f"Empuñas: {item['nombre']} (+{item['bonus']} de ataque).")
        else:
            self.aviso(f"Te ciñes: {item['nombre']} (+{item['bonus']} de defensa).")


def _equipar(self: Juego, arg: str) -> None:
    if not arg:
        self.tenue("¿Equipar qué? Prueba  equipar <cosa>  o el submenú de gestiones.")
        return
    clave = self._buscar_item(arg, self.jugador.inventario)
    if not clave:
        self.tenue("No llevas eso.")
        return
    item = self.av.items[clave]
    tipo = item["tipo"]
    if tipo not in ("arma", "armadura"):
        self.tenue("Eso no se equipa: se usa, se bebe o se lleva por lo que es.")
        return
    if self.jugador.equipado.get(tipo) == clave:
        self.tenue(f"Ya llevas {item['nombre']} puesto.")
        return
    self.jugador.equipado[tipo] = clave
    if tipo == "arma":
        self.exito(f"Empuñas: {item['nombre']} (+{item['bonus']} de ataque).")
        self.tenue(f"Tu ataque total ahora es {self.ataque_total()}.")
    else:
        self.exito(f"Te ajustas: {item['nombre']} (+{item['bonus']} de defensa).")


def _desequipar(self: Juego, arg: str) -> None:
    puestas = self.jugador.equipado
    if not puestas:
        self.tenue("No llevas nada equipado.")
        return
    t = normaliza(arg)
    tipo: str | None = None
    if t in puestas:
        tipo = t
    else:
        clave = self._buscar_item(arg, list(puestas.values()))
        tipo = next((s for s, k in puestas.items() if k == clave), None)
    if tipo is None:
        self.tenue("Eso no está equipado.")
        return
    clave = puestas.pop(tipo)
    self.escribir(f"Guardas: {self.av.items[clave]['nombre']}.")


def _opciones_equipo(self: Juego) -> list[tuple[str, str, str]]:
    """Equipar lo que no está puesto y desequipar lo que sí."""
    ops: list[tuple[str, str, str]] = []
    for tipo in ("arma", "armadura"):
        puesta = self.jugador.equipado.get(tipo)
        unidad = "ataque" if tipo == "arma" else "defensa"
        ops += [
            (
                f"equipar {k}",
                f"Equipar: {self.av.items[k]['nombre']}",
                f"+{self.av.items[k]['bonus']} {unidad}",
            )
            for k in self.jugador.inventario
            if self.av.items[k]["tipo"] == tipo and k != puesta
        ]
        if puesta:
            ops.append((
                f"desequipar {tipo}",
                f"Desequipar: {self.av.items[puesta]['nombre']}",
                "",
            ))
    return ops

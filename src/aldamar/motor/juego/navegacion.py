"""La orden del jugador: menús navegables, submenús por verbo y despacho.

Con teclado real, el menú raíz apila un submenú por verbo (issue 26) y
Esc sube; sin teclado, se lee una línea tipeada. `_ejecutar` despacha
la orden a las acciones de `acciones.py`. Ensambla `nucleo.Juego`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...contenido.mundo import Lugar, normaliza
from ...interfaz.menu import ARCHIVO_PARTIDA, ayuda
from ...interfaz.opciones import elegir_opcion, pantalla_completa
from .constantes import COMPRAR, ESCRIBIR, HABLAR, IR, OTRAS, RECLUTAR, TOMAR, USAR

if TYPE_CHECKING:
    from ...contenido.personajes import Enemigo
    from .nucleo import Juego


def _pista(self: Juego) -> str:
    if self._usa_flechas():
        return "(Elige con ↑/↓ y Enter: cada verbo abre su listado, y Esc vuelve; las gestiones están en «Otras acciones…».)"
    return "(Escribe  ayuda  para ver los comandos.)"


def _leer_orden(
    self: Juego,
    titulo: str,
    prompt: str,
    opciones: list[tuple[str, str, str]],
    aviso_esc: str | None = "No hay vuelta atrás: elige una acción de la lista.",
) -> str:
    """La próxima orden del jugador.

    Con teclado real se elige en menús navegables anidados: la raíz
    es el menú del juego (o de combate), y cada verbo —«Tomar…»,
    «Comprar…», «Otras acciones…»— apila su listado; Esc sube un
    nivel y en la raíz no lleva a ningún sitio: queda un aviso y se
    sigue eligiendo. Los menús viven dentro del relato (issue 36):
    se dibujan debajo de lo leído, navegar entre ellos no suma ni
    una línea (el submenú reemplaza al menú en el mismo sitio) y al
    elegir se borran solos, sin llevarse por delante lo de antes ni
    dejar rastro: el resultado narra la decisión. Encima va una
    línea de estado, y solo cuando algo cambió (vida, monedas o
    lugar): lo repetido no se vuelve a escribir. Sin teclado real,
    se lee una línea, como toda la vida.
    """
    if not self._usa_flechas():
        return self.entrada(prompt).strip()
    estado = self._estado_linea()
    if estado != self._estado_mostrado:  # lo que no cambió, no se reescribe
        self._cabecera()  # el estado vive en la primera fila, nunca en el relato
        self._estado_mostrado = estado
    pila: list[tuple[str, list[tuple[str, str, str]], str | None]] = [
        (titulo, opciones, aviso_esc)
    ]

    def resuelve(clave: str | None) -> tuple[str, list[tuple[str, str, str]], str | None] | None:
        """El menú al que se pasa: clave = un verbo; None = volver con Esc."""
        if clave is None:
            pila.pop()
            return pila[-1] if pila else None
        sublista = self._submenu(clave)
        if sublista is None:  # una decisión final: termina el menú
            return None
        pila.append((sublista[0], sublista[1], None))
        return pila[-1]

    clave = elegir_opcion(
        titulo,
        opciones,
        entrada=self.entrada,
        salida=self.salida,
        color=self.color,
        flechas=True,
        aviso_esc=aviso_esc,
        relato=True,
        resuelve=resuelve,
        separador=not self.en_combate,  # en duelo, el bloque vuelve a su fila
    )
    if clave is None:  # Esc en la raíz: de vuelta al juego sin orden
        return ""
    if clave == ESCRIBIR:
        return self.entrada(prompt).strip()
    return clave


def _opciones_juego(self: Juego) -> list[tuple[str, str, str]]:
    """El menú de acciones del mundo: una entrada por verbo.

    Cada verbo abre su submenú con el listado (`_submenu`); con una
    sola cosa que hacer, el verbo queda directo («Ir a: El ejido»)
    y sin nada que mostrar, no aparece.
    """
    lugar = self.aqui()
    ops: list[tuple[str, str, str]] = [
        ("mirar", "Mirar alrededor", "El lugar, lo que hay y a dónde ir"),
    ]
    destinos = self.destinos(lugar)
    if len(destinos) == 1:
        ops.append(("ir 1", f"Ir a: {destinos[0][2]}", ""))
    elif destinos:
        ops.append((IR, "Ir a…", f"{len(destinos)} destinos"))
    en_suelo = self.restantes(lugar)
    hay_monedas = bool(lugar.monedas) and lugar.id not in self.monedas_tomadas
    if len(en_suelo) == 1 and not hay_monedas:
        ops.append((f"tomar {en_suelo[0]}", f"Tomar: {self.av.items[en_suelo[0]]['nombre']}", ""))
    elif en_suelo or hay_monedas:
        ops.append((TOMAR, "Tomar…", self._cuenta_tomar(lugar)))
    npcs = list(lugar.npcs)
    if len(npcs) == 1:
        ops.append((f"hablar {npcs[0]}", f"Hablar: {npcs[0]}", ""))
    elif npcs:
        ops.append((HABLAR, "Hablar…", f"{len(npcs)} personas aquí"))
    aliados = [npc for npc, clave in lugar.npcs.items() if clave in self.av.reclutas]
    if len(aliados) == 1:
        ops.append((f"reclutar {aliados[0]}", f"Reclutar: {aliados[0]}", "Se suma a tu grupo"))
    elif aliados:
        ops.append((RECLUTAR, "Reclutar…", f"{len(aliados)} aliados"))
    if lugar.tienda:
        stock = self.av.tiendas[lugar.id]
        if len(stock) == 1 and not self._opciones_equipo():
            item = self.av.items[stock[0]]
            ops.append((f"comprar {stock[0]}", f"Comprar: {item['nombre']}", f"{item['precio']} monedas"))
        else:
            ops.append((COMPRAR, "Comprar…", f"{len(stock)} cosas en venta"))
    tipos_inv = {self.av.items[k].get("tipo") for k in self.jugador.inventario}
    if "consumible" in tipos_inv:
        ops.append(self._entrada_usar())
    if lugar.descanso:
        ops.append(("descansar", "Descansar", "Curarte del todo aquí mismo"))
    ops.append((OTRAS, "Otras acciones…", "Estado, inventario, partida y ayuda"))
    return ops


def _entrada_usar(self: Juego) -> tuple[str, str, str]:
    """La entrada del verbo «usar»: directa si hay un solo consumible."""
    consumibles = [
        k for k in self.jugador.inventario
        if self.av.items[k]["tipo"] == "consumible"
    ]
    if len(consumibles) == 1:
        k = consumibles[0]
        return (f"usar {k}", f"Usar: {self.av.items[k]['nombre']}", f"cura {self.av.items[k]['curacion']}")
    return (USAR, "Usar…", f"{len(consumibles)} provisiones")


def _cuenta_tomar(self: Juego, lugar: Lugar) -> str:
    """Lo que hay por el suelo, para contar junto al verbo."""
    objetos = len(self.restantes(lugar))
    hay_monedas = bool(lugar.monedas) and lugar.id not in self.monedas_tomadas
    cosas = "" if not objetos else ("1 objeto" if objetos == 1 else f"{objetos} objetos")
    if cosas and hay_monedas:
        return f"{cosas} y monedas"
    return cosas or "monedas"


def _submenu(self: Juego, clave: str) -> tuple[str, list[tuple[str, str, str]]] | None:
    """El listado de un verbo: (título, opciones) del submenú a apilar.

    El título dice dónde estás y cuántas cosas hay. Devuelve None si
    la clave no abre submenú: es una orden directa.
    """
    lugar = self.aqui()
    if clave == OTRAS:
        return ("Otras acciones", self._opciones_otras())
    if clave == IR:
        destinos = self.destinos(lugar)
        return (
            f"Ir a — desde {lugar.nombre} ({len(destinos)} destinos)",
            [(f"ir {i}", nombre, "") for i, (_d, _p, nombre) in enumerate(destinos, 1)],
        )
    if clave == TOMAR:
        ops = [("tomar todo", "Tomar todo", "Objetos del suelo y monedas")]
        ops += [(f"tomar {k}", self.av.items[k]["nombre"], "") for k in self.restantes(lugar)]
        return (f"Tomar — en {lugar.nombre} ({self._cuenta_tomar(lugar)})", ops)
    if clave == HABLAR:
        npcs = list(lugar.npcs)
        return (
            f"Hablar — {lugar.nombre} ({len(npcs)} personas aquí)",
            [(f"hablar {npc}", npc, "") for npc in npcs],
        )
    if clave == RECLUTAR:
        aliados = [npc for npc, clave in lugar.npcs.items() if clave in self.av.reclutas]
        return (
            f"Reclutar — {lugar.nombre} ({len(aliados)} aliados)",
            [(f"reclutar {npc}", npc, "Se suma a tu grupo") for npc in aliados],
        )
    if clave == COMPRAR:
        stock = self.av.tiendas[lugar.id]
        ops = [
            (f"comprar {k}", self.av.items[k]["nombre"], f"{self.av.items[k]['precio']} monedas")
            for k in stock
        ]
        ops += self._opciones_equipo()  # en la tienda, probar lo llevado
        return (f"Comprar — {lugar.nombre} ({len(stock)} cosas en venta)", ops)
    if clave == USAR:
        ops = [
            (f"usar {k}", self.av.items[k]["nombre"], f"cura {self.av.items[k]['curacion']}")
            for k in self.jugador.inventario
            if self.av.items[k]["tipo"] == "consumible"
        ]
        return (f"Usar — tu mochila ({len(ops)} provisiones)", ops)
    return None


def _opciones_otras(self: Juego) -> list[tuple[str, str, str]]:
    """Las gestiones que no son del mundo: ficha, equipo, partida y ayuda."""
    ops: list[tuple[str, str, str]] = [
        ("estado", "Estado", "Vida, nivel, corrupción y equipo"),
        ("inventario", "Inventario", "Lo que llevas"),
    ]
    ops += self._opciones_equipo()
    ops += [
        ("guardar", "Guardar partida", f"En {ARCHIVO_PARTIDA}"),
        ("cargar", "Cargar partida", "Volver a un archivo guardado"),
        ("ayuda", "Ayuda", "Los comandos, a pantalla completa"),
        (ESCRIBIR, "Escribir un comando…", "Órdenes a mano, como siempre"),
        ("salir", "Salir del juego", "Dejar de jugar"),
    ]
    return ops


def _opciones_combate(self: Juego, enemigo: Enemigo) -> list[tuple[str, str, str]]:
    ops: list[tuple[str, str, str]] = [("atacar", "Atacar", "Golpe a golpe")]
    if self.av.comando_especial and self.av.ataque_especial:
        ops.append((
            normaliza(self.av.comando_especial),
            self.av.comando_especial,
            "El golpe especial de la aventura",
        ))
    tipos_inv = {self.av.items[k].get("tipo") for k in self.jugador.inventario}
    if "consumible" in tipos_inv:
        ops.append(self._entrada_usar())
    if "cuerno" in tipos_inv:
        ops.append(("cuerno", "Tocar el cuerno", "Pone en fuga a las criaturas menores"))
    ops += [
        ("huir", "Huir", "Retirada al lugar anterior"),
        ("estado", "Estado", ""),
        ("inventario", "Inventario", ""),
        (ESCRIBIR, "Escribir un comando…", ""),
    ]
    return ops


# ── despacho de comandos ─────────────────────────────────────────
def _ejecutar(self: Juego, linea: str) -> None:
    linea = linea.strip()
    if not linea:
        return
    partes = normaliza(linea).split(maxsplit=1)
    cmd, arg = partes[0], (partes[1] if len(partes) > 1 else "")
    acciones: dict[str, object] = {
        "ayuda": self._ayuda,
        "mirar": self._mirar,
        "estado": self._estado,
        "inventario": self._inventario,
        "inv": self._inventario,
        "tomar": self._tomar,
        "comprar": self._comprar,
        "usar": self._usar,
        "equipar": self._equipar,
        "desequipar": self._desequipar,
        "hablar": self._hablar,
        "reclutar": self._reclutar,
        "descansar": self._descansar,
        "ir": self._ir,
        "guardar": self._guardar,
        "cargar": self._cargar,
        "salir": self._salir,
    }
    accion = acciones.get(cmd)
    if accion is not None:
        accion(arg)  # type: ignore[operator]
    elif (secreto := self._buscar_secreto(cmd)) is not None:
        self._ejecutar_secreto(secreto)
    elif self.av.comando_especial and cmd == normaliza(self.av.comando_especial):
        self.aviso(self.av.texto_especial_fuera)
    elif cmd in ("atacar", "huir", "cuerno"):
        self.escribir("No hay combate aquí. Viaja con  ir <destino>.")
    elif self.viva is not None and (comando := self.viva.interpretar(linea)):
        # el intérprete del modo vivo solo puede devolver una orden de
        # esta misma tabla: se re-despacha una vez
        self._ejecutar(comando)
    else:
        self.tenue("No entiendo eso. Escribe  ayuda  para ver los comandos.")


def _salir(self: Juego, _arg: str = "") -> None:
    self.escribir("Guardas las tomillas en el bolsillo y miras atrás una vez. Hasta pronto.")
    self.fin = True


def _ayuda(self: Juego, _arg: str = "") -> None:
    pantalla_completa(ayuda(self.av), entrada=self.entrada, salida=self.salida, color=self.color)

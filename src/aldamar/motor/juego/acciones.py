"""Las acciones del jugador sobre el mundo: mirar, tomar, hablar, viajar.

Cada verbo del juego —y las utilidades de lugar que los alimentan
(`aqui`, `restantes`, `destinos`)— vive aquí, junto a la corrupción y
los secretos escondidos. Ensambla `nucleo.Juego`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...contenido.aventura import Secreto
from ...contenido.mundo import Lugar, normaliza
from ...contenido.personajes import CORRUPCION_MAXIMA, Companero, Enemigo
from ...contenido.rasgos import RASGOS

if TYPE_CHECKING:
    from .nucleo import Juego


# ── utilidades de mundo ──────────────────────────────────────────
def aqui(self: Juego) -> Lugar:
    return self.av.lugares[self.lugar]


def crear_enemigo(self: Juego, clave: str) -> Enemigo:
    return self.av.crear_enemigo(clave, self.dificultad)


def restantes(self: Juego, lugar: Lugar) -> list[str]:
    return [k for k in lugar.objetos if (lugar.id, k) not in self.tomados]


def destinos(self: Juego, lugar: Lugar) -> list[tuple[str, str, str]]:
    """Destinos deduplicados: (id, palabra de ejemplo, nombre)."""
    vistos: dict[str, str] = {}
    for palabra, destino in lugar.salidas.items():
        if destino not in vistos:
            vistos[destino] = palabra
    return [(d, p, self.av.lugares[d].nombre) for d, p in vistos.items()]


def corruptear(self: Juego, puntos: int) -> None:
    puntos = round(puntos * self.dificultad.corrupcion)
    antes = self.jugador.corrupcion
    self.jugador.corruptear(puntos)
    delta = self.jugador.corrupcion - antes
    if delta > 0:
        self.aviso(f"El Corazón susurra… la grieta avanza (+{delta} corrupción).")
    elif delta < 0:
        self.exito(f"El agua y la distancia alivian la grieta ({delta} corrupción).")
    if self.jugador.corrupcion >= CORRUPCION_MAXIMA:
        self.aviso("\n" + self._texto_heroe(self.av.epilogo_caida))
        self.fin = True
        self.final = "caida"


# ── mirar / estado / inventario ──────────────────────────────────
def _mirar(self: Juego, _arg: str = "", limpiar: bool = True) -> None:
    if limpiar:
        self._limpiar()  # la vista del lugar se ve sola (issue 36)
    lugar = self.aqui()
    self.epico(f"\n{lugar.nombre.capitalize()}")
    self.escribir(lugar.descripcion)
    restantes = self.restantes(lugar)
    if restantes:
        nombres = ", ".join(self.av.items[k]["nombre"] for k in restantes)
        self.exito(f"En el suelo ves: {nombres}.")
    if lugar.monedas and lugar.id not in self.monedas_tomadas:
        self.exito(f"Brillan {lugar.monedas} monedas de plata olvidadas.")
    for npc, clave in lugar.npcs.items():
        if clave in self.av.dialogos:
            self.aviso(f"Está aquí: {npc}. (hablar {npc})")
    pendientes = self.enemigos[lugar.id]
    if pendientes:
        nombres = ", ".join(self.av.enemigos[k]["nombre"] for k in pendientes)
        self.peligro(f"¡Se avecina: {nombres}!")
    lista = ", ".join(f"{i+1}) {n} ({p})" for i, (_d, p, n) in enumerate(self.destinos(lugar)))
    self.escribir(f"Puedes ir a: {lista}")


def _estado(self: Juego, _arg: str = "") -> None:
    j = self.jugador
    ficha = self.av.personajes[self.personaje]
    self.epico(f"\n— {j.nombre} · {ficha.titulo} —")
    self.escribir(f"Vida: {j.vida}/{j.vida_max}   Corrupción: {j.recepcion()} {j.corrupcion}%")
    self.escribir(f"Nivel: {j.nivel}   Experiencia: {j.progreso_xp()}")
    if j.envenenado:
        self.peligro(f"Envenenado: −{j.veneno_dano} por turno ({j.veneno_turnos} turnos).")
    if j.rasgos:
        self.escribir(
            "Rasgos: "
            + " · ".join(f"{RASGOS[r].nombre} ({RASGOS[r].descripcion})" for r in j.rasgos)
        )
    arma = self._item_equipado("arma")
    armadura = self._item_equipado("armadura")
    texto_arma = f"{arma['nombre']} (+{arma['bonus']})" if arma else "tus propias manos"
    texto_armadura = f"{armadura['nombre']}" if armadura else "túnica de jardinería"
    self.escribir(
        f"Arma: {texto_arma}   Armadura: {texto_armadura} (+{self.bonus_armadura()})"
    )
    self.escribir(f"Monedas: {j.monedas}   Lugar: {self.aqui().nombre}")
    if j.companeros:
        fila = ", ".join(
            f"{c.nombre} ({c.vida}/{c.vida_max})" if c.viva else f"{c.nombre} (cayó)"
            for c in j.companeros
        )
        self.escribir(f"Compañeros: {fila}")


def _inventario(self: Juego, _arg: str = "") -> None:
    j = self.jugador
    self.epico("\nLlevas contigo:")
    if not j.inventario:
        self.tenue("  (nada más que un poco de harina en el bolsillo)")
    for k in j.inventario:
        i = self.av.items[k]
        if i["tipo"] == "reliquia":
            self.aviso(f"  {i['nombre']}  ·  {i.get('desc', '')}")
            continue
        extra = ""
        if i["tipo"] == "arma":
            extra = f" (+{i['bonus']} ataque)"
        elif i["tipo"] == "armadura":
            extra = f" (+{i['bonus']} defensa)"
        elif i["tipo"] == "consumible":
            extra = f" (cura {i['curacion']})"
        puesto = " · puesto" if k in j.equipado.values() else ""
        self.escribir(f"  {i['nombre']}{extra}{puesto}")


# ── objetos ──────────────────────────────────────────────────────
def _tomar(self: Juego, arg: str) -> None:
    lugar = self.aqui()
    restantes = self.restantes(lugar)
    hay_monedas = bool(lugar.monedas) and lugar.id not in self.monedas_tomadas
    if arg in ("todo", "todas", "todo."):
        for k in restantes:
            self.tomados.add((lugar.id, k))
            self.adquirir(k)
            self.exito(f"Tomas: {self.av.items[k]['nombre']}.")
        if hay_monedas:
            self.monedas_tomadas.add(lugar.id)
            ganancia = round(lugar.monedas * self.dificultad.monedas)
            self.jugador.monedas += ganancia
            self.stats.recoge(ganancia)
            self.exito(f"Recoges {ganancia} monedas de plata.")
        if not restantes and not hay_monedas:
            self.tenue("No hay nada que tomar aquí.")
        return
    clave = self._buscar_item(arg, restantes)
    if clave:
        self.tomados.add((lugar.id, clave))
        self.adquirir(clave)
        self.exito(f"Tomas: {self.av.items[clave]['nombre']}.")
    else:
        self.tenue("Eso no está por aquí.")


def _buscar_item(self: Juego, texto: str, opciones: list[str]) -> str | None:
    t = normaliza(texto)
    if not t:
        return None
    for k in opciones:
        if t in normaliza(self.av.items[k]["nombre"]) or t in normaliza(k):
            return k
    return None


def _comprar(self: Juego, arg: str) -> None:
    lugar = self.aqui()
    if not lugar.tienda:
        self.tenue("Aquí no hay tienda.")
        return
    stock = self.av.tiendas[lugar.id]
    if not arg:
        self.escribir(
            "En venta: "
            + ", ".join(
                f"{self.av.items[k]['nombre']} ({self.av.items[k]['precio']} monedas)" for k in stock
            )
        )
        return
    clave = self._buscar_item(arg, stock)
    if not clave:
        self.tenue("No venden eso aquí.")
        return
    precio = self.av.items[clave]["precio"] or 0
    precio = max(1, precio - self._modificador("descuento_compra"))
    if self.jugador.monedas < precio:
        self.aviso(f"Te faltan monedas: cuesta {precio} y llevas {self.jugador.monedas}.")
        return
    self.jugador.monedas -= precio
    self.adquirir(clave)
    self.stats.gasta(precio, clave)
    self.exito(f"Compras {self.av.items[clave]['nombre']} por {precio} monedas.")


def _usar(self: Juego, arg: str) -> None:
    clave = self._buscar_item(arg, self.jugador.inventario)
    if not clave:
        self.tenue("No llevas eso.")
        return
    i = self.av.items[clave]
    if i["tipo"] == "consumible":
        self.jugador.inventario.remove(clave)
        antes = self.jugador.vida
        self.jugador.curar(round(i["curacion"] * self.dificultad.curacion))
        self.exito(f"Te tomas {i['nombre']}: vida {antes} → {self.jugador.vida}.")
    elif i["tipo"] == "cuerno":
        self.tenue("El cuerno solo sirve en combate, cuando el peligro esté delante.")
    elif i.get("texto_uso"):
        self.epico("\n" + self._texto_heroe(i["texto_uso"]))
    else:
        self.tenue("Eso no se usa así: ya te sirve solo por llevarlo.")


# ── gente ────────────────────────────────────────────────────────
def _hablar(self: Juego, arg: str) -> None:
    lugar = self.aqui()
    t = normaliza(arg)
    if t:
        for npc, clave in lugar.npcs.items():
            if t in normaliza(npc) or t in normaliza(clave):
                self._limpiar()  # la conversación se ve sola (issue 36)
                flag_cuenta = f"_charla_{clave}"
                cuenta = self.flags.get(flag_cuenta, 0)
                if not isinstance(cuenta, int):
                    cuenta = 0
                texto = self.av.obtener_dialogo(clave, cuenta)
                if isinstance(self.av.dialogos.get(clave), list):
                    self.flags[flag_cuenta] = cuenta + 1
                if texto:
                    self.epico("\n" + self._texto_heroe(texto))
                return
    self.tenue("Aquí no hay nadie con ese nombre.")


def _reclutar(self: Juego, arg: str) -> None:
    lugar = self.aqui()
    t = normaliza(arg)
    if t:
        for npc, clave in lugar.npcs.items():
            if clave in self.av.reclutas and (t in normaliza(npc) or t in normaliza(clave)):
                comp = self.av.reclutas[clave]
                if any(c.clave == comp.clave for c in self.jugador.companeros):
                    self.escribir(
                        f"{comp.nombre} ya viaja contigo (o ya cayó; en la Torre de Belthar pueden sanarlo)."
                    )
                    return
                self.jugador.companeros.append(Companero(**comp.__dict__))
                self.exito(f"{comp.nombre} se une a tu viaje.")
                return
    self.tenue("Aquí no hay nadie que pueda sumarse.")


def _descansar(self: Juego, _arg: str = "") -> None:
    lugar = self.aqui()
    if not lugar.descanso:
        self.tenue("No hay cama ni fogata aquí. El barro tampoco es acogedor.")
        return
    antes = self.jugador.vida
    self.jugador.curar(self.jugador.vida_max)
    for c in self.jugador.companeras_vivas():
        c.vida = c.vida_max
    caidos = any(not c.viva for c in self.jugador.companeros)
    self.exito(
        f"Duermes como piedra: vida {antes} → {self.jugador.vida}."
        + (" Los caídos no despiertan aquí; busca la Torre de Belthar." if caidos else "")
    )


# ── viaje y eventos ──────────────────────────────────────────────
def _ir(self: Juego, arg: str) -> None:
    lugar = self.aqui()
    destinos = self.destinos(lugar)
    elegido: str | None = None
    t = normaliza(arg)
    if t.isdigit():
        n = int(t)
        if 1 <= n <= len(destinos):
            elegido = destinos[n - 1][0]
    elif t:
        for palabra, destino_id in lugar.salidas.items():
            if t == normaliza(palabra) or t in normaliza(self.av.lugares[destino_id].nombre):
                elegido = destino_id
                break
    if not elegido:
        self.tenue(
            "No puedes ir ahí. Destinos: " + ", ".join(n for _, _, n in destinos)
        )
        return
    destino = self.av.lugares[elegido]
    if destino.requiere and destino.requiere not in self.jugador.inventario:
        self.aviso(destino.requiere_texto)
        return
    self.lugar_previo = self.lugar
    self.lugar = elegido
    self._entrar(destino)


def _entrar(self: Juego, destino: Lugar) -> None:
    if destino.id not in self.visitados:
        self.visitados.append(destino.id)
    if self._usa_flechas():
        self._limpiar()  # la escena nueva se ve sola (issue 36)
    else:
        self.tenue("\n" + "─" * 40)  # en el relato tipeado, la raya marca la escena
    if self.viva is not None:
        # el modo vivo rellena el lugar si aún era un borrador;
        # puede reemplazar `self.av` entera: el lugar se vuelve a pedir
        self.viva.al_entrar(self, destino.id)
        destino = self.aqui()
    self.epico(f"\n{destino.nombre.capitalize()}")
    self.escribir(destino.descripcion)
    eventos = [self.av.eventos[c] for c in destino.eventos if c in self.av.eventos]
    es_final = "final" in destino.eventos
    if eventos and not es_final:
        for evento in eventos:
            evento(self, destino)
            if self.fin:
                return
    pendientes = self.enemigos[destino.id]
    if pendientes:
        self._combate()
        if self.fin or self.lugar != destino.id:
            return
    if es_final and eventos and not pendientes:
        for evento in eventos:
            evento(self, destino)


# ── secretos ─────────────────────────────────────────────────────
def _buscar_secreto(self: Juego, cmd: str) -> Secreto | None:
    cmd_norm = normaliza(cmd)
    for secreto in self.av.secretos.values():
        if cmd_norm == normaliza(secreto.comando) or any(cmd_norm == normaliza(a) for a in secreto.alias):
            return secreto
    return None


def _ejecutar_secreto(self: Juego, secreto: Secreto) -> None:
    cuenta = self.flags.get(f"_secreto_{secreto.comando}", 0)
    if not isinstance(cuenta, int):
        cuenta = 0
    self.flags[f"_secreto_{secreto.comando}"] = cuenta + 1
    texto = secreto.texto_para(cuenta, self.semilla)
    self.epico("\n" + self._texto_heroe(texto))

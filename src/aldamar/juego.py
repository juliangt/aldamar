"""Bucle principal de Aldamar: comandos, combate, guardado y finales."""

from __future__ import annotations

import argparse
import json
import random
import sys

from . import __version__
from .datos import (
    DIALOGOS,
    EPILogo_CAIDA,
    EPILogo_MUERTE,
    EPILogo_PURO,
    EPILogo_RECLAMO,
    EPILogo_TENTADO,
    ITEMS,
    RECLUTAS,
    TEXTO_CONSEJO,
    TEXTO_RITUAL,
    TIENDAS,
    crear_enemigo,
)
from .mundo import LUGARES, LUGAR_INICIAL, Lugar, normaliza
from .personajes import (
    CORRUPCION_MAXIMA,
    CORRUPCION_TENTADO,
    Combatiente,
    Companero,
    Enemigo,
    Jugador,
)

ARCHIVO_PARTIDA = "partida.json"

TITULO, VERDE, ROJO, AMARILLO, DIM = "1;36", "32", "31", "33", "2"

PROLOGO = """══════════════════════════════════════════════════════════════════
    A L D A M A R  ·  El Corazón de Ceniza
    Una aventura de fantasía épica para la terminal
══════════════════════════════════════════════════════════════════

Hace mil lunas, el hechicero Morvath forjó en el corazón ardiente del
Monte Umbak un amuleto al que llamó el Corazón de Ceniza. Con su aliento
oscuro doblegó a los reinos del oeste, y solo la alianza de las razas
libres —humanos, sylvos, goran y falros— logró arrancárselo.

Morvath cayó, pero su obra no supo morir: solo la Forja Eterna que lo
vio nacer puede devolverlo al fuego. Los consejeros de antaño lo
escondieron y juraron olvidar. El olvido cumplió.

Durante veinte generaciones el amuleto durmió en un baúl de jardinería,
en la aldea falra de Vegaverde, herencia de tu tío Oldo Panverde.

Esta noche los cuervos vuelan hacia el este. Belthar el Errante,
último mago del viejo consejo, acaba de tocar tu puerta.
"""

AYUDA = """Comandos:
  mirar              Mirar alrededor (salidas, objetos, gente)
  ir <destino>       Viajar: por número, dirección o nombre (ir 1, ir este)
  estado             Tu vida, corrupción, equipo y compañeros
  inventario         Lo que llevas
  tomar <cosa>       Recoger del suelo (tomar todo)
  comprar <cosa>     En las tiendas
  usar <cosa>        Consumir provisiones o hierbas
  hablar <quién>     Escuchar a quien esté aquí
  reclutar <quién>   Sumar un aliado a tu grupo
  descansar          Curarte del todo donde haya cama
  guardar [archivo]  Guardar partida (partida.json por defecto)
  cargar [archivo]   Cargar partida
  ayuda              Esta ayuda
  salir              Dejar de jugar

En combate:  atacar · usar <cosa> · corazon · cuerno · huir · estado
"""


class Juego:
    def __init__(
        self,
        semilla: int | None = None,
        entrada=input,
        salida=print,
        color: bool | None = None,
    ) -> None:
        self.rng = random.Random(semilla)
        self.entrada = entrada
        self.salida = salida
        if color is None:
            color = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
        self.color = color
        self.jugador = Jugador(nombre="Tilo", inventario=["corazon"])
        self.lugar: str = LUGAR_INICIAL
        self.lugar_previo: str = LUGAR_INICIAL
        self.flags: dict[str, bool] = {}
        self.enemigos: dict[str, list[str]] = {
            lid: list(l.enemigos) for lid, l in LUGARES.items()
        }
        self.tomados: set[tuple[str, str]] = set()
        self.monedas_tomadas: set[str] = set()
        self.fin = False
        self.final: str | None = None
        self.en_combate = False

    # ── salida con color ─────────────────────────────────────────────
    def _c(self, texto: str, *codigos: str) -> str:
        if not self.color or not codigos:
            return texto
        return "\033[" + ";".join(codigos) + "m" + texto + "\033[0m"

    def _escribe(self, texto: str = "", *codigos: str) -> None:
        self.salida(self._c(texto, *codigos))

    # ── equipo derivado ──────────────────────────────────────────────
    def _mejor(self, tipo: str) -> dict | None:
        candidatos = [ITEMS[k] for k in self.jugador.inventario if ITEMS[k]["tipo"] == tipo]
        return max(candidatos, key=lambda i: i["bonus"], default=None)

    def bonus_arma(self) -> int:
        arma = self._mejor("arma")
        return arma["bonus"] if arma else 0

    def bonus_armadura(self) -> int:
        armadura = self._mejor("armadura")
        return armadura["bonus"] if armadura else 0

    def ataque_total(self) -> int:
        return self.jugador.ataque + self.bonus_arma()

    # ── utilidades de mundo ──────────────────────────────────────────
    def aqui(self) -> Lugar:
        return LUGARES[self.lugar]

    def restantes(self, lugar: Lugar) -> list[str]:
        return [k for k in lugar.objetos if (lugar.id, k) not in self.tomados]

    def destinos(self, lugar: Lugar) -> list[tuple[str, str, str]]:
        """Destinos deduplicados: (id, palabra de ejemplo, nombre)."""
        vistos: dict[str, str] = {}
        for palabra, destino in lugar.salidas.items():
            if destino not in vistos:
                vistos[destino] = palabra
        return [(d, p, LUGARES[d].nombre) for d, p in vistos.items()]

    def _corruptear(self, puntos: int) -> None:
        antes = self.jugador.corrupcion
        self.jugador.corruptear(puntos)
        delta = self.jugador.corrupcion - antes
        if delta > 0:
            self._escribe(f"El Corazón susurra… la grieta avanza (+{delta} corrupción).", AMARILLO)
        elif delta < 0:
            self._escribe(f"El agua y la distancia alivian la grieta ({delta} corrupción).", VERDE)
        if self.jugador.corrupcion >= CORRUPCION_MAXIMA:
            self._escribe("\n" + EPILogo_CAIDA, AMARILLO)
            self.fin = True
            self.final = "caida"

    # ── ciclo principal ──────────────────────────────────────────────
    def ciclo(self) -> None:
        self._prologo()
        while not self.fin:
            try:
                linea = self.entrada(self._c("> ", DIM))
            except EOFError:
                linea = "salir"
            self._ejecutar(linea)
        if self.final:
            self._escribe(f"\n— FIN —  (final: {self.final})", TITULO)

    def _prologo(self) -> None:
        self._escribe(PROLOGO, TITULO)
        try:
            nombre = self.entrada("¿Cómo te llamas, heredero de Vegaverde? (Tilo): ").strip()
        except EOFError:
            nombre = ""
        if nombre:
            self.jugador.nombre = nombre
        self._escribe(
            "\nOldo te cuelga el Corazón al cuello con dedos temblorosos y te abraza\n"
            "como se abraza a quien ya está de viaje. Belthar asiente: el este espera."
        )
        self._mirar()
        self._escribe("(Escribe  ayuda  para ver los comandos.)", DIM)

    # ── despacho de comandos ─────────────────────────────────────────
    def _ejecutar(self, linea: str) -> None:
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
            "hablar": self._hablar,
            "reclutar": self._reclutar,
            "descansar": self._descansar,
            "ir": self._ir,
            "guardar": self._guardar,
            "cargar": self._cargar,
            "corazon": self._corazon_fuera,
            "salir": self._salir,
        }
        accion = acciones.get(cmd)
        if accion is not None:
            accion(arg)  # type: ignore[operator]
        elif cmd in ("atacar", "huir", "cuerno"):
            self._escribe("No hay combate aquí. Viaja con  ir <destino>.")
        else:
            self._escribe("No entiendo eso. Escribe  ayuda  para ver los comandos.", DIM)

    def _salir(self, _arg: str = "") -> None:
        self._escribe("Guardas las tomillas en el bolsillo y miras atrás una vez. Hasta pronto.")
        self.fin = True

    def _ayuda(self, _arg: str = "") -> None:
        self._escribe(AYUDA)

    # ── mirar / estado / inventario ──────────────────────────────────
    def _mirar(self, _arg: str = "") -> None:
        l = self.aqui()
        self._escribe(f"\n{l.nombre.capitalize()}", TITULO)
        self._escribe(l.descripcion)
        restantes = self.restantes(l)
        if restantes:
            nombres = ", ".join(ITEMS[k]["nombre"] for k in restantes)
            self._escribe(f"En el suelo ves: {nombres}.", VERDE)
        if l.monedas and l.id not in self.monedas_tomadas:
            self._escribe(f"Brillan {l.monedas} monedas de plata olvidadas.", VERDE)
        for npc, clave in l.npcs.items():
            if clave in DIALOGOS:
                self._escribe(f"Está aquí: {npc}. (hablar {npc})", AMARILLO)
        pendientes = self.enemigos[l.id]
        if pendientes:
            nombres = ", ".join(crear_enemigo(k).nombre for k in pendientes)
            self._escribe(f"¡Se avecina: {nombres}!", ROJO)
        lista = ", ".join(f"{i+1}) {n} ({p})" for i, (_d, p, n) in enumerate(self.destinos(l)))
        self._escribe(f"Puedes ir a: {lista}")

    def _estado(self, _arg: str = "") -> None:
        j = self.jugador
        self._escribe(f"\n— {j.nombre} · falro de Vegaverde —", TITULO)
        self._escribe(f"Vida: {j.vida}/{j.vida_max}   Corrupción: {j.recepcion()} {j.corrupcion}%")
        arma = self._mejor("arma")
        armadura = self._mejor("armadura")
        texto_arma = f"{arma['nombre']} (+{arma['bonus']})" if arma else "tus propias manos"
        texto_armadura = f"{armadura['nombre']}" if armadura else "túnica de jardinería"
        self._escribe(
            f"Arma: {texto_arma}   Armadura: {texto_armadura} (+{self.bonus_armadura()})"
        )
        self._escribe(f"Monedas: {j.monedas}   Lugar: {self.aqui().nombre}")
        if j.companeros:
            fila = ", ".join(
                f"{c.nombre} ({c.vida}/{c.vida_max})" if c.viva else f"{c.nombre} (cayó)"
                for c in j.companeros
            )
            self._escribe(f"Compañeros: {fila}")

    def _inventario(self, _arg: str = "") -> None:
        j = self.jugador
        self._escribe("\nLlevas contigo:", TITULO)
        if not j.inventario:
            self._escribe("  (nada más que un poco de harina en el bolsillo)", DIM)
        for k in j.inventario:
            i = ITEMS[k]
            if i["tipo"] == "reliquia":
                self._escribe("  el Corazón de Ceniza  ·  cuelga de tu cuello, caliente como una brasa", AMARILLO)
                continue
            i = ITEMS[k]
            extra = ""
            if i["tipo"] == "arma":
                extra = f" (+{i['bonus']} ataque)"
            elif i["tipo"] == "armadura":
                extra = f" (+{i['bonus']} defensa)"
            elif i["tipo"] == "consumible":
                extra = f" (cura {i['curacion']})"
            self._escribe(f"  {i['nombre']}{extra}")

    # ── objetos ──────────────────────────────────────────────────────
    def _tomar(self, arg: str) -> None:
        l = self.aqui()
        restantes = self.restantes(l)
        hay_monedas = bool(l.monedas) and l.id not in self.monedas_tomadas
        if arg in ("todo", "todas", "todo."):
            for k in restantes:
                self.tomados.add((l.id, k))
                self.jugador.inventario.append(k)
                self._escribe(f"Tomas: {ITEMS[k]['nombre']}.", VERDE)
            if hay_monedas:
                self.monedas_tomadas.add(l.id)
                self.jugador.monedas += l.monedas
                self._escribe(f"Recoges {l.monedas} monedas de plata.", VERDE)
            if not restantes and not hay_monedas:
                self._escribe("No hay nada que tomar aquí.", DIM)
            return
        clave = self._buscar_item(arg, restantes)
        if clave:
            self.tomados.add((l.id, clave))
            self.jugador.inventario.append(clave)
            self._escribe(f"Tomas: {ITEMS[clave]['nombre']}.", VERDE)
        else:
            self._escribe("Eso no está por aquí.", DIM)

    def _buscar_item(self, texto: str, opciones: list[str]) -> str | None:
        t = normaliza(texto)
        for k in opciones:
            if t and (t in normaliza(ITEMS[k]["nombre"]) or t in normaliza(k)):
                return k
        return None

    def _comprar(self, arg: str) -> None:
        l = self.aqui()
        if not l.tienda:
            self._escribe("Aquí no hay tienda.", DIM)
            return
        stock = TIENDAS[l.id]
        if not arg:
            self._escribe(
                "En venta: "
                + ", ".join(f"{ITEMS[k]['nombre']} ({ITEMS[k]['precio']} monedas)" for k in stock)
            )
            return
        clave = self._buscar_item(arg, stock)
        if not clave:
            self._escribe("No venden eso aquí.", DIM)
            return
        precio = ITEMS[clave]["precio"] or 0
        if self.jugador.monedas < precio:
            self._escribe(f"Te faltan monedas: cuesta {precio} y llevas {self.jugador.monedas}.", AMARILLO)
            return
        self.jugador.monedas -= precio
        self.jugador.inventario.append(clave)
        self._escribe(f"Compras {ITEMS[clave]['nombre']} por {precio} monedas.", VERDE)

    def _usar(self, arg: str) -> None:
        clave = self._buscar_item(arg, self.jugador.inventario)
        if not clave:
            self._escribe("No llevas eso.", DIM)
            return
        i = ITEMS[clave]
        if i["tipo"] == "consumible":
            self.jugador.inventario.remove(clave)
            antes = self.jugador.vida
            self.jugador.curar(i["curacion"])
            self._escribe(f"Te tomas {i['nombre']}: vida {antes} → {self.jugador.vida}.", VERDE)
        elif i["tipo"] == "cuerno":
            self._escribe("El cuerno solo sirve en combate, cuando el peligro esté delante.", DIM)
        else:
            self._escribe("Eso no se usa así: ya te sirve solo por llevarlo.", DIM)

    # ── gente ────────────────────────────────────────────────────────
    def _hablar(self, arg: str) -> None:
        l = self.aqui()
        t = normaliza(arg)
        for npc, clave in l.npcs.items():
            if t and (t in normaliza(npc) or t in normaliza(clave)):
                self._escribe("\n" + DIALOGOS[clave], TITULO)
                return
        self._escribe("Aquí no hay nadie con ese nombre.", DIM)

    def _reclutar(self, arg: str) -> None:
        l = self.aqui()
        t = normaliza(arg)
        for npc, clave in l.npcs.items():
            if clave in RECLUTAS and t and (t in normaliza(npc) or t in normaliza(clave)):
                comp = RECLUTAS[clave]
                if any(c.clave == comp.clave for c in self.jugador.companeros):
                    self._escribe(
                        f"{comp.nombre} ya viaja contigo (o ya cayó; en la Torre de Belthar pueden sanarlo)."
                    )
                    return
                self.jugador.companeros.append(Companero(**comp.__dict__))
                self._escribe(f"{comp.nombre} se une a tu viaje.", VERDE)
                return
        self._escribe("Aquí no hay nadie que pueda sumarse.", DIM)

    def _descansar(self, _arg: str = "") -> None:
        l = self.aqui()
        if not l.descanso:
            self._escribe("No hay cama ni fogata aquí. El barro tampoco es acogedor.", DIM)
            return
        antes = self.jugador.vida
        self.jugador.curar(self.jugador.vida_max)
        for c in self.jugador.companeras_vivas():
            c.vida = c.vida_max
        caidos = any(not c.viva for c in self.jugador.companeros)
        self._escribe(
            f"Duermes como piedra: vida {antes} → {self.jugador.vida}."
            + (" Los caídos no despiertan aquí; busca la Torre de Belthar." if caidos else ""),
            VERDE,
        )

    # ── viaje y eventos ──────────────────────────────────────────────
    def _ir(self, arg: str) -> None:
        l = self.aqui()
        destinos = self.destinos(l)
        elegido: str | None = None
        t = normaliza(arg)
        if t.isdigit():
            n = int(t)
            if 1 <= n <= len(destinos):
                elegido = destinos[n - 1][0]
        else:
            for palabra, destino_id in l.salidas.items():
                if t and (t == normaliza(palabra) or t in normaliza(LUGARES[destino_id].nombre)):
                    elegido = destino_id
                    break
        if not elegido:
            self._escribe(
                "No puedes ir ahí. Destinos: " + ", ".join(n for _, _, n in destinos), DIM
            )
            return
        destino = LUGARES[elegido]
        if destino.requiere and destino.requiere not in self.jugador.inventario:
            self._escribe(destino.requiere_texto, AMARILLO)
            return
        self.lugar_previo = self.lugar
        self.lugar = elegido
        self._entrar(destino)

    def _entrar(self, destino: Lugar) -> None:
        self._escribe(f"\n{destino.nombre.capitalize()}", TITULO)
        self._escribe(destino.descripcion)
        if destino.evento == "corrupcion":
            self._escribe("La niebla te repasa como una mano fría…", AMARILLO)
            self._corruptear(8)
            if self.fin:
                return
        if destino.evento == "consejo" and not self.flags.get("consejo"):
            self.flags["consejo"] = True
            self.jugador.inventario.append("estandarte")
            self._escribe("\n" + TEXTO_CONSEJO, TITULO)
        if destino.evento == "ritual" and not self.flags.get("ritual"):
            self.flags["ritual"] = True
            self.jugador.curar(self.jugador.vida_max)
            for c in self.jugador.companeros:
                c.viva = True
                c.vida = c.vida_max
            self._escribe("\n" + TEXTO_RITUAL, TITULO)
            self._corruptear(-15)
            if self.fin:
                return
        pendientes = self.enemigos[destino.id]
        if pendientes:
            self._combate(list(pendientes))
            if self.fin or self.lugar != destino.id:
                return
        if destino.evento == "final" and destino.id == "umbak" and not self.enemigos["umbak"]:
            self._final()

    # ── combate ──────────────────────────────────────────────────────
    def _objetivo(self) -> Combatiente:
        vivas = self.jugador.companeras_vivas()
        if vivas and self.rng.random() < 0.5:
            return self.rng.choice(vivas)
        return self.jugador

    def _recibe(self, objetivo: Combatiente | Jugador, dano: int) -> int:
        """Aplica daño a un combatiente o al jugador (defensa según armadura)."""
        if isinstance(objetivo, Jugador):
            efectivo = max(1, dano - self.bonus_armadura())
            self.jugador.vida = max(0, self.jugador.vida - efectivo)
            return efectivo
        return objetivo.recibir(dano)

    def _golpea(self, atacante: Combatiente, objetivo: Combatiente, extra: int = 3) -> int:
        dano = self.rng.randint(max(1, atacante.ataque), atacante.ataque + extra)
        return self._recibe(objetivo, dano)

    def _duelo(self, enemigo: Enemigo) -> str:
        """Un enemigo por vez. Devuelve victoria | huida | muerte."""
        self._escribe(f"\n¡{enemigo.nombre} se abalanza!", ROJO)
        while not self.fin:
            accion = self._turno_jugador(enemigo)
            if accion == "huida":
                return "huida"
            if accion == "cuerno":
                self._escribe(f"{enemigo.nombre} huye con los demás. Combate resuelto.", VERDE)
                return "victoria"
            if self.fin:
                return "muerte"
            if not enemigo.vivo:
                self._escribe(f"{enemigo.nombre} cae y se deshace en humo pardo.", VERDE)
                return "victoria"
            objetivo = self._objetivo()
            efectivo = self._golpea(enemigo, objetivo)
            if isinstance(objetivo, Companero):
                self._escribe(
                    f"{enemigo.nombre} golpea a {objetivo.nombre}: −{efectivo} ({objetivo.vida}/{objetivo.vida_max}).",
                    ROJO,
                )
                if not objetivo.vivo:
                    objetivo.viva = False
                    self._escribe(f"{objetivo.nombre} cae…", ROJO)
            else:
                self._escribe(
                    f"{enemigo.nombre} te golpea: −{efectivo} ({self.jugador.vida}/{self.jugador.vida_max}).",
                    ROJO,
                )
                if not self.jugador.vivo:
                    self._escribe("\n" + EPILogo_MUERTE, AMARILLO)
                    self.fin = True
                    self.final = "muerte"
                    return "muerte"
        return "muerte"

    def _turno_jugador(self, enemigo: Enemigo) -> str:
        """Acción del jugador y contraataque de los compañeros.

        Devuelve: "seguir" (turno normal), "huida" o "cuerno" (combate resuelto).
        """
        while True:
            try:
                linea = self.entrada(self._c("combate> ", DIM))
            except EOFError:
                # se acabó la entrada: suspendemos la partida en vez de colgarnos
                self.fin = True
                self.final = self.final or "suspendida"
                return "seguir"
            partes = normaliza(linea).split(maxsplit=1)
            cmd = partes[0] if partes else ""
            arg = partes[1] if len(partes) > 1 else ""

            if cmd == "atacar":
                efectivo = self._golpea(self.jugador, enemigo)
                self._escribe(f"Golpeas a {enemigo.nombre}: −{efectivo} ({enemigo.vida}/{enemigo.vida_max}).")
            elif cmd == "usar":
                clave = self._buscar_item(arg, self.jugador.inventario)
                if clave and ITEMS[clave]["tipo"] == "consumible":
                    self.jugador.inventario.remove(clave)
                    antes = self.jugador.vida
                    self.jugador.curar(ITEMS[clave]["curacion"])
                    self._escribe(f"{ITEMS[clave]['nombre']}: vida {antes} → {self.jugador.vida}.", VERDE)
                else:
                    self._escribe("Eso no se puede usar en combate.", DIM)
                    continue
            elif cmd == "corazon":
                dano = 12 + self.jugador.corrupcion // 3
                efectivo = enemigo.recibir(dano)
                self._escribe(f"El Corazón brilla oscuro y golpea por −{efectivo}…", AMARILLO)
                self._corruptear(15)
                if self.fin:
                    return "seguir"
            elif cmd == "cuerno":
                if "cuerno_valoria" in self.jugador.inventario:
                    if enemigo.sin_huida:
                        self._escribe("El toque resuena… y el guardián ni parpadea.", AMARILLO)
                        continue
                    self.jugador.inventario.remove("cuerno_valoria")
                    self._escribe("El cuerno de Valoria retumba: las criaturas menores huyen despavoridas.", TITULO)
                    self.enemigos[self.lugar].clear()
                    return "cuerno"
                self._escribe("No llevas ningún cuerno.", DIM)
                continue
            elif cmd == "huir":
                if enemigo.sin_huida:
                    self._escribe("No hay a dónde ir: el guardián cierra el paso.", AMARILLO)
                    continue
                if self.rng.random() < 0.55:
                    self._escribe("Retrocedes con el corazón en la garganta…")
                    return "huida"
                self._escribe("El enemigo te corta la retirada.", ROJO)
            elif cmd == "estado":
                self._estado()
                continue
            elif cmd in ("inventario", "inv"):
                self._inventario()
                continue
            else:
                self._escribe("En combate: atacar · usar <cosa> · corazon · cuerno · huir · estado", DIM)
                continue

            # acción válida: los compañeros golpean también
            for c in self.jugador.companeras_vivas():
                dano = self.rng.randint(c.ataque, c.ataque + 2)
                efectivo = enemigo.recibir(dano)
                self._escribe(f"{c.nombre} ataca: −{efectivo} ({enemigo.vida}/{enemigo.vida_max}).")
                if not enemigo.vivo:
                    break
            return "seguir"

    def _combate(self, claves: list[str]) -> None:
        self.en_combate = True
        lugar = self.lugar
        pendientes = self.enemigos[lugar]
        for clave in claves:
            if clave not in pendientes:
                continue
            enemigo = crear_enemigo(clave)
            resultado = self._duelo(enemigo)
            if self.fin:
                self.en_combate = False
                return
            if resultado == "victoria":
                if clave in pendientes:
                    pendientes.remove(clave)
                if not pendientes:
                    self._escribe("El aire vuelve a moverse. El camino queda libre.", VERDE)
            else:  # huida
                self.lugar = self.lugar_previo
                self._escribe(
                    f"Vuelves a {LUGARES[self.lugar].nombre}. Los enemigos siguen ahí, esperando.",
                    AMARILLO,
                )
                self.en_combate = False
                return
        self.en_combate = False

    def _corazon_fuera(self, _arg: str = "") -> None:
        self._escribe("El Corazón susurra, pero aquí no hay nadie a quien golpear.", AMARILLO)

    # ── final ────────────────────────────────────────────────────────
    def _final(self) -> None:
        self._escribe(
            "\nLa Forja Eterna respira frente a ti: una boca de luz lenta y antigua.\n"
            "El Corazón late contra tu pecho como un segundo corazón, y su voz ya\n"
            "no susurra: conversa. Habla de lo fácil que sería que todo el mundo\n"
            "te escuchara, por fin, si tú tuvieras la última palabra."
        )
        while not self.fin:
            try:
                respuesta = self.entrada("\n¿Qué haces? (destruir / reclamar): ")
            except EOFError:
                respuesta = "destruir"
            t = normaliza(respuesta)
            if "destru" in t:
                texto = EPILogo_TENTADO if self.jugador.corrupcion >= CORRUPCION_TENTADO else EPILogo_PURO
                self._escribe("\n" + texto, TITULO)
                vivas = [c.nombre for c in self.jugador.companeras_vivas()]
                if vivas:
                    self._escribe(f"Junto a ti, al alba: {', '.join(vivas)}.")
                self.final = "victoria con cicatriz" if texto is EPILogo_TENTADO else "victoria pura"
                self.fin = True
                return
            if "reclam" in t:
                self._escribe("\n" + EPILogo_RECLAMO, AMARILLO)
                self.final = "la Sombra nueva"
                self.fin = True
                return
            self._escribe("La montaña espera: destruir o reclamar.", DIM)

    # ── guardar / cargar ─────────────────────────────────────────────
    def _guardar(self, arg: str = "") -> None:
        ruta = arg.strip() or ARCHIVO_PARTIDA
        estado = {
            "nombre": self.jugador.nombre,
            "vida": self.jugador.vida,
            "monedas": self.jugador.monedas,
            "corrupcion": self.jugador.corrupcion,
            "inventario": self.jugador.inventario,
            "companeros": [
                {"clave": c.clave, "vida": c.vida, "viva": c.viva} for c in self.jugador.companeros
            ],
            "lugar": self.lugar,
            "lugar_previo": self.lugar_previo,
            "flags": self.flags,
            "enemigos": self.enemigos,
            "tomados": sorted("|".join(t) for t in self.tomados),
            "monedas_tomadas": sorted(self.monedas_tomadas),
            "final": self.final,
        }
        try:
            with open(ruta, "w", encoding="utf-8") as f:
                json.dump(estado, f, ensure_ascii=False, indent=2)
            self._escribe(f"Partida guardada en {ruta}.", VERDE)
        except OSError as e:
            self._escribe(f"No se pudo guardar: {e}", ROJO)

    def _cargar(self, arg: str = "") -> None:
        ruta = arg.strip() or ARCHIVO_PARTIDA
        try:
            with open(ruta, encoding="utf-8") as f:
                estado = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            self._escribe(f"No se pudo cargar {ruta}: {e}", ROJO)
            return
        j = self.jugador
        j.nombre = estado["nombre"]
        j.vida = estado["vida"]
        j.monedas = estado["monedas"]
        j.corrupcion = estado["corrupcion"]
        j.inventario = list(estado["inventario"])
        j.companeros = []
        for c in estado["companeros"]:
            base = RECLUTAS[c["clave"]]
            j.companeros.append(Companero(**{**base.__dict__, "vida": c["vida"], "viva": c["viva"]}))
        self.lugar = estado["lugar"]
        self.lugar_previo = estado["lugar_previo"]
        self.flags = dict(estado["flags"])
        self.enemigos = {k: list(v) for k, v in estado["enemigos"].items()}
        self.tomados = {tuple(t.split("|", 1)) for t in estado["tomados"]}
        self.monedas_tomadas = set(estado["monedas_tomadas"])
        self.fin = False
        self.final = estado["final"]
        self._escribe(f"Partida cargada de {ruta}. De nuevo en {self.aqui().nombre}.", VERDE)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="aldamar",
        description="Aldamar: el Corazón de Ceniza — aventura de fantasía épica para la terminal.",
    )
    parser.add_argument(
        "--semilla", type=int, default=None, help="semilla aleatoria para partidas reproducibles"
    )
    parser.add_argument("--sin-color", action="store_true", help="desactivar colores ANSI")
    parser.add_argument(
        "--cargar", nargs="?", const=ARCHIVO_PARTIDA, metavar="ARCHIVO", help="cargar una partida guardada"
    )
    parser.add_argument("--version", action="version", version=f"aldamar {__version__}")
    args = parser.parse_args(argv)

    juego = Juego(semilla=args.semilla)
    if args.cargar:
        juego._cargar(args.cargar)
    try:
        juego.ciclo()
    except KeyboardInterrupt:
        print("\nEl viso cae sobre Aldamar. Partida suspendida.")

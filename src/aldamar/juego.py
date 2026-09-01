"""Bucle principal de Aldamar: comandos, combate, guardado y finales.

El motor es agnóstico de la aventura: todo el contenido llega en el
objeto `Aventura` y el balance en la `Dificultad` elegida. Los eventos
narrativos de cada lugar y el golpe especial de combate son funciones
definidas por la aventura.
"""

from __future__ import annotations

import argparse
import json
import random
import sys

from . import __version__, aventuras  # noqa: F401  (aventuras: registra el contenido)
from .aventura import AVENTURAS, Aventura, obtener_aventura
from .dificultad import DIFICULTADES, Dificultad, obtener_dificultad
from .menu import ARCHIVO_PARTIDA, ayuda, menu_principal
from .mundo import Lugar, normaliza
from .opciones import _es_interactivo, elegir_opcion, pantalla_completa
from .personajes import CORRUPCION_MAXIMA, Combatiente, Companero, Enemigo, Jugador

TITULO, VERDE, ROJO, AMARILLO, DIM = "1;36", "32", "31", "33", "2"

ESCRIBIR = "\x00texto"  # clave del menú que abre el modo tipeado clásico


class Juego:
    def __init__(
        self,
        aventura: Aventura,
        dificultad: Dificultad | None = None,
        personaje: str | None = None,
        semilla: int | None = None,
        entrada=input,
        salida=print,
        color: bool | None = None,
        flechas: bool | None = None,
    ) -> None:
        self.av = aventura
        self.dificultad = dificultad or obtener_dificultad()
        self.personaje = personaje or aventura.jugador_inicial
        self.rng = random.Random(semilla)
        self.entrada = entrada
        self.salida = salida
        self.flechas = flechas  # None = autodetectar; False = siempre tipear
        if color is None:
            color = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
        self.color = color
        self.jugador = self.av.crear_jugador(self.personaje, self.dificultad)
        self.lugar: str = self.av.lugar_inicial
        self.lugar_previo: str = self.av.lugar_inicial
        self.flags: dict[str, bool] = {}
        self.enemigos: dict[str, list[str]] = {
            lid: list(l.enemigos) for lid, l in self.av.lugares.items()
        }
        self.tomados: set[tuple[str, str]] = set()
        self.monedas_tomadas: set[str] = set()
        self.fin = False
        self.final: str | None = None
        self.en_combate = False
        self.reanudada = False

    # ── salida con color ─────────────────────────────────────────────
    def _c(self, texto: str, *codigos: str) -> str:
        if not self.color or not codigos:
            return texto
        return "\033[" + ";".join(codigos) + "m" + texto + "\033[0m"

    def escribir(self, texto: str = "", *codigos: str) -> None:
        self.salida(self._c(texto, *codigos))

    def epico(self, texto: str) -> None:
        self.escribir(texto, TITULO)

    def exito(self, texto: str) -> None:
        self.escribir(texto, VERDE)

    def peligro(self, texto: str) -> None:
        self.escribir(texto, ROJO)

    def aviso(self, texto: str) -> None:
        self.escribir(texto, AMARILLO)

    def tenue(self, texto: str) -> None:
        self.escribir(texto, DIM)

    # ── equipo derivado ──────────────────────────────────────────────
    def _mejor(self, tipo: str) -> dict | None:
        candidatos = [self.av.items[k] for k in self.jugador.inventario if self.av.items[k]["tipo"] == tipo]
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
        return self.av.lugares[self.lugar]

    def crear_enemigo(self, clave: str) -> Enemigo:
        return self.av.crear_enemigo(clave, self.dificultad)

    def restantes(self, lugar: Lugar) -> list[str]:
        return [k for k in lugar.objetos if (lugar.id, k) not in self.tomados]

    def destinos(self, lugar: Lugar) -> list[tuple[str, str, str]]:
        """Destinos deduplicados: (id, palabra de ejemplo, nombre)."""
        vistos: dict[str, str] = {}
        for palabra, destino in lugar.salidas.items():
            if destino not in vistos:
                vistos[destino] = palabra
        return [(d, p, self.av.lugares[d].nombre) for d, p in vistos.items()]

    def corruptear(self, puntos: int) -> None:
        puntos = round(puntos * self.dificultad.corrupcion)
        antes = self.jugador.corrupcion
        self.jugador.corruptear(puntos)
        delta = self.jugador.corrupcion - antes
        if delta > 0:
            self.aviso(f"El Corazón susurra… la grieta avanza (+{delta} corrupción).")
        elif delta < 0:
            self.exito(f"El agua y la distancia alivian la grieta ({delta} corrupción).")
        if self.jugador.corrupcion >= CORRUPCION_MAXIMA:
            self.aviso("\n" + self.av.epilogo_caida)
            self.fin = True
            self.final = "caida"

    # ── ciclo principal ──────────────────────────────────────────────
    def ciclo(self) -> None:
        if self.reanudada:
            self._mirar()
            self.tenue("(Partida recuperada.) " + self._pista())
            self.reanudada = False
        else:
            self._prologo()
        while not self.fin:
            try:
                linea = self._leer_orden("¿Qué haces?", self._c("> ", DIM), self._opciones_juego())
            except EOFError:
                linea = "salir"
            self._ejecutar(linea)
        if self.final:
            self.epico(f"\n— FIN —  (final: {self.final})")

    def _prologo(self) -> None:
        self.epico(self.av.prologo)
        ficha = self.av.personajes[self.personaje]
        try:
            nombre = self.entrada(self.av.texto_nombre.format(nombre=ficha.nombre)).strip()
        except EOFError:
            nombre = ""
        if nombre:
            self.jugador.nombre = nombre
        self.escribir("\n" + ficha.presentacion)
        self._mirar()
        self.tenue(self._pista())

    # ── la orden del jugador: menú con flechas o texto ───────────────
    def _usa_flechas(self) -> bool:
        """Menús navegables solo con teclado y pantalla reales (o forzados)."""
        if self.flechas is None:
            return _es_interactivo(self.entrada, self.salida)
        return self.flechas

    def _pista(self) -> str:
        if self._usa_flechas():
            return "(Elige qué hacer con ↑/↓ y Enter; Esc descarta.)"
        return "(Escribe  ayuda  para ver los comandos.)"

    def _leer_orden(self, titulo: str, prompt: str, opciones: list[tuple[str, str, str]]) -> str:
        """La próxima orden del jugador.

        Con teclado real se elige en un menú navegable; Esc devuelve ""
        (no hace nada) y "Escribir un comando…" abre el modo tipeado de
        siempre. Sin teclado real, se lee una línea, como toda la vida.
        """
        if self._usa_flechas():
            clave = elegir_opcion(
                titulo,
                opciones,
                entrada=self.entrada,
                salida=self.salida,
                color=self.color,
                flechas=True,
            )
            if clave is None:
                return ""
            if clave == ESCRIBIR:
                return self.entrada(prompt).strip()
            return clave
        return self.entrada(prompt).strip()

    def _opciones_juego(self) -> list[tuple[str, str, str]]:
        """Lo que se puede hacer ahora mismo, según el lugar y el momento."""
        l = self.aqui()
        ops: list[tuple[str, str, str]] = [
            ("mirar", "Mirar alrededor", "El lugar, lo que hay y a dónde ir"),
        ]
        ops += [
            (f"ir {i}", f"Ir a: {nombre}", "")
            for i, (_d, _p, nombre) in enumerate(self.destinos(l), 1)
        ]
        en_suelo = self.restantes(l)
        hay_monedas = bool(l.monedas) and l.id not in self.monedas_tomadas
        if en_suelo or hay_monedas:
            ops.append(("tomar todo", "Tomar todo", "Objetos del suelo y monedas"))
        ops += [
            (f"tomar {k}", f"Tomar: {self.av.items[k]['nombre']}", "")
            for k in en_suelo
        ]
        ops += [(f"hablar {npc}", f"Hablar: {npc}", "") for npc in l.npcs]
        ops += [
            (f"reclutar {npc}", f"Reclutar: {npc}", "Se suma a tu grupo")
            for npc, clave in l.npcs.items()
            if clave in self.av.reclutas
        ]
        if l.tienda:
            ops += [
                (
                    f"comprar {k}",
                    f"Comprar: {self.av.items[k]['nombre']}",
                    f"{self.av.items[k]['precio']} monedas",
                )
                for k in self.av.tiendas[l.id]
            ]
        ops += [
            (f"usar {k}", f"Usar: {self.av.items[k]['nombre']}", f"cura {self.av.items[k]['curacion']}")
            for k in self.jugador.inventario
            if self.av.items[k]["tipo"] == "consumible"
        ]
        if l.descanso:
            ops.append(("descansar", "Descansar", "Curarte del todo aquí mismo"))
        ops += [
            ("estado", "Estado", "Vida, corrupción y equipo"),
            ("inventario", "Inventario", "Lo que llevas"),
            ("guardar", "Guardar partida", f"En {ARCHIVO_PARTIDA}"),
            ("cargar", "Cargar partida", "Volver a un archivo guardado"),
            ("ayuda", "Ayuda", "Los comandos, a pantalla completa"),
            (ESCRIBIR, "Escribir un comando…", "Órdenes a mano, como siempre"),
            ("salir", "Salir del juego", "Dejar de jugar"),
        ]
        return ops

    def _opciones_combate(self, enemigo: Enemigo) -> list[tuple[str, str, str]]:
        ops: list[tuple[str, str, str]] = [("atacar", "Atacar", "Golpe a golpe")]
        if self.av.comando_especial and self.av.ataque_especial:
            ops.append((
                normaliza(self.av.comando_especial),
                self.av.comando_especial,
                "El golpe especial de la aventura",
            ))
        ops += [
            (f"usar {k}", f"Usar: {self.av.items[k]['nombre']}", f"cura {self.av.items[k]['curacion']}")
            for k in self.jugador.inventario
            if self.av.items[k]["tipo"] == "consumible"
        ]
        if any(self.av.items[k]["tipo"] == "cuerno" for k in self.jugador.inventario):
            ops.append(("cuerno", "Tocar el cuerno", "Pone en fuga a las criaturas menores"))
        ops += [
            ("huir", "Huir", "Retirada al lugar anterior"),
            ("estado", "Estado", ""),
            ("inventario", "Inventario", ""),
            (ESCRIBIR, "Escribir un comando…", ""),
        ]
        return ops

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
            "salir": self._salir,
        }
        accion = acciones.get(cmd)
        if accion is not None:
            accion(arg)  # type: ignore[operator]
        elif self.av.comando_especial and cmd == normaliza(self.av.comando_especial):
            self.aviso(self.av.texto_especial_fuera)
        elif cmd in ("atacar", "huir", "cuerno"):
            self.escribir("No hay combate aquí. Viaja con  ir <destino>.")
        else:
            self.tenue("No entiendo eso. Escribe  ayuda  para ver los comandos.")

    def _salir(self, _arg: str = "") -> None:
        self.escribir("Guardas las tomillas en el bolsillo y miras atrás una vez. Hasta pronto.")
        self.fin = True

    def _ayuda(self, _arg: str = "") -> None:
        pantalla_completa(ayuda(self.av), entrada=self.entrada, salida=self.salida, color=self.color)

    # ── mirar / estado / inventario ──────────────────────────────────
    def _mirar(self, _arg: str = "") -> None:
        l = self.aqui()
        self.epico(f"\n{l.nombre.capitalize()}")
        self.escribir(l.descripcion)
        restantes = self.restantes(l)
        if restantes:
            nombres = ", ".join(self.av.items[k]["nombre"] for k in restantes)
            self.exito(f"En el suelo ves: {nombres}.")
        if l.monedas and l.id not in self.monedas_tomadas:
            self.exito(f"Brillan {l.monedas} monedas de plata olvidadas.")
        for npc, clave in l.npcs.items():
            if clave in self.av.dialogos:
                self.aviso(f"Está aquí: {npc}. (hablar {npc})")
        pendientes = self.enemigos[l.id]
        if pendientes:
            nombres = ", ".join(self.av.enemigos[k]["nombre"] for k in pendientes)
            self.peligro(f"¡Se avecina: {nombres}!")
        lista = ", ".join(f"{i+1}) {n} ({p})" for i, (_d, p, n) in enumerate(self.destinos(l)))
        self.escribir(f"Puedes ir a: {lista}")

    def _estado(self, _arg: str = "") -> None:
        j = self.jugador
        ficha = self.av.personajes[self.personaje]
        self.epico(f"\n— {j.nombre} · {ficha.titulo} —")
        self.escribir(f"Vida: {j.vida}/{j.vida_max}   Corrupción: {j.recepcion()} {j.corrupcion}%")
        arma = self._mejor("arma")
        armadura = self._mejor("armadura")
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

    def _inventario(self, _arg: str = "") -> None:
        j = self.jugador
        self.epico("\nLlevas contigo:")
        if not j.inventario:
            self.tenue("  (nada más que un poco de harina en el bolsillo)")
        for k in j.inventario:
            i = self.av.items[k]
            if i["tipo"] == "reliquia":
                self.aviso("  el Corazón de Ceniza  ·  cuelga de tu cuello, caliente como una brasa")
                continue
            extra = ""
            if i["tipo"] == "arma":
                extra = f" (+{i['bonus']} ataque)"
            elif i["tipo"] == "armadura":
                extra = f" (+{i['bonus']} defensa)"
            elif i["tipo"] == "consumible":
                extra = f" (cura {i['curacion']})"
            self.escribir(f"  {i['nombre']}{extra}")

    # ── objetos ──────────────────────────────────────────────────────
    def _tomar(self, arg: str) -> None:
        l = self.aqui()
        restantes = self.restantes(l)
        hay_monedas = bool(l.monedas) and l.id not in self.monedas_tomadas
        if arg in ("todo", "todas", "todo."):
            for k in restantes:
                self.tomados.add((l.id, k))
                self.jugador.inventario.append(k)
                self.exito(f"Tomas: {self.av.items[k]['nombre']}.")
            if hay_monedas:
                self.monedas_tomadas.add(l.id)
                ganancia = round(l.monedas * self.dificultad.monedas)
                self.jugador.monedas += ganancia
                self.exito(f"Recoges {ganancia} monedas de plata.")
            if not restantes and not hay_monedas:
                self.tenue("No hay nada que tomar aquí.")
            return
        clave = self._buscar_item(arg, restantes)
        if clave:
            self.tomados.add((l.id, clave))
            self.jugador.inventario.append(clave)
            self.exito(f"Tomas: {self.av.items[clave]['nombre']}.")
        else:
            self.tenue("Eso no está por aquí.")

    def _buscar_item(self, texto: str, opciones: list[str]) -> str | None:
        t = normaliza(texto)
        for k in opciones:
            if t and (t in normaliza(self.av.items[k]["nombre"]) or t in normaliza(k)):
                return k
        return None

    def _comprar(self, arg: str) -> None:
        l = self.aqui()
        if not l.tienda:
            self.tenue("Aquí no hay tienda.")
            return
        stock = self.av.tiendas[l.id]
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
        if self.jugador.monedas < precio:
            self.aviso(f"Te faltan monedas: cuesta {precio} y llevas {self.jugador.monedas}.")
            return
        self.jugador.monedas -= precio
        self.jugador.inventario.append(clave)
        self.exito(f"Compras {self.av.items[clave]['nombre']} por {precio} monedas.")

    def _usar(self, arg: str) -> None:
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
        else:
            self.tenue("Eso no se usa así: ya te sirve solo por llevarlo.")

    # ── gente ────────────────────────────────────────────────────────
    def _hablar(self, arg: str) -> None:
        l = self.aqui()
        t = normaliza(arg)
        for npc, clave in l.npcs.items():
            if t and (t in normaliza(npc) or t in normaliza(clave)):
                self.epico("\n" + self.av.dialogos[clave])
                return
        self.tenue("Aquí no hay nadie con ese nombre.")

    def _reclutar(self, arg: str) -> None:
        l = self.aqui()
        t = normaliza(arg)
        for npc, clave in l.npcs.items():
            if clave in self.av.reclutas and t and (t in normaliza(npc) or t in normaliza(clave)):
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

    def _descansar(self, _arg: str = "") -> None:
        l = self.aqui()
        if not l.descanso:
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
                if t and (t == normaliza(palabra) or t in normaliza(self.av.lugares[destino_id].nombre)):
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

    def _entrar(self, destino: Lugar) -> None:
        self.epico(f"\n{destino.nombre.capitalize()}")
        self.escribir(destino.descripcion)
        evento = self.av.eventos.get(destino.evento) if destino.evento else None
        es_final = destino.evento == "final"
        if evento and not es_final:
            evento(self, destino)
            if self.fin:
                return
        pendientes = self.enemigos[destino.id]
        if pendientes:
            self._combate(list(pendientes))
            if self.fin or self.lugar != destino.id:
                return
        if es_final and evento and not pendientes:
            evento(self, destino)

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
        self.peligro(f"\n¡{enemigo.nombre} se abalanza!")
        while not self.fin:
            accion = self._turno_jugador(enemigo)
            if accion == "huida":
                return "huida"
            if accion == "cuerno":
                self.exito(f"{enemigo.nombre} huye con los demás. Combate resuelto.")
                return "victoria"
            if self.fin:
                return "muerte"
            if not enemigo.vivo:
                self.exito(f"{enemigo.nombre} cae y se deshace en humo pardo.")
                return "victoria"
            objetivo = self._objetivo()
            efectivo = self._golpea(enemigo, objetivo)
            if isinstance(objetivo, Companero):
                self.peligro(
                    f"{enemigo.nombre} golpea a {objetivo.nombre}: −{efectivo} ({objetivo.vida}/{objetivo.vida_max})."
                )
                if not objetivo.vivo:
                    objetivo.viva = False
                    self.peligro(f"{objetivo.nombre} cae…")
            else:
                self.peligro(
                    f"{enemigo.nombre} te golpea: −{efectivo} ({self.jugador.vida}/{self.jugador.vida_max})."
                )
                if not self.jugador.vivo:
                    self.aviso("\n" + self.av.epilogo_muerte)
                    self.fin = True
                    self.final = "muerte"
                    return "muerte"
        return "muerte"

    def _turno_jugador(self, enemigo: Enemigo) -> str:
        """Acción del jugador y contraataque de los compañeros.

        Devuelve: "seguir" (turno normal), "huida" o "cuerno" (combate resuelto).
        """
        especial = normaliza(self.av.comando_especial) if self.av.comando_especial else None
        while True:
            try:
                linea = self._leer_orden(
                    f"¡{enemigo.nombre}! ¿Qué haces?",
                    self._c("combate> ", DIM),
                    self._opciones_combate(enemigo),
                )
            except EOFError:
                # se acabó la entrada: suspendemos la partida en vez de colgarnos
                self.fin = True
                self.final = self.final or "suspendida"
                return "seguir"
            partes = normaliza(linea).split(maxsplit=1)
            cmd = partes[0] if partes else ""
            arg = partes[1] if len(partes) > 1 else ""
            if not cmd:
                continue  # Esc en el menú: se espera otra orden

            if cmd == "atacar":
                efectivo = self._golpea(self.jugador, enemigo)
                self.escribir(f"Golpeas a {enemigo.nombre}: −{efectivo} ({enemigo.vida}/{enemigo.vida_max}).")
            elif cmd == "usar":
                clave = self._buscar_item(arg, self.jugador.inventario)
                if clave and self.av.items[clave]["tipo"] == "consumible":
                    self.jugador.inventario.remove(clave)
                    antes = self.jugador.vida
                    curacion = round(self.av.items[clave]["curacion"] * self.dificultad.curacion)
                    self.jugador.curar(curacion)
                    self.exito(f"{self.av.items[clave]['nombre']}: vida {antes} → {self.jugador.vida}.")
                else:
                    self.tenue("Eso no se puede usar en combate.")
                    continue
            elif especial and cmd == especial and self.av.ataque_especial:
                self.av.ataque_especial(self, enemigo)
                if self.fin:
                    return "seguir"
            elif cmd == "cuerno":
                clave = next(
                    (k for k in self.jugador.inventario if self.av.items[k]["tipo"] == "cuerno"),
                    None,
                )
                if clave:
                    if enemigo.sin_huida:
                        self.aviso("El toque resuena… y el guardián ni parpadea.")
                        continue
                    self.jugador.inventario.remove(clave)
                    self.epico("El cuerno retumba en el aire: las criaturas menores huyen despavoridas.")
                    self.enemigos[self.lugar].clear()
                    return "cuerno"
                self.tenue("No llevas ningún cuerno.")
                continue
            elif cmd == "huir":
                if enemigo.sin_huida:
                    self.aviso("No hay a dónde ir: el guardián cierra el paso.")
                    continue
                if self.rng.random() < 0.55:
                    self.escribir("Retrocedes con el corazón en la garganta…")
                    return "huida"
                self.peligro("El enemigo te corta la retirada.")
            elif cmd == "estado":
                self._estado()
                continue
            elif cmd in ("inventario", "inv"):
                self._inventario()
                continue
            else:
                self.tenue(ayuda_combate(self.av))
                continue

            # acción válida: los compañeros golpean también
            for c in self.jugador.companeras_vivas():
                dano = self.rng.randint(c.ataque, c.ataque + 2)
                efectivo = enemigo.recibir(dano)
                self.escribir(f"{c.nombre} ataca: −{efectivo} ({enemigo.vida}/{enemigo.vida_max}).")
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
            enemigo = self.crear_enemigo(clave)
            resultado = self._duelo(enemigo)
            if self.fin:
                self.en_combate = False
                return
            if resultado == "victoria":
                if clave in pendientes:
                    pendientes.remove(clave)
                if not pendientes:
                    self.exito("El aire vuelve a moverse. El camino queda libre.")
            else:  # huida
                self.lugar = self.lugar_previo
                self.aviso(
                    f"Vuelves a {self.av.lugares[self.lugar].nombre}. Los enemigos siguen ahí, esperando."
                )
                self.en_combate = False
                return
        self.en_combate = False

    # ── guardar / cargar ─────────────────────────────────────────────
    def _guardar(self, arg: str = "") -> None:
        ruta = arg.strip() or ARCHIVO_PARTIDA
        estado = {
            "aventura": self.av.id,
            "dificultad": self.dificultad.clave,
            "personaje": self.personaje,
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
            self.exito(f"Partida guardada en {ruta}.")
        except OSError as e:
            self.peligro(f"No se pudo guardar: {e}")

    def _aplicar_estado(self, estado: dict, ruta: str) -> None:
        self.av = obtener_aventura(estado.get("aventura"))
        self.dificultad = obtener_dificultad(estado.get("dificultad"))
        self.personaje = estado.get("personaje") or self.av.jugador_inicial
        self.jugador = self.av.crear_jugador(self.personaje, self.dificultad)
        j = self.jugador
        j.nombre = estado["nombre"]
        j.vida = estado["vida"]
        j.monedas = estado["monedas"]
        j.corrupcion = estado["corrupcion"]
        j.inventario = list(estado["inventario"])
        j.companeros = []
        for c in estado["companeros"]:
            base = self.av.reclutas[c["clave"]]
            j.companeros.append(Companero(**{**base.__dict__, "vida": c["vida"], "viva": c["viva"]}))
        self.lugar = estado["lugar"]
        self.lugar_previo = estado["lugar_previo"]
        self.flags = dict(estado["flags"])
        # guardados viejos pueden traer menos lugares: los faltantes
        # recuperan sus enemigos originales
        guardados = {k: list(v) for k, v in estado["enemigos"].items()}
        self.enemigos = {
            lid: guardados.get(lid, list(l.enemigos)) for lid, l in self.av.lugares.items()
        }
        self.tomados = {tuple(t.split("|", 1)) for t in estado["tomados"]}
        self.monedas_tomadas = set(estado["monedas_tomadas"])
        self.fin = False
        self.final = estado.get("final")
        self.reanudada = True
        self.exito(f"Partida cargada de {ruta}. De nuevo en {self.aqui().nombre}.")

    def _cargar(self, arg: str = "") -> None:
        ruta = arg.strip() or ARCHIVO_PARTIDA
        try:
            with open(ruta, encoding="utf-8") as f:
                estado = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            self.peligro(f"No se pudo cargar {ruta}: {e}")
            return
        self._aplicar_estado(estado, ruta)

    @classmethod
    def desde_archivo(
        cls,
        ruta: str,
        *,
        semilla: int | None = None,
        entrada=input,
        salida=print,
        color: bool | None = None,
        flechas: bool | None = None,
    ) -> "Juego":
        """Construye una partida a partir de un archivo de guardado."""
        with open(ruta, encoding="utf-8") as f:
            estado = json.load(f)
        juego = cls(
            aventura=obtener_aventura(estado.get("aventura")),
            dificultad=obtener_dificultad(estado.get("dificultad")),
            personaje=estado.get("personaje"),
            semilla=semilla,
            entrada=entrada,
            salida=salida,
            color=color,
            flechas=flechas,
        )
        juego._aplicar_estado(estado, ruta)
        return juego


def ayuda_combate(av: Aventura) -> str:
    """Recordatorio de comandos de combate para la línea de órdenes."""
    especial = f" · {av.comando_especial}" if av.comando_especial else ""
    return f"En combate: atacar · usar <cosa>{especial} · cuerno · huir · estado"


def main(argv: list[str] | None = None, *, entrada=input, salida=print) -> None:
    parser = argparse.ArgumentParser(
        prog="aldamar",
        description="Aldamar: aventuras de fantasía épica para la terminal.",
    )
    parser.add_argument(
        "--semilla", type=int, default=None, help="semilla aleatoria para partidas reproducibles"
    )
    parser.add_argument("--sin-color", action="store_true", help="desactivar colores ANSI")
    parser.add_argument(
        "--sin-flechas", action="store_true", help="menús respondiendo a texto, sin flechas del teclado"
    )
    parser.add_argument(
        "--cargar", nargs="?", const=ARCHIVO_PARTIDA, metavar="ARCHIVO", help="cargar una partida guardada"
    )
    parser.add_argument(
        "--aventura", choices=sorted(AVENTURAS), default=None, help="aventura a jugar (salta el menú)"
    )
    parser.add_argument(
        "--dificultad", choices=sorted(DIFICULTADES), default=None, help="dificultad del balance"
    )
    parser.add_argument("--personaje", default=None, help="héroe inicial de la aventura")
    parser.add_argument("--version", action="version", version=f"aldamar {__version__}")
    args = parser.parse_args(argv)
    color = False if args.sin_color else None
    flechas = False if args.sin_flechas else None
    color_menu = bool(color) if color is not None else hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

    try:
        if args.cargar:
            juego = Juego.desde_archivo(
                args.cargar,
                semilla=args.semilla,
                entrada=entrada,
                salida=salida,
                color=color,
                flechas=flechas,
            )
        elif args.aventura and args.dificultad:
            # todo definido por CLI: ni menú
            juego = Juego(
                aventura=obtener_aventura(args.aventura),
                dificultad=obtener_dificultad(args.dificultad),
                personaje=args.personaje,
                semilla=args.semilla,
                entrada=entrada,
                salida=salida,
                color=color,
                flechas=flechas,
            )
        else:
            eleccion = menu_principal(
                entrada=entrada,
                salida=salida,
                color=color_menu,
                flechas=flechas,
                aventura=args.aventura,
                dificultad=args.dificultad,
                personaje=args.personaje,
            )
            if eleccion is None or eleccion.accion == "salir":
                salida("Hasta pronto.")
                return
            if eleccion.accion == "cargar":
                juego = Juego.desde_archivo(
                    eleccion.archivo or ARCHIVO_PARTIDA,
                    semilla=args.semilla,
                    entrada=entrada,
                    salida=salida,
                    color=color,
                    flechas=flechas,
                )
            else:
                juego = Juego(
                    aventura=eleccion.aventura,
                    dificultad=eleccion.dificultad,
                    personaje=eleccion.personaje,
                    semilla=args.semilla,
                    entrada=entrada,
                    salida=salida,
                    color=color,
                    flechas=flechas,
                )
        juego.ciclo()
    except KeyboardInterrupt:
        salida("\nEl viso cae sobre Aldamar. Partida suspendida.")
    except (OSError, json.JSONDecodeError) as e:
        salida(f"No se pudo abrir la partida: {e}")
    except KeyError as e:
        salida(f"Opción desconocida: {e}")

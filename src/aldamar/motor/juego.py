"""Bucle principal de Aldamar: comandos, combate, guardado y finales.

El motor es agnóstico de la aventura: todo el contenido llega en el
objeto `Aventura` y el balance en la `Dificultad` elegida. Los eventos
narrativos de cada lugar y el golpe especial de combate son efectos del
vocabulario declarativo (`eventos.py`) que cada aventura declara en su
JSON (que `cargador.py` valida y convierte en funciones).
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys

from .. import __version__, datos  # noqa: F401  (datos: registra el contenido)
from ..contenido.aventura import AVENTURAS, Aventura, obtener_aventura
from ..contenido.mundo import Lugar, normaliza
from ..contenido.personajes import (
    CORRUPCION_MAXIMA,
    SUBIDA_ATAQUE,
    SUBIDA_VIDA,
    XP_NIVEL,
    Combatiente,
    Companero,
    Enemigo,
    Habilidad,
    Jugador,
)
from ..contenido.rasgos import RASGOS
from ..interfaz.menu import ARCHIVO_PARTIDA, ayuda, menu_principal
from ..interfaz import audio as modulo_audio
from ..interfaz import opciones, presentacion
from ..interfaz.opciones import (
    LIMPIAR,
    _es_interactivo,
    elegir_opcion,
    pantalla_completa,
)
from . import configuracion
from . import guardado
from .dificultad import DIFICULTADES, Dificultad, ajusta, obtener_dificultad
from . import legado as modulo_legado
from .estadisticas import ARCHIVO_ESTADISTICAS, Estadisticas
from .guardado import PartidaInvalida

TITULO, VERDE, ROJO, AMARILLO, DIM = "1;36", "32", "31", "33", "2"

ESCRIBIR = "\x00texto"  # clave del menú que abre el modo tipeado clásico
OTRAS = "\x00otras"  # clave del menú que abre el submenú de gestiones

# Claves de los verbos con submenú: un verbo, un listado (issue 26). En el
# menú de acciones cada verbo es una sola entrada; elegirlo apila su
# listado y Esc vuelve al menú de abajo.
IR = "\x00ir"
TOMAR = "\x00tomar"
HABLAR = "\x00hablar"
RECLUTAR = "\x00reclutar"
COMPRAR = "\x00comprar"
USAR = "\x00usar"

# La tómbola del turno enemigo: el golpe normal tira con este peso, las
# habilidades con el suyo (declarado en el JSON).
PESO_GOLPE = 2


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
        nombre: str | None = None,
        legado: dict | None = None,
        audio: bool = True,
    ) -> None:
        self.av = aventura
        self.dificultad = dificultad or obtener_dificultad()
        self.personaje = personaje or aventura.jugador_inicial
        self.rng = random.Random(semilla)
        self.entrada = entrada
        self.salida = salida
        self.flechas = flechas  # None = autodetectar; False = siempre tipear
        self.audio = audio  # el jingle del cierre; la presentación decide el suyo
        if color is None:
            color = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
        self.color = color
        self.jugador = self.av.crear_jugador(self.personaje, self.dificultad)
        if nombre:
            self.jugador.nombre = nombre  # «jugar otra vez»: el nombre se queda
        self.nombre_dado = bool(nombre)
        self._autoequipar()  # el héroe empieza con lo suyo puesto
        self.lugar: str = self.av.lugar_inicial
        self.lugar_previo: str = self.av.lugar_inicial
        self.flags: dict[str, bool] = {}
        # el legado de la serie: lo que otras aventuras recuerdan de ti
        # (issue 19); sus banderas canónicas se encienden al empezar
        self.legado = dict(legado) if legado else {}
        modulo_legado.enciende(self.flags, self.av.legado.importa, self.legado)
        self.enemigos: dict[str, list[str]] = {
            lid: list(lugar.enemigos) for lid, lugar in self.av.lugares.items()
        }
        self.tomados: set[tuple[str, str]] = set()
        self.monedas_tomadas: set[str] = set()
        self.derrotados: list[str] = []  # claves de los caídos, en orden
        self.visitados: list[str] = [self.av.lugar_inicial]
        self.epilogo: str | None = (
            None  # el texto del final, para la pantalla de cierre
        )
        self.fin = False
        self.final: str | None = None
        self.en_combate = False
        self.reanudada = False
        self._estado_mostrado: str | None = None  # la última cabecera de estado escrita
        self._marco_activo = False  # la región de scroll: fila 1 fija, historia abajo
        # el bloque del duelo (issue 36): los renglones del turno en curso
        # se guardan para mostrarse en el bloque, no apilarse en el relato
        self._bloque_activo = False
        self._turno_lineas: list[str] = []
        # lo que la partida va sabiendo de sí misma, por si la piden (--stats)
        self.stats = Estadisticas()

    # ── salida con color ─────────────────────────────────────────────
    def _c(self, texto: str, *codigos: str) -> str:
        if not self.color or not codigos:
            return texto
        return "\033[" + ";".join(codigos) + "m" + texto + "\033[0m"

    def escribir(self, texto: str = "", *codigos: str) -> None:
        if self._bloque_activo:  # en pleno duelo: el turno va al bloque, no al relato
            self._turno_lineas.append(self._c(texto, *codigos))
            return
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

    def _texto_heroe(self, texto: str) -> str:
        """Sustituye {trato} y {quien} por los apodos del héroe en marcha."""
        ficha = self.av.personajes[self.personaje]
        return texto.format(trato=ficha.trato, quien=ficha.quien)

    # ── equipo derivado ──────────────────────────────────────────────
    def _item_equipado(self, tipo: str) -> dict | None:
        """La pieza puesta en ese sitio (arma/armadura), si la sigues llevando."""
        clave = self.jugador.equipado.get(tipo)
        if clave and clave in self.jugador.inventario:
            return self.av.items[clave]
        self.jugador.equipado.pop(tipo, None)
        return None

    def bonus_arma(self) -> int:
        arma = self._item_equipado("arma")
        return arma["bonus"] if arma else 0

    def bonus_armadura(self) -> int:
        armadura = self._item_equipado("armadura")
        return armadura["bonus"] if armadura else 0

    def ataque_total(self) -> int:
        return self.jugador.ataque + self.bonus_arma()

    def _modificador(self, campo: str, objetivo: Combatiente | None = None) -> int:
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

    def _autoequipar(self) -> None:
        """Viste lo mejor que haya, sin decisión: al empezar y al cargar
        un guardado viejo —que vestía siempre lo mejor del inventario—.
        A partir de ahí, equiparse es un comando, no un efecto automático."""
        for tipo in ("arma", "armadura"):
            if self.jugador.equipado.get(tipo):
                continue
            candidatos = [
                k for k in self.jugador.inventario if self.av.items[k]["tipo"] == tipo
            ]
            mejor = max(
                candidatos, key=lambda k: self.av.items[k]["bonus"], default=None
            )
            if mejor is not None:
                self.jugador.equipado[tipo] = mejor

    def adquirir(self, clave: str) -> None:
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

    def _equipar(self, arg: str) -> None:
        if not arg:
            self.tenue(
                "¿Equipar qué? Prueba  equipar <cosa>  o el submenú de gestiones."
            )
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

    def _desequipar(self, arg: str) -> None:
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

    def _opciones_equipo(self) -> list[tuple[str, str, str]]:
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
                ops.append(
                    (
                        f"desequipar {tipo}",
                        f"Desequipar: {self.av.items[puesta]['nombre']}",
                        "",
                    )
                )
        return ops

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
            self.exito(
                f"El agua y la distancia alivian la grieta ({delta} corrupción)."
            )
        if self.jugador.corrupcion >= CORRUPCION_MAXIMA:
            self.aviso("\n" + self._texto_heroe(self.av.epilogo_caida))
            self.fin = True
            self.final = "caida"

    # ── ciclo principal ──────────────────────────────────────────────
    def ciclo(self) -> str | None:
        """Juega hasta el final. Devuelve la decisión de la pantalla de
        cierre: "otra" (repetir), "menu" (otra aventura) o None (salir;
        también si se dejó a medias con «salir»)."""
        self._activa_marco()
        try:
            if self.reanudada:
                self._mirar()
                self.tenue("(Partida recuperada.) " + self._pista())
                self.reanudada = False
            else:
                self._prologo()
            while not self.fin:
                try:
                    linea = self._leer_orden(
                        "¿Qué haces?", self._c("> ", DIM), self._opciones_juego()
                    )
                except EOFError:
                    linea = "salir"
                self._ejecutar(linea)
            if self.final:
                return self._cierre()
            return None
        finally:
            self._desactiva_marco()

    # ── la pantalla de cierre ────────────────────────────────────────
    def _remate(self) -> str:
        """El título grande de la despedida, según cómo acabó."""
        final = self.final or ""
        if final == "muerte":
            return "Aquí se apaga tu historia"
        if final == "caida":
            return "La grieta te alcanzó"
        if final == "suspendida":
            return "La historia queda a medias"
        if "victoria" in final:
            if "cicatriz" in final:
                return "Ganaste… y la marca se queda"
            return "¡La noche retrocede!"
        return "Así acaba este cantar"

    def _texto_cierre(self) -> str:
        """Remate, final, epílogo, balance del héroe y huella del viaje."""
        j = self.jugador
        ficha = self.av.personajes[self.personaje]
        lineas = ["═" * 66, self._remate().center(66), "═" * 66]
        if self.final not in (None, "muerte", "caida", "suspendida"):
            lineas.append(f"\nTu historia queda contada: «{self.final}».")
        if self.epilogo:
            lineas.append(f"\n{self.epilogo}")
        lineas.append("\n— El balance del héroe —")
        lineas.append(f"{j.nombre}, {ficha.titulo}")
        lineas.append(
            f"Nivel {j.nivel} · {j.experiencia} XP · Vida {j.vida}/{j.vida_max}"
            f" · Corrupción {j.corrupcion}% · Monedas: {j.monedas}"
        )
        if j.inventario:
            lineas.append(
                "Llevabas: "
                + ", ".join(self.av.items[k]["nombre"] for k in j.inventario)
            )
        if j.companeros:
            lineas.append(
                "Compañeros: "
                + ", ".join(
                    f"{c.nombre} ({c.vida}/{c.vida_max})"
                    if c.viva
                    else f"{c.nombre} (cayó)"
                    for c in j.companeros
                )
            )
        if self.derrotados:
            cuenta: dict[str, int] = {}
            for clave in self.derrotados:
                cuenta[clave] = cuenta.get(clave, 0) + 1
            lineas.append(
                "Enemigos derrotados: "
                + ", ".join(
                    self.av.enemigos[clave]["nombre"]
                    if n == 1
                    else f"{self.av.enemigos[clave]['nombre']} ×{n}"
                    for clave, n in cuenta.items()
                )
            )
        if len(self.visitados) > 1:
            lineas.append(
                f"Lugares visitados: {len(self.visitados)} — "
                + ", ".join(self.av.lugares[lid].nombre for lid in self.visitados)
            )
        if self.flags:
            lineas.append(
                "Decisiones: " + ", ".join(k.replace("_", " ") for k in self.flags)
            )
        return "\n".join(lineas)

    def _cierre(self) -> str | None:
        """La despedida a pantalla completa y el menú de «¿y ahora qué?».

        Devuelve la decisión: "otra", "menu" o None/salir.
        """
        self._desactiva_marco()  # el cierre es pantalla completa, sin marco
        if self._usa_flechas():
            self.salida(LIMPIAR)  # el cierre se ve solo, fuera del relato
        if self.audio:
            # el mismo jingle de la presentación (issue 34): la despedida
            # suena, victoria o desgracia
            modulo_audio.reproducir(entrada=self.entrada, salida=self.salida)
        lineas = self._texto_cierre().splitlines()
        for linea in lineas[:3]:
            self.epico(linea)  # el remate, en grande
        self.escribir("\n".join(lineas[3:]))
        return elegir_opcion(
            "¿Y ahora qué?",
            [
                ("otra", "Jugar otra vez", "Misma aventura, mismo héroe y dificultad"),
                ("menu", "Elegir otra aventura", "De vuelta al menú principal"),
                ("salir", "Salir", "Hasta pronto"),
            ],
            entrada=self.entrada,
            salida=self.salida,
            color=self.color,
            flechas=self.flechas,
            aviso_esc="Elige a dónde ir: otra partida, el menú o salir.",
        )

    def _estado_linea(self) -> str:
        """Quién, cómo y dónde: lo que vive en la primera fila (issue 36)."""
        j = self.jugador
        return f"{j.nombre} · Vida {j.vida}/{j.vida_max} · {j.monedas} monedas · {self.aqui().nombre}"

    def _cabecera(self) -> None:
        """Reescribe la primera fila con el estado del héroe, en el sitio.

        Guarda el cursor, ancla la fila 1 y lo restaura: no importa
        dónde esté el relato, la cabecera no lo mueve ni se mueve.
        """
        if not self._usa_flechas():
            return
        self.salida(
            "\x1b7\x1b[1;1H\x1b[2K" + self._c(self._estado_linea(), TITULO) + "\x1b8"
        )

    def _activa_marco(self) -> None:
        """El marco de la partida: fila 1 fija para la cabecera, la
        historia vive de la fila 2 para abajo (issue 36)."""
        if not self._usa_flechas():
            return
        self._marco_activo = True
        self.salida("\x1b[2r\x1b[2;1H")  # el scroll pasa a vivir bajo la cabecera
        self._cabecera()
        self._estado_mostrado = self._estado_linea()

    def _desactiva_marco(self) -> None:
        """Libera la región de scroll: la terminal queda como estaba."""
        if self._marco_activo:
            self._marco_activo = False
            self.salida("\x1b[r")

    def _limpiar(self) -> None:
        """Una vista nueva: la pantalla limpia en modo navegable (issue 36).

        Las vistas —mirar, una conversación, un lugar nuevo— se ven
        solas; lo que no es una vista (tomar, usar, comprar…) se anota
        debajo de lo anterior hasta que llegue la próxima. En modo
        tipeado el relato es completo y no se limpia nunca.
        """
        if self._usa_flechas():
            self.salida(LIMPIAR)
            self._cabecera()
            self.salida("\x1b[2;1H")  # la vista arranca bajo la cabecera
            self._estado_mostrado = self._estado_linea()
        else:
            self._estado_mostrado = None

    def _barra(self, vida: int, vida_max: int, ancho: int = 16) -> str:
        llenos = round(ancho * max(0, min(vida, vida_max)) / max(1, vida_max))
        return "█" * llenos + "░" * (ancho - llenos)

    def _titulo_combate(self, enemigo: Enemigo) -> str:
        """El bloque del duelo, como título del menú (issue 36).

        La vida de todos en barras y los renglones del último turno,
        en el mismo sitio: los duelos largos no apilan líneas. En modo
        tipeado, el título de siempre — el turno se cuenta entero.
        """
        if not self._usa_flechas():
            return f"¡{enemigo.nombre}! ¿Qué haces?"
        lineas = [f"¡{enemigo.nombre}! ¿Qué haces?"]
        margen = max(
            [len(enemigo.nombre), len(self.jugador.nombre)]
            + [len(c.nombre) for c in self.jugador.companeros]
        )
        filas = [(enemigo.nombre, enemigo.vida, enemigo.vida_max, ROJO)]
        filas.append(
            (self.jugador.nombre, self.jugador.vida, self.jugador.vida_max, VERDE)
        )
        filas += [
            (c.nombre, c.vida, c.vida_max, None if c.viva else DIM)
            for c in self.jugador.companeros
        ]
        for nombre, vida, vida_max, color in filas:
            barra = f"{self._barra(vida, vida_max)} {vida}/{vida_max}"
            linea = f"  {nombre:<{margen}}  {barra}"
            lineas.append(self._c(linea, color) if color else linea)
        if self.jugador.envenenado:
            lineas.append(
                self._c(
                    f"  Envenenado: −{self.jugador.veneno_dano} por turno ({self.jugador.veneno_turnos} turnos).",
                    self.color,
                    AMARILLO,
                )
            )
        if self._turno_lineas:  # el último turno, debajo del estado; nada se repite
            lineas += self._turno_lineas[-4:]
            self._turno_lineas.clear()
        return "\n".join(lineas)

    def _vuelca_bloque(self) -> None:
        """Los renglones que quedaban en el bloque del duelo, al relato."""
        for linea in self._turno_lineas:
            self.salida(linea)
        self._turno_lineas.clear()

    def _prologo(self) -> None:
        ficha = self.av.personajes[self.personaje]
        self.epico(ficha.prologo or self.av.prologo)
        if self.legado and self.av.legado.importa:
            # la serie recuerda: el gesto de la fama, con la voz del héroe
            texto = self.av.legado.texto_fama or modulo_legado.FAMA
            self.epico(
                "\n"
                + texto.format(
                    nombre=self.legado.get("nombre") or ficha.nombre,
                    trato=ficha.trato,
                    quien=ficha.quien,
                )
            )
        if not self.nombre_dado:  # «jugar otra vez» conserva el nombre puesto
            try:
                pregunta = ficha.texto_nombre or self.av.texto_nombre
                nombre = self.entrada(pregunta.format(nombre=ficha.nombre)).strip()
            except EOFError:
                nombre = ""
            if nombre:
                self.jugador.nombre = nombre
        # el nombre también es "avanzar": la presentación y la vista del
        # lugar se ven solas, sobre la pantalla recién limpiada
        self._limpiar()
        self.escribir("\n" + ficha.presentacion)
        self._mirar(limpiar=False)
        self.tenue(self._pista())

    # ── la orden del jugador: menú con flechas o texto ───────────────
    def _usa_flechas(self) -> bool:
        """Menús navegables solo con teclado y pantalla reales (o forzados)."""
        if self.flechas is None:
            return _es_interactivo(self.entrada, self.salida)
        return self.flechas

    def _pista(self) -> str:
        if self._usa_flechas():
            return "(Elige con ↑/↓ y Enter: cada verbo abre su listado, y Esc vuelve; las gestiones están en «Otras acciones…».)"
        return "(Escribe  ayuda  para ver los comandos.)"

    def _leer_orden(
        self,
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

        def resuelve(
            clave: str | None,
        ) -> tuple[str, list[tuple[str, str, str]], str | None] | None:
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

    def _opciones_juego(self) -> list[tuple[str, str, str]]:
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
            ops.append(
                (
                    f"tomar {en_suelo[0]}",
                    f"Tomar: {self.av.items[en_suelo[0]]['nombre']}",
                    "",
                )
            )
        elif en_suelo or hay_monedas:
            ops.append((TOMAR, "Tomar…", self._cuenta_tomar(lugar)))
        npcs = list(lugar.npcs)
        if len(npcs) == 1:
            ops.append((f"hablar {npcs[0]}", f"Hablar: {npcs[0]}", ""))
        elif npcs:
            ops.append((HABLAR, "Hablar…", f"{len(npcs)} personas aquí"))
        aliados = [
            npc for npc, clave in lugar.npcs.items() if clave in self.av.reclutas
        ]
        if len(aliados) == 1:
            ops.append(
                (
                    f"reclutar {aliados[0]}",
                    f"Reclutar: {aliados[0]}",
                    "Se suma a tu grupo",
                )
            )
        elif aliados:
            ops.append((RECLUTAR, "Reclutar…", f"{len(aliados)} aliados"))
        if lugar.tienda:
            stock = self.av.tiendas[lugar.id]
            if len(stock) == 1 and not self._opciones_equipo():
                item = self.av.items[stock[0]]
                ops.append(
                    (
                        f"comprar {stock[0]}",
                        f"Comprar: {item['nombre']}",
                        f"{item['precio']} monedas",
                    )
                )
            else:
                ops.append((COMPRAR, "Comprar…", f"{len(stock)} cosas en venta"))
        if any(
            self.av.items[k]["tipo"] == "consumible" for k in self.jugador.inventario
        ):
            ops.append(self._entrada_usar())
        if lugar.descanso:
            ops.append(("descansar", "Descansar", "Curarte del todo aquí mismo"))
        ops.append((OTRAS, "Otras acciones…", "Estado, inventario, partida y ayuda"))
        return ops

    def _entrada_usar(self) -> tuple[str, str, str]:
        """La entrada del verbo «usar»: directa si hay un solo consumible."""
        consumibles = [
            k
            for k in self.jugador.inventario
            if self.av.items[k]["tipo"] == "consumible"
        ]
        if len(consumibles) == 1:
            k = consumibles[0]
            return (
                f"usar {k}",
                f"Usar: {self.av.items[k]['nombre']}",
                f"cura {self.av.items[k]['curacion']}",
            )
        return (USAR, "Usar…", f"{len(consumibles)} provisiones")

    def _cuenta_tomar(self, lugar: Lugar) -> str:
        """Lo que hay por el suelo, para contar junto al verbo."""
        objetos = len(self.restantes(lugar))
        hay_monedas = bool(lugar.monedas) and lugar.id not in self.monedas_tomadas
        cosas = (
            ""
            if not objetos
            else ("1 objeto" if objetos == 1 else f"{objetos} objetos")
        )
        if cosas and hay_monedas:
            return f"{cosas} y monedas"
        return cosas or "monedas"

    def _submenu(self, clave: str) -> tuple[str, list[tuple[str, str, str]]] | None:
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
                [
                    (f"ir {i}", nombre, "")
                    for i, (_d, _p, nombre) in enumerate(destinos, 1)
                ],
            )
        if clave == TOMAR:
            ops = [("tomar todo", "Tomar todo", "Objetos del suelo y monedas")]
            ops += [
                (f"tomar {k}", self.av.items[k]["nombre"], "")
                for k in self.restantes(lugar)
            ]
            return (f"Tomar — en {lugar.nombre} ({self._cuenta_tomar(lugar)})", ops)
        if clave == HABLAR:
            npcs = list(lugar.npcs)
            return (
                f"Hablar — {lugar.nombre} ({len(npcs)} personas aquí)",
                [(f"hablar {npc}", npc, "") for npc in npcs],
            )
        if clave == RECLUTAR:
            aliados = [
                npc for npc, clave in lugar.npcs.items() if clave in self.av.reclutas
            ]
            return (
                f"Reclutar — {lugar.nombre} ({len(aliados)} aliados)",
                [(f"reclutar {npc}", npc, "Se suma a tu grupo") for npc in aliados],
            )
        if clave == COMPRAR:
            stock = self.av.tiendas[lugar.id]
            ops = [
                (
                    f"comprar {k}",
                    self.av.items[k]["nombre"],
                    f"{self.av.items[k]['precio']} monedas",
                )
                for k in stock
            ]
            ops += self._opciones_equipo()  # en la tienda, probar lo llevado
            return (f"Comprar — {lugar.nombre} ({len(stock)} cosas en venta)", ops)
        if clave == USAR:
            ops = [
                (
                    f"usar {k}",
                    self.av.items[k]["nombre"],
                    f"cura {self.av.items[k]['curacion']}",
                )
                for k in self.jugador.inventario
                if self.av.items[k]["tipo"] == "consumible"
            ]
            return (f"Usar — tu mochila ({len(ops)} provisiones)", ops)
        return None

    def _opciones_otras(self) -> list[tuple[str, str, str]]:
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

    def _opciones_combate(self, enemigo: Enemigo) -> list[tuple[str, str, str]]:
        ops: list[tuple[str, str, str]] = [("atacar", "Atacar", "Golpe a golpe")]
        if self.av.comando_especial and self.av.ataque_especial:
            ops.append(
                (
                    normaliza(self.av.comando_especial),
                    self.av.comando_especial,
                    "El golpe especial de la aventura",
                )
            )
        if any(
            self.av.items[k]["tipo"] == "consumible" for k in self.jugador.inventario
        ):
            ops.append(self._entrada_usar())
        if any(self.av.items[k]["tipo"] == "cuerno" for k in self.jugador.inventario):
            ops.append(
                ("cuerno", "Tocar el cuerno", "Pone en fuga a las criaturas menores")
            )
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
        elif self.av.comando_especial and cmd == normaliza(self.av.comando_especial):
            self.aviso(self.av.texto_especial_fuera)
        elif cmd in ("atacar", "huir", "cuerno"):
            self.escribir("No hay combate aquí. Viaja con  ir <destino>.")
        else:
            self.tenue("No entiendo eso. Escribe  ayuda  para ver los comandos.")

    def _salir(self, _arg: str = "") -> None:
        self.escribir(
            "Guardas las tomillas en el bolsillo y miras atrás una vez. Hasta pronto."
        )
        self.fin = True

    def _ayuda(self, _arg: str = "") -> None:
        pantalla_completa(
            ayuda(self.av), entrada=self.entrada, salida=self.salida, color=self.color
        )

    # ── mirar / estado / inventario ──────────────────────────────────
    def _mirar(self, _arg: str = "", limpiar: bool = True) -> None:
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
        lista = ", ".join(
            f"{i + 1}) {n} ({p})" for i, (_d, p, n) in enumerate(self.destinos(lugar))
        )
        self.escribir(f"Puedes ir a: {lista}")

    def _estado(self, _arg: str = "") -> None:
        j = self.jugador
        ficha = self.av.personajes[self.personaje]
        self.epico(f"\n— {j.nombre} · {ficha.titulo} —")
        self.escribir(
            f"Vida: {j.vida}/{j.vida_max}   Corrupción: {j.recepcion()} {j.corrupcion}%"
        )
        self.escribir(f"Nivel: {j.nivel}   Experiencia: {j.progreso_xp()}")
        if j.envenenado:
            self.peligro(
                f"Envenenado: −{j.veneno_dano} por turno ({j.veneno_turnos} turnos)."
            )
        if j.rasgos:
            self.escribir(
                "Rasgos: "
                + " · ".join(
                    f"{RASGOS[r].nombre} ({RASGOS[r].descripcion})" for r in j.rasgos
                )
            )
        arma = self._item_equipado("arma")
        armadura = self._item_equipado("armadura")
        texto_arma = (
            f"{arma['nombre']} (+{arma['bonus']})" if arma else "tus propias manos"
        )
        texto_armadura = f"{armadura['nombre']}" if armadura else "túnica de jardinería"
        self.escribir(
            f"Arma: {texto_arma}   Armadura: {texto_armadura} (+{self.bonus_armadura()})"
        )
        self.escribir(f"Monedas: {j.monedas}   Lugar: {self.aqui().nombre}")
        if j.companeros:
            fila = ", ".join(
                f"{c.nombre} ({c.vida}/{c.vida_max})"
                if c.viva
                else f"{c.nombre} (cayó)"
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
    def _tomar(self, arg: str) -> None:
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

    def _buscar_item(self, texto: str, opciones: list[str]) -> str | None:
        t = normaliza(texto)
        for k in opciones:
            if t and (t in normaliza(self.av.items[k]["nombre"]) or t in normaliza(k)):
                return k
        return None

    def _comprar(self, arg: str) -> None:
        lugar = self.aqui()
        if not lugar.tienda:
            self.tenue("Aquí no hay tienda.")
            return
        stock = self.av.tiendas[lugar.id]
        if not arg:
            self.escribir(
                "En venta: "
                + ", ".join(
                    f"{self.av.items[k]['nombre']} ({self.av.items[k]['precio']} monedas)"
                    for k in stock
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
            self.aviso(
                f"Te faltan monedas: cuesta {precio} y llevas {self.jugador.monedas}."
            )
            return
        self.jugador.monedas -= precio
        self.adquirir(clave)
        self.stats.gasta(precio, clave)
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
            self.tenue(
                "El cuerno solo sirve en combate, cuando el peligro esté delante."
            )
        else:
            self.tenue("Eso no se usa así: ya te sirve solo por llevarlo.")

    # ── gente ────────────────────────────────────────────────────────
    def _hablar(self, arg: str) -> None:
        lugar = self.aqui()
        t = normaliza(arg)
        for npc, clave in lugar.npcs.items():
            if t and (t in normaliza(npc) or t in normaliza(clave)):
                self._limpiar()  # la conversación se ve sola (issue 36)
                self.epico("\n" + self._texto_heroe(self.av.dialogos[clave]))
                return
        self.tenue("Aquí no hay nadie con ese nombre.")

    def _reclutar(self, arg: str) -> None:
        lugar = self.aqui()
        t = normaliza(arg)
        for npc, clave in lugar.npcs.items():
            if (
                clave in self.av.reclutas
                and t
                and (t in normaliza(npc) or t in normaliza(clave))
            ):
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
            + (
                " Los caídos no despiertan aquí; busca la Torre de Belthar."
                if caidos
                else ""
            )
        )

    # ── viaje y eventos ──────────────────────────────────────────────
    def _ir(self, arg: str) -> None:
        lugar = self.aqui()
        destinos = self.destinos(lugar)
        elegido: str | None = None
        t = normaliza(arg)
        if t.isdigit():
            n = int(t)
            if 1 <= n <= len(destinos):
                elegido = destinos[n - 1][0]
        else:
            for palabra, destino_id in lugar.salidas.items():
                if t and (
                    t == normaliza(palabra)
                    or t in normaliza(self.av.lugares[destino_id].nombre)
                ):
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
        if destino.id not in self.visitados:
            self.visitados.append(destino.id)
        if self._usa_flechas():
            self._limpiar()  # la escena nueva se ve sola (issue 36)
        else:
            self.tenue("\n" + "─" * 40)  # en el relato tipeado, la raya marca la escena
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

    # ── combate ──────────────────────────────────────────────────────
    def _objetivo(self) -> Combatiente:
        vivas = self.jugador.companeras_vivas()
        if vivas and self.rng.random() < 0.5:
            return self.rng.choice(vivas)
        return self.jugador

    def _recibe(self, objetivo: Combatiente | Jugador, dano: int) -> int:
        """Aplica daño a un combatiente o al jugador (defensa según armadura)."""
        if isinstance(objetivo, Jugador):
            mitigacion = self.bonus_armadura() + self._modificador(
                "dano_recibido_menos"
            )
            efectivo = max(1, dano - mitigacion)
            self.jugador.vida = max(0, self.jugador.vida - efectivo)
            return efectivo
        return objetivo.recibir(dano)

    def _golpea(
        self, atacante: Combatiente, objetivo: Combatiente, extra: int = 3
    ) -> int:
        ataque = self.ataque_total() if atacante is self.jugador else atacante.ataque
        dano = self.rng.randint(max(1, ataque), ataque + extra)
        if atacante is self.jugador:
            dano += self._modificador("dano_extra", objetivo=objetivo)
        return self._recibe(objetivo, dano)

    def _duelo(self, enemigo: Enemigo) -> str:
        """Un enemigo por vez. Devuelve victoria | huida | muerte."""
        self.peligro(f"\n¡{enemigo.nombre} se abalanza!")
        # los estados alterados viven lo que vive el combate
        self._limpiar_estados(enemigo)
        self.stats.empieza_combate(self.lugar, enemigo.clave, enemigo.nombre)
        usos: dict[int, int] = {}  # cuántas veces usó cada habilidad
        try:
            while not self.fin:
                accion = self._turno_jugador(enemigo)
                self.stats.cuenta_turno()
                if accion == "huida":
                    return "huida"
                if accion == "cuerno":
                    self.exito(
                        f"{enemigo.nombre} huye con los demás. Combate resuelto."
                    )
                    return "victoria"
                if self.fin:
                    return "muerte"
                if not enemigo.vivo:
                    self.exito(f"{enemigo.nombre} cae y se deshace en humo pardo.")
                    return "victoria"
                # el turno del enemigo también va al bloque del duelo
                self._bloque_activo = self._usa_flechas()
                try:
                    self._turno_enemigo(enemigo, usos)
                finally:
                    self._bloque_activo = False
        finally:
            self._limpiar_estados(enemigo)
            if self.fin:  # muerte o partida suspendida: lo del bloque, al relato
                self._vuelca_bloque()
        return "muerte"

    def _limpiar_estados(self, enemigo: Enemigo) -> None:
        self.jugador.veneno_dano = self.jugador.veneno_turnos = 0
        enemigo.cargado = 0
        enemigo.texto_cargado = ""

    def _turno_enemigo(self, enemigo: Enemigo, usos: dict[int, int]) -> None:
        """El turno del enemigo: fase pendiente, veneno y su acción.

        Si el héroe cae aquí dentro, deja `fin`/`final` puestos, como el
        resto del motor.
        """
        enemigo.turno += 1
        transicion = enemigo.avanzar_fase()
        if transicion:
            self.peligro("\n" + transicion)
        if self._pica_veneno():
            return
        if enemigo.cargado:  # el golpe avisado cae sí o sí
            self._ataca_enemigo(
                enemigo,
                extra=enemigo.cargado,
                texto=enemigo.texto_cargado
                or f"{enemigo.nombre} suelta el golpe que venía tensando",
            )
            enemigo.cargado = 0
            enemigo.texto_cargado = ""
            return
        candidatos: list[object] = ["golpe"]
        pesos = [PESO_GOLPE]
        for i, hab in enumerate(enemigo.habilidades):
            if self._habilitada(enemigo, hab, usos.get(i, 0)):
                candidatos.append(i)
                pesos.append(hab.peso)
        eleccion = self.rng.choices(candidatos, pesos)[0]
        if eleccion == "golpe":
            self._ataca_enemigo(enemigo)
        else:
            self._usa_habilidad(enemigo, enemigo.habilidades[eleccion], eleccion, usos)

    def _habilitada(self, enemigo: Enemigo, hab: Habilidad, usada: int) -> bool:
        """La habilidad entra en la tómbola de este turno."""
        if hab.veces and usada >= hab.veces:
            return False
        if (
            hab.cond_vida is not None
            and enemigo.vida >= enemigo.vida_max * hab.cond_vida / 100
        ):
            return False
        if hab.cond_turnos is not None and enemigo.turno % hab.cond_turnos != 0:
            return False
        return True

    def _usa_habilidad(
        self, enemigo: Enemigo, hab: Habilidad, indice: int, usos: dict[int, int]
    ) -> None:
        """Ejecuta la habilidad elegida: cada tipo, su efecto y su texto."""
        usos[indice] = usos.get(indice, 0) + 1
        if hab.tipo == "veneno":
            self.jugador.envenenar(hab.dano, hab.turnos)
            self.peligro(
                f"{hab.texto} (−{hab.dano} por turno durante {hab.turnos} turnos)."
            )
        elif hab.tipo == "curarse":
            antes = enemigo.vida
            enemigo.curar(hab.puntos)
            self.aviso(
                f"{hab.texto} (+{enemigo.vida - antes} vida: {enemigo.vida}/{enemigo.vida_max})."
            )
        elif hab.tipo == "refuerzo":
            self.enemigos[self.lugar].append(hab.enemigo)
            nombre = self.av.enemigos[hab.enemigo]["nombre"]
            self.peligro(f"{hab.texto} ¡{nombre} entra en combate!")
        elif hab.tipo == "golpe_fuerte":
            enemigo.cargado = hab.dano_extra
            enemigo.texto_cargado = hab.texto_golpe
            self.aviso(hab.texto_aviso)

    def _pica_veneno(self) -> bool:
        """El veneno cobra su turno al empezar el del enemigo.

        Devuelve True si el héroe cayó envenenado: la partida se acaba.
        """
        j = self.jugador
        if not j.envenenado:
            return False
        j.veneno_turnos -= 1
        j.vida = max(0, j.vida - j.veneno_dano)
        self.stats.golpe_recibido(j.veneno_dano)
        self.peligro(f"El veneno arde: −{j.veneno_dano} ({j.vida}/{j.vida_max}).")
        if j.veneno_turnos <= 0:
            j.veneno_dano = j.veneno_turnos = 0
            self.tenue("El ardor del veneno se apaga.")
        if not j.vivo:
            self.aviso("\n" + self._texto_heroe(self.av.epilogo_muerte))
            self.fin = True
            self.final = "muerte"
            return True
        return False

    def _ataca_enemigo(self, enemigo: Enemigo, extra: int = 0, texto: str = "") -> None:
        """El enemigo pega a su objetivo: el golpe normal, o el cargado
        (que llega con `extra` de daño y su `texto` propio)."""
        objetivo = self._objetivo()
        dano = self.rng.randint(max(1, enemigo.ataque), enemigo.ataque + 3) + extra
        efectivo = self._recibe(objetivo, dano)
        self.stats.golpe_recibido(efectivo)
        if texto:
            linea = texto.format(efectivo=efectivo)
        elif isinstance(objetivo, Companero):
            linea = f"{enemigo.nombre} golpea a {objetivo.nombre}: −{efectivo}"
        else:
            linea = f"{enemigo.nombre} te golpea: −{efectivo}"
        if isinstance(objetivo, Companero):
            self.peligro(f"{linea} ({objetivo.vida}/{objetivo.vida_max}).")
            if not objetivo.vivo:
                objetivo.viva = False
                self.peligro(f"{objetivo.nombre} cae…")
        else:
            self.peligro(f"{linea} ({self.jugador.vida}/{self.jugador.vida_max}).")
            if not self.jugador.vivo:
                self.aviso("\n" + self._texto_heroe(self.av.epilogo_muerte))
                self.fin = True
                self.final = "muerte"

    def _turno_jugador(self, enemigo: Enemigo) -> str:
        """Acción del jugador y contraataque de los compañeros.

        Devuelve: "seguir" (turno normal), "huida" o "cuerno" (combate resuelto).
        """
        especial = (
            normaliza(self.av.comando_especial) if self.av.comando_especial else None
        )
        while True:
            try:
                linea = self._leer_orden(
                    self._titulo_combate(enemigo),
                    self._c("combate> ", DIM),
                    self._opciones_combate(enemigo),
                    aviso_esc="En combate no hay vuelta atrás: lucha, usa algo o huye.",
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
            # el turno se anota en el bloque del duelo, no en el relato
            self._bloque_activo = self._usa_flechas()
            try:
                if cmd == "atacar":
                    efectivo = self._golpea(self.jugador, enemigo)
                    self.stats.golpe_infligido(efectivo)
                    self.escribir(
                        f"Golpeas a {enemigo.nombre}: −{efectivo} ({enemigo.vida}/{enemigo.vida_max})."
                    )
                elif cmd == "usar":
                    clave = self._buscar_item(arg, self.jugador.inventario)
                    if clave and self.av.items[clave]["tipo"] == "consumible":
                        self.jugador.inventario.remove(clave)
                        antes = self.jugador.vida
                        curacion = round(
                            self.av.items[clave]["curacion"] * self.dificultad.curacion
                        )
                        self.jugador.curar(curacion)
                        self.exito(
                            f"{self.av.items[clave]['nombre']}: vida {antes} → {self.jugador.vida}."
                        )
                    else:
                        self.tenue("Eso no se puede usar en combate.")
                        continue
                elif especial and cmd == especial and self.av.ataque_especial:
                    # el daño del especial ocurre dentro del evento: se mide
                    # por la vida que pierde el enemigo en la llamada
                    antes = enemigo.vida
                    self.av.ataque_especial(self, enemigo)
                    self.stats.golpe_infligido(antes - enemigo.vida)
                    if self.fin:
                        return "seguir"
                elif cmd == "cuerno":
                    clave = next(
                        (
                            k
                            for k in self.jugador.inventario
                            if self.av.items[k]["tipo"] == "cuerno"
                        ),
                        None,
                    )
                    if clave:
                        if enemigo.sin_huida:
                            self.aviso("El toque resuena… y el guardián ni parpadea.")
                            continue
                        self.jugador.inventario.remove(clave)
                        self.epico(
                            "El cuerno retumba en el aire: las criaturas menores huyen despavoridas."
                        )
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
                    self.stats.golpe_infligido(efectivo)
                    self.escribir(
                        f"{c.nombre} ataca: −{efectivo} ({enemigo.vida}/{enemigo.vida_max})."
                    )
                    if not enemigo.vivo:
                        break
            finally:
                self._bloque_activo = False
            return "seguir"

    def _combate(self) -> None:
        """Resuelve los duelos del lugar, uno a uno, mientras haya cola.

        Los refuerzos que entren en plena pelea se suman a la cola y
        también pelean antes de que el lugar quede libre.
        """
        self.en_combate = True
        pendientes = self.enemigos[self.lugar]
        while pendientes and not self.fin:
            clave = pendientes[0]
            enemigo = self.crear_enemigo(clave)
            resultado = self._duelo(enemigo)
            self.stats.cierra_combate(resultado)
            if self.fin:
                break
            if resultado == "victoria":
                # el cuerno vacía la cola entera: ya no está quien huyó
                if clave in pendientes:
                    pendientes.remove(clave)
                    self.derrotados.append(clave)
                self._conceder_experiencia(clave)
                if not pendientes:
                    self.exito("El aire vuelve a moverse. El camino queda libre.")
            else:  # huida
                self.lugar = self.lugar_previo
                self.aviso(
                    f"Vuelves a {self.av.lugares[self.lugar].nombre}. Los enemigos siguen ahí, esperando."
                )
                break
        self.en_combate = False

    def _conceder_experiencia(self, clave: str) -> None:
        """La XP del caído y, si toca, las subidas de nivel."""
        base = self.av.enemigos[clave].get("experiencia", 0)
        if base <= 0:
            return
        j = self.jugador
        j.experiencia += ajusta(base, self.dificultad.experiencia)
        self.exito(f"Ganas experiencia: {j.experiencia}.")
        while j.nivel <= len(XP_NIVEL) and j.experiencia >= XP_NIVEL[j.nivel - 1]:
            j.nivel += 1
            j.ataque += SUBIDA_ATAQUE
            j.vida_max += SUBIDA_VIDA
            j.curar(SUBIDA_VIDA)  # el aliento nuevo llega con vida nueva
            self.epico(
                f"\n¡{j.nombre} alcanza el nivel {j.nivel}! (+{SUBIDA_ATAQUE} ataque, +{SUBIDA_VIDA} vida máxima)"
            )

    # ── guardar / cargar ─────────────────────────────────────────────
    def _guardar(self, arg: str = "") -> None:
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
                {"clave": c.clave, "vida": c.vida, "viva": c.viva}
                for c in self.jugador.companeros
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
            j.companeros.append(
                Companero(**{**base.__dict__, "vida": c["vida"], "viva": c["viva"]})
            )
        self.lugar = estado["lugar"]
        self.lugar_previo = estado["lugar_previo"]
        self.flags = dict(estado["flags"])
        # un guardado de una edición anterior del juego puede traer menos
        # lugares que la aventura de hoy: los faltantes recuperan sus
        # enemigos originales (esto es evolución del contenido, no del
        # esquema, y por eso no lo lleva la migración)
        guardados = {k: list(v) for k, v in estado["enemigos"].items()}
        self.enemigos = {
            lid: guardados.get(lid, list(lugar.enemigos))
            for lid, lugar in self.av.lugares.items()
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

    def _cargar(self, arg: str = "") -> None:
        ruta = arg.strip() or ARCHIVO_PARTIDA
        try:
            estado = guardado.cargar(ruta)
        except PartidaInvalida as e:
            self.peligro(str(e))
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
        audio: bool = True,
    ) -> "Juego":
        """Construye una partida a partir de un archivo de guardado."""
        estado = guardado.cargar(ruta)
        juego = cls(
            aventura=obtener_aventura(estado.get("aventura")),
            dificultad=obtener_dificultad(estado.get("dificultad")),
            personaje=estado.get("personaje"),
            semilla=semilla,
            entrada=entrada,
            salida=salida,
            color=color,
            flechas=flechas,
            audio=audio,
        )
        juego._aplicar_estado(estado, ruta)
        return juego


def ayuda_combate(av: Aventura) -> str:
    """Recordatorio de comandos de combate para la línea de órdenes."""
    especial = f" · {av.comando_especial}" if av.comando_especial else ""
    return f"En combate: atacar · usar <cosa>{especial} · cuerno · huir · estado"


def _escribir_legado(juego: "Juego", ruta: str, salida) -> None:
    """Al terminar una aventura (final con nombre), escribe su legado.

    Las muertes, caídas y partidas suspendidas no dejan legado: la serie
    recuerda lo que se contó, no lo que se quedó a medias.
    """
    if not juego.av.legado.exporta:
        return
    if juego.final in (None, "muerte", "caida", "suspendida"):
        return
    try:
        modulo_legado.escribir(juego.av, juego, ruta)
    except OSError as e:
        salida(f"No se pudo escribir el legado: {e}")


def main(
    argv: list[str] | None = None,
    *,
    entrada=input,
    salida=print,
    legado_ruta: str | None = None,
) -> None:
    parser = argparse.ArgumentParser(
        prog="aldamar",
        description="Aldamar: aventuras de fantasía épica para la terminal.",
    )
    parser.add_argument(
        "--semilla",
        type=int,
        default=None,
        help="semilla aleatoria para partidas reproducibles",
    )
    parser.add_argument(
        "--sin-color", action="store_true", help="desactivar colores ANSI"
    )
    parser.add_argument(
        "--sin-flechas",
        action="store_true",
        help="menús respondiendo a texto, sin flechas del teclado",
    )
    parser.add_argument(
        "--sin-audio",
        action="store_true",
        help="sin jingle en la presentación y en el cierre",
    )
    parser.add_argument(
        "--sin-splash",
        action="store_true",
        help="sin pantalla de presentación: directo al menú",
    )
    parser.add_argument(
        "--cargar",
        nargs="?",
        const=ARCHIVO_PARTIDA,
        metavar="ARCHIVO",
        help="cargar una partida guardada",
    )
    parser.add_argument(
        "--aventura",
        choices=sorted(AVENTURAS),
        default=None,
        help="aventura a jugar (salta el menú)",
    )
    parser.add_argument(
        "--dificultad",
        choices=sorted(DIFICULTADES),
        default=None,
        help="dificultad del balance",
    )
    parser.add_argument(
        "--personaje", default=None, help="héroe inicial de la aventura"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="conservar lo que el lanzador escribió antes del juego (informe del build de uv, avisos)",
    )
    parser.add_argument(
        "--legado",
        default=None,
        metavar="ARCHIVO",
        help=f"archivo de legado de la serie ({modulo_legado.ARCHIVO_LEGADO} por defecto)",
    )
    parser.add_argument(
        "--stats",
        nargs="?",
        const=ARCHIVO_ESTADISTICAS,
        default=None,
        metavar="ARCHIVO",
        help=f"escribir estadísticas de la partida al terminar ({ARCHIVO_ESTADISTICAS} por defecto)",
    )
    parser.add_argument("--version", action="version", version=f"aldamar {__version__}")
    args = parser.parse_args(argv)
    # Las preferencias (issue 34): el archivo configuracion.json trae lo
    # suyo, y sobre él mandan la variable de entorno y el flag de CLI.
    config = configuracion.cargar()
    if opciones._es_interactivo(entrada, salida):
        # solo una sesión de verdad estrena el archivo: ni tests ni
        # tuberías dejan un configuracion.json nuevo a su paso
        try:
            configuracion.asegurar()
        except OSError:
            pass  # un archivo que no nace no impide jugar
    if args.debug:
        debug = True
    elif "ALDAMAR_DEBUG" in os.environ:
        debug = os.environ["ALDAMAR_DEBUG"] not in ("", "0")
    else:
        debug = config.debug
    audio = config.audio and not args.sin_audio
    color = False if (args.sin_color or not config.color) else None
    flechas = False if (args.sin_flechas or not config.flechas) else None
    semilla = args.semilla if args.semilla is not None else config.semilla
    color_menu = (
        bool(color)
        if color is not None
        else hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
    )
    ruta_legado = legado_ruta or args.legado or modulo_legado.ARCHIVO_LEGADO
    ruta_stats = args.stats
    # lo que la serie recuerda de partidas anteriores (issue 19); si el
    # archivo falta o está roto, se juega igual, solo que sin memoria
    datos_legado = modulo_legado.leer(ruta_legado)

    # El lanzador (uv y compañía) cuenta su build en pantalla antes de que
    # el juego empiece, y el informe queda mezclado con el relato. Salvo
    # en modo debug, arrancamos limpios; en tuberías y tests, sin códigos.
    interactivo = _es_interactivo(entrada, salida)
    if not debug and interactivo:
        salida(LIMPIAR)

    # La presentación (issue 34): sello, jingle y una tecla. Solo en
    # sesiones de verdad y cuando el arranque pasa por el menú; los
    # atajos (--cargar, aventura y dificultad por CLI) van directos.
    presenta = (
        interactivo
        and config.splash
        and not args.sin_splash
        and not args.cargar
        and not (args.aventura and args.dificultad)
    )

    def _partida_del_menu() -> Juego | None:
        """La partida que nace del menú principal; None si no se juega."""
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
            return None
        if eleccion.accion == "cargar":
            return Juego.desde_archivo(
                eleccion.archivo or ARCHIVO_PARTIDA,
                semilla=semilla,
                entrada=entrada,
                salida=salida,
                color=color,
                flechas=flechas,
                audio=audio,
            )
        return Juego(
            aventura=eleccion.aventura,
            dificultad=eleccion.dificultad,
            personaje=eleccion.personaje,
            semilla=semilla,
            entrada=entrada,
            salida=salida,
            color=color,
            flechas=flechas,
            legado=datos_legado,
            audio=audio,
        )

    # Bucle de sesión: menú → partida → pantalla de cierre → menú…
    # el proceso vive hasta que el jugador elige salir de verdad.
    try:
        if presenta:
            presentacion.presentar(
                entrada=entrada, salida=salida, color=color_menu, sonar=audio
            )
        if args.cargar:
            juego = Juego.desde_archivo(
                args.cargar,
                semilla=semilla,
                entrada=entrada,
                salida=salida,
                color=color,
                flechas=flechas,
                audio=audio,
            )
        elif args.aventura and args.dificultad:
            # todo definido por CLI: ni menú
            juego = Juego(
                aventura=obtener_aventura(args.aventura),
                dificultad=obtener_dificultad(args.dificultad),
                personaje=args.personaje,
                semilla=semilla,
                entrada=entrada,
                salida=salida,
                color=color,
                flechas=flechas,
                legado=datos_legado,
                audio=audio,
            )
        else:
            juego = _partida_del_menu()
        while juego is not None:
            eleccion = juego.ciclo()
            if ruta_stats:
                # la sesión deja sus números antes de decidir «¿y ahora qué?»
                try:
                    juego.stats.escribir(juego, ruta_stats)
                    salida(f"Estadísticas de la partida en {ruta_stats}.")
                except OSError as e:
                    salida(f"No se pudieron escribir las estadísticas: {e}")
            _escribir_legado(juego, ruta_legado, salida)
            if eleccion == "otra":
                # nueva partida al instante: misma aventura, héroe y
                # dificultad, y el nombre puesto se conserva
                juego = Juego(
                    aventura=juego.av,
                    dificultad=juego.dificultad,
                    personaje=juego.personaje,
                    nombre=juego.jugador.nombre,
                    semilla=semilla,
                    entrada=entrada,
                    salida=salida,
                    color=color,
                    flechas=flechas,
                    legado=datos_legado,
                    audio=audio,
                )
            elif eleccion == "menu":
                juego = _partida_del_menu()
            else:
                juego = None
    except KeyboardInterrupt:
        salida("\nEl viso cae sobre Aldamar. Partida suspendida.")
    except PartidaInvalida as e:
        salida(str(e))
    except (OSError, json.JSONDecodeError) as e:
        salida(f"No se pudo abrir la partida: {e}")
    except KeyError as e:
        salida(f"Opción desconocida: {e}")

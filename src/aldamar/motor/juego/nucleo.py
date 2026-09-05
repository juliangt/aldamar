"""El núcleo del juego: la clase `Juego`, su estado y su ciclo.

`Juego` es una sola clase; sus métodos viven repartidos en módulos por
responsabilidad (`salida`, `equipo`, `combate`, `acciones`,
`navegación`, `persistencia`) y se ensamblan aquí abajo como métodos
de clase. Cada función declara `self: Juego`, de modo que mypy la
revisa contra el estado que `__init__` crea. El motor es agnóstico de
la aventura: todo el contenido llega en el objeto `Aventura` y el
balance en la `Dificultad` elegida; los eventos narrativos de cada
lugar y el golpe especial de combate son efectos del vocabulario
declarativo (`eventos.py`) que cada aventura declara en su JSON (que
`cargador.py` valida y convierte en funciones).
"""

from __future__ import annotations

import random
import sys
from typing import TYPE_CHECKING

from ...contenido.aventura import Aventura
from .. import guardado
from .. import legado as modulo_legado
from ..dificultad import Dificultad, obtener_dificultad
from ..estadisticas import Estadisticas
from . import acciones, combate, equipo, navegacion, persistencia, salida
from .constantes import DIM

if TYPE_CHECKING:
    from ...viva.sesion import SesionViva


class Juego:
    """Una partida en marcha: héroe, lugar, cola de enemigos y pantalla.

    El estado lo crea `__init__`; el comportamiento vive en los módulos
    hermanos, ensamblado aquí como métodos. La superficie pública —
    `ciclo`, `desde_archivo`, los verbos que los eventos pueden llamar—
    no cambia: `aldamar.motor.juego` reexporta todo.
    """

    # ── salida con color ─────────────────────────────────────────
    _c = salida._c
    escribir = salida.escribir
    epico = salida.epico
    exito = salida.exito
    peligro = salida.peligro
    aviso = salida.aviso
    tenue = salida.tenue
    _texto_heroe = salida._texto_heroe
    _usa_flechas = salida._usa_flechas
    _estado_linea = salida._estado_linea
    _cabecera = salida._cabecera
    _activa_marco = salida._activa_marco
    _desactiva_marco = salida._desactiva_marco
    _limpiar = salida._limpiar
    _barra = salida._barra
    _vuelca_bloque = salida._vuelca_bloque
    _prologo = salida._prologo
    _remate = salida._remate
    _texto_cierre = salida._texto_cierre
    _cierre = salida._cierre

    # ── equipo derivado ──────────────────────────────────────────
    _item_equipado = equipo._item_equipado
    bonus_arma = equipo.bonus_arma
    bonus_armadura = equipo.bonus_armadura
    ataque_total = equipo.ataque_total
    _modificador = equipo._modificador
    _autoequipar = equipo._autoequipar
    adquirir = equipo.adquirir
    _equipar = equipo._equipar
    _desequipar = equipo._desequipar
    _opciones_equipo = equipo._opciones_equipo

    # ── combate ──────────────────────────────────────────────────
    _titulo_combate = combate._titulo_combate
    _objetivo = combate._objetivo
    _recibe = combate._recibe
    _golpea = combate._golpea
    _duelo = combate._duelo
    _limpiar_estados = combate._limpiar_estados
    _turno_enemigo = combate._turno_enemigo
    _habilitada = combate._habilitada
    _usa_habilidad = combate._usa_habilidad
    _pica_veneno = combate._pica_veneno
    _ataca_enemigo = combate._ataca_enemigo
    _turno_jugador = combate._turno_jugador
    _combate = combate._combate
    _conceder_experiencia = combate._conceder_experiencia

    # ── acciones de mundo ────────────────────────────────────────
    aqui = acciones.aqui
    crear_enemigo = acciones.crear_enemigo
    restantes = acciones.restantes
    destinos = acciones.destinos
    corruptear = acciones.corruptear
    _mirar = acciones._mirar
    _estado = acciones._estado
    _inventario = acciones._inventario
    _tomar = acciones._tomar
    _buscar_item = acciones._buscar_item
    _comprar = acciones._comprar
    _usar = acciones._usar
    _hablar = acciones._hablar
    _reclutar = acciones._reclutar
    _descansar = acciones._descansar
    _ir = acciones._ir
    _entrar = acciones._entrar
    _buscar_secreto = acciones._buscar_secreto
    _ejecutar_secreto = acciones._ejecutar_secreto

    # ── navegación y despacho ────────────────────────────────────
    _pista = navegacion._pista
    _leer_orden = navegacion._leer_orden
    _opciones_juego = navegacion._opciones_juego
    _entrada_usar = navegacion._entrada_usar
    _cuenta_tomar = navegacion._cuenta_tomar
    _submenu = navegacion._submenu
    _opciones_otras = navegacion._opciones_otras
    _opciones_combate = navegacion._opciones_combate
    _ejecutar = navegacion._ejecutar
    _salir = navegacion._salir
    _ayuda = navegacion._ayuda

    # ── guardar / cargar ─────────────────────────────────────────
    _guardar = persistencia._guardar
    _aplicar_estado = persistencia._aplicar_estado
    _cargar = persistencia._cargar

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
        viva: SesionViva | None = None,
    ) -> None:
        self.av = aventura
        self.dificultad = dificultad or obtener_dificultad()
        self.personaje = personaje or aventura.jugador_inicial
        self.rng = random.Random(semilla)
        self.semilla = semilla
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
        self.flags: dict[str, bool | int] = {}
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
        self.epilogo: str | None = None  # el texto del final, para la pantalla de cierre
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
        # el modo «Aventura Viva»: None en las partidas
        # clásicas; su sesión rellena lugares al pisarlos y viaja en el
        # guardado bajo la clave "viva"
        self.viva = viva

    # ── ciclo principal ──────────────────────────────────────────
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
                    linea = self._leer_orden("¿Qué haces?", self._c("> ", DIM), self._opciones_juego())
                except EOFError:
                    linea = "salir"
                self._ejecutar(linea)
            if self.final:
                return self._cierre()
            return None
        finally:
            self._desactiva_marco()

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
    ) -> Juego:
        """Construye una partida a partir de un archivo de guardado."""
        from .persistencia import _aventura_del_guardado

        estado = guardado.cargar(ruta)
        juego = cls(
            aventura=_aventura_del_guardado(estado, ruta),
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

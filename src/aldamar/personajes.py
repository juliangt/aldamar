"""Modelos de personajes: jugador, compañeros y enemigos.

Aquí vive también el vocabulario de combate declarado en el JSON:
las `Habilidad` de los enemigos y las `Fase` de los jefes, que el
cargador valida y `aventura.crear_enemigo` convierte en objetos.

Semilla de diseño (aún sin implementar): la corrupción y la progresión
están llamadas a cruzarse — niveles que dejan grieta, o el final
«Sombra nueva» potenciado por el nivel alcanzado. El modelo de abajo
no los mezcla todavía, pero tampoco lo impediría.
"""

from __future__ import annotations

from dataclasses import dataclass, field

CORRUPCION_MAXIMA = 100
CORRUPCION_TENTADO = 60

# ── progresión ───────────────────────────────────────────────────────────
# Curva corta y explícita: experiencia acumulada necesaria para alcanzar
# el nivel 2, 3, 4 y 5. La campaña es de una sesión: no hay nivel 6.
XP_NIVEL: tuple[int, ...] = (30, 80, 150, 240)
SUBIDA_ATAQUE = 1  # por nivel
SUBIDA_VIDA = 8  # por nivel (y se cura lo mismo: subir da aliento)

# ── habilidades de enemigo ───────────────────────────────────────────────
TIPOS_HABILIDAD = {"veneno", "curarse", "refuerzo", "golpe_fuerte"}


@dataclass(frozen=True)
class Habilidad:
    """Una técnica de enemigo declarada en el JSON.

    Campos comunes: `texto` (lo que se lee al activarse), `peso` (frente
    a cuánto tira el golpe normal) y `cond_vida`/`cond_turnos`
    (solo con la vida por debajo de un %, o solo en turnos múltiplos
    de N). El resto depende del tipo.
    """

    tipo: str
    texto: str = ""
    dano: int = 0  # veneno: daño por turno
    turnos: int = 0  # veneno: duración en turnos
    puntos: int = 0  # curarse: vida que recupera
    enemigo: str = ""  # refuerzo: clave del convocado
    veces: int = 1  # refuerzo: cuántas veces puede llamar por combate
    dano_extra: int = 0  # golpe_fuerte: daño extra del golpe cargado
    texto_aviso: str = ""  # golpe_fuerte: la telegrafía
    texto_golpe: str = ""  # golpe_fuerte: el golpe en sí
    peso: int = 1
    cond_vida: int | None = None  # % de vida_max por debajo del cual se activa
    cond_turnos: int | None = None  # solo en turnos múltiplos de N


def habilidad_desde(datos: dict) -> Habilidad:
    """Arma una Habilidad desde el dict del JSON (ya validado)."""
    condicion = datos.get("condicion") or {}
    return Habilidad(
        tipo=datos["tipo"],
        texto=datos.get("texto", ""),
        dano=datos.get("dano", 0),
        turnos=datos.get("turnos", 0),
        puntos=datos.get("puntos", 0),
        enemigo=datos.get("enemigo", ""),
        veces=datos.get("veces", 1),
        dano_extra=datos.get("dano_extra", 0),
        texto_aviso=datos.get("texto_aviso", ""),
        texto_golpe=datos.get("texto_golpe", ""),
        peso=datos.get("peso", 1),
        cond_vida=condicion.get("vida_menor_que"),
        cond_turnos=condicion.get("cada_n_turnos"),
    )


@dataclass(frozen=True)
class Fase:
    """Un tramo de la vida de un jefe: al cruzar el umbral, cambia la ficha.

    `umbral` es un % de vida_max: por debajo de ahí, la fase entra en
    escena con su texto de transición. Campos None conservan lo que haya;
    `habilidades` vacío conserva las vigentes.
    """

    umbral: int
    texto: str
    nombre: str | None = None
    ataque: int | None = None
    defensa: int | None = None
    habilidades: tuple[Habilidad, ...] = ()


def fase_desde(datos: dict) -> Fase:
    """Arma una Fase desde el dict del JSON (ya validado)."""
    return Fase(
        umbral=datos["vida_menor_que"],
        texto=datos["texto"],
        nombre=datos.get("nombre"),
        ataque=datos.get("ataque"),
        defensa=datos.get("defensa"),
        habilidades=tuple(habilidad_desde(h) for h in datos.get("habilidades", [])),
    )


@dataclass
class Combatiente:
    """Base de todo el que puede pelear.

    Los estados alterados son mínimos y duran lo que dure el combate:
    `veneno_dano`/`veneno_turnos` muerden al inicio del turno envenenado.
    """

    nombre: str
    vida: int
    vida_max: int
    ataque: int
    defensa: int = 0
    veneno_dano: int = 0
    veneno_turnos: int = 0

    @property
    def vivo(self) -> bool:
        return self.vida > 0

    @property
    def envenenado(self) -> bool:
        return self.veneno_turnos > 0 and self.veneno_dano > 0

    def envenenar(self, dano: int, turnos: int) -> None:
        """Renueva el veneno: el más reciente manda."""
        self.veneno_dano = max(self.veneno_dano, dano)
        self.veneno_turnos = max(self.veneno_turnos, turnos)

    def recibir(self, dano: int) -> int:
        """Aplica daño tras la defensa; devuelve el daño efectivo."""
        efectivo = max(1, dano - self.defensa)
        self.vida = max(0, self.vida - efectivo)
        return efectivo

    def curar(self, puntos: int) -> None:
        self.vida = min(self.vida_max, self.vida + max(0, puntos))


@dataclass
class Enemigo(Combatiente):
    """Criatura hostil controlada por el juego.

    `habilidades` y `fases` llegan del JSON (validado por el cargador);
    `fase_actual` es −1 mientras pelea con su ficha base. `cargado`
    guarda el daño extra del golpe telegrafiado pendiente.
    """

    clave: str = ""
    sin_huida: bool = False  # los guardianes no dejan escapar
    habilidades: tuple[Habilidad, ...] = ()
    fases: tuple[Fase, ...] = ()  # umbrales de mayor a menor
    fase_actual: int = -1
    cargado: int = 0  # daño extra del golpe telegrafiado pendiente
    texto_cargado: str = ""  # el texto con que ese golpe caerá
    turno: int = 0  # contador de turnos propios, para las condiciones «cada N»

    def avanzar_fase(self) -> str | None:
        """Cruza al siguiente umbral pendiente si la vida cayó lo bastante.

        Devuelve el texto de la transición, o None si sigue en la misma
        fase. Las fases solo se cruzan hacia delante: curarse no deshace
        una ya estrenada.
        """
        siguiente = self.fase_actual + 1
        if siguiente >= len(self.fases):
            return None
        fase = self.fases[siguiente]
        if self.vida >= self.vida_max * fase.umbral / 100:
            return None
        self.fase_actual = siguiente
        if fase.nombre:
            self.nombre = fase.nombre
        if fase.ataque is not None:
            self.ataque = fase.ataque
        if fase.defensa is not None:
            self.defensa = fase.defensa
        if fase.habilidades:
            self.habilidades = fase.habilidades
        return fase.texto


@dataclass
class Companero:
    """Aliado que viaja y pelea con el jugador."""

    clave: str
    nombre: str
    vida: int
    vida_max: int
    ataque: int
    defensa: int = 0
    viva: bool = True

    @property
    def vivo(self) -> bool:
        return self.vida > 0

    def recibir(self, dano: int) -> int:
        efectivo = max(1, dano - self.defensa)
        self.vida = max(0, self.vida - efectivo)
        return efectivo

    def como_combatiente(self) -> Combatiente:
        return Combatiente(self.nombre, self.vida, self.vida_max, self.ataque, self.defensa)


@dataclass
class Jugador:
    """El héroe elegido: lleva los rasgos de su ficha sobre sus hombros.

    La progresión de una campaña cabe en dos campos: `experiencia`
    acumulada y `nivel` (1..len(XP_NIVEL) + 1). El equipamiento es lo
    que declara `equipado` —clave de item por tipo—, no «lo mejor del
    inventario»: llevar y llevar puesto son decisiones distintas.
    """

    nombre: str
    vida: int = 45
    vida_max: int = 45
    ataque: int = 4
    corrupcion: int = 0
    monedas: int = 10
    inventario: list[str] = field(default_factory=list)
    companeros: list[Companero] = field(default_factory=list)
    rasgos: list[str] = field(default_factory=list)  # claves de RASGOS
    veneno_dano: int = 0
    veneno_turnos: int = 0
    experiencia: int = 0
    nivel: int = 1
    equipado: dict[str, str] = field(default_factory=dict)  # tipo -> clave de item

    @property
    def vivo(self) -> bool:
        return self.vida > 0

    @property
    def envenenado(self) -> bool:
        return self.veneno_turnos > 0 and self.veneno_dano > 0

    def envenenar(self, dano: int, turnos: int) -> None:
        self.veneno_dano = max(self.veneno_dano, dano)
        self.veneno_turnos = max(self.veneno_turnos, turnos)

    def companeras_vivas(self) -> list[Companero]:
        return [c for c in self.companeros if c.viva]

    def curar(self, puntos: int) -> None:
        self.vida = min(self.vida_max, self.vida + max(0, puntos))

    def corruptear(self, puntos: int) -> None:
        self.corrupcion = max(0, min(CORRUPCION_MAXIMA, self.corrupcion + puntos))

    def recepcion(self) -> str:
        """Barra de corrupción para el estado."""
        lleno = round(self.corrupcion / 10)
        return "[" + "▓" * lleno + "░" * (10 - lleno) + "]"

    def progreso_xp(self) -> str:
        """Cuánto falta para el nivel siguiente, en texto de estado."""
        if self.nivel > len(XP_NIVEL):
            return f"{self.experiencia} (nivel máximo)"
        return f"{self.experiencia}/{XP_NIVEL[self.nivel - 1]}"

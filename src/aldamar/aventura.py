"""El contrato de una aventura: todo el contenido de una campaña en un objeto.

El motor (`juego.py`) no conoce ninguna aventura concreta: lee mapa,
objetos, criaturas, textos y eventos desde aquí. Sumar una aventura
nueva = definir un `Aventura` en `aventuras/` y registrarlo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

from .dificultad import Dificultad, ajusta
from .mundo import Lugar
from .personajes import RASGOS, Companero, Enemigo, Jugador

if TYPE_CHECKING:  # solo para anotaciones; evita import circular en runtime
    from .juego import Juego

# Un evento de lugar recibe (juego, lugar) y hace su magia narrativa.
Evento = Callable[["Juego", Lugar], None]
# Un golpe especial de combate recibe (juego, enemigo).
AtaqueEspecial = Callable[["Juego", Enemigo], None]


@dataclass
class PersonajeInicial:
    """Ficha de un héroe con el que se puede empezar la aventura.

    Además de las estadísticas, cada héroe puede traer rasgos (claves de
    `RASGOS`) y su propia voz: prólogo, pregunta del nombre y los apodos
    con los que los textos se dirigen a él o hablan de él.
    """

    clave: str
    nombre: str
    titulo: str  # quién es, p.ej. "falro jardinero de Vegaverde"
    presentacion: str  # texto que se lee tras elegir el nombre
    vida: int = 45
    ataque: int = 4
    monedas: int = 10
    inventario: list[str] = field(default_factory=list)  # claves de items
    rasgos: list[str] = field(default_factory=list)  # claves de RASGOS
    prologo: str | None = None  # None = el prólogo de la aventura
    texto_nombre: str | None = None  # None = el de la aventura ({nombre})
    trato: str = "caminante"  # cómo te hablan: "jardinero", "arquera"…
    quien: str = "el caminante"  # cómo dicen de ti en los cantares, con artículo


@dataclass
class Aventura:
    id: str
    titulo: str
    descripcion: str  # línea para el menú
    prologo: str
    texto_nombre: str  # pregunta del nombre; {nombre} es el del héroe elegido
    lugares: dict[str, Lugar]
    lugar_inicial: str
    items: dict[str, dict]
    enemigos: dict[str, dict]
    reclutas: dict[str, Companero]
    tiendas: dict[str, list[str]]
    dialogos: dict[str, str]
    personajes: dict[str, PersonajeInicial]
    jugador_inicial: str
    epilogo_muerte: str  # lo que el motor muestra si caes en combate
    epilogo_caida: str  # lo que muestra si la corrupción te consume
    # Los textos de prólogo, diálogos y epílogos pueden usar {trato} y
    # {quien}: se sustituyen por los apodos del héroe elegido.
    comando_especial: str | None = None  # p.ej. "corazon"; None = sin especial
    texto_especial_fuera: str = ""
    ataque_especial: AtaqueEspecial | None = None
    # eventos por clave de Lugar.evento; el evento "final" se dispara
    # cuando el lugar queda limpio de enemigos, el resto al entrar.
    eventos: dict[str, Evento] = field(default_factory=dict)

    def crear_enemigo(self, clave: str, dif: Dificultad) -> Enemigo:
        d = self.enemigos[clave]
        return Enemigo(
            clave=clave,
            nombre=d["nombre"],
            vida=ajusta(d["vida"], dif.vida_enemigos),
            vida_max=ajusta(d["vida"], dif.vida_enemigos),
            ataque=ajusta(d["ataque"], dif.ataque_enemigos),
            defensa=d.get("defensa", 0),
            sin_huida=d.get("sin_huida", False),
        )

    def crear_jugador(self, clave: str | None, dif: Dificultad) -> Jugador:
        clave = clave or self.jugador_inicial
        if clave not in self.personajes:
            raise KeyError(
                f"{self.titulo} no tiene al personaje {clave!r}; "
                f"disponibles: {', '.join(self.personajes)}"
            )
        f = self.personajes[clave]
        desconocidos = [r for r in f.rasgos if r not in RASGOS]
        if desconocidos:
            raise ValueError(
                f"{f.nombre} tiene rasgos desconocidos: {', '.join(desconocidos)}; "
                f"válidos: {', '.join(RASGOS)}"
            )
        return Jugador(
            nombre=f.nombre,
            vida=ajusta(f.vida, dif.vida_jugador),
            vida_max=ajusta(f.vida, dif.vida_jugador),
            ataque=ajusta(f.ataque, dif.ataque_jugador),
            monedas=ajusta(f.monedas, dif.monedas),
            inventario=list(f.inventario),
            rasgos=list(f.rasgos),
        )


# ── Registro de aventuras conocidas ─────────────────────────────────────
# Los módulos de contenido se autorregistran al importarse; el paquete
# `aldamar.aventuras` importa los conocidos.
AVENTURAS: dict[str, Aventura] = {}


def registrar(av: Aventura) -> None:
    if av.id in AVENTURAS:
        raise ValueError(f"La aventura {av.id!r} ya está registrada")
    AVENTURAS[av.id] = av


def obtener_aventura(clave: str | None = None) -> Aventura:
    """Resuelve una aventura por clave; None devuelve la primera registrada."""
    if clave is None:
        if not AVENTURAS:
            raise KeyError("No hay aventuras registradas")
        return next(iter(AVENTURAS.values()))
    if clave not in AVENTURAS:
        raise KeyError(
            f"No existe la aventura {clave!r}; registradas: {', '.join(AVENTURAS)}"
        )
    return AVENTURAS[clave]

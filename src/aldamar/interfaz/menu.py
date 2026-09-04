"""Menú principal interactivo y ayuda, sin dependencias externas.

`menu_principal` orquesta el arranque (nueva partida con
aventura/personaje/dificultad, cargar, ayuda, salir) y devuelve una
`Eleccion` que `juego.main` convierte en partida. La selección de
opciones vive en `opciones.py`: con teclado real se navega con flechas.
"""

from __future__ import annotations

from dataclasses import dataclass

from .. import datos  # noqa: F401  (garantiza el registro del contenido)
from ..contenido.aventura import AVENTURAS, Aventura, obtener_aventura
from ..motor.dificultad import DIFICULTADES, Dificultad, obtener_dificultad
from .opciones import (
    LIMPIAR,
    _es_interactivo,
    elegir_opcion,
    pantalla_completa,
)

ARCHIVO_PARTIDA = "partida.json"

TITULO, AMARILLO, DIM = "1;36", "33", "2"


def _c(texto: str, color: bool, *codigos: str) -> str:
    if not color or not codigos:
        return texto
    return "\033[" + ";".join(codigos) + "m" + texto + "\033[0m"


@dataclass
class Eleccion:
    """Lo que el menú principal decide: nueva partida, cargar o salir."""

    accion: str  # "nueva" | "cargar" | "salir"
    aventura: Aventura | None = None
    dificultad: Dificultad | None = None
    personaje: str | None = None
    archivo: str | None = None


def ayuda(av: Aventura) -> str:
    """Los comandos del motor, con el golpe especial de cada aventura."""
    especial = f" · {av.comando_especial}" if av.comando_especial else ""
    return f"""Comandos:
  mirar              Mirar alrededor (salidas, objetos, gente)
  ir <destino>       Viajar: por número, dirección o nombre (ir 1, ir este)
  estado             Vida, nivel, corrupción, equipo y compañeros
  inventario         Lo que llevas
  tomar <cosa>       Recoger del suelo (tomar todo)
  comprar <cosa>     En las tiendas
  usar <cosa>        Consumir provisiones o hierbas
  equipar <cosa>     Empuñar un arma o ponerte una pieza de armadura
  desequipar <cosa>  Guardar lo que llevas puesto (o: desequipar arma)
  hablar <quién>     Escuchar a quien esté aquí
  reclutar <quién>   Sumar un aliado a tu grupo
  descansar          Curarte del todo donde haya cama
  guardar [archivo]  Guardar partida ({ARCHIVO_PARTIDA} por defecto)
  cargar [archivo]   Cargar partida
  ayuda              Esta ayuda
  salir              Dejar de jugar

Cada enemigo caído da experiencia; con la suficiente, subes de nivel
(+1 ataque, +8 de vida máxima). Los enemigos con habilidades avisan lo
que van a hacer: léelos y decide cuándo gastar provisiones.

En combate:  atacar · usar <cosa>{especial} · cuerno · huir · estado
"""


def _portada(salida, color: bool) -> None:
    salida(_c(
        "══════════════════════════════════════════════════════════════════\n"
        "    A L D A M A R\n"
        "    aventuras de fantasía épica para la terminal\n"
        "══════════════════════════════════════════════════════════════════",
        color, TITULO,
    ))


def menu_principal(
    *,
    entrada,
    salida,
    color: bool = False,
    flechas: bool | None = None,
    aventura: str | None = None,
    dificultad: str | None = None,
    personaje: str | None = None,
) -> Eleccion:
    """Muestra el menú de arranque. Los parámetros preselección saltan pasos.

    Devuelve la Elección del jugador; `accion == "salir"` (o None por EOF)
    significa que no se juega. Con `flechas=True` (o detección automática)
    las listas se navegan con ↑/↓ y Enter.
    """
    navegable = flechas or (flechas is None and _es_interactivo(entrada, salida))
    _portada(salida, color)

    def _de_vuelta() -> None:
        """El menú anterior volvió con la pantalla limpia: falta la portada."""
        if navegable:
            _portada(salida, color)

    while True:
        clave = elegir_opcion(
            "Menú principal",
            [
                ("nueva", "Nueva partida", ""),
                ("cargar", "Cargar partida", f"Retoma un archivo guardado ({ARCHIVO_PARTIDA} por defecto)"),
                ("ayuda", "Cómo jugar", "Los comandos del viaje"),
                ("salir", "Salir", ""),
            ],
            entrada=entrada,
            salida=salida,
            color=color,
            flechas=flechas,
        )
        if clave is None or clave == "salir":
            return Eleccion("salir")

        if clave == "ayuda":
            pantalla_completa(
                ayuda(obtener_aventura(aventura)),
                entrada=entrada,
                salida=salida,
                color=color,
            )
            if navegable:
                # la ayuda restauró la pantalla de antes: el bloque viejo del
                # menú sigue ahí; se limpia para no apilar otro debajo
                salida(LIMPIAR)
            _de_vuelta()
            continue

        if clave == "cargar":
            try:
                archivo = entrada(f"Archivo de partida ({ARCHIVO_PARTIDA}): ").strip()
            except EOFError:
                archivo = ""
            return Eleccion("cargar", archivo=archivo or ARCHIVO_PARTIDA)

        # ── nueva partida: aventura → personaje → dificultad ──────────
        if aventura is not None:
            av = obtener_aventura(aventura)
        else:
            clave_av = elegir_opcion(
                "¿Qué aventura quieres vivir?",
                [(a.id, a.titulo, a.descripcion) for a in AVENTURAS.values()],
                entrada=entrada,
                salida=salida,
                color=color,
                flechas=flechas,
            )
            if clave_av is None:
                _de_vuelta()
                continue
            av = obtener_aventura(clave_av)

        per = personaje
        if per is not None and per not in av.personajes:
            salida(_c(f"{av.titulo} no tiene al personaje {per!r}.", color, AMARILLO))
            personaje = None
            per = None
        if per is None:
            if len(av.personajes) > 1:
                per = elegir_opcion(
                    "¿Quién será tu héroe?",
                    [(p.clave, f"{p.nombre}, {p.titulo}", p.presentacion) for p in av.personajes.values()],
                    entrada=entrada,
                    salida=salida,
                    color=color,
                    flechas=flechas,
                )
                if per is None:
                    _de_vuelta()
                    continue
            else:
                per = av.jugador_inicial

        if dificultad is not None:
            dif = obtener_dificultad(dificultad)
        else:
            clave_dif = elegir_opcion(
                "¿A qué ritmo quieres caminar?",
                [(d.clave, d.nombre, d.descripcion) for d in DIFICULTADES.values()],
                entrada=entrada,
                salida=salida,
                color=color,
                flechas=flechas,
            )
            if clave_dif is None:
                _de_vuelta()
                continue
            dif = obtener_dificultad(clave_dif)

        return Eleccion("nueva", aventura=av, dificultad=dif, personaje=per)

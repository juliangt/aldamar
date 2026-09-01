"""Vocabulario declarativo de eventos: lo que un JSON de aventura puede pedir.

Los archivos de aventura no llevan código: declaran efectos de este
vocabulario y aquí se convierten en las funciones —evento de lugar y
golpe especial de combate— que el objeto `Aventura` guarda y el motor
ejecuta. Sumar un efecto nuevo = una entrada nueva aquí y su validación
en `cargador.py`; el JSON de la aventura sigue siendo puro dato.

Eventos de lugar:
- "otorgar": entrega un objeto, una sola vez si declara `una_vez`.
- "curar_grupo": cura al héroe, resucita y cura a los compañeros.
- "corrupcion": un aviso y puntos de corrupción, cada vez que se entra.
- "final": un texto, una elección y el desenlace (el epílogo cambia si
  la corrupción del héroe superó el umbral).

Golpe especial de combate: daño base más corrupción // divisor, con
coste de corrupción y mensaje parametrizados.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from .mundo import Lugar
from .opciones import elegir_opcion
from .personajes import Enemigo

if TYPE_CHECKING:  # solo anotaciones
    from .juego import Juego

# Un evento de lugar recibe (juego, lugar) y hace su magia narrativa.
Evento = Callable[["Juego", Lugar], None]
# Un golpe especial de combate recibe (juego, enemigo).
AtaqueEspecial = Callable[["Juego", Enemigo], None]

TIPOS_EVENTOS = {"otorgar", "curar_grupo", "corrupcion", "final"}


def evento_otorgar(item: str, texto: str, una_vez: str | None = None) -> Evento:
    def evento(j: "Juego", lugar: "Lugar") -> None:
        if una_vez and j.flags.get(una_vez):
            return
        if una_vez:
            j.flags[una_vez] = True
        j.jugador.inventario.append(item)
        j.epico("\n" + texto)

    return evento


def evento_curar_grupo(texto: str, corrupcion: int = 0, una_vez: str | None = None) -> Evento:
    def evento(j: "Juego", lugar: "Lugar") -> None:
        if una_vez and j.flags.get(una_vez):
            return
        if una_vez:
            j.flags[una_vez] = True
        j.jugador.curar(j.jugador.vida_max)
        for c in j.jugador.companeros:
            c.viva = True
            c.vida = c.vida_max
        j.epico("\n" + texto)
        if corrupcion:
            j.corruptear(corrupcion)

    return evento


def evento_corrupcion(puntos: int, aviso: str | None = None) -> Evento:
    def evento(j: "Juego", lugar: "Lugar") -> None:
        if aviso:
            j.aviso(aviso)
        j.corruptear(puntos)

    return evento


def evento_final(
    texto: str,
    pregunta: str,
    opciones: list[dict],
    epilogo_puro: str,
    final_puro: str,
    epilogo_tentado: str,
    final_tentado: str,
    umbral_tentado: int,
    texto_companeros: str = "",
) -> Evento:
    """La opción sin `epilogo` es el desenlace por defecto: el epílogo
    elegido depende de la corrupción del héroe contra el umbral."""

    def evento(j: "Juego", lugar: "Lugar") -> None:
        j.escribir("\n" + texto)
        clave = elegir_opcion(
            pregunta,
            [
                (str(op["clave"]), str(op["titulo"]), str(op.get("detalle", "")))
                for op in opciones
            ],
            entrada=j.entrada,
            salida=j.salida,
            color=j.color,
            flechas=getattr(j, "flechas", None),
        )
        elegida = next((op for op in opciones if op["clave"] == clave), None)
        if elegida is not None and "epilogo" in elegida:
            mostrar = j.aviso if elegida.get("estilo", "aviso") == "aviso" else j.epico
            mostrar("\n" + elegida["epilogo"])
            j.final = elegida["final"]
            j.fin = True
            return
        # desenlace por defecto (también si cancela la elección)
        tentado = j.jugador.corrupcion >= umbral_tentado
        j.epico("\n" + (epilogo_tentado if tentado else epilogo_puro))
        vivas = [c.nombre for c in j.jugador.companeras_vivas()]
        if vivas and texto_companeros:
            j.escribir(texto_companeros.format(nombres=", ".join(vivas)))
        j.final = final_tentado if tentado else final_puro
        j.fin = True

    return evento


def ataque_con_corrupcion(
    dano_base: int,
    dano_por_corrupcion: int,
    corrupcion_coste: int,
    mensaje: str,
) -> AtaqueEspecial:
    """Un golpe fuerte que deja grieta: el daño crece con la corrupción."""

    def ataque(j: "Juego", enemigo: "Enemigo") -> None:
        dano = dano_base + j.jugador.corrupcion // dano_por_corrupcion
        efectivo = enemigo.recibir(dano)
        j.aviso(mensaje.format(efectivo=efectivo))
        j.corruptear(corrupcion_coste)

    return ataque


def evento_desde(datos: dict) -> Evento:
    """Construye el evento declarado en el JSON (ya validado por el cargador)."""
    tipo = datos["tipo"]
    if tipo == "otorgar":
        return evento_otorgar(datos["item"], datos["texto"], datos.get("una_vez"))
    if tipo == "curar_grupo":
        return evento_curar_grupo(
            datos["texto"], datos.get("corrupcion", 0), datos.get("una_vez")
        )
    if tipo == "corrupcion":
        return evento_corrupcion(datos["puntos"], datos.get("aviso"))
    if tipo == "final":
        return evento_final(
            datos["texto"],
            datos["pregunta"],
            datos["opciones"],
            datos["epilogo_puro"],
            datos["final_puro"],
            datos["epilogo_tentado"],
            datos["final_tentado"],
            datos["umbral_tentado"],
            datos.get("texto_companeros", ""),
        )
    raise ValueError(f"tipo de evento desconocido: {tipo!r}")


def ataque_especial_desde(datos: dict) -> AtaqueEspecial:
    return ataque_con_corrupcion(
        datos["dano_base"],
        datos["dano_por_corrupcion"],
        datos["corrupcion_coste"],
        datos["mensaje"],
    )

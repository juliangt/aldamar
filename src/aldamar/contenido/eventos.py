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
- "narrar": un texto de puro relato, una sola vez si declara `una_vez`,
  reservable con una `condicion` de banderas y con texto alternativo
  (`texto_grieta` + `grieta_desde`) cuando la corrupción del héroe
  supera el umbral.
- "decision": un texto y una elección con efectos inmediatos (objeto,
  corrupción, bandera); la bandera es la que después leen los eventos
  que quieran reaccionar a la decisión.
- "emboscar": suma enemigos al lugar al entrar, solo si se cumple su
  condición de banderas (decisiones tardías que cobran su precio).
- "final": un texto, una elección y el desenlace (el epílogo cambia si
  la corrupción del héroe superó el umbral; una opción puede exigir
  `requiere_flag` para aparecer solo si hubo cierta decisión).

Golpe especial de combate: daño base más corrupción // divisor, con
coste de corrupción y mensaje parametrizados. Las otras dos piezas del
vocabulario de combate —`habilidades` de enemigo y `fases` de jefe— se
declaran dentro de cada enemigo del JSON y viven en `personajes.py`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from ..interfaz.opciones import elegir_opcion
from .mundo import Lugar
from .personajes import Enemigo

if TYPE_CHECKING:  # solo anotaciones
    from ..motor.juego import Juego

# Un evento de lugar recibe (juego, lugar) y hace su magia narrativa.
Evento = Callable[["Juego", Lugar], None]
# Un golpe especial de combate recibe (juego, enemigo).
AtaqueEspecial = Callable[["Juego", Enemigo], None]

TIPOS_EVENTOS = {"otorgar", "curar_grupo", "corrupcion", "narrar", "decision", "emboscar", "final"}


def evento_otorgar(item: str, texto: str, una_vez: str | None = None) -> Evento:
    def evento(j: "Juego", lugar: "Lugar") -> None:
        if una_vez and j.flags.get(una_vez):
            return
        if una_vez:
            j.flags[una_vez] = True
        j.adquirir(item)
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


def evento_narrar(
    texto: str,
    una_vez: str | None = None,
    condicion: dict | None = None,
    texto_grieta: str | None = None,
    grieta_desde: int | None = None,
) -> Evento:
    """Un texto de puro relato, una sola vez si declara `una_vez`.

    `condicion` (`flag`/`no_flag`) lo reserva a una circunstancia: sin
    ella, la escena no se cuenta ni se marca (legado que aún no llegó).
    Y si declara `texto_grieta` con su `grieta_desde`, el texto que se
    lee depende de la grieta que lleva el héroe: la corrupción vista
    desde el mundo, no solo del epílogo.
    """

    def evento(j: "Juego", lugar: "Lugar") -> None:
        if una_vez and j.flags.get(una_vez):
            return
        if condicion:
            if condicion.get("flag") and not j.flags.get(condicion["flag"]):
                return
            if condicion.get("no_flag") and j.flags.get(condicion["no_flag"]):
                return
        if texto_grieta and grieta_desde and j.jugador.corrupcion >= grieta_desde:
            j.epico("\n" + j._texto_heroe(texto_grieta))
        else:
            j.epico("\n" + j._texto_heroe(texto))
        if una_vez:
            j.flags[una_vez] = True

    return evento


def evento_decision(texto: str, pregunta: str, opciones: list[dict], una_vez: str) -> Evento:
    """Una elección con efectos inmediatos: la escena no se repite.

    Cada opción puede declarar `texto` (lo que se lee al elegirla),
    `item` (se suma al inventario), `corrupcion` (positiva o negativa) y
    `flag` (la bandera que dejan encendida para el resto de la aventura).
    Cancelar la elección no decide: la escena espera otra visita.
    """

    def evento(j: "Juego", lugar: "Lugar") -> None:
        if j.flags.get(una_vez):
            return
        j.epico("\n" + j._texto_heroe(texto))
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
        if elegida is None:
            return  # canceló: la decisión sigue abierta
        j.flags[una_vez] = True
        if elegida.get("flag"):
            j.flags[elegida["flag"]] = True
        if elegida.get("item"):
            j.adquirir(elegida["item"])
        if elegida.get("corrupcion"):
            j.corruptear(elegida["corrupcion"])
        if elegida.get("texto"):
            j.epico("\n" + j._texto_heroe(elegida["texto"]))

    return evento


def evento_emboscar(
    enemigos: list[str],
    texto: str,
    flag: str | None = None,
    no_flag: str | None = None,
) -> Evento:
    """Al entrar, si la condición de banderas se cumple, suma enemigos.

    `flag` exige una decisión tomada; `no_flag` exige una no tomada.
    Los enemigos quedan en el lugar hasta resolverse: la emboscada no se
    repite, pero tampoco se olvida.
    """

    def evento(j: "Juego", lugar: "Lugar") -> None:
        if flag and not j.flags.get(flag):
            return
        if no_flag and j.flags.get(no_flag):
            return
        pendientes = j.enemigos[lugar.id]
        nuevos = [e for e in enemigos if e not in pendientes]
        if not nuevos:
            return
        pendientes.extend(nuevos)
        j.peligro("\n" + j._texto_heroe(texto))

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
    elegido depende de la corrupción del héroe contra el umbral. Una
    opción puede declarar `requiere_flag`: solo se ofrece si la decisión
    que encendió esa bandera ocurrió.

    El epílogo no se imprime aquí: queda en `juego.epilogo` y la pantalla
    de cierre lo presenta con aire (así no aparece dos veces)."""

    def evento(j: "Juego", lugar: "Lugar") -> None:
        j.escribir("\n" + texto)
        visibles = [
            op for op in opciones
            if not op.get("requiere_flag") or j.flags.get(op["requiere_flag"])
        ]
        clave = elegir_opcion(
            pregunta,
            [
                (str(op["clave"]), str(op["titulo"]), str(op.get("detalle", "")))
                for op in visibles
            ],
            entrada=j.entrada,
            salida=j.salida,
            color=j.color,
            flechas=getattr(j, "flechas", None),
        )
        elegida = next((op for op in visibles if op["clave"] == clave), None)
        if elegida is not None and "epilogo" in elegida:
            j.epilogo = elegida["epilogo"]
            j.final = elegida["final"]
            j.fin = True
            return
        # desenlace por defecto (también si cancela la elección)
        tentado = j.jugador.corrupcion >= umbral_tentado
        j.epilogo = epilogo_tentado if tentado else epilogo_puro
        vivas = [c.nombre for c in j.jugador.companeras_vivas()]
        if vivas and texto_companeros:
            j.epilogo += "\n\n" + texto_companeros.format(nombres=", ".join(vivas))
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


def evento_desde(datos: dict, clave: str | None = None) -> Evento:
    """Construye el evento declarado en el JSON (ya validado por el cargador).

    `clave` es la clave con la que la aventura registra el evento: la
    decisión que no declara `una_vez` usa la suya para marcarse hecha.
    """
    tipo = datos["tipo"]
    if tipo == "otorgar":
        return evento_otorgar(datos["item"], datos["texto"], datos.get("una_vez"))
    if tipo == "curar_grupo":
        return evento_curar_grupo(
            datos["texto"], datos.get("corrupcion", 0), datos.get("una_vez")
        )
    if tipo == "corrupcion":
        return evento_corrupcion(datos["puntos"], datos.get("aviso"))
    if tipo == "narrar":
        return evento_narrar(
            datos["texto"],
            datos.get("una_vez"),
            datos.get("condicion"),
            datos.get("texto_grieta"),
            datos.get("grieta_desde"),
        )
    if tipo == "decision":
        return evento_decision(
            datos["texto"],
            datos["pregunta"],
            datos["opciones"],
            datos.get("una_vez") or clave or "",
        )
    if tipo == "emboscar":
        condicion = datos.get("condicion") or {}
        return evento_emboscar(
            datos["enemigos"],
            datos["texto"],
            condicion.get("flag"),
            condicion.get("no_flag"),
        )
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

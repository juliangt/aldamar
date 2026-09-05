"""El arranque del ejecutable: `main`, argparse y el bucle de sesión.

Del flag de CLI a la partida: preferencias (`configuracion.json` +
entorno + flags), presentación, menú principal y el bucle
menú → partida → cierre → menú. La partida en sí vive en `nucleo.Juego`.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from ... import __version__, datos  # noqa: F401  (datos: registra el contenido)
from ...contenido.aventura import AVENTURAS, obtener_aventura
from ...interfaz import opciones, presentacion
from ...interfaz.menu import ARCHIVO_PARTIDA, menu_principal
from ...interfaz.opciones import LIMPIAR, _es_interactivo
from .. import configuracion
from .. import legado as modulo_legado
from ..dificultad import DIFICULTADES, obtener_dificultad
from ..estadisticas import ARCHIVO_ESTADISTICAS
from ..guardado import PartidaInvalida
from .nucleo import Juego


def _escribir_legado(juego: Juego, ruta: str, salida) -> None:
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
        "--semilla", type=int, default=None, help="semilla aleatoria para partidas reproducibles"
    )
    parser.add_argument("--sin-color", action="store_true", help="desactivar colores ANSI")
    parser.add_argument(
        "--sin-flechas", action="store_true", help="menús respondiendo a texto, sin flechas del teclado"
    )
    parser.add_argument(
        "--sin-audio", action="store_true", help="sin jingle en la presentación y en el cierre"
    )
    parser.add_argument(
        "--sin-splash", action="store_true", help="sin pantalla de presentación: directo al menú"
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
    color_menu = bool(color) if color is not None else hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
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
        while True:
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
            if eleccion.accion == "viva":
                # el modo vivo: premisa, héroe y arranque, todo
                # suyo; import perezoso: sin modo vivo, ni se carga el
                # paquete. Si no arranca (sin Ollama, sin modelo, o se
                # arrepintió), el aviso se dio y el menú vuelve a mostrarse
                from ...viva.interfaz import partida_viva

                partida = partida_viva(
                    entrada=entrada,
                    salida=salida,
                    color=color,
                    flechas=flechas,
                    semilla=semilla,
                    audio=audio,
                    debug=debug,
                )
                if partida is None:
                    continue
                return partida
            if eleccion.aventura is None:  # inalcanzable: una Eleccion «nueva» trae aventura
                return None
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
        juego: Juego | None
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
                # dificultad, y el nombre puesto se conserva. Una partida
                # viva se rejuega estática: el mundo ya generado queda
                # como contenido, sin cronista
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

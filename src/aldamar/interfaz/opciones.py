"""Selección de opciones y pantallas auxiliares con flechas del teclado.

`elegir_opcion` detecta si hay teclado y pantalla reales (stdin/stdout
son TTYs y no se inyectaron entrada/salida): en ese caso se navega con
↑/↓ y se confirma con Enter. Si no — tests, tuberías, `--sin-flechas` —
vuelve al modo tipeado: número o nombre de la opción. `pantalla_completa`
muestra un texto a pantalla completa (la ayuda) y lo quita con Esc.

Solo biblioteca estándar: termios/select en POSIX, msvcrt en Windows.
"""

from __future__ import annotations

import os
import select
import shutil
import sys
import textwrap
from contextlib import contextmanager

from ..contenido.mundo import normaliza

TITULO, SELECCION, AMARILLO, DIM = "1;36", "1;36", "33", "2"

LIMPIAR = "\x1b[2J\x1b[H"  # pantalla nueva para lo que venga después

FLECHA_ARRIBA = {"\x1b[A", "\x00H", "\xe0H"}
FLECHA_ABAJO = {"\x1b[B", "\x00P", "\xe0P"}


def _c(texto: str, color: bool, *codigos: str) -> str:
    if not color or not codigos:
        return texto
    return "\033[" + ";".join(codigos) + "m" + texto + "\033[0m"


def _es_interactivo(entrada, salida) -> bool:
    """Flechas solo con teclado y pantalla reales; nunca con entrada inyectada."""
    try:
        return (
            entrada is input
            and salida is print
            and sys.stdin.isatty()
            and sys.stdout.isatty()
        )
    except (AttributeError, ValueError):
        return False


# ── teclado crudo ────────────────────────────────────────────────────────

_en_crudo = 0  # profundidad de modo crudo activo


@contextmanager
def _modo_crudo():
    """Teclado sin búfer de línea durante el bloque.

    Se entra una sola vez, no por tecla: en darwin cualquier tcsetattr
    descarta la entrada pendiente, así que tocar el terminal entre teclas
    traga pulsaciones (p. ej. flechas pulsadas seguidas).

    El modo es cbreak, no raw: solo apaga eco y búfer de línea. El
    post-procesado de salida sigue activo (el `\n` sigue devolviendo el
    carro) y Ctrl-C sigue interrumpiendo; un raw completo deja los
    prints del menú en escalera. En no-terminales — tests, tuberías — es
    un bloque sin efecto.
    """
    global _en_crudo
    if os.name == "nt":
        yield  # msvcrt no necesita modo crudo
        return
    import termios
    import tty

    try:
        fd = sys.stdin.fileno()
        viejo = termios.tcgetattr(fd)
    except (OSError, ValueError, termios.error):
        yield
        return
    tty.setcbreak(fd)
    _en_crudo += 1
    try:
        yield
    finally:
        _en_crudo -= 1
        termios.tcsetattr(fd, termios.TCSADRAIN, viejo)


def _tecla_posix() -> str:
    """Una tecla, suponiendo el teclado ya en modo crudo."""
    fd = sys.stdin.fileno()
    dato = os.read(fd, 1).decode("utf-8", "ignore")
    if dato == "\x1b":
        # Esc sola o el arranque de una secuencia (flechas)
        while len(dato) < 3 and select.select([fd], [], [], 0.05)[0]:
            dato += os.read(fd, 1).decode("utf-8", "ignore")
    return dato


def _tecla_windows() -> str:
    import msvcrt

    tecla = msvcrt.getwch()
    if tecla in ("\x00", "\xe0"):  # teclas especiales: llega un segundo código
        tecla += msvcrt.getwch()
    return tecla


def _leer_tecla() -> str:
    try:
        if os.name == "nt":
            return _tecla_windows()
        if _en_crudo:  # ya en crudo: ni tocar el terminal entre teclas
            return _tecla_posix()
        with _modo_crudo():
            return _tecla_posix()
    except (OSError, ValueError):
        return "\x1b"  # sin teclado crudo: cancelar es lo seguro


# ── pantalla completa ────────────────────────────────────────────────────

def pantalla_completa(texto: str, *, entrada, salida, color: bool = False) -> None:
    """Muestra `texto` a pantalla completa y lo quita con una tecla.

    Usa la pantalla alternativa del terminal: al volver queda exactamente
    lo que se veía antes, como en `less` o `vim`. Sin teclado y pantalla
    reales — tests, tuberías — escribe el texto y sigue, como toda la vida.
    """
    if not _es_interactivo(entrada, salida):
        salida(texto)
        return
    salida("\x1b[?1049h\x1b[H\x1b[2J")  # pantalla alternativa, limpia y en el origen
    try:
        salida(texto)
        salida(_c("\n  Esc para volver", color, DIM))
        _leer_tecla()  # una tecla cualquiera devuelve
    finally:
        salida("\x1b[?1049l")  # restaurar la vista anterior


# ── render ───────────────────────────────────────────────────────────────

def _desdibuja(dibujadas: int, salida) -> None:
    """Borra el bloque del menú entero, título incluido, sin tocar el relato.

    El cursor queda en la fila donde estaba la primera opción: lo que se
    escriba a continuación fluye justo debajo de donde estaba el menú.
    Solo vale si el bloque cabe en la pantalla; si el título pudo
    haberse salido por arriba, no hay forma segura de subir a borrar.
    """
    salida(f"\x1b[{dibujadas + 1}A")  # a la primera línea del bloque (el salto del print lo compensa)
    salida("\x1b[1A\x1b[J")  # al título; borrar desde ahí hasta el fin de la pantalla


def _reescribe(
    dibujadas: int, titulo: str, lineas: list[str], salida, color: bool
) -> None:
    """Cambia el menú por otro en el mismo sitio: cero crecimiento.

    Sube hasta la fila del título, escribe el nuevo en su lugar y
    reescribe el bloque debajo. Si el menú nuevo es más corto, los
    renglones que le sobran al viejo se borran.
    """
    salida(f"\x1b[{dibujadas + 2}A")  # a la fila del título (el salto del print lo compensa)
    salida(f"\x1b[2K{_c(titulo, color, TITULO)}")
    for linea in lineas:
        salida(f"\x1b[2K{linea}")
    viejos = dibujadas - len(lineas)
    if viejos > 0:  # el menú nuevo es más corto: limpiar lo que le sobraba al viejo
        for _ in range(viejos):
            salida("\x1b[2K")
        salida(f"\x1b[{viejos + 1}A")  # y volver a quedar justo debajo del bloque nuevo


def _renglones_desc(desc: str, ancho: int) -> list[str]:
    """Reengloniza una descripción extensa al ancho de la terminal."""
    ancho = max(1, ancho)
    renglones: list[str] = []
    for trozo in desc.strip().splitlines():
        renglones.extend(textwrap.wrap(trozo, width=ancho) or [""])
    return renglones


def _lineas_menu(opciones: list[tuple[str, str, str]], sel: int, color: bool) -> list[str]:
    ancho = shutil.get_terminal_size().columns
    rotulados = [f"{i+1}) {etiqueta}" for i, (_c, etiqueta, _d) in enumerate(opciones)]
    columna = max(map(len, rotulados))  # las descripciones arrancan alineadas
    lineas: list[str] = []
    for i, (_clave, _etiqueta, desc) in enumerate(opciones):
        rotulo = rotulados[i]
        if i == sel:
            linea = _c(f"  ❯ {rotulo}", color, SELECCION)
        else:
            linea = f"    {rotulo}"
        if desc and "\n" not in desc:
            hueco = " " * (columna - len(rotulo) + 3)
            margen = ancho - 1 - (4 + len(rotulo) + len(hueco))
            if 0 < len(desc) <= margen:
                # la descripción corta viaja al lado de su opción
                linea += _c(f"{hueco}{desc}", color, DIM)
                lineas.append(linea)
                continue
        # descripción extensa (ficha de héroe) o larga: renglones propios
        # debajo de la opción — nunca se corta con «…»
        lineas.append(linea)
        for renglon in _renglones_desc(desc, ancho - 8):
            lineas.append(_c(f"     {renglon}", color, DIM))
    lineas.append(_c("  ↑/↓ mover · Enter elegir · 1-9 atajo · Esc volver", color, DIM))
    return lineas


def _elegir_con_flechas(
    titulo: str,
    opciones: list[tuple[str, str, str]],
    salida,
    color: bool,
    aviso_esc: str | None = None,
    relato: bool = False,
    resuelve=None,
) -> str | None:
    """El bucle del menú navegable.

    Con `resuelve`, el menú es una pila viva (solo con `relato`): al
    elegir, `resuelve(clave)` devuelve el submenú a mostrar —y el menú
    nuevo reemplaza al viejo en el mismo sitio, sin crecer una línea—,
    o None si la clave ya es una decisión final; `resuelve(None)` trae
    el menú de arriba al volver con Esc. Si no hay `resuelve`, toda
    elección termina el menú.
    """
    if not relato:
        resuelve = None
    sel = 0
    aviso: str | None = None
    salida(_c(f"\n{titulo}", color, TITULO))
    dibujadas = 0  # líneas del bloque; el cursor queda justo debajo

    def cerrar() -> None:
        """Salir del menú. En modo relato se borra el propio bloque —título
        incluido— y el relato sigue debajo; si el bloque no cabe en
        pantalla (el título pudo salirse por arriba) o el modo no es
        relato, pantalla nueva como de toda la vida."""
        cabe = dibujadas + 1 <= shutil.get_terminal_size().lines
        if relato and cabe:
            _desdibuja(dibujadas, salida)
        else:
            salida(LIMPIAR)

    def cambia(nuevo_titulo: str, nuevas: list[tuple[str, str, str]], nuevo_aviso: str | None) -> None:
        """Otro menú, en el mismo lugar: navegar no suma ni una fila."""
        nonlocal titulo, opciones, aviso_esc, aviso, sel, dibujadas
        titulo, opciones, aviso_esc = nuevo_titulo, nuevas, nuevo_aviso
        aviso, sel = None, 0
        lineas = _lineas_menu(opciones, sel, color)
        _reescribe(dibujadas, titulo, lineas, salida, color)
        dibujadas = len(lineas)

    try:
        with _modo_crudo():
            while True:
                lineas = _lineas_menu(opciones, sel, color)
                if aviso:
                    lineas.append(_c(f"  {aviso}", color, AMARILLO))
                if not dibujadas:
                    # ocultar el cursor mientras se elige, sin gastar una línea
                    # propia: si el primer bloque midiera más, el último renglón
                    # del redibujado anterior quedaría sin borrar en pantalla
                    lineas[0] = "\x1b[?25l" + lineas[0]
                if dibujadas:
                    # +1 porque la salida añade un salto de línea tras la secuencia
                    salida(f"\x1b[{dibujadas + 1}A")
                for linea in lineas:
                    salida(f"\x1b[2K{linea}")  # limpiar y reescribir cada línea
                dibujadas = len(lineas)

                tecla = _leer_tecla()
                if tecla in FLECHA_ABAJO:
                    sel = (sel + 1) % len(opciones)
                elif tecla in FLECHA_ARRIBA:
                    sel = (sel - 1) % len(opciones)
                elif tecla in ("\r", "\n") or (tecla.isdigit() and tecla != "0" and int(tecla) <= len(opciones)):
                    if tecla not in ("\r", "\n"):
                        sel = int(tecla) - 1
                    clave = opciones[sel][0]
                    if resuelve is not None:
                        siguiente = resuelve(clave)
                        if siguiente is not None:
                            cambia(*siguiente)
                            continue
                    cerrar()
                    return clave
                elif tecla in ("\x1b", "q", "Q", "\x04"):  # Esc, q o Ctrl-D: volver
                    if aviso_esc is None:
                        if resuelve is not None:
                            siguiente = resuelve(None)  # subir un nivel
                            if siguiente is not None:
                                cambia(*siguiente)
                                continue
                        cerrar()  # volver: sin rastro del menú
                        return None
                    # no hay a dónde volver: el menú se queda, el aviso queda
                    # dicho y nada se vuelve a imprimir (el bloque no se apila)
                    aviso = aviso_esc
                elif tecla == "\x03":  # Ctrl-C en modo crudo llega como byte
                    raise KeyboardInterrupt
    finally:
        salida("\x1b[?25h")  # devolver el cursor siempre


def _elegir_tipeando(
    titulo: str,
    opciones: list[tuple[str, str, str]],
    entrada,
    salida,
    color: bool,
) -> str | None:
    salida(_c(f"\n{titulo}", color, TITULO))
    for i, (_clave, etiqueta, desc) in enumerate(opciones, 1):
        salida(f"  {i}) {etiqueta}")
        for renglon in (desc.strip().splitlines() if desc else []):
            salida(_c(f"     {renglon}", color, DIM))
    while True:
        try:
            linea = entrada(f"\nElige una opción (1-{len(opciones)}): ").strip()
        except EOFError:
            return None
        if not linea:
            continue
        t = normaliza(linea)
        if t.isdigit():
            n = int(t)
            if 1 <= n <= len(opciones):
                return opciones[n - 1][0]
        for clave, etiqueta, _desc in opciones:
            if t == normaliza(clave) or normaliza(etiqueta).startswith(t):
                return clave
        salida(_c(f"No entiendo: responde 1-{len(opciones)} o el nombre de la opción.", color, AMARILLO))


def elegir_opcion(
    titulo: str,
    opciones: list[tuple[str, str, str]],
    *,
    entrada,
    salida,
    color: bool = False,
    flechas: bool | None = None,
    aviso_esc: str | None = None,
    relato: bool = False,
    resuelve=None,
) -> str | None:
    """Menú de opciones. `opciones` son (clave, etiqueta, descripción).

    La descripción puede ocupar varios renglones (se muestran todos,
    debajo de su opción). Con teclado real (o `flechas=True`) navega con
    ↑/↓ y Enter; los dígitos eligen al vuelo y Esc vuelve (None). Al
    salir, por cualquier vía —elegir o volver—, la pantalla se limpia:
    lo que se pinte después se ve solo. Con `relato=True`, en cambio,
    el menú vive dentro del relato: al salir solo se borra su propio
    bloque —título incluido— y lo que se pinte después continúa debajo
    de lo que ya se estaba leyendo (issue 36).
    Con `aviso_esc`, Esc no saca del menú: el aviso queda escrito bajo
    las opciones y se sigue eligiendo. Con `relato` y `resuelve`, el
    menú es una pila: `resuelve(clave)` devuelve el (título, opciones,
    aviso_esc) del submenú al que pasar —reemplazando al actual en el
    mismo sitio— o None si la clave es una decisión final;
    `resuelve(None)` trae el menú de arriba al volver con Esc.
    En modo tipeado acepta número o nombre. Sin opciones, devuelve None.
    """
    if not opciones:
        return None
    if flechas or (flechas is None and _es_interactivo(entrada, salida)):
        return _elegir_con_flechas(titulo, opciones, salida, color, aviso_esc, relato, resuelve)
    return _elegir_tipeando(titulo, opciones, entrada, salida, color)

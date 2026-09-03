"""Navegación con flechas del selector de opciones."""

from __future__ import annotations

import os
import re

import pytest

import aldamar.interfaz.opciones as opciones_mod
from aldamar.interfaz.opciones import elegir_opcion

from conftest import EntradaTipeada

OPCIONES = [
    ("a", "Uno", ""),
    ("b", "Dos", "el segundo"),
    ("c", "Tres", ""),
]


class Terminal:
    """Emula lo mínimo para ver el bloque del menú como lo ve el jugador.

    Cada llamada a `escribe` es un print: aplica los escapes de control y
    deja el cursor en la fila siguiente (el salto de línea va incluido).
    """

    def __init__(self):
        self.filas: list[str] = []
        self.fila = 0

    def escribe(self, texto: str) -> None:
        if texto.startswith("\n"):  # la línea en blanco que abre el menú: baja una fila
            self.fila += 1
            texto = texto[1:]
        if texto == "\x1b[1A\x1b[J":  # borrar desde la fila de arriba hasta el final
            self.fila = max(0, self.fila - 1)
            for i in range(self.fila, len(self.filas)):
                self.filas[i] = ""
            self.fila += 1  # el salto del print devuelve el cursor a su fila
            return
        subida = re.fullmatch(r"\x1b\[(\d+)A", texto)
        if subida:  # el print añade un salto: subir n deja el cursor n-1 más arriba
            self.fila = max(0, self.fila - (int(subida.group(1)) - 1))
            return
        self._poner(self.fila, re.sub(r"\x1b\[[0-9;?]*[a-zA-Z]", "", texto))
        self.fila += 1

    def _poner(self, i: int, texto: str) -> None:
        while len(self.filas) <= i:
            self.filas.append("")
        self.filas[i] = texto

    def texto(self) -> str:
        return "\n".join(self.filas)


def elegir_con_teclas(monkeypatch, teclas, lista=OPCIONES):
    pendientes = list(teclas)
    monkeypatch.setattr(opciones_mod, "_leer_tecla", lambda: pendientes.pop(0))
    salida: list[str] = []
    clave = elegir_opcion(
        "Prueba", lista, entrada=input, salida=salida.append, flechas=True
    )
    return clave, salida


def test_enter_confirma_la_opcion_actual(monkeypatch):
    clave, salida = elegir_con_teclas(monkeypatch, ["\r"])
    assert clave == "a"
    texto = "\n".join(salida)
    assert "❯" in texto  # la fila elegida lleva marcador
    assert "↑/↓" in texto  # y hay pista de teclas


def test_la_descripcion_va_al_lado_de_su_opcion(monkeypatch):
    _clave, salida = elegir_con_teclas(monkeypatch, ["\r"])
    assert any("2) Dos" in linea and "el segundo" in linea for linea in salida)


LARGA = [
    ("a", "Uno", "primera linea de la ficha\nsegunda linea\ntercera linea"),
    ("b", "Dos", "corta"),
]


def test_las_descripciones_extensas_se_muestran_completas(monkeypatch):
    clave, salida = elegir_con_teclas(monkeypatch, ["\r"], lista=LARGA)
    texto = "\n".join(salida)
    assert clave == "a"
    for linea in ("primera linea de la ficha", "segunda linea", "tercera linea"):
        assert linea in texto, f"falta «{linea}» en el menú"
    # las descripciones cortas siguen al lado de su opción
    assert any("2) Dos" in linea and "corta" in linea for linea in salida)


def test_la_descripcion_extensa_se_reengloniza_al_ancho(monkeypatch):
    terminal = os.terminal_size((40, 24))
    monkeypatch.setattr(opciones_mod.shutil, "get_terminal_size", lambda: terminal)
    lista = [("a", "Uno", " ".join(["palabra"] * 30) + "\nfinal")]
    lineas = opciones_mod._lineas_menu(lista, 0, color=False)
    assert lineas[-2].rstrip().endswith("final")  # el segundo párrafo también está
    de_desc = [linea for linea in lineas if "palabra" in linea or linea.endswith("final")]
    assert len(de_desc) > 3  # el párrafo se partió en varios renglones
    assert all(len(linea) <= 41 for linea in de_desc)  # nada se sale de la terminal


# ── descripciones largas de una línea: renglones, no «…» (issue 25) ──────

HISTORIA = (
    "Una aguja de basalto atraviesa la niebla del puerto y nadie recuerda "
    "quién la levantó: la ciudad duerme a su sombra y la Sombra, dicen "
    "los viejos, duerme dentro."
)


def test_la_descripcion_larga_se_muestra_completa_en_varios_renglones(monkeypatch):
    terminal = os.terminal_size((80, 24))
    monkeypatch.setattr(opciones_mod.shutil, "get_terminal_size", lambda: terminal)
    lista = [("a", "Aguja sin Sombra", HISTORIA), ("b", "Otra", "corta")]
    lineas = opciones_mod._lineas_menu(lista, 0, color=False)
    texto = " ".join(" ".join(lineas).split())
    assert "…" not in texto  # nada se corta
    for palabra in ("basalto", "levantó", "duerme dentro"):
        assert palabra in texto  # la historia entera está
    renglones = [linea for linea in lineas if linea.startswith("     ") and linea.strip()]
    assert len(renglones) >= 2  # se partió debajo de su opción
    assert all(len(linea) <= 80 for linea in lineas)  # y nada se sale del ancho
    # la opción corta de al lado sigue con su descripción al lado
    assert any("Otra" in linea and "corta" in linea for linea in lineas)


def test_el_atajo_elige_la_opcion_aun_con_renglones_de_por_medio(monkeypatch):
    terminal = os.terminal_size((80, 24))
    monkeypatch.setattr(opciones_mod.shutil, "get_terminal_size", lambda: terminal)
    lista = [("a", "Aguja sin Sombra", HISTORIA), ("b", "Otra", "corta")]
    clave, _ = elegir_con_teclas(monkeypatch, ["2"], lista=lista)
    assert clave == "b"  # el 1-9 elige opciones, no renglones de descripción


def test_el_redibujo_cuadra_con_opciones_de_alto_distinto(monkeypatch):
    """Una opción ocupa cuatro renglones y la siguiente, uno: al moverse
    por la lista el bloque no deja restos ni duplica la pista de teclas."""
    terminal = os.terminal_size((80, 24))
    monkeypatch.setattr(opciones_mod.shutil, "get_terminal_size", lambda: terminal)
    term = Terminal()
    teclas = iter(["\x1b[B", "\r"])
    esperadas: list[str] = []

    def tecla():
        esperadas.append(term.texto())  # pantalla tal y como está al esperar
        return next(teclas)

    monkeypatch.setattr(opciones_mod, "_leer_tecla", tecla)
    lista = [("a", "Aguja sin Sombra", HISTORIA), ("b", "Otra", "")]
    elegir_opcion("Prueba", lista, entrada=input, salida=term.escribe, flechas=True)
    assert esperadas[-1].count("↑/↓") == 1
    assert esperadas[-1].count("Prueba") == 1


def test_el_modo_tipeado_tambien_muestra_toda_la_descripcion():
    salida: list[str] = []
    elegir_opcion(
        "Prueba", LARGA, entrada=EntradaTipeada(["2"]), salida=salida.append
    )
    texto = "\n".join(salida)
    assert "primera linea de la ficha" in texto
    assert "tercera linea" in texto


def test_al_avanzar_se_limpia_la_pantalla(monkeypatch):
    _clave, salida = elegir_con_teclas(monkeypatch, ["\r"])
    assert "\x1b[2J\x1b[H" in salida  # el contenido nuevo se ve solo


def test_un_atajo_tambien_limpia(monkeypatch):
    _clave, salida = elegir_con_teclas(monkeypatch, ["2"])
    assert "\x1b[2J\x1b[H" in salida


def test_al_volver_con_esc_se_limpia_la_pantalla(monkeypatch):
    """Invariante: salir del menú deja la pantalla limpia, se salga como se salga."""
    _clave, salida = elegir_con_teclas(monkeypatch, ["\x1b"])
    assert "\x1b[2J\x1b[H" in salida  # al volver también: lo que venga se ve solo


def test_ctrl_d_vuelve_y_tambien_limpia(monkeypatch):
    _clave, salida = elegir_con_teclas(monkeypatch, ["\x04"])
    assert _clave is None
    assert "\x1b[2J\x1b[H" in salida


# ── modo relato: el menú se borra, el relato queda (issue 36) ────────────

def elegir_en_relato(monkeypatch, teclas, lista=OPCIONES, filas=24):
    """Menú con `relato=True`: devuelve (clave, impresos, pantalla).

    `impresos` son los prints tal cual salieron; `pantalla`, la terminal
    emulada después de aplicarlos.
    """
    terminal = os.terminal_size((80, filas))
    monkeypatch.setattr(opciones_mod.shutil, "get_terminal_size", lambda: terminal)
    pendientes = list(teclas)
    monkeypatch.setattr(opciones_mod, "_leer_tecla", lambda: pendientes.pop(0))
    term = Terminal()
    impresos: list[str] = []

    def salida(texto: str) -> None:
        impresos.append(texto)
        term.escribe(texto)

    clave = elegir_opcion(
        "Prueba", lista, entrada=input, salida=salida, flechas=True, relato=True
    )
    return clave, impresos, term.texto()


def test_en_relato_no_se_limpia_la_pantalla(monkeypatch):
    clave, impresos, _pantalla = elegir_en_relato(monkeypatch, ["\r"])
    assert clave == "a"
    assert "\x1b[2J\x1b[H" not in "\n".join(impresos)  # el relato sigue donde estaba


def test_en_relato_el_bloque_se_borra_entero(monkeypatch):
    clave, _impresos, pantalla = elegir_en_relato(monkeypatch, ["\r"])
    assert clave == "a"
    assert "Prueba" not in pantalla  # el título también se borró
    assert "❯" not in pantalla and "↑/↓" not in pantalla  # y el bloque con él


def test_en_relato_volver_con_esc_no_deja_rastro_del_menu(monkeypatch):
    clave, _impresos, pantalla = elegir_en_relato(monkeypatch, ["\x1b"])
    assert clave is None
    assert "Prueba" not in pantalla and "❯" not in pantalla


def test_menu_mas_alto_que_la_pantalla_vuelve_a_limpiar(monkeypatch):
    """Si el título pudo haberse salido por arriba, no hay forma segura
    de subir a borrar: pantalla nueva, como de toda la vida."""
    lista = [(c, f"Opción {c}", "") for c in "abcdefghijklmnopqrstu"]
    clave, impresos, _pantalla = elegir_en_relato(monkeypatch, ["2"], lista=lista, filas=10)
    assert clave == "b"
    assert "\x1b[2J\x1b[H" in impresos


def elegir_con_pila(monkeypatch, teclas):
    """Un menú raíz con un verbo que abre submenú, navegable con `resuelve`.

    Devuelve (clave, pantallas): cada pantalla es la terminal emulada
    en el momento de esperar una tecla.
    """
    raiz = [("verbo", "Un verbo…", ""), ("fin", "Elegir", "")]
    sub = [("a", "Todo", ""), ("b", "Una cosa", "")]
    pantallas: list[str] = []

    def resuelve(clave):
        if clave == "verbo":
            return ("Submenú", sub, None)
        if clave is None:  # Esc: el menú de arriba, en su sitio
            return ("Raíz", raiz, None)
        return None  # una decisión final

    pendientes = iter(teclas)
    term = Terminal()

    def tecla():
        pantallas.append(term.texto())
        return next(pendientes)

    monkeypatch.setattr(opciones_mod, "_leer_tecla", tecla)
    clave = elegir_opcion(
        "Raíz", raiz, entrada=input, salida=term.escribe, flechas=True,
        relato=True, resuelve=resuelve,
    )
    return clave, pantallas


def test_navegar_submenus_no_hace_crecer_la_pantalla(monkeypatch):
    """Entrar al submenú y volver con Esc, dos veces: la pantalla queda
    exactamente igual que al principio (issue 36: navegar no apila)."""
    teclas = ["\r", "\x1b", "\r", "\x1b", "2"]  # entrar, volver, entrar, volver, elegir
    clave, pantallas = elegir_con_pila(monkeypatch, teclas)
    assert clave == "fin"
    assert pantallas[0] == pantallas[2] == pantallas[4]  # la raíz, siempre en su sitio
    assert pantallas[1] == pantallas[3]  # y el submenú, también


def test_navegar_no_deja_restos_del_menu_anterior(monkeypatch):
    """El submenú reemplaza al menú: ni el título viejo ni renglones sueltos."""
    _clave, pantallas = elegir_con_pila(monkeypatch, ["\r", "\x1b", "2"])
    pantalla = pantallas[1]  # el submenú, ya dibujado donde estaba la raíz
    assert "Raíz" not in pantalla  # el título del menú anterior ya no está
    assert "Un verbo…" not in pantalla
    assert pantalla.count("Submenú") == 1  # y el nuevo título, escrito una vez


def test_con_aviso_esc_se_queda_dentro_del_menu(monkeypatch):
    pendientes = ["\x1b", "\r"]
    monkeypatch.setattr(opciones_mod, "_leer_tecla", lambda: pendientes.pop(0))
    salida: list[str] = []
    clave = elegir_opcion(
        "Prueba",
        OPCIONES,
        entrada=input,
        salida=salida.append,
        flechas=True,
        aviso_esc="Aquí no hay vuelta atrás.",
    )
    texto = "\n".join(salida)
    assert clave == "a"  # Esc no sacó del menú: siguió eligiendo
    assert "Aquí no hay vuelta atrás." in texto  # y quedó dicho por qué
    assert texto.count("Prueba") == 1  # sin apilar un bloque nuevo


def test_flecha_abajo_mueve_la_seleccion(monkeypatch):
    clave, salida = elegir_con_teclas(monkeypatch, ["\x1b[B", "\r"])
    assert clave == "b"
    # la descripción viaja con la opción
    assert any("el segundo" in linea for linea in salida)


def test_flechas_envuelven_de_arriba_a_abajo(monkeypatch):
    clave, _ = elegir_con_teclas(monkeypatch, ["\x1b[A", "\r"])
    assert clave == "c"


def test_flechas_envuelven_de_abajo_a_arriba(monkeypatch):
    clave, _ = elegir_con_teclas(
        monkeypatch, ["\x1b[B", "\x1b[B", "\x1b[B", "\r"]
    )
    assert clave == "a"


def test_un_digito_elige_al_vuelo(monkeypatch):
    clave, _ = elegir_con_teclas(monkeypatch, ["2"])
    assert clave == "b"


def test_esc_cancela_y_devuelve_el_cursor(monkeypatch):
    clave, salida = elegir_con_teclas(monkeypatch, ["\x1b"])
    assert clave is None
    assert salida[-1] == "\x1b[?25h"  # cursor restaurado


def test_la_tecla_q_tambien_cancela(monkeypatch):
    clave, _ = elegir_con_teclas(monkeypatch, ["q"])
    assert clave is None


def test_teclas_desconocidas_no_rompen_nada(monkeypatch):
    clave, _ = elegir_con_teclas(monkeypatch, ["x", "\x1b[D", " ", "\r"])
    assert clave == "a"


def test_ctrl_c_interrumpe_como_en_cualquier_terminal(monkeypatch):
    with pytest.raises(KeyboardInterrupt):
        elegir_con_teclas(monkeypatch, ["\x03"])


def test_redibujo_reusa_el_bloque(monkeypatch):
    """El título se pinta una vez y cada movimiento solo sube el cursor."""
    _clave, salida = elegir_con_teclas(monkeypatch, ["\x1b[B", "\x1b[B", "\r"])
    texto = "\n".join(salida)
    assert texto.count("Prueba") == 1  # el título no se repite: se reescribe el bloque
    subidas = [l for l in salida if l.startswith("\x1b[") and l.endswith("A")]
    assert len(subidas) == 2  # un redibujado por movimiento, sin apilar menús


def test_redibujado_no_deja_lineas_sueltas(monkeypatch):
    """Cada redibujado ocupa las mismas filas: la pista de teclas no se duplica."""
    term = Terminal()
    teclas = iter(["\x1b[B", "\r"])
    esperadas: list[str] = []

    def tecla():
        esperadas.append(term.texto())  # pantalla tal y como está al esperar
        return next(teclas)

    monkeypatch.setattr(opciones_mod, "_leer_tecla", tecla)
    elegir_opcion("Prueba", OPCIONES, entrada=input, salida=term.escribe, flechas=True)
    assert esperadas[-1].count("↑/↓") == 1


def test_flechas_false_fuerza_el_modo_tipeado():
    clave = elegir_opcion(
        "Prueba",
        OPCIONES,
        entrada=EntradaTipeada(["2"]),
        salida=lambda _t: None,
        flechas=False,
    )
    assert clave == "b"


def test_con_entrada_inyectada_se_detecta_modo_tipeado():
    """La autodetección nunca intenta flechas con entrada/salida falsas."""
    clave = elegir_opcion(
        "Prueba",
        OPCIONES,
        entrada=EntradaTipeada(["3"]),
        salida=lambda _t: None,
    )
    assert clave == "c"


@pytest.mark.skipif(os.name == "nt", reason="os.openpty no existe en Windows")
def test_el_modo_sin_buffer_conserva_el_salto_de_linea(monkeypatch):
    """Sin búfer de línea pero con salida intacta: el \\n devuelve el carro.

    Un modo raw completo dejaba los prints del menú en escalera (cada
    línea empezaba donde acabó la anterior) porque apagaba el
    post-procesado del terminal.
    """
    import sys
    import termios

    maestro, esclavo = os.openpty()

    class Teclado:
        def fileno(self):
            return esclavo

    monkeypatch.setattr(sys, "stdin", Teclado())
    try:
        with opciones_mod._modo_crudo():
            lflag = termios.tcgetattr(esclavo)[3]
            assert not lflag & termios.ICANON  # tecla a tecla, sin esperar Enter
            assert lflag & termios.OPOST  # pero el \n sigue devolviendo el carro
        lflag = termios.tcgetattr(esclavo)[3]
        assert lflag & termios.ICANON  # al salir, el terminal como estaba
    finally:
        os.close(maestro)
        os.close(esclavo)

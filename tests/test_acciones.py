"""El menú de acciones dentro del juego: flechas, Esc y el tipeado escondido."""

from __future__ import annotations

import aldamar.opciones as opciones_mod
from aldamar import __version__
from aldamar.juego import ESCRIBIR, OTRAS, Juego

from conftest import AVENTURA, EntradaTipeada

MENU_MINIMO = [
    ("mirar", "Mirar alrededor", ""),
    ("estado", "Estado", ""),
    ("salir", "Salir", ""),
]


def teclado(secuencia):
    """_leer_tecla sintético: consume la secuencia y luego siempre Enter."""
    pendientes = list(secuencia)
    return lambda: pendientes.pop(0) if pendientes else "\r"


def juego_flechas(monkeypatch, secuencia=(), opciones=None, lineas=(" ",)):
    """Partida forzada a flechas: teclas sintéticas + líneas para el tipeado.

    La primera línea es el nombre del héroe en el prólogo (vacío: el de
    siempre); las demás alimentan la opción "Escribir un comando…".
    """
    monkeypatch.setattr(opciones_mod, "_leer_tecla", teclado(secuencia))
    if opciones is not None:
        monkeypatch.setattr(Juego, "_opciones_juego", lambda self: opciones)
    salida: list[str] = []
    juego = Juego(
        AVENTURA,
        semilla=7,
        entrada=EntradaTipeada(list(lineas)),
        salida=salida.append,
        color=False,
        flechas=True,
    )
    return juego, salida


def test_el_menu_refleja_lo_que_hay_en_el_lugar(fabrica):
    juego, _ = fabrica(["ayuda", "salir"])
    claves = [c for c, _e, _d in juego._opciones_juego()]
    assert claves[0] == "mirar"
    assert any(c.startswith("ir ") for c in claves)  # los destinos del lugar
    assert "tomar provisiones" in claves  # hay objetos en el suelo de arranque
    assert "hablar belthar" in claves
    assert claves[-1] == OTRAS  # lo que no es gameplay vive en el submenú
    assert "guardar" not in claves and "estado" not in claves
    otras = [c for c, _e, _d in juego._opciones_otras()]
    assert "estado" in otras and "guardar" in otras and "ayuda" in otras
    assert otras[-1] == "salir"
    assert ESCRIBIR in otras  # el modo tipeado sigue ahí, escondido


def test_elegir_un_destino_del_menu_viaja(monkeypatch):
    juego, _ = juego_flechas(monkeypatch, ["2"], lineas=["", ""])
    juego.jugador.vida = juego.jugador.vida_max = 200
    juego._prologo()
    orden = juego._leer_orden("¿Qué haces?", "> ", juego._opciones_juego())
    assert orden == "ir 1"  # segundo renglón del menú: el primer destino
    juego._ejecutar(orden)
    assert juego.lugar != juego.av.lugar_inicial


def test_esc_avisa_y_el_menu_no_se_apila(monkeypatch):
    juego, salida = juego_flechas(monkeypatch, ["\x1b", "3"], opciones=MENU_MINIMO)
    juego.ciclo()
    texto = "\n".join(salida)
    assert juego.fin
    assert juego.lugar == juego.av.lugar_inicial  # Esc no movió de sitio
    assert "No hay vuelta atrás" in texto  # queda dicho por qué se queda
    assert texto.count("¿Qué haces?") == 1  # el menú no se vuelve a pintar


def test_tras_el_nombre_se_limpia_la_pantalla(monkeypatch):
    juego, salida = juego_flechas(monkeypatch, lineas=["", ""])
    juego._prologo()
    texto = "\n".join(salida)
    presentacion = AVENTURA.personajes[AVENTURA.jugador_inicial].presentacion
    assert texto.count("\x1b[2J\x1b[H") == 1  # una limpieza, la del nombre
    # el prólogo queda antes y la presentación después: se ve sola
    assert texto.index(AVENTURA.prologo[:15]) < texto.index("\x1b[2J\x1b[H") < texto.index(presentacion)


def test_la_cabecera_abre_cada_pantalla(monkeypatch):
    juego, salida = juego_flechas(monkeypatch, ["\x1b", "3"], opciones=MENU_MINIMO)
    juego._prologo()
    juego.ciclo()
    texto = "\n".join(salida)
    lugar = AVENTURA.lugares[AVENTURA.lugar_inicial].nombre
    assert f"Aldamar {__version__}" in texto  # primera línea: juego y versión
    cabecera = next(l for l in salida if l.startswith(juego.jugador.nombre) and "Vida" in l)
    assert f"Vida {juego.jugador.vida}/{juego.jugador.vida_max}" in cabecera
    assert f"{juego.jugador.monedas} monedas" in cabecera
    assert lugar in cabecera  # segunda línea: quién, cómo, cuánto y dónde


def test_el_modo_tipeado_no_lleva_cabecera(fabrica):
    juego, salida = fabrica(["", "ayuda", "salir"])
    juego.ciclo()
    assert not any("Aldamar " in l and __version__ in l for l in salida)


def test_las_otras_acciones_son_un_submenu_de_ida_y_vuelta(monkeypatch):
    opciones = [("mirar", "Mirar alrededor", ""), (OTRAS, "Otras acciones…", "")]
    juego, salida = juego_flechas(monkeypatch, ["2", "\x1b", "2", "7"], opciones=opciones)
    juego.ciclo()
    texto = "\n".join(salida)
    assert juego.fin  # la segunda visita terminó en "salir"
    assert texto.count("\nOtras acciones\n") == 2  # entró, volvió con Esc y reentró
    assert texto.count("¿Qué haces?") == 2  # el menú del juego, al inicio y al volver


def test_escribir_comando_mantiene_el_tipeado(monkeypatch):
    opciones = MENU_MINIMO[:2] + [(ESCRIBIR, "Escribir un comando…", ""), MENU_MINIMO[2]]
    juego, salida = juego_flechas(monkeypatch, ["3", "4"], opciones=opciones, lineas=["", "estado"])
    juego.ciclo()
    assert any("Vida:" in l for l in salida)  # ejecutó `estado` tipeado
    assert juego.fin


def test_la_ayuda_abre_pantalla_completa_y_esc_la_cierra(monkeypatch):
    juego, salida = juego_flechas(
        monkeypatch,
        ["\r", "\x1b", "2"],
        opciones=[("ayuda", "Ayuda", ""), ("salir", "Salir", "")],
    )
    monkeypatch.setattr(opciones_mod, "_es_interactivo", lambda e, s: True)
    juego.ciclo()
    texto = "\n".join(salida)
    assert "Comandos:" in texto
    assert "\x1b[?1049h" in texto and "\x1b[?1049l" in texto  # entra y sale de la pantalla llena
    assert juego.fin


def test_la_ayuda_tipeada_sale_en_el_diario(fabrica):
    juego, salida = fabrica(["", "ayuda", "salir"])  # la primera línea es el nombre
    juego.ciclo()
    texto = "\n".join(salida)
    assert "Comandos:" in texto
    assert "\x1b" not in texto  # sin terminal real: ni pantalla llena ni esperar teclas


def test_el_combate_se_navega_con_flechas(monkeypatch):
    juego, salida = juego_flechas(monkeypatch, lineas=["", ""])
    juego.jugador.vida = juego.jugador.vida_max = 200
    juego.enemigos[juego.lugar] = ["lobo"]
    juego._combate(["lobo"])
    assert not juego.enemigos[juego.lugar]  # Enter siempre elegía "Atacar"
    texto = "\n".join(salida)
    assert "Atacar" in texto  # el menú de combate ofreció sus opciones
    assert "Escribir un comando…" in texto
    assert "se abalanza" in texto

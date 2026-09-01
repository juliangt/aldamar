"""El menú principal: listas numeradas que validan lo que se responde."""

from __future__ import annotations

from aldamar.dificultad import obtener_dificultad
from aldamar.menu import Eleccion, elegir_opcion, menu_principal

from conftest import EntradaTipeada

OPCIONES = [
    ("nueva", "Nueva partida", ""),
    ("cargar", "Cargar partida", "retoma un archivo"),
    ("salir", "Salir", ""),
]


def elegir(lineas, opciones=OPCIONES):
    salida: list[str] = []
    clave = elegir_opcion(
        "Prueba", opciones, entrada=EntradaTipeada(lineas), salida=salida.append
    )
    return clave, salida


def test_elige_por_numero():
    clave, _ = elegir(["2"])
    assert clave == "cargar"


def test_elige_por_nombre_sin_importar_tildes_o_mayusculas():
    clave, _ = elegir(["nueva"])
    assert clave == "nueva"


def test_repregunta_si_la_respuesta_no_encaja():
    clave, salida = elegir(["teletransporte", "3"])
    assert clave == "salir"
    assert any("No entiendo" in linea for linea in salida)


def test_ignora_lineas_vacias_y_eof_devuelve_none():
    clave, _ = elegir(["", ""])
    assert clave is None


def test_la_descripcion_se_muestra_en_el_listado():
    _clave, salida = elegir(["1"])
    assert any("retoma un archivo" in linea for linea in salida)


def test_menu_principal_nueva_partida_flujo_completo():
    # 1) Nueva partida → 1) Corazón de Ceniza → 1) Tilo → 1) dificultad Paseo
    salida: list[str] = []
    eleccion = menu_principal(
        entrada=EntradaTipeada(["1", "1", "1", "1"]), salida=salida.append
    )
    assert eleccion == Eleccion(
        "nueva",
        aventura=eleccion.aventura,
        dificultad=obtener_dificultad("paseo"),
        personaje="tilo",
    )
    assert eleccion.aventura.id == "corazon_ceniza"


def test_menu_principal_ofrece_a_los_cuatro_heroes():
    salida: list[str] = []
    eleccion = menu_principal(
        entrada=EntradaTipeada(["1", "3"]),  # nueva partida; tercera en la lista: Dagna
        salida=salida.append,
        aventura="corazon_ceniza",
        dificultad="camino",
    )
    texto = "\n".join(salida)
    for nombre in ("Tilo", "Ithel", "Dagna Escudagris", "Ruy"):
        assert nombre in texto, f"falta {nombre} en la lista de héroes"
    assert eleccion.accion == "nueva"
    assert eleccion.personaje == "dagna"


def test_menu_principal_con_presets_solo_pregunta_lo_que_falta():
    # con aventura y dificultad prefijadas, "1" (nueva) y "1" (Tilo) llegan directo a jugar
    eleccion = menu_principal(
        entrada=EntradaTipeada(["1", "1"]),
        salida=lambda _t: None,
        aventura="corazon_ceniza",
        dificultad="camino",
    )
    assert eleccion.accion == "nueva"
    assert eleccion.aventura.id == "corazon_ceniza"
    assert eleccion.dificultad == obtener_dificultad("camino")
    assert eleccion.personaje == "tilo"


def test_menu_principal_preset_personaje_invalido_avisa_y_pregunta():
    # con héroe inválido, avisa y pregunta de la lista (el "1" cae en Tilo)
    eleccion = menu_principal(
        entrada=EntradaTipeada(["1", "1"]),
        salida=lambda _t: None,
        aventura="corazon_ceniza",
        dificultad="camino",
        personaje="rey_de_valoria",
    )
    assert eleccion.accion == "nueva"
    assert eleccion.personaje == "tilo"


def test_menu_principal_cargar_pide_archivo():
    eleccion = menu_principal(
        entrada=EntradaTipeada(["2", "mis_guardados.json"]),
        salida=lambda _t: None,
    )
    assert eleccion.accion == "cargar"
    assert eleccion.archivo == "mis_guardados.json"


def test_menu_principal_salir_y_eof():
    assert menu_principal(entrada=EntradaTipeada(["salir"]), salida=lambda _t: None).accion == "salir"
    assert menu_principal(entrada=EntradaTipeada([]), salida=lambda _t: None).accion == "salir"

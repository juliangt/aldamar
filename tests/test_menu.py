"""El menú principal: listas numeradas que validan lo que se responde."""

from __future__ import annotations

from aldamar.motor.dificultad import obtener_dificultad
from aldamar.interfaz.menu import Eleccion, elegir_opcion, menu_principal

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


def test_la_lista_de_heroes_muestra_la_ficha_completa():
    salida: list[str] = []
    menu_principal(
        entrada=EntradaTipeada(["1", "1"]),
        salida=salida.append,
        aventura="corazon_ceniza",
        dificultad="camino",
    )
    texto = "\n".join(salida)
    assert "¿Quién será tu héroe?" in texto
    # el texto completo de cada héroe, hasta su último renglón
    for cierre in (
        "a quien ya está de viaje",  # Tilo
        "viajeros ligeros",  # Ithel
        "un punto menos de vida",  # Dagna
        "en cada compra",  # Ruy
    ):
        assert cierre in texto, f"falta el cierre de ficha «{cierre}»"
    assert texto.count("Rasgo ·") == 3  # y los tres rasgos documentados


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


# ── flechas: Esc vuelve atrás con la pantalla limpia (issue 24) ──────────

def menu_flechas(monkeypatch, teclas):
    """menu_principal en modo flechas con teclas sintéticas."""
    import aldamar.interfaz.opciones as opciones_mod

    pendientes = list(teclas)
    monkeypatch.setattr(opciones_mod, "_leer_tecla", lambda: pendientes.pop(0))
    salida: list[str] = []
    eleccion = menu_principal(
        entrada=input, salida=salida.append, flechas=True, dificultad="camino"
    )
    return eleccion, salida


def test_esc_en_la_eleccion_de_heroe_vuelve_al_menu_principal(monkeypatch):
    # Enter (Nueva) → Enter (aventura) → Esc (héroe) → Esc (menú: salir)
    eleccion, salida = menu_flechas(monkeypatch, ["\r", "\r", "\x1b", "\x1b"])
    assert eleccion.accion == "salir"
    texto = "\n".join(salida)
    assert "¿Quién será tu héroe?" in texto
    assert "¿Qué aventura quieres vivir?" in texto
    # cada salida del menú dejó la pantalla limpia: nada se apila
    assert texto.count("\x1b[2J\x1b[H") == 4


def test_volver_atras_repinta_la_portada(monkeypatch):
    _, salida = menu_flechas(monkeypatch, ["\r", "\r", "\x1b", "\x1b"])
    texto = "\n".join(salida)
    # la portada vive una vez por pantalla: la inicial y la de la vuelta atrás
    assert texto.count("A L D A M A R") == 2


def test_el_bucle_del_menu_sobrevive_a_muchas_vueltas(monkeypatch):
    # dos idas y vueltas completas (aventuras → héroes → atrás) antes de salir
    teclas = ["\r", "\r", "\x1b", "\r", "\r", "\x1b", "\x1b"]
    eleccion, salida = menu_flechas(monkeypatch, teclas)
    assert eleccion.accion == "salir"
    texto = "\n".join(salida)
    assert texto.count("¿Qué aventura quieres vivir?") == 2
    assert texto.count("¿Quién será tu héroe?") == 2
    # la lista nunca se apila: cada redibujado parte de pantalla limpia
    assert texto.count("\x1b[2J\x1b[H") == 7

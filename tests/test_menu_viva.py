"""La entrada del modo «Aventura Viva» en el menú y sus pantallas.

El modo es opcional por contrato: sin Ollama, la pantalla
explica cómo encenderlo y no se crea ninguna sesión. Y la elección de
modelo respeta lo fijado por el jugador; con varios instalados y nada
fijado, pregunta.
"""

from __future__ import annotations

import pytest
from conftest import EntradaTipeada

from aldamar.interfaz.menu import menu_principal
from aldamar.motor import configuracion
from aldamar.motor.juego import main
from aldamar.viva import cronista
from aldamar.viva.cronista import ProveedorFalso
from aldamar.viva.interfaz import partida_viva

PROLOGO = "Prólogo de latón, dos párrafos y a jugar." * 2
EPILOGOS = {
    "muerte": "Muerte con nombre y apellido, en dos frases y algo más de ochenta caracteres.",
    "caida": "Caída por la grieta, en dos frases y también más de ochenta caracteres.",
}
PROSA_P1 = "El camino empieza aquí, con esta prosa recién salida del cronista."
DATOS_P1 = {
    "nombre": "el Sendero del Agua Parada",
    "hecho": "El héroe tomó el camino.",
    "situacion": "Dos direcciones, ninguna ayuda.",
    "pregunta": "¿Por dónde?",
    "opcion_1": "Seguir el agua",
    "opcion_2": "Cortar campo",
}


@pytest.fixture(autouse=True)
def entorno_limpio(monkeypatch, tmp_path):
    """Ni Ollama real ni restos de configuración: cada test, su mundo."""
    monkeypatch.delenv("ALDAMAR_MODELO", raising=False)
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    monkeypatch.chdir(tmp_path)


def test_el_menu_trae_la_entrada_del_modo_vivo():
    eleccion = menu_principal(
        entrada=EntradaTipeada(["2"]),
        salida=lambda _t: None,
    )
    assert eleccion.accion == "viva"


def test_sin_ollama_explica_y_no_crea_nada(monkeypatch):
    # disponible() False: ni siquiera se pregunta la premisa
    falso = ProveedorFalso([], disponible=False)
    monkeypatch.setattr(cronista, "proveedor_por_defecto", lambda: falso)
    pantalla: list[str] = []
    juego = partida_viva(
        entrada=EntradaTipeada([]),
        salida=pantalla.append,
        color=False,
        flechas=False,
        semilla=7,
    )
    assert juego is None
    assert falso.pedidos == []
    assert any("Ollama" in linea for linea in pantalla)


def test_sin_ollama_el_aviso_no_saca_del_juego(monkeypatch):
    """Elegir el modo vivo sin Ollama: aviso a pantalla completa y de vuelta
    al menú — no una salida del juego."""
    monkeypatch.setattr(
        cronista, "proveedor_por_defecto", lambda: ProveedorFalso([], disponible=False)
    )
    pantalla: list[str] = []
    main([], entrada=EntradaTipeada(["2", "salir"]), salida=pantalla.append)
    texto = "\n".join(pantalla)
    assert texto.count("Menú principal") == 2  # el menú se mostró otra vez
    assert "ollama pull" in texto
    assert texto.rstrip().endswith("Hasta pronto.")


def test_con_ollama_pero_sin_ningun_modelo_instalado_avisa_y_no_continua(monkeypatch):
    """El servicio arriba no basta: sin modelos, aviso concreto y al menú."""
    falso = ProveedorFalso([], instalados=[])
    monkeypatch.setattr(cronista, "proveedor_por_defecto", lambda: falso)
    pantalla: list[str] = []
    juego = partida_viva(
        entrada=EntradaTipeada([]),
        salida=pantalla.append,
        color=False,
        flechas=False,
        semilla=7,
    )
    assert juego is None
    assert falso.pedidos == []
    texto = "\n".join(pantalla)
    assert "ningún modelo instalado" in texto
    assert "ollama pull" in texto


def test_con_ollama_arranca_la_partida(monkeypatch):
    falso = ProveedorFalso([PROLOGO, EPILOGOS, PROSA_P1, DATOS_P1])
    monkeypatch.setattr(cronista, "proveedor_por_defecto", lambda: falso)
    juego = partida_viva(
        # un solo modelo instalado: ni pregunta de modelo
        entrada=EntradaTipeada(["1", "1", "camino"]),
        salida=lambda _t: None,
        color=False,
        flechas=False,
        semilla=7,
    )
    assert juego is not None
    assert juego.viva is not None
    assert juego.av.id.startswith("viva_")
    assert juego.personaje == "espada"
    assert juego.dificultad.clave == "camino"
    assert juego.av.lugares["p1"].descripcion == PROSA_P1


# ── la premisa propia, completada por el cronista ────────────────────────

PREMISA_PROPIA = {
    "titulo": "La Deuda del Farero",
    "antagonista": "el farero que no enciende",
    "corte": "el Farol Negro",
    "tono": "costero y paciente, de luces que no llegan",
}


def test_la_premisa_propia_la_completa_el_cronista(monkeypatch):
    falso = ProveedorFalso([PREMISA_PROPIA, PROLOGO, EPILOGOS, PROSA_P1, DATOS_P1])
    monkeypatch.setattr(cronista, "proveedor_por_defecto", lambda: falso)
    juego = partida_viva(
        entrada=EntradaTipeada(["propia", "una deuda de luz en la costa", "1", "camino"]),
        salida=lambda _t: None,
        color=False,
        flechas=False,
        semilla=7,
    )
    assert juego is not None
    assert juego.viva is not None
    premisa = juego.viva.premisa
    assert premisa.clave == "propia"
    assert premisa.texto == "una deuda de luz en la costa"
    assert premisa.titulo == "La Deuda del Farero"
    assert premisa.antagonista == "el farero que no enciende"
    assert premisa.corte == "el Farol Negro"
    assert any("deuda de luz" in pedido for pedido in falso.pedidos)  # se le pidió
    # y el jefe nació con la cara de ese antagonista
    assert juego.av.enemigos["guardian_cima"]["nombre"] == "El farero que no enciende"


def test_la_premisa_propia_sin_cronista_va_tal_cual(monkeypatch):
    falso = ProveedorFalso([])  # seco: ni completar la premisa
    monkeypatch.setattr(cronista, "proveedor_por_defecto", lambda: falso)
    juego = partida_viva(
        entrada=EntradaTipeada(["propia", "una deuda de luz en la costa", "1", "camino"]),
        salida=lambda _t: None,
        color=False,
        flechas=False,
        semilla=7,
    )
    assert juego is not None
    assert juego.viva is not None
    premisa = juego.viva.premisa
    assert premisa.titulo == "Una deuda de luz en la costa"
    assert premisa.antagonista == "lo que espera al final del camino"
    assert premisa.corte == "el lugar del final"
    assert any("deuda de luz" in pedido for pedido in falso.pedidos)


# ── la elección de modelo ────────────────────────────────────────────────


def _proveedor_varios(monkeypatch: pytest.MonkeyPatch) -> ProveedorFalso:
    falso = ProveedorFalso([PROLOGO, EPILOGOS, PROSA_P1, DATOS_P1])
    falso.instalados = ["llama3.1:8b", "qwen2.5:7b", "mistral-nemo:12b"]
    monkeypatch.setattr(cronista, "proveedor_por_defecto", lambda: falso)
    return falso


def test_con_varios_modelos_pregunta_y_usa_el_elegido(monkeypatch):
    _proveedor_varios(monkeypatch)
    juego = partida_viva(
        # «2» en el menú de modelos = qwen2.5:7b; luego premisa, héroe y ritmo
        entrada=EntradaTipeada(["2", "1", "1", "camino"]),
        salida=lambda _t: None,
        color=False,
        flechas=False,
        semilla=7,
    )
    assert juego is not None
    assert juego.viva.proveedor.modelo == "qwen2.5:7b"
    assert configuracion.cargar().modelo_viva is None  # elegir no es fijar


def test_fijar_modelo_lo_escribe_en_configuracion(monkeypatch, tmp_path):
    _proveedor_varios(monkeypatch)
    juego = partida_viva(
        # «fijar» → segundo menú: «qwen» (por nombre) → el resto del arranque
        entrada=EntradaTipeada(["fijar", "qwen", "1", "1", "camino"]),
        salida=lambda _t: None,
        color=False,
        flechas=False,
        semilla=7,
    )
    assert juego is not None
    assert juego.viva.proveedor.modelo == "qwen2.5:7b"
    assert (
        configuracion.cargar(tmp_path / configuracion.ARCHIVO_CONFIGURACION).modelo_viva
        == "qwen2.5:7b"
    )


def test_con_un_modelo_fijado_no_se_pregunta(monkeypatch):
    falso = _proveedor_varios(monkeypatch)
    monkeypatch.setenv("ALDAMAR_MODELO", "elfijo:8b")
    juego = partida_viva(
        # tres respuestas y ni una más: sin menú de modelo en medio
        entrada=EntradaTipeada(["1", "1", "camino"]),
        salida=lambda _t: None,
        color=False,
        flechas=False,
        semilla=7,
    )
    assert juego is not None
    assert juego.viva.proveedor is falso

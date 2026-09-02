"""El arranque: el informe del lanzador no se ve, salvo en modo debug."""

from __future__ import annotations

import aldamar.motor.juego as juego_mod
from aldamar.motor.juego import main
from aldamar.interfaz.opciones import LIMPIAR

from conftest import EntradaTipeada


def arrancar(monkeypatch, interactivo: bool, argv: list[str]) -> list[str]:
    """Corre main() hasta «salir» y devuelve lo escrito, línea a línea."""
    monkeypatch.setattr(juego_mod, "_es_interactivo", lambda entrada, salida: interactivo)
    salida: list[str] = []
    main(["--sin-flechas", *argv], entrada=EntradaTipeada(["salir"]), salida=salida.append)
    return salida


def test_arrancando_interactivo_la_pantalla_queda_limpia(monkeypatch):
    salida = arrancar(monkeypatch, interactivo=True, argv=[])
    assert LIMPIAR in salida


def test_en_modo_debug_no_se_limpia(monkeypatch):
    salida = arrancar(monkeypatch, interactivo=True, argv=["--debug"])
    assert LIMPIAR not in salida


def test_la_variable_de_entorno_tambien_activa_el_modo_debug(monkeypatch):
    monkeypatch.setenv("ALDAMAR_DEBUG", "1")
    salida = arrancar(monkeypatch, interactivo=True, argv=[])
    assert LIMPIAR not in salida


def test_la_variable_de_entorno_acepta_un_cero_explícito(monkeypatch):
    monkeypatch.setenv("ALDAMAR_DEBUG", "0")
    salida = arrancar(monkeypatch, interactivo=True, argv=[])
    assert LIMPIAR in salida


def test_en_tuberia_no_se_manda_ningun_codigo_de_pantalla(monkeypatch):
    salida = arrancar(monkeypatch, interactivo=False, argv=[])
    assert not any("\x1b[" in linea for linea in salida)

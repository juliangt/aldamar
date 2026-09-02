"""El catálogo de rasgos vive en `rasgos.json` y el motor lo aplica genérico."""

from __future__ import annotations

import pytest

from aldamar.juego import Juego
from aldamar.personajes import Enemigo
from aldamar.rasgos import RASGOS, cargar_rasgos


def _saco(vida: int) -> Enemigo:
    return Enemigo(clave="saco", nombre="saco de entrenamiento", vida=vida, vida_max=10, ataque=0)


# ── El catálogo de serie ─────────────────────────────────────────────────


def test_el_catalogo_trae_los_tres_dones_de_serie():
    assert set(RASGOS) == {"ojo_halcon", "piel_piedra", "lengua_mercado"}
    halcon = RASGOS["ojo_halcon"]
    assert halcon.nombre == "Ojo de halcón"
    assert halcon.dano_extra == 1
    assert halcon.cond_vida_enemigo == 50  # enemigo con más de la mitad de su vida
    assert RASGOS["piel_piedra"].dano_recibido_menos == 1
    assert RASGOS["lengua_mercado"].descuento_compra == 1
    for rasgo in RASGOS.values():
        assert rasgo.descripcion.strip()  # lo que el estado muestra de cada don


# ── Un don nuevo: puro dato, el motor lo aplica por el camino genérico ───


DON_PRUEBA = {
    "escudo_runico": {
        "nombre": "Escudo rúnico",
        "descripcion": "recibes 2 puntos menos de daño de cualquier golpe",
        "efecto": {"dano_recibido_menos": 2},
    }
}


def test_un_don_de_prueba_declarado_en_datos_carga(monkeypatch):
    cargado = cargar_rasgos(DON_PRUEBA, "<prueba>")
    assert cargado["escudo_runico"].dano_recibido_menos == 2
    assert cargado["escudo_runico"].dano_extra == 0  # lo que no declara, no usa


def test_un_don_de_prueba_declarado_en_datos_aplica(monkeypatch, fabrica):
    monkeypatch.setitem(RASGOS, "escudo_runico", cargar_rasgos(DON_PRUEBA)["escudo_runico"])
    juego, _ = fabrica([], personaje="tilo")
    juego.jugador.rasgos = ["escudo_runico"]
    assert juego._modificador("dano_recibido_menos") == 2
    assert juego._recibe(juego.jugador, 6) == 4  # 6 − escudo rúnico (2)


def test_dos_dones_se_suman_en_un_solo_camino(monkeypatch, fabrica):
    monkeypatch.setitem(RASGOS, "escudo_runico", cargar_rasgos(DON_PRUEBA)["escudo_runico"])
    juego, _ = fabrica([], personaje="dagna")  # dagna ya trae piel de piedra (1)
    juego.jugador.rasgos = ["piel_piedra", "escudo_runico"]
    assert juego._recibe(juego.jugador, 9) == 5  # 9 − capa gris (1) − piel (1) − escudo (2)


def test_la_condicion_mira_la_vida_del_objetivo(monkeypatch, fabrica):
    datos = {
        "cazador_primero": {
            "nombre": "Cazador primero",
            "descripcion": "+3 de daño mientras el enemigo conserve más de tres cuartos de vida",
            "efecto": {"dano_extra": 3, "condicion": {"vida_enemigo_mayor_que": 75}},
        }
    }
    monkeypatch.setitem(RASGOS, "cazador_primero", cargar_rasgos(datos)["cazador_primero"])
    juego, _ = fabrica([], personaje="tilo")
    juego.jugador.rasgos = ["cazador_primero"]
    assert juego._modificador("dano_extra", objetivo=_saco(9)) == 3  # 90% de vida
    assert juego._modificador("dano_extra", objetivo=_saco(7)) == 0  # 70%: ya no


def test_el_descuento_declarado_aplica_y_nunca_deja_el_precio_en_cero(monkeypatch, fabrica):
    datos = {
        "trato_hecho": {
            "nombre": "Trato hecho",
            "descripcion": "pagas 5 monedas menos en cada compra",
            "efecto": {"descuento_compra": 5},
        },
        "regalo_del_gremio": {
            "nombre": "Regalo del gremio",
            "descripcion": "pagas 20 monedas menos en cada compra",
            "efecto": {"descuento_compra": 20},
        },
    }
    cargado = cargar_rasgos(datos)
    for clave, rasgo in cargado.items():
        monkeypatch.setitem(RASGOS, clave, rasgo)
    juego, _ = fabrica([], personaje="tilo")
    juego.lugar = "rioclaro"
    juego.jugador.monedas = 50
    juego.jugador.rasgos = ["trato_hecho"]
    juego._comprar("antorcha")  # cuesta 8; con el don, 3
    assert juego.jugador.monedas == 47
    juego.jugador.inventario.remove("antorcha")
    juego.jugador.rasgos = ["regalo_del_gremio"]
    juego._comprar("antorcha")  # 8 − 20 se queda en 1: la tienda no regala
    assert juego.jugador.monedas == 46


# ── El cargador del catálogo, exigente como el de aventuras ─────────────


def test_la_raiz_debe_ser_un_objeto():
    with pytest.raises(ValueError, match="la raíz del archivo debe ser un objeto"):
        cargar_rasgos([1, 2], "<prueba>")


def test_cada_don_necesita_nombre_y_descripcion():
    with pytest.raises(ValueError, match="'x': falta el campo 'nombre'"):
        cargar_rasgos({"x": {"descripcion": "d"}}, "<prueba>")
    with pytest.raises(ValueError, match="'x': falta el campo 'descripcion'"):
        cargar_rasgos({"x": {"nombre": "n"}}, "<prueba>")


def test_campo_de_efecto_desconocido_nombra_lo_valido():
    datos = {"x": {"nombre": "n", "descripcion": "d", "efecto": {"volar": 1}}}
    with pytest.raises(ValueError, match="campos de efecto desconocidos: volar.*dano_extra"):
        cargar_rasgos(datos, "<prueba>")


def test_los_modificadores_son_enteros_mayores_a_cero():
    base = {"nombre": "n", "descripcion": "d"}
    with pytest.raises(ValueError, match="'dano_extra' debe ser mayor a cero"):
        cargar_rasgos({"x": base | {"efecto": {"dano_extra": 0}}}, "<prueba>")
    with pytest.raises(ValueError, match="debe ser entero"):
        cargar_rasgos({"x": base | {"efecto": {"descuento_compra": "mucho"}}}, "<prueba>")


def test_condicion_sin_efecto_no_tiene_sentido():
    datos = {"x": {"nombre": "n", "descripcion": "d", "efecto": {"condicion": {"vida_enemigo_mayor_que": 50}}}}
    with pytest.raises(ValueError, match="declara 'condicion' pero ningún efecto"):
        cargar_rasgos(datos, "<prueba>")


def test_condicion_desconocida_y_fuera_de_rango():
    base = {"nombre": "n", "descripcion": "d"}
    datos = base | {"efecto": {"dano_extra": 1, "condicion": {"llueva": 1}}}
    with pytest.raises(ValueError, match="condiciones desconocidas: llueva"):
        cargar_rasgos({"x": datos}, "<prueba>")
    datos = base | {"efecto": {"dano_extra": 1, "condicion": {"vida_enemigo_mayor_que": 0}}}
    with pytest.raises(ValueError, match="porcentaje entre 1 y 99"):
        cargar_rasgos({"x": datos}, "<prueba>")


def test_un_don_sin_efecto_es_admitido_solo_narrativo():
    cargado = cargar_rasgos(
        {"bariton": {"nombre": "Baritón", "descripcion": "tus cantares suenan graves"}}, "<prueba>"
    )
    assert cargado["bariton"].dano_extra == 0

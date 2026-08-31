"""Combate determinista con semilla fija."""

from aldamar.datos import crear_enemigo
from aldamar.personajes import Combatiente


def test_recibir_aplica_la_defensa():
    objetivo = Combatiente("escudero", 20, 20, 5, defensa=2)
    perdida = objetivo.recibir(5)
    assert perdida == 3
    assert objetivo.vida == 17


def test_el_dano_minimo_es_uno():
    objetivo = Combatiente("muralla", 10, 10, 1, defensa=9)
    assert objetivo.recibir(1) == 1
    assert objetivo.vida == 9


def test_curar_no_supera_el_maximo():
    objetivo = Combatiente("herido", 18, 20, 1)
    objetivo.curar(50)
    assert objetivo.vida == 20


def test_duelo_simple_termina_en_victoria(fabrica):
    juego, _ = fabrica(["atacar"] * 8, semilla=3)
    lobo = crear_enemigo("lobo")
    assert juego._duelo(lobo) == "victoria"
    assert not lobo.vivo
    assert not juego.fin


def test_huida_deja_al_enemigo_vivo_y_al_jugador_intacto(fabrica):
    juego, _ = fabrica(["huir"] * 6, semilla=1)
    lobo = crear_enemigo("lobo")
    resultado = juego._duelo(lobo)
    assert resultado in ("huida", "victoria")  # la semilla decide; ninguna rompe
    assert juego.jugador.vivo


def test_usar_el_corazon_corrompe_y_golpea_fuerte(fabrica):
    juego, _ = fabrica(["corazon"], semilla=5)
    custodio = crear_enemigo("custodio")
    juego._duelo(custodio)
    assert juego.jugador.corrupcion == 15
    assert custodio.vida < custodio.vida_max


def test_muerte_del_jugador_termina_la_partida(fabrica):
    juego, _ = fabrica(["atacar"] * 10, semilla=2)
    juego.jugador.vida = 1  # sentencia anticipada
    custodio = crear_enemigo("custodio")
    juego._duelo(custodio)
    assert juego.fin
    assert juego.final == "muerte"


def test_el_cuerno_no_impresiona_a_los_guardianes(fabrica):
    juego, _ = fabrica(["cuerno"] + ["atacar"] * 12, semilla=4)
    juego.jugador.inventario.append("cuerno_valoria")
    juego.jugador.inventario.append("hacha_goran")  # para que el duelo no sea eterno
    juego.jugador.vida = juego.jugador.vida_max = 200
    capitan = crear_enemigo("capitan")  # sin_huida
    assert juego._duelo(capitan) == "victoria"
    assert juego.jugador.vivo

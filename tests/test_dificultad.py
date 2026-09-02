"""Las dificultades ajustan el balance sin tocar el contenido."""

from __future__ import annotations

from aldamar.motor.dificultad import DIFICULTADES, Dificultad, obtener_dificultad

from conftest import AVENTURA, CAMINO, EntradaTipeada
from aldamar.motor.juego import Juego


def test_camino_es_el_balance_original():
    dif = obtener_dificultad(None)
    assert dif.clave == "camino"
    neutra = Dificultad(clave="x", nombre="x", descripcion="x")
    for campo in (
        "vida_jugador",
        "ataque_jugador",
        "monedas",
        "vida_enemigos",
        "ataque_enemigos",
        "corrupcion",
        "curacion",
    ):
        assert getattr(dif, campo) == getattr(neutra, campo) == 1.0


def test_hay_tres_dificultades_registradas():
    assert set(DIFICULTADES) == {"paseo", "camino", "ceniza"}


def test_obtener_dificultad_desconocida_explica_las_validas():
    try:
        obtener_dificultad("imposible")
    except KeyError as e:
        assert "paseo" in str(e) and "camino" in str(e) and "ceniza" in str(e)
    else:
        raise AssertionError("debía fallar")


def test_crear_enemigo_ajusta_vida_y_ataque():
    base = AVENTURA.enemigos["lobo"]
    paseo = AVENTURA.crear_enemigo("lobo", DIFICULTADES["paseo"])
    ceniza = AVENTURA.crear_enemigo("lobo", DIFICULTADES["ceniza"])
    normal = AVENTURA.crear_enemigo("lobo", CAMINO)
    assert (normal.vida, normal.vida_max, normal.ataque) == (base["vida"], base["vida"], base["ataque"])
    assert paseo.vida < normal.vida < ceniza.vida
    assert paseo.ataque < normal.ataque < ceniza.ataque
    assert paseo.vida == paseo.vida_max  # nace entero


def test_los_guardianes_siguen_sin_huida_en_cualquier_dificultad():
    for dif in DIFICULTADES.values():
        assert AVENTURA.crear_enemigo("custodio", dif).sin_huida


def test_crear_jugador_ajusta_ficha_del_heroe():
    paseo = AVENTURA.crear_jugador("tilo", DIFICULTADES["paseo"])
    ceniza = AVENTURA.crear_jugador("tilo", DIFICULTADES["ceniza"])
    normal = AVENTURA.crear_jugador("tilo", CAMINO)
    assert (normal.vida, normal.vida_max, normal.monedas) == (45, 45, 10)
    assert paseo.vida > normal.vida > ceniza.vida
    assert paseo.monedas > normal.monedas > ceniza.monedas
    assert paseo.inventario == normal.inventario == ["corazon"]  # el guion no cambia


def test_personaje_desconocido_explica_los_disponibles():
    try:
        AVENTURA.crear_jugador("rey_de_valoria", CAMINO)
    except KeyError as e:
        assert "tilo" in str(e)
    else:
        raise AssertionError("debía fallar")


def test_corruptear_aplica_el_multiplicador_de_dificultad():
    def juego_con(clave: str) -> Juego:
        return Juego(
            AVENTURA,
            dificultad=obtener_dificultad(clave),
            semilla=1,
            entrada=EntradaTipeada([]),
            salida=lambda _t: None,
            color=False,
        )

    ceniza = juego_con("ceniza")
    ceniza.corruptear(8)
    assert ceniza.jugador.corrupcion == 10  # 8 × 1.25

    paseo = juego_con("paseo")
    paseo.corruptear(10)
    assert paseo.jugador.corrupcion == 6  # 10 × 0.6

    camino = juego_con("camino")
    camino.corruptear(15)
    assert camino.jugador.corrupcion == 15  # la partida scripted no cambia


def test_la_curacion_aplica_el_multiplicador_al_usar_consumibles():
    juego = Juego(
        AVENTURA,
        dificultad=obtener_dificultad("paseo"),  # curacion 1.25: provisiones curan 15 → 19
        semilla=1,
        entrada=EntradaTipeada([]),
        salida=lambda _t: None,
        color=False,
    )
    juego.jugador.vida = 20
    juego.jugador.inventario.append("provisiones")
    juego._usar("provisiones")
    assert juego.jugador.vida == 39

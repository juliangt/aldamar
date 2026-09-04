"""Las dificultades ajustan el balance sin tocar el contenido."""

from __future__ import annotations

import pytest
from conftest import AVENTURA, CAMINO, EntradaTipeada

from aldamar.motor.dificultad import (
    DIFICULTAD_POR_DEFECTO,
    DIFICULTADES,
    Dificultad,
    cargar_dificultades,
    obtener_dificultad,
)
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


# ── el catálogo vive en datos/dificultades.json ──────────────────────────

def test_el_json_real_declara_los_tres_perfiles_historicos():
    """Las claves de siempre, en el orden del archivo (el del menú)."""
    assert list(DIFICULTADES) == ["paseo", "camino", "ceniza"]
    assert DIFICULTAD_POR_DEFECTO == "camino"
    for dif in DIFICULTADES.values():
        assert dif.nota is None or dif.nota.strip()  # las notas del balance llegaron al JSON


DIF_PRUEBA = {
    "por_defecto": "prueba",
    "dificultades": {
        "camino": {"nombre": "El camino", "descripcion": "tal cual"},
        "prueba": {
            "nombre": "Dificultad de prueba",
            "descripcion": "enemigos de doble vida; los multiplicadores ausentes valen 1.0",
            "vida_enemigos": 2.0,
        },
    },
}


def test_una_dificultad_de_prueba_declarada_en_datos_carga():
    catalogo, por_defecto = cargar_dificultades(DIF_PRUEBA, "<prueba>")
    assert por_defecto == "prueba"
    assert list(catalogo) == ["camino", "prueba"]  # el orden del menú es el del archivo
    prueba = catalogo["prueba"]
    assert prueba.vida_enemigos == 2.0
    assert prueba.vida_jugador == prueba.ataque_jugador == 1.0  # lo que falta, 1.0


def test_una_dificultad_de_prueba_declarada_en_datos_aplica():
    catalogo, _ = cargar_dificultades(DIF_PRUEBA, "<prueba>")
    normal = AVENTURA.crear_enemigo("lobo", catalogo["camino"])
    doble = AVENTURA.crear_enemigo("lobo", catalogo["prueba"])
    assert doble.vida == normal.vida * 2
    assert doble.ataque == normal.ataque  # el multiplicador que no declara no toca nada
    heroe = AVENTURA.crear_jugador("tilo", catalogo["prueba"])
    base = AVENTURA.crear_jugador("tilo", CAMINO)
    assert (heroe.vida, heroe.ataque, heroe.monedas) == (base.vida, base.ataque, base.monedas)


# ── un JSON roto nombra archivo y campo ──────────────────────────────────

def test_la_raiz_no_es_un_objeto():
    with pytest.raises(ValueError, match="la raíz del archivo debe ser un objeto"):
        cargar_dificultades([1, 2], "<prueba>")


def test_falta_la_clave_por_defecto():
    datos = {"dificultades": {"camino": {"nombre": "x", "descripcion": "x"}}}
    with pytest.raises(ValueError, match="por_defecto"):
        cargar_dificultades(datos, "<prueba>")


def test_el_por_defecto_no_existe_en_los_perfiles():
    datos = {
        "por_defecto": "fantasma",
        "dificultades": {"camino": {"nombre": "x", "descripcion": "x"}},
    }
    with pytest.raises(ValueError, match=r"'por_defecto' apunta a 'fantasma'.*válidas: camino"):
        cargar_dificultades(datos, "<prueba>")


def test_sin_perfiles_no_hay_juego():
    for datos in ({"por_defecto": "camino"}, {"por_defecto": "camino", "dificultades": {}}):
        with pytest.raises(ValueError, match="al menos un perfil"):
            cargar_dificultades(datos, "<prueba>")


def test_un_multiplicador_desconocido_nombra_los_validos():
    datos = {
        "por_defecto": "camino",
        "dificultades": {"camino": {"nombre": "x", "descripcion": "x", "suerte": 2.0}},
    }
    with pytest.raises(ValueError, match="multiplicador desconocido 'suerte'.*vida_jugador"):
        cargar_dificultades(datos, "<prueba>")


def test_los_multiplicadores_deben_ser_numeros_mayores_a_cero():
    base = {"nombre": "x", "descripcion": "x"}
    for valor in (0, -1.5, "mucho", True):
        datos = {
            "por_defecto": "camino",
            "dificultades": {"camino": {**base, "corrupcion": valor}},
        }
        with pytest.raises(ValueError, match="'corrupcion'"):
            cargar_dificultades(datos, "<prueba>")


def test_nombre_y_descripcion_no_pueden_quedar_vacios():
    base = {"por_defecto": "camino"}
    for hueco in ("nombre", "descripcion"):
        datos = {
            **base,
            "dificultades": {"camino": {"nombre": "x", "descripcion": "x", hueco: ""}},
        }
        with pytest.raises(ValueError, match=f"{hueco!r}"):
            cargar_dificultades(datos, "<prueba>")


def test_campos_de_raiz_desconocidos_se_rechazan():
    datos = {
        "por_defecto": "camino",
        "dificultades": {"camino": {"nombre": "x", "descripcion": "x"}},
        "sorpresa": True,
    }
    with pytest.raises(ValueError, match="campos desconocidos: sorpresa"):
        cargar_dificultades(datos, "<prueba>")


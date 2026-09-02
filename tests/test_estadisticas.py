"""Las estadísticas de partida: los números del playtesting (issue 21).

La partida ya lo sabe todo, pero no lo escribe: aquí se comprueba que
el informe de `--stats` dice lo que el balance necesita — combates uno
a uno con turnos y daño, gasto frente a tiendas, corrupción final,
decisiones — y que sin la bandera no se escribe nada.
"""

from __future__ import annotations

import json

from aldamar.motor.estadisticas import Estadisticas
from aldamar.motor.juego import main

from conftest import EntradaTipeada

# hasta el puente y su lobo, y de vuelta: dos dueños de duelo en un viaje
HASTA_EL_LOBO = ["", "ir este", "tomar todo", "ir este", "atacar", "atacar", "atacar", "tomar todo"]
HASTA_EL_ESPECTRO = ["ir sur", "prometer", "ir norte", "ir norte", "atacar", "atacar", "atacar", "atacar"]


def test_el_duelo_del_lobo_queda_anotado(fabrica):
    juego, _ = fabrica(HASTA_EL_LOBO + ["salir"], semilla=7)
    juego.ciclo()
    s = juego.stats
    assert len(s.combates) == 1
    duelo = s.combates[0]
    assert duelo["lugar"] == "puente"
    assert duelo["enemigo"] == "lobo"
    assert duelo["resultado"] == "victoria"
    assert duelo["turnos"] == 2  # dos pasadas del duelo: el lobo cayó en dos golpes
    assert duelo["dano_infligido"] == s.dano_infligido > 0
    assert duelo["dano_recibido"] == s.dano_recibido
    assert s.monedas_recogidas > 0  # las monedas del puente
    assert s.monedas_gastadas == 0
    assert s._en_curso is None  # el duelo queda cerrado


def test_cada_enemigo_es_su_propio_duelo(fabrica):
    juego, _ = fabrica(HASTA_EL_LOBO + HASTA_EL_ESPECTRO + ["salir"], semilla=7)
    juego.ciclo()
    s = juego.stats
    assert [(c["lugar"], c["enemigo"], c["resultado"]) for c in s.combates] == [
        ("puente", "lobo", "victoria"),
        ("bosque", "espectro", "victoria"),
    ]
    # los totales son la suma de los duelos, ni un punto perdido
    assert s.dano_infligido == sum(c["dano_infligido"] for c in s.combates)
    assert s.dano_recibido == sum(c["dano_recibido"] for c in s.combates)


def test_comprar_deja_la_huella_del_gasto(fabrica):
    juego, _ = fabrica([])
    juego.lugar = "rioclaro"
    bolsillo = juego.jugador.monedas
    juego._comprar("antorcha")
    assert juego.stats.monedas_gastadas == bolsillo - juego.jugador.monedas == 8
    assert juego.stats.compras == ["antorcha"]


def test_el_resumen_reune_lo_que_la_partida_ya_sabia(fabrica):
    juego, _ = fabrica(HASTA_EL_LOBO + HASTA_EL_ESPECTRO + ["salir"], semilla=7)
    juego.ciclo()
    r = juego.stats.resumen(juego)
    assert r["aventura"] == "corazon_ceniza"
    assert r["dificultad"] == "camino"
    assert r["personaje"] == "tilo"
    assert r["heroe"]["corrupcion"] == juego.jugador.corrupcion
    assert r["heroe"]["nivel"] == juego.jugador.nivel
    assert r["final"] is None  # se salió: la partida quedó a medias
    assert "vegaverde" in r["lugares_visitados"] and "bosque" in r["lugares_visitados"]
    assert r["tiendas_visitadas"] == ["rioclaro"]  # se pasó por la tienda
    assert "encargo" in r["decisiones"] and "promesa" in r["decisiones"]
    assert r["companeros_caidos"] == []
    assert r["totales"]["combates"] == 2
    assert r["totales"]["monedas_gastadas"] == 0


def test_el_informe_se_escribe_en_json(tmp_path, fabrica):
    ruta = str(tmp_path / "estadisticas.json")
    juego, _ = fabrica(HASTA_EL_LOBO + ["salir"], semilla=7)
    juego.ciclo()
    escrito = juego.stats.escribir(juego, ruta)
    with open(ruta, encoding="utf-8") as f:
        leido = json.load(f)
    assert leido == escrito == juego.stats.resumen(juego)


def test_la_bandera_stats_escribe_y_sin_ella_no(tmp_path, monkeypatch):
    """Con --stats el informe aparece al terminar; sin ella, nada."""
    ruta = tmp_path / "estadisticas.json"

    def arrancar(argv, lineas):
        salida: list[str] = []
        main(
            ["--aventura", "corazon_ceniza", "--dificultad", "camino", "--semilla", "7", *argv],
            entrada=EntradaTipeada(lineas),
            salida=salida.append,
        )
        return salida

    salida = arrancar(["--stats", str(ruta)], HASTA_EL_LOBO + ["salir"])
    informe = json.loads(ruta.read_text(encoding="utf-8"))
    assert informe["combates"][0]["enemigo"] == "lobo"
    assert informe["totales"]["dano_infligido"] > 0
    assert any("Estadísticas de la partida" in linea for linea in salida)

    ruta_sin = tmp_path / "sin_stats.json"
    arrancar([], HASTA_EL_LOBO + ["salir"])
    assert not ruta_sin.exists()


def test_stats_sin_valor_toma_el_nombre_por_defecto(tmp_path, monkeypatch):
    """--stats a secas escribe en estadisticas.json del directorio actual."""
    import os

    anterior = os.getcwd()
    os.chdir(tmp_path)
    try:
        salida: list[str] = []
        main(
            ["--aventura", "corazon_ceniza", "--dificultad", "camino", "--semilla", "7", "--stats"],
            entrada=EntradaTipeada(["salir"]),
            salida=salida.append,
        )
    finally:
        os.chdir(anterior)
    assert (tmp_path / "estadisticas.json").exists()
    assert any("estadisticas.json" in linea for linea in salida)


# ── el recolector, a pelo: los casos que el juego no pisa ────────────────

def test_el_recolector_no_apunta_ni_dano_ni_duelos_vacios():
    s = Estadisticas()
    s.golpe_infligido(0)
    s.golpe_recibido(-3)
    s.cierra_combate("victoria")  # sin duelo abierto: no pasa nada
    assert s.combates == [] and s.dano_infligido == 0 and s.dano_recibido == 0

    s.empieza_combate("puente", "lobo", "Lobo de sombra")
    s.cuenta_turno()
    s.golpe_infligido(4)
    s.golpe_recibido(2)
    s.cierra_combate("huida")
    assert s.combates == [{
        "lugar": "puente",
        "enemigo": "lobo",
        "nombre": "Lobo de sombra",
        "turnos": 1,
        "dano_infligido": 4,
        "dano_recibido": 2,
        "resultado": "huida",
    }]
    assert s.dano_infligido == 4 and s.dano_recibido == 2

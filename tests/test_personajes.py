"""Los héroes jugables: fichas distintas, rasgos con efecto real."""

from __future__ import annotations

import pytest

from aldamar.aventura import PersonajeInicial
from aldamar.juego import Juego
from aldamar.personajes import RASGOS, Enemigo

from conftest import AVENTURA, CAMINO, EntradaTipeada


def test_hay_cuatro_heroes_y_todos_cargan_el_corazon():
    assert set(AVENTURA.personajes) == {"tilo", "ithel", "dagna", "ruy"}
    for ficha in AVENTURA.personajes.values():
        assert "corazon" in ficha.inventario  # el amuleto, al cuello desde el arranque
        assert ficha.titulo and ficha.presentacion.strip()
        for r in ficha.rasgos:
            assert r in RASGOS, f"{ficha.nombre} usa un rasgo desconocido: {r}"


def test_cada_heroe_tiene_su_historia_propia():
    for clave, ficha in AVENTURA.personajes.items():
        assert ficha.trato and ficha.quien  # el "quien" lleva artículo: para los epílogos
        if clave == AVENTURA.jugador_inicial:
            continue  # Tilo hereda el prólogo de la aventura
        assert ficha.prologo and "Vegaverde" in ficha.prologo
        assert ficha.texto_nombre and "{nombre}" in ficha.texto_nombre


def test_los_rasgos_estan_documentados_en_la_presentacion():
    for ficha in AVENTURA.personajes.values():
        for r in ficha.rasgos:
            assert RASGOS[r].nombre in ficha.presentacion


def test_las_estadisticas_respetan_el_diseno():
    esperado = {
        "tilo": (45, 4, 10),
        "ithel": (36, 4, 12),
        "dagna": (60, 3, 5),
        "ruy": (45, 4, 12),
    }
    for clave, (vida, ataque, monedas) in esperado.items():
        jugador = AVENTURA.crear_jugador(clave, CAMINO)
        assert (jugador.vida, jugador.vida_max) == (vida, vida)
        assert (jugador.ataque, jugador.monedas) == (ataque, monedas)
        assert jugador.rasgos == AVENTURA.personajes[clave].rasgos


def test_la_diversidad_entre_heroes_es_real():
    tilo = AVENTURA.crear_jugador("tilo", CAMINO)
    ithel = AVENTURA.crear_jugador("ithel", CAMINO)
    dagna = AVENTURA.crear_jugador("dagna", CAMINO)
    ruy = AVENTURA.crear_jugador("ruy", CAMINO)
    # la arquera pega más (trae hoja sylva) y aguanta menos
    assert ithel.vida < tilo.vida
    assert "hoja_sylva" in ithel.inventario
    # la guerrera aguanta todo y tiene el bolsillo vacío
    assert dagna.vida > tilo.vida
    assert dagna.ataque < tilo.ataque and dagna.monedas < tilo.monedas
    # el errante viaja con recursos: provisiones y antorcha de arranque
    assert "provisiones" in ruy.inventario and "antorcha" in ruy.inventario


def test_un_rasgo_desconocido_se_rechaza_al_crear_al_jugador():
    AVENTURA.personajes["falso"] = PersonajeInicial(
        clave="falso", nombre="Falso", titulo="x", presentacion="x", rasgos=["volar"]
    )
    try:
        with pytest.raises(ValueError, match="volar"):
            AVENTURA.crear_jugador("falso", CAMINO)
    finally:
        del AVENTURA.personajes["falso"]


# ── Los efectos mecánicos de cada rasgo ──────────────────────────────────


def test_piel_de_piedra_mitiga_cada_golpe(fabrica):
    juego, _ = fabrica([], personaje="dagna")
    assert juego._recibe(juego.jugador, 6) == 4  # 6 − capa gris (1) − piel de piedra (1)
    juego.jugador.inventario.remove("capa_gris")
    assert juego._recibe(juego.jugador, 6) == 5  # el rasgo solo
    assert juego._recibe(juego.jugador, 1) == 1  # el golpe nunca se anula del todo


def _saco(vida: int) -> Enemigo:
    return Enemigo(clave="saco", nombre="saco de entrenamiento", vida=vida, vida_max=10, ataque=0)


def test_ojo_de_halcon_castiga_al_enemigo_entero(fabrica):
    # misma semilla, dos sacos: uno entero y otro a la mitad; la única
    # diferencia entre los golpes es el +1 del rasgo
    juego_entero, _ = fabrica([], personaje="ithel", semilla=5)
    juego_herido, _ = fabrica([], personaje="ithel", semilla=5)
    assert juego_entero._golpea(juego_entero.jugador, _saco(10)) == (
        juego_herido._golpea(juego_herido.jugador, _saco(5)) + 1
    )


def test_sin_ojo_de_halcon_no_hay_bonus(fabrica):
    juego_entero, _ = fabrica([], personaje="tilo", semilla=5)
    juego_herido, _ = fabrica([], personaje="tilo", semilla=5)
    assert juego_entero._golpea(juego_entero.jugador, _saco(10)) == (
        juego_herido._golpea(juego_herido.jugador, _saco(5))
    )


def test_lengua_de_mercado_ahorra_una_moneda_por_compra(fabrica):
    juego, _ = fabrica([], personaje="ruy")
    juego.lugar = "rioclaro"
    juego.jugador.monedas = 50
    juego._comprar("antorcha")
    assert juego.jugador.monedas == 43  # la antorcha cuesta 8, no 9 ni 7: 8 − 1

    juego2, _ = fabrica([], personaje="tilo")  # sin el rasgo se paga el precio justo
    juego2.lugar = "rioclaro"
    juego2.jugador.monedas = 50
    juego2._comprar("antorcha")
    assert juego2.jugador.monedas == 42


# ── Los rasgos y las voces se notan en la partida ────────────────────────


def test_el_estado_muestra_los_rasgos(fabrica):
    juego, salida = fabrica([], personaje="dagna")
    juego._estado()
    texto = "\n".join(salida)
    assert "Piel de piedra" in texto
    assert "Dagna Escudagris · guerrera goran" in texto


def test_belthar_se_dirige_a_cada_quien_por_su_trato(fabrica):
    for personaje, trato in (("tilo", "jardinero"), ("dagna", "guerrera"), ("ruy", "errante")):
        juego, salida = fabrica([], personaje=personaje)
        juego._hablar("belthar")
        texto = "\n".join(salida)
        assert f"escúchame, {trato}" in texto


def test_el_epilogo_de_muerte_nombra_al_heroe_como_se_debe(fabrica):
    juego, salida = fabrica(["atacar"] * 10, personaje="dagna", semilla=2)
    juego.jugador.vida = 1  # sentencia anticipada
    juego._duelo(juego.crear_enemigo("custodio"))
    assert juego.final == "muerte"
    assert "la guerrera que se atrevió" in " ".join("\n".join(salida).split())


def test_ithel_abate_al_lobo_de_un_solo_golpe(fabrica):
    # hoja sylva + ojo de halcón: el primer flechazo ya es letal contra un lobo
    juego, _ = fabrica(["atacar"], personaje="ithel", semilla=3)
    lobo = juego.crear_enemigo("lobo")
    assert juego._duelo(lobo) == "victoria"
    assert not lobo.vivo
    assert juego.jugador.vida == juego.jugador.vida_max  # el enemigo ni se movió


def test_dagna_aguanta_el_duelo_del_puente(fabrica):
    juego, _ = fabrica(["atacar"] * 6, personaje="dagna", semilla=3)
    lobo = juego.crear_enemigo("lobo")
    assert juego._duelo(lobo) == "victoria"
    assert juego.jugador.vivo
    # con capa y piel de piedra, cada contraataque del lobo cuesta 4 como mucho
    assert juego.jugador.vida >= juego.jugador.vida_max - 8


def test_al_cargar_la_partida_se_recuperan_los_rasgos(tmp_path, fabrica):
    ruta = str(tmp_path / "partida.json")
    juego, _ = fabrica(["", "tomar todo", f"guardar {ruta}", "salir"], semilla=9, personaje="ithel")
    juego.ciclo()

    juego2 = Juego.desde_archivo(
        ruta, entrada=EntradaTipeada([]), salida=lambda _t: None, color=False
    )
    assert juego2.personaje == "ithel"
    assert juego2.jugador.rasgos == ["ojo_halcon"]
    assert juego2.jugador.vida == juego.jugador.vida

"""Partida completa scripted: de Vegaverde a la cumbre del Monte Umbak."""

from __future__ import annotations

import json

from aldamar.dificultad import obtener_dificultad
from aldamar.juego import Juego, main

from conftest import EntradaTipeada

RUTA_BASE = [
    "Tilo",
    "tomar todo",  # vegaverde: provisiones, capa gris, monedas
    "ir este",  # molino
    "tomar todo",
    "ir este",  # puente de piedra: lobo de sombra
    "atacar",
    "atacar",
    "atacar",
    "tomar todo",  # monedas del puente
    "ir sur",  # rioclaro
    "comprar espada corta",
    "comprar antorcha",
    "descansar",
    "ir norte",  # puente, ya limpio
    "ir norte",  # bosque umbrío: espectro
    "atacar",
    "atacar",
    "atacar",
    "atacar",
    "hablar sylvana",
    "reclutar sylvana",
    "tomar todo",  # hierbas, antorcha, monedas
    "ir sur",  # puente
    "ir sur",  # rioclaro
    "descansar",
    "comprar provisiones",
    "ir sur",  # valoria: consejo (estandarte)
    "reclutar aldric",
    "ir este",  # minas de Barrok: trasgos
    "atacar",
    "atacar",
    "atacar",
    "atacar",
    "atacar",
    "atacar",
    "reclutar torkan",
    "tomar todo",  # hacha goran, monedas
    "ir este",  # ciénagas del olvido: espectros (+corrupción)
    "atacar",
    "atacar",
    "atacar",
    "atacar",
    "atacar",
    "atacar",
    "ir norte",  # torre de Belthar: ritual
    "descansar",
    "ir sur",  # ciénagas otra vez (+corrupción, sin enemigos)
    "ir este",  # yermos de ceniza: lóberos
    "atacar",
    "atacar",
    "corazon",  # la tentación, una vez
    "atacar",
    "atacar",
    "atacar",
    "atacar",
    "atacar",
    "atacar",
    "usar provisiones",
    "ir este",  # monte Umbak: el Custodio Pálido
    "atacar",
    "atacar",
    "atacar",
    "atacar",
    "atacar",
    "atacar",
    "atacar",
    "atacar",
]


def test_partida_completa_hasta_la_victoria(fabrica):
    juego, salida = fabrica(RUTA_BASE + ["destruir"], semilla=7)
    juego.ciclo()
    texto = "\n".join(salida)
    assert juego.fin
    assert juego.final and "victoria" in juego.final
    assert "— FIN —" in texto
    # con corrupción baja (16%), el epílogo es el de la victoria sin cicatriz
    assert juego.jugador.corrupcion < 60
    plano = " ".join(texto.split())
    assert "El Jardín que venció a la Sombra" in plano


def test_reclamar_en_la_cumbre_tiene_su_propio_final(fabrica):
    juego, salida = fabrica(RUTA_BASE + ["reclamar"], semilla=7)
    juego.ciclo()
    texto = "\n".join(salida)
    assert juego.final == "la Sombra nueva"
    assert "trono vacío" in texto
    assert "— FIN —" in texto


def test_guardar_y_cargar_preserva_el_estado(tmp_path, fabrica):
    ruta = str(tmp_path / "partida.json")
    juego, _ = fabrica(["", "tomar todo", f"guardar {ruta}", "salir"], semilla=9)
    juego.ciclo()
    assert (tmp_path / "partida.json").exists()

    juego2, salida2 = fabrica(["", f"cargar {ruta}", "estado", "salir"], semilla=1)
    juego2.ciclo()
    texto = "\n".join(salida2)
    assert "Partida cargada" in texto
    assert juego2.lugar == juego.lugar == "vegaverde"
    assert juego2.jugador.inventario == juego.jugador.inventario
    assert juego2.jugador.monedas == juego.jugador.monedas
    assert juego2.jugador.corrupcion == juego.jugador.corrupcion

    # el guardado recuerda en qué aventura y con qué dificultad se juega
    guardado = json.loads((tmp_path / "partida.json").read_text(encoding="utf-8"))
    assert guardado["aventura"] == "corazon_ceniza"
    assert guardado["dificultad"] == "camino"
    assert guardado["personaje"] == "tilo"


def test_cargar_recupera_aventura_y_dificultad(tmp_path, fabrica):
    ruta = str(tmp_path / "ceniza.json")
    juego, _ = fabrica(
        ["", "guardar " + ruta, "salir"],
        semilla=3,
        dificultad=obtener_dificultad("ceniza"),
    )
    juego.ciclo()

    juego2 = Juego.desde_archivo(
        ruta,
        entrada=EntradaTipeada([]),
        salida=lambda _t: None,
        color=False,
    )
    assert juego2.av.id == "corazon_ceniza"
    assert juego2.dificultad.clave == "ceniza"
    assert juego2.personaje == "tilo"
    assert juego2.jugador.vida == juego.jugador.vida
    assert juego2.reanudada


def test_partida_completa_a_traves_del_menu_de_arranque():
    """E2E: menú principal (nueva → aventura → héroe → dificultad) y victoria."""
    salida: list[str] = []
    lineas = ["1", "1", "1", "2"] + RUTA_BASE + ["destruir"]  # tilo; camino = opción 2
    main(["--semilla", "7", "--sin-color"], entrada=EntradaTipeada(lineas), salida=salida.append)
    texto = "\n".join(salida)
    assert "A L D A M A R" in texto  # la portada del menú apareció
    assert "¿Quién será tu héroe?" in texto
    assert "¿A qué ritmo quieres caminar?" in texto
    assert "— FIN —" in texto
    assert "El Jardín que venció a la Sombra" in " ".join(texto.split())


def test_partida_completa_con_ruy_el_errante(fabrica):
    """Otro héroe, otra voz, misma suerte: la aventura se puede acabar igual."""
    # primera línea: se conserva el nombre de la ficha (Ruy); luego, Belthar
    lineas = ["", "hablar belthar"] + RUTA_BASE[1:] + ["destruir"]
    juego, salida = fabrica(lineas, semilla=7, personaje="ruy")
    juego.ciclo()
    texto = "\n".join(salida)
    assert juego.fin
    assert juego.final and "victoria" in juego.final
    # el prólogo y el trato de Belthar son los del errante
    assert "el pliego de un viejo falro" in texto
    assert "escúchame, errante" in texto
    assert "— FIN —" in texto

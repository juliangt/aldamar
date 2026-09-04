"""Partida completa scripted: de Vegaverde a la cumbre del Monte Umbak."""

from __future__ import annotations

import json

from conftest import AVENTURA, CAMINO, EntradaTipeada

from aldamar.motor.dificultad import obtener_dificultad
from aldamar.motor.juego import Juego, main

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
    "ir sur",  # rioclaro: el encargo de Dorotea
    "prometer",
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
    "ir sur",  # valoria: el consejo (juramento del estandarte)
    "alianza",
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
    # la pantalla de cierre: remate, epílogo con aire y menú para seguir
    assert "¡La noche retrocede!" in texto
    assert "Tu historia queda contada: «victoria pura»" in texto
    assert "¿Y ahora qué?" in texto and "Jugar otra vez" in texto
    # con corrupción baja (16%), el epílogo es el de la victoria sin cicatriz
    assert juego.jugador.corrupcion < 60
    plano = " ".join(texto.split())
    assert "El Jardín que venció a la Sombra" in plano


def test_reclamar_en_la_cumbre_tiene_su_propio_final(fabrica):
    juego, salida = fabrica(RUTA_BASE + ["reclamar"], semilla=7)
    juego.ciclo()
    texto = "\n".join(salida)
    assert juego.final == "la Sombra nueva"
    assert "trono vacío" in texto  # el epílogo, ahora en la pantalla de cierre
    assert "Así acaba este cantar" in texto  # el remate de un final nombrado
    assert "«la Sombra nueva»" in texto


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


def test_partida_completa_a_traves_del_menu_de_arranque(tmp_path):
    """E2E: menú principal (nueva → aventura → héroe → dificultad) y victoria.

    Al ganar, el legado queda escrito donde se le diga: la serie sabe
    que este héroe juró la Alianza."""
    salida: list[str] = []
    ruta_legado = str(tmp_path / "legado.json")
    lineas = ["1", "1", "1", "2"] + RUTA_BASE + ["destruir"]  # tilo; camino = opción 2
    main(
        ["--semilla", "7", "--sin-color"],
        entrada=EntradaTipeada(lineas),
        salida=salida.append,
        legado_ruta=ruta_legado,
    )
    texto = "\n".join(salida)
    assert "A L D A M A R" in texto  # la portada del menú apareció
    assert "¿Quién será tu héroe?" in texto
    assert "¿A qué ritmo quieres caminar?" in texto
    assert "¿Y ahora qué?" in texto  # la pantalla de cierre ofrece seguir
    assert "El Jardín que venció a la Sombra" in " ".join(texto.split())

    legado = json.loads((tmp_path / "legado.json").read_text(encoding="utf-8"))
    assert legado["aventura"] == "corazon_ceniza"
    assert legado["juramento"] is True  # la Alianza, jurada en Valoria
    assert "grieta" not in legado  # la corona se quedó donde duerme
    assert legado["nombre"]  # el nombre del héroe viaja con la fama


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
    assert "Tu historia queda contada: «victoria pura»" in texto  # el cierre


# ── el Corazón a la altura del motor: decisiones, emboscadas y grieta ───

def test_el_encargo_de_dorotea_deja_bandera_y_tercio(fabrica):
    juego, _ = fabrica(["prometer"])
    juego.av.eventos["encargo"](juego, juego.aqui())
    assert juego.flags == {"encargo": True, "promesa": True}
    assert "tercio" in juego.jugador.inventario
    juego.av.eventos["encargo"](juego, juego.aqui())  # una sola vez
    assert juego.jugador.inventario.count("tercio") == 1


def test_el_consejo_ofrece_jurar_o_deposito(fabrica):
    juego, _ = fabrica(["alianza"])
    juego.av.eventos["consejo"](juego, juego.aqui())
    assert juego.flags == {"consejo": True, "alianza": True}
    assert "estandarte" in juego.jugador.inventario

    juego2, _ = fabrica(["deposito"])
    juego2.av.eventos["consejo"](juego2, juego2.aqui())
    assert juego2.flags == {"consejo": True, "deposito": True}
    assert "estandarte" in juego2.jugador.inventario  # el paño, de un modo u otro


def test_la_emboscada_de_la_aguja_castiga_el_deposito(fabrica):
    juego, _ = fabrica(["deposito"])
    juego.flags["deposito"] = True
    juego.av.eventos["ceniza_sabe"](juego, juego.av.lugares["aguja"])
    assert juego.enemigos["aguja"] == ["capitan", "espectro", "espectro"]

    juego2, _ = fabrica(["alianza"])
    juego2.flags["alianza"] = True
    juego2.av.eventos["ceniza_sabe"](juego2, juego2.av.lugares["aguja"])
    assert juego2.enemigos["aguja"] == ["capitan"]  # la Alianza cubre


def test_la_corona_cuesta_grieta_y_se_cobra_en_los_yermos(fabrica):
    juego, _ = fabrica(["tomarla"])
    juego.av.eventos["corona"](juego, juego.aqui())
    assert juego.flags["coronado"] and "corona_plata" in juego.jugador.inventario
    assert juego.jugador.corrupcion == 6  # (+6 corrupción, dice el texto)

    juego.av.eventos["coronado"](juego, juego.av.lugares["yerma"])
    assert juego.enemigos["yerma"] == ["lobero", "lobero", "espectro", "espectro"]

    juego2, _ = fabrica(["dejarla"])
    juego2.av.eventos["corona"](juego2, juego2.aqui())
    assert "coronado" not in juego2.flags and juego2.jugador.corrupcion == 0
    juego2.av.eventos["coronado"](juego2, juego2.av.lugares["yerma"])
    assert juego2.enemigos["yerma"] == ["lobero", "lobero"]


def test_la_grieta_se_siente_en_el_camino(fabrica):
    # Torkan huele el humo de quien usó el Corazón; el limpio no lo lee
    juego, salida = fabrica([])
    juego.jugador.corruptear(15)  # una vez de corazon basta
    juego.av.eventos["forja"](juego, juego.aqui())
    assert "Hay humo colgado de ti" in "\n".join(salida)

    juego2, salida2 = fabrica([])
    juego2.av.eventos["forja"](juego2, juego2.aqui())
    assert "Hay humo colgado de ti" not in "\n".join(salida2)
    assert "viene de fragua y no de guerra" in "\n".join(salida2)


def test_el_umbral_de_los_yermos_reconoce_al_muy_tocado(fabrica):
    juego, salida = fabrica([])
    juego.jugador.corruptear(40)
    juego.av.eventos["umbral"](juego, juego.av.lugares["yerma"])
    assert "Ya eres de aquí" in "\n".join(salida)

    juego2, salida2 = fabrica([])
    juego2.av.eventos["umbral"](juego2, juego2.av.lugares["yerma"])
    assert "Ya eres de aquí" not in "\n".join(salida2)
    assert "el polvo todavía lo sabe" in "\n".join(salida2)


def test_el_custodio_pelea_en_dos_fases_y_el_capitan_silba_el_mandoble():
    custodio = AVENTURA.crear_enemigo("custodio", CAMINO)
    assert custodio.sin_huida and len(custodio.fases) == 1  # la ficha base y una transición
    segunda = custodio.fases[0]
    assert segunda.nombre == "el Custodio, abierto"
    assert any(h.tipo == "curarse" for h in segunda.habilidades)
    capitan = AVENTURA.crear_enemigo("capitan", CAMINO)
    assert any(h.tipo == "golpe_fuerte" for h in capitan.habilidades)
    espectro = AVENTURA.crear_enemigo("espectro", CAMINO)
    assert any(h.tipo == "veneno" for h in espectro.habilidades)


def test_el_brindis_final_requiere_la_promesa(fabrica):
    juego, salida = fabrica(["brindis"])
    juego.flags["promesa"] = True
    juego.av.eventos["final"](juego, juego.aqui())
    assert juego.fin and juego.final == "la victoria compartida"
    assert "tercio de Dorotea" in "\n".join(salida)

    juego2, _ = fabrica(["brindis", "destruir"])
    juego2.av.eventos["final"](juego2, juego2.aqui())
    assert juego2.fin and juego2.final == "victoria pura"  # sin promesa, no se ofrece


def test_partida_completa_con_la_aguja_el_deposito_y_el_brindis(fabrica):
    """El otro camino: paño en depósito (la Aguja lo cobra), la corona
    donde duerme y la victoria brindada con el tercio de Dorotea."""
    G6, G12 = ["atacar"] * 6, ["atacar"] * 12
    lineas = (
        ["", "tomar todo"]
        + ["ir este", "tomar todo"]
        + ["ir este"] + G6 + ["tomar todo"]
        + ["ir sur", "prometer", "comprar espada corta", "comprar antorcha", "descansar"]
        + ["ir norte", "ir norte"] + G6 + ["tomar todo", "reclutar sylvana"]
        + ["ir sur", "ir sur", "descansar", "comprar provisiones", "comprar provisiones"]
        + ["ir sur", "deposito", "reclutar aldric"]
        + ["ir este"] + G6 + ["tomar todo", "reclutar torkan"]
        + ["ir este"] + G6
        + ["ir norte", "descansar"]
        + ["ir sur", "ir este"] + G6 + ["usar provisiones"] + G6 + ["tomar todo"]
        + ["ir norte", "dejarla"] + G6 + ["usar provisiones"] + G12   # Aguja: emboscada + Capitán
        + ["ir sur", "ir este"] + ["atacar"] * 8 + ["usar provisiones"] + G12  # el Custodio, abierto
        + ["brindis"]
    )
    juego, salida = fabrica(lineas, semilla=7)
    juego.ciclo()
    texto = "\n".join(salida)
    assert juego.fin and juego.final == "la victoria compartida"
    assert "dos espectros que sabían de esperas" in " ".join(texto.split())
    assert "el Custodio, abierto" in texto  # la segunda fase del jefe
    assert juego.enemigos["umbak"] == []  # los lóberos de la corona: solo si se toma

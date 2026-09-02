"""Progresión: experiencia, niveles y equipamiento elegido (issue #17).

El héroe que llega al Monte Umbak ya no es el que salió de Vegaverde:
los enemigos caídos pagan experiencia, la curva sube el ataque y la
vida, y el equipo lleva puesto lo que el jugador decide, no lo mejor
del inventario.
"""

from __future__ import annotations

import json

from aldamar.dificultad import DIFICULTADES, obtener_dificultad
from aldamar.juego import Juego
from aldamar.personajes import SUBIDA_ATAQUE, SUBIDA_VIDA, XP_NIVEL

from conftest import AVENTURA, CAMINO, EntradaTipeada


def _juego(lineas: list[str] | None = None, semilla: int = 7, dificultad=None, personaje=None):
    salida: list[str] = []
    juego = Juego(
        AVENTURA,
        dificultad=dificultad,
        personaje=personaje,
        semilla=semilla,
        entrada=EntradaTipeada(list(lineas or [])),
        salida=salida.append,
        color=False,
    )
    return juego, salida


def test_la_curva_es_corta_y_creciente():
    assert len(XP_NIVEL) == 4  # del 2 al 5: subidas contadas
    assert list(XP_NIVEL) == sorted(XP_NIVEL)
    assert len(set(XP_NIVEL)) == len(XP_NIVEL)


def test_ganar_experiencia_sub_de_nivel_y_sube_stats():
    juego, salida = _juego()
    j = juego.jugador
    vida_antes = j.vida = 20
    juego._conceder_experiencia("lobo")  # 12 XP: aún sin nivel
    assert j.nivel == 1 and j.experiencia == 12

    juego._conceder_experiencia("espectro")  # 18 más: 30, justo el nivel 2
    assert j.nivel == 2
    ataque_base = AVENTURA.crear_jugador("tilo", CAMINO).ataque
    assert j.ataque == ataque_base + SUBIDA_ATAQUE
    assert j.vida_max == 45 + SUBIDA_VIDA
    assert j.vida == vida_antes + SUBIDA_VIDA  # subir sana lo que añade
    assert "nivel 2" in "\n".join(salida)


def test_la_curva_se_agota_en_el_nivel_5():
    juego, salida = _juego()
    j = juego.jugador
    for _ in range(20):  # mucha más XP de la que la curva pide
        juego._conceder_experiencia("custodio")
    assert j.nivel == len(XP_NIVEL) + 1 == 5
    assert "nivel 5" in "\n".join(salida)
    # el nivel máximo deja de pedir umbral: el progreso se cuenta igual
    assert str(j.experiencia) in j.progreso_xp() and "máximo" in j.progreso_xp()


def test_la_dificultad_ajusta_la_experiencia():
    paseo, _ = _juego(dificultad=DIFICULTADES["paseo"])
    camino, _ = _juego()
    ceniza, _ = _juego(dificultad=DIFICULTADES["ceniza"])
    paseo._conceder_experiencia("lobo")
    camino._conceder_experiencia("lobo")
    ceniza._conceder_experiencia("lobo")
    assert paseo.jugador.experiencia > camino.jugador.experiencia > 0
    assert ceniza.jugador.experiencia < camino.jugador.experiencia


def test_ganar_un_enemigo_en_combate_paga_su_experiencia():
    juego, salida = _juego(["atacar"] * 5)
    juego.jugador.vida = juego.jugador.vida_max = 100
    juego.enemigos[juego.lugar] = ["lobo"]
    juego._combate()
    assert juego.jugador.experiencia == 12  # el lobo paga 12 en camino
    assert "Ganas experiencia: 12" in "\n".join(salida)


def test_el_equipo_equipado_manda_no_lo_mejor_del_inventario():
    juego, _ = _juego()
    juego.jugador.inventario += ["hoja_sylva", "espada_corta"]  # +4 y +2
    juego.jugador.equipado["arma"] = "espada_corta"
    assert juego.bonus_arma() == 2
    assert juego.ataque_total() == juego.jugador.ataque + 2


def test_equipar_cambia_el_bonus_y_desequipar_lo_quita():
    juego, salida = _juego(["", "equipar hoja sylva", "salir"])
    juego.jugador.inventario += ["hoja_sylva", "espada_corta"]
    juego.jugador.equipado["arma"] = "espada_corta"
    juego.ciclo()
    assert juego.jugador.equipado["arma"] == "hoja_sylva"
    assert juego.bonus_arma() == 4
    assert "Empuñas" in "\n".join(salida)

    juego2, salida2 = _juego(["", "desequipar arma", "salir"])
    juego2.jugador.inventario += ["hoja_sylva"]
    juego2.jugador.equipado["arma"] = "hoja_sylva"
    juego2.ciclo()
    assert "arma" not in juego2.jugador.equipado
    assert juego2.bonus_arma() == 0
    assert "Guardas" in "\n".join(salida2)


def test_equipar_lo_que_no_es_equipo_no_se_deja():
    juego, salida = _juego(["", "equipar provisiones", "salir"])
    juego.jugador.inventario.append("provisiones")
    juego.ciclo()
    assert "arma" not in juego.jugador.equipado
    assert "no se equipa" in "\n".join(salida)


def test_al_empezar_se_viste_lo_mejor_de_la_ficha():
    ithel, _ = _juego(personaje="ithel")
    ficha = AVENTURA.personajes["ithel"]
    armas = [k for k in ficha.inventario if AVENTURA.items[k]["tipo"] == "arma"]
    if armas:  # la arquera trae hoja sylva: se empuña sola al arrancar
        assert ithel.jugador.equipado["arma"] in ficha.inventario
        assert ithel.bonus_arma() == max(AVENTURA.items[k]["bonus"] for k in armas)


def test_adquirir_con_el_sitio_vacio_viste_y_avisa():
    juego, salida = _juego()
    juego.adquirir("hoja_sylva")
    assert juego.jugador.equipado["arma"] == "hoja_sylva"
    assert "Empuñas: hoja sylva" in "\n".join(salida)


def test_adquirir_con_el_sitio_ocupado_no_cambia_lo_empunado():
    juego, salida = _juego()
    juego.jugador.equipado["arma"] = "espada_corta"
    juego.jugador.inventario.append("espada_corta")
    juego.adquirir("hoja_sylva")
    assert juego.jugador.equipado["arma"] == "espada_corta"  # decidir es del jugador
    assert not any("Empuñas" in s for s in salida)


def test_tomar_una_pieza_cuando_el_sitio_esta_vacio_la_viste():
    juego, salida = _juego(["", "tomar todo"])
    juego.ciclo()
    # Vegaverde guarda una capa gris: sin armadura puesta, se ciñe sola
    assert juego.jugador.equipado.get("armadura") == "capa_gris"
    assert "Te ciñes" in "\n".join(salida)


def test_el_estado_muestra_nivel_experiencia_y_envenenado():
    juego, salida = _juego(["", "estado", "salir"])
    juego.jugador.envenenar(2, 3)
    juego.ciclo()
    texto = "\n".join(salida)
    assert "Nivel: 1" in texto
    assert "Experiencia: 0/30" in texto
    assert "Envenenado: −2 por turno (3 turnos)" in texto


def test_el_guardado_lleva_nivel_experiencia_y_equipo(tmp_path):
    ruta = str(tmp_path / "partida.json")
    juego, _ = _juego(["", f"guardar {ruta}", "salir"])
    juego.jugador.experiencia = 95
    juego.jugador.nivel = 3
    juego.jugador.inventario.append("espada_corta")
    juego.jugador.equipado["arma"] = "espada_corta"
    juego.ciclo()
    guardado = json.loads((tmp_path / "partida.json").read_text(encoding="utf-8"))
    assert guardado["experiencia"] == 95
    assert guardado["nivel"] == 3
    assert guardado["equipado"] == {"arma": "espada_corta"}

    juego2, _ = _juego(["", f"cargar {ruta}", "salir"])
    juego2.ciclo()
    assert juego2.jugador.experiencia == 95
    assert juego2.jugador.nivel == 3
    assert juego2.jugador.equipado == {"arma": "espada_corta"}
    assert juego2.bonus_arma() == 2


def test_cargar_un_guardado_viejo_migra_sin_perder_el_equipo(tmp_path):
    """Los guardados de antes del issue 17 vestían lo mejor del inventario."""
    ruta = str(tmp_path / "vieja.json")
    juego, _ = _juego(["", f"guardar {ruta}", "salir"])
    juego.jugador.inventario += ["espada_corta", "capa_gris"]
    juego.ciclo()
    estado = json.loads((tmp_path / "vieja.json").read_text(encoding="utf-8"))
    # un guardado de antes del versionado tampoco trae campo 'version':
    # guardado.preparar lo trata como esquema 0 y lo migra a la actual
    for campo in ("experiencia", "nivel", "equipado", "version"):
        del estado[campo]
    (tmp_path / "vieja.json").write_text(json.dumps(estado, ensure_ascii=False), encoding="utf-8")

    juego2, _ = _juego(["", f"cargar {ruta}", "salir"])
    juego2.ciclo()
    assert juego2.jugador.nivel == 1 and juego2.jugador.experiencia == 0
    # la migración viste lo mejor que había, como hacía el motor viejo
    assert juego2.jugador.equipado["arma"] == "espada_corta"
    assert juego2.jugador.equipado["armadura"] == "capa_gris"


def test_desequipado_a_proposito_se_mantiene_tras_guardar_y_cargar(tmp_path):
    ruta = str(tmp_path / "vacia.json")
    juego, _ = _juego(["", f"guardar {ruta}", "salir"])
    juego.jugador.inventario.append("espada_corta")
    juego.jugador.equipado.pop("arma", None)
    juego.ciclo()

    juego2, _ = _juego(["", f"cargar {ruta}", "salir"])
    juego2.ciclo()
    assert "arma" not in juego2.jugador.equipado  # la decisión se respeta
    assert juego2.bonus_arma() == 0


def test_un_nivel_nuevo_se_siente_en_el_combate():
    juego, _ = _juego(["atacar"] * 6)
    lobo = AVENTURA.crear_enemigo("lobo", CAMINO)
    antes = juego.ataque_total()
    for _ in range(3):  # 120 XP: nivel 3
        juego._conceder_experiencia("custodio")
    assert juego.jugador.nivel == 3
    assert juego.ataque_total() > antes
    juego.jugador.vida = juego.jugador.vida_max = 200
    assert juego._duelo(lobo) == "victoria"

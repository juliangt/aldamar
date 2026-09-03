"""Tests de los easter eggs y secretos de Aldamar (issue #9).

- Diálogos con capas: insistir al hablar revela la leyenda del escribano.
- Comando secreto global `cuervo` / `cuervos`: progreso narrativo, semilla 42 y combate.
- Sabor narrativo en objetos: `texto_uso` al usar reliquias o equipo fuera de combate.
- Validación exigente en el cargador.
"""

from __future__ import annotations

import copy
import pytest

from aldamar.contenido.aventura import obtener_aventura
from aldamar.contenido.cargador import AventuraInvalida, cargar_aventura_dict
from aldamar.motor.dificultad import obtener_dificultad
from aldamar.motor.juego import Juego
from conftest import AVENTURA, EntradaTipeada
from test_cargador import AVENTURA_MINIMA


def test_dialogos_en_capas_revela_leyenda_del_escribano(fabrica):
    """Hablar repetidas veces con Belthar en Vegaverde agota las capas."""
    lineas = ["", "hablar belthar", "hablar belthar", "hablar belthar", "hablar belthar", "salir"]
    juego, salida = fabrica(lineas)
    juego.ciclo()

    texto = "\n".join(salida)
    # 1ª vez: el encargo canónico
    assert "No vine por té" in texto
    assert "Corazón de Ceniza" in texto

    # 2ª vez: el secreto del escribano distraído
    assert "escribano distraído" in texto
    assert "borrón afortunado" in texto

    # 3ª y 4ª vez: despedida impaciente
    assert "El camino al este sigue esperando" in texto
    assert texto.count("El camino al este sigue esperando") == 2


def test_dialogos_en_capas_persisten_en_guardado(tmp_path, fabrica):
    """El progreso de las conversaciones con NPCs se conserva en partida.json."""
    ruta = str(tmp_path / "partida_charla.json")
    lineas1 = ["", "hablar belthar", "hablar belthar", f"guardar {ruta}", "salir"]
    juego1, salida1 = fabrica(lineas1)
    juego1.ciclo()

    texto1 = "\n".join(salida1)
    assert "escribano distraído" in texto1

    lineas2 = ["", f"cargar {ruta}", "hablar belthar", "salir"]
    juego2, salida2 = fabrica(lineas2)
    juego2.ciclo()

    texto2 = "\n".join(salida2)
    assert "El camino al este sigue esperando" in texto2


def test_comando_secreto_cuervo_fuera_de_combate(fabrica):
    """El comando secreto cuervo responde y evoluciona con insistencia."""
    lineas = ["", "cuervo", "cuervos", "cuervo", "salir"]
    juego, salida = fabrica(lineas, semilla=7)
    juego.ciclo()

    texto = "\n".join(salida)
    # 1ª llamada: cuervo ceniciento
    assert "Un cuervo ceniciento se posa en lo alto" in texto
    # 2ª llamada: fastidio
    assert "«Caw», suelta con fastidio" in texto
    # 3ª llamada: paciencia de piedra
    assert "El cuervo ni se inmuta" in texto


def test_comando_secreto_cuervo_semilla_42(fabrica):
    """La semilla mágica 42 desata una respuesta única del cuervo."""
    lineas = ["", "cuervo", "salir"]
    juego, salida = fabrica(lineas, semilla=42)
    juego.ciclo()

    texto = "\n".join(salida)
    assert "pluma plateada" in texto
    assert "la respuesta a todas las preguntas del mundo" in texto


def test_comando_cuervo_en_combate_no_consume_turno(fabrica):
    """En combate, llamar a los cuervos no gasta turno y devuelve aviso."""
    juego, salida = fabrica(["cuervo"] + ["atacar"] * 8, semilla=3)
    lobo = AVENTURA.crear_enemigo("lobo", obtener_dificultad("camino"))
    assert juego._duelo(lobo) == "victoria"
    texto = "\n".join(salida)
    assert "los duelos ajenos no son asunto suyo" in texto
    assert not lobo.vivo


def test_usar_objeto_con_texto_uso(fabrica):
    """Los objetos con texto_uso muestran su texto especial al usarse."""
    lineas = ["", "tomar capa gris", "usar capa gris", "salir"]
    juego, salida = fabrica(lineas)
    juego.ciclo()

    texto = "\n".join(salida)
    assert "Te ajustas la capa al cuello" in texto
    assert "terquedad de la gente sencilla" in texto


def test_usar_objeto_sin_texto_uso_mantiene_mensaje_defecto(fabrica):
    """Un objeto de equipo sin texto_uso mantiene el aviso clásico."""
    juego, salida = fabrica(["", "usar espada corta", "salir"])
    juego.jugador.inventario.append("espada_corta")
    juego.ciclo()

    texto = "\n".join(salida)
    assert "Eso no se usa así: ya te sirve solo por llevarlo" in texto


def test_usar_carta_belthar_en_brasa_vegaverde():
    """En La Brasa de Vegaverde, la carta de Belthar tiene su propio texto_uso."""
    av_brasa = obtener_aventura("brasa_vegaverde")
    salida: list[str] = []
    lineas = ["", "tomar carta", "usar carta", "salir"]
    juego = Juego(
        av_brasa,
        entrada=EntradaTipeada(lineas),
        salida=salida.append,
        color=False,
    )
    juego.ciclo()

    texto = "\n".join(salida)
    assert "Desdoblas la carta de Belthar" in texto
    assert "las ascuas de Morvath no se apagan con rezos" in texto


def test_cargador_valida_dialogos_y_texto_uso():
    """El cargador valida que dialogos sea texto o lista no vacía de textos y texto_uso sea texto."""
    # Diálogo que no es ni str ni list
    mal = copy.deepcopy(AVENTURA_MINIMA)
    mal["dialogos"] = {"npc": 123}
    with pytest.raises(AventuraInvalida, match="dialogos\\['npc'\\].*debe ser un texto o una lista"):
        cargar_aventura_dict(mal)

    # Diálogo que es lista vacía
    mal = copy.deepcopy(AVENTURA_MINIMA)
    mal["dialogos"] = {"npc": []}
    with pytest.raises(AventuraInvalida, match="dialogos\\['npc'\\].*debe ser un texto o una lista no vacía"):
        cargar_aventura_dict(mal)

    # Diálogo que es lista con elementos no string
    mal = copy.deepcopy(AVENTURA_MINIMA)
    mal["dialogos"] = {"npc": ["hola", 42]}
    with pytest.raises(AventuraInvalida, match="dialogos\\['npc'\\].*debe ser un texto o una lista no vacía de textos"):
        cargar_aventura_dict(mal)

    # Objeto con texto_uso inválido
    mal_item = copy.deepcopy(AVENTURA_MINIMA)
    mal_item["items"]["capa"] = {
        "nombre": "capa",
        "tipo": "armadura",
        "bonus": 1,
        "precio": None,
        "texto_uso": 999,
    }
    with pytest.raises(AventuraInvalida, match="items\\['capa'\\].*el campo 'texto_uso' debe ser texto"):
        cargar_aventura_dict(mal_item)


def test_cargador_valida_secretos():
    """El cargador valida la estructura de la sección opcional secretos."""
    # secretos no es dict
    mal = copy.deepcopy(AVENTURA_MINIMA)
    mal["secretos"] = "invalido"
    with pytest.raises(AventuraInvalida, match="el campo 'secretos' debe ser un objeto"):
        cargar_aventura_dict(mal)

    # textos inválido (no str ni list)
    mal = copy.deepcopy(AVENTURA_MINIMA)
    mal["secretos"] = {"secreto": {"textos": 123}}
    with pytest.raises(AventuraInvalida, match="secretos\\['secreto'\\].textos debe ser texto o una lista no vacía"):
        cargar_aventura_dict(mal)

    # semillas con clave no entera
    mal = copy.deepcopy(AVENTURA_MINIMA)
    mal["secretos"] = {"secreto": {"textos": ["hola"], "semillas": {"no_numero": "texto"}}}
    with pytest.raises(AventuraInvalida, match="debe representar un número entero"):
        cargar_aventura_dict(mal)


def test_secreto_exclusivo_brasa_vegaverde():
    """La Brasa de Vegaverde tiene el secreto de las abejas y diálogos en capas de Oldo."""
    av = obtener_aventura("brasa_vegaverde")
    salida: list[str] = []
    lineas = ["", "abejas", "abeja", "zumbido", "abejas", "hablar oldo", "hablar oldo", "hablar oldo", "salir"]
    juego = Juego(av, entrada=EntradaTipeada(lineas), salida=salida.append, color=False, semilla=7)
    juego.ciclo()
    texto = "\n".join(salida)
    assert "Un rumor dorado se levanta" in texto
    assert "Dos abejas cargadas de polen" in texto
    assert "El zumbido se apaga entre los tallos" in texto
    assert "Un mes hacía de aquella luz" in texto
    assert "Tu primo Tilo era más de correr" in texto
    assert "si ves a Morvath... dile que los Panverde pagamos las deudas" in texto


def test_secreto_brasa_semilla_42_y_combate():
    """En La Brasa de Vegaverde, semilla 42 y combate con abejas."""
    av = obtener_aventura("brasa_vegaverde")
    salida: list[str] = []
    juego = Juego(av, entrada=EntradaTipeada(["", "abejas", "salir"]), salida=salida.append, color=False, semilla=42)
    juego.ciclo()
    assert "abeja reina con reflejos de ámbar antiguo" in "\n".join(salida)

    # En combate
    salida_c: list[str] = []
    juego_c = Juego(av, entrada=EntradaTipeada(["abeja"] + ["atacar"] * 5), salida=salida_c.append, color=False, semilla=7)
    mirlo = av.crear_enemigo("mirlo", obtener_dificultad("camino"))
    assert juego_c._duelo(mirlo) == "victoria"
    assert "las abejas de Bruna no pican a sombras" in "\n".join(salida_c)


def test_secreto_exclusivo_sal_y_ceniza():
    """La Sal y la Ceniza tiene el secreto de la gaviota y diálogos en capas de Dorotea."""
    av = obtener_aventura("sal_y_ceniza")
    salida: list[str] = []
    lineas = ["", "gaviota", "gaviotas", "caracola", "gaviota", "hablar dorotea", "hablar dorotea", "hablar dorotea", "salir"]
    juego = Juego(av, entrada=EntradaTipeada(lineas), salida=salida.append, color=False, semilla=7)
    juego.ciclo()
    texto = "\n".join(salida)
    assert "Una gaviota de ojos claros" in texto
    assert "La gaviota desciende sobre una estaca" in texto
    assert "perdiéndose en la bruma de las salinas" in texto
    assert "Las caravanas no cruzan el vado" in texto
    assert "Belthar pasó por aquí camino de los Yermos" in texto
    assert "La sopa se enfría si la piensas mucho" in texto


def test_secreto_sal_semilla_42_y_items():
    """En La Sal y la Ceniza, semilla 42 y texto_uso en farol de sal."""
    av = obtener_aventura("sal_y_ceniza")
    salida: list[str] = []
    juego = Juego(av, entrada=EntradaTipeada(["", "gaviota", "salir"]), salida=salida.append, color=False, semilla=42)
    juego.ciclo()
    assert "concha marina pulida por cuarenta inviernos" in "\n".join(salida)

    # texto_uso
    salida_i: list[str] = []
    juego_i = Juego(av, entrada=EntradaTipeada(["", "usar farol_sal", "salir"]), salida=salida_i.append, color=False)
    juego_i.jugador.inventario.append("farol_sal")
    juego_i.ciclo()
    assert "Alzas el farol de sal" in "\n".join(salida_i)


def test_secreto_exclusivo_aguja_sin_sombra():
    """La Aguja sin Sombra tiene el secreto de la campanilla y diálogos en capas de Oldo."""
    av = obtener_aventura("aguja_sin_sombra")
    salida: list[str] = []
    lineas = ["", "campanilla", "campana", "bronce", "campanilla", "hablar oldo", "hablar oldo", "hablar oldo", "salir"]
    juego = Juego(av, entrada=EntradaTipeada(lineas), salida=salida.append, color=False, semilla=7)
    juego.ciclo()
    texto = "\n".join(salida)
    assert "Haces sonar suavemente el borde de bronce" in texto
    assert "El bronce vibra entre tus dedos" in texto
    assert "El silencio que deja la campanilla" in texto
    assert "Dos ascuas ahogadas y aquí seguimos" in texto
    assert "sylvos de orejas tiesas" in texto
    assert "apaga ese canto de una vez" in texto


def test_secreto_aguja_semilla_42_y_item_campanilla():
    """En La Aguja sin Sombra, semilla 42 y texto_uso al usar el item campanilla."""
    av = obtener_aventura("aguja_sin_sombra")
    salida: list[str] = []
    juego = Juego(av, entrada=EntradaTipeada(["", "campanilla", "salir"]), salida=salida.append, color=False, semilla=42)
    juego.ciclo()
    assert "cuarenta y dos campanadas parecen replicar a lo lejos" in "\n".join(salida)

    # texto_uso del item campanilla
    salida_i: list[str] = []
    juego_i = Juego(av, entrada=EntradaTipeada(["", "usar campanilla", "salir"]), salida=salida_i.append, color=False)
    juego_i.jugador.inventario.append("campanilla")
    juego_i.ciclo()
    assert "Haces vibrar suavemente la campanilla" in "\n".join(salida_i)


def test_exclusividad_de_secretos():
    """Cada aventura tiene sus propios secretos temáticos exclusivos."""
    av_corazon = obtener_aventura("corazon_ceniza")
    av_brasa = obtener_aventura("brasa_vegaverde")
    av_sal = obtener_aventura("sal_y_ceniza")
    av_aguja = obtener_aventura("aguja_sin_sombra")

    assert "cuervo" in av_corazon.secretos
    assert "abejas" not in av_corazon.secretos
    assert "gaviota" not in av_corazon.secretos
    assert "campanilla" not in av_corazon.secretos

    assert "abejas" in av_brasa.secretos
    assert "cuervo" not in av_brasa.secretos
    assert "gaviota" not in av_brasa.secretos
    assert "campanilla" not in av_brasa.secretos

    assert "gaviota" in av_sal.secretos
    assert "cuervo" not in av_sal.secretos
    assert "abejas" not in av_sal.secretos
    assert "campanilla" not in av_sal.secretos

    assert "campanilla" in av_aguja.secretos
    assert "cuervo" not in av_aguja.secretos
    assert "abejas" not in av_aguja.secretos
    assert "gaviota" not in av_aguja.secretos

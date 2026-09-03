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

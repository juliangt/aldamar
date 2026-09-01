"""El cargador de aventuras JSON: descubrimiento, validación y efectos.

Los tests de comportamiento corren sobre una `Aventura` cargada directo
del JSON (`AV`), no sobre el registro, para probar la cadena completa
archivo → validación → objeto → gameplay.
"""

from __future__ import annotations

import copy
import json
from importlib import resources

import pytest

from aldamar import aventuras  # noqa: F401  (descubre y registra las del paquete)
from aldamar import cargador
from aldamar.aventura import AVENTURAS, obtener_aventura, registrar
from aldamar.cargador import AventuraInvalida, cargar_aventura, cargar_aventura_dict, cargar_todas
from aldamar.dificultad import obtener_dificultad
from aldamar.juego import Juego
from aldamar.personajes import CORRUPCION_TENTADO, Companero
from conftest import EntradaTipeada
from test_flujo import RUTA_BASE

CAMINO = obtener_dificultad("camino")
TEXTO_CORAZON = (
    resources.files("aldamar.aventuras")
    .joinpath("corazon_ceniza.json")
    .read_text(encoding="utf-8")
)
AV = cargar_aventura(TEXTO_CORAZON, "corazon_ceniza.json")

AVENTURA_MINIMA = {
    "id": "aventura_de_prueba",
    "titulo": "La Prueba",
    "descripcion": "una aventura mínima para los tests",
    "texto_nombre": "¿Cómo te llamas, probadora? ({nombre}): ",
    "lugar_inicial": "claro",
    "jugador_inicial": "ana",
    "epilogos": {"muerte": "Ahí quedó.", "caida": "La grieta ganó."},
    "personajes": {
        "ana": {"nombre": "Ana", "titulo": "probadora", "presentacion": "Hola."}
    },
    "items": {},
    "enemigos": {},
    "reclutas": {},
    "tiendas": {},
    "dialogos": {},
    "lugares": {"claro": {"nombre": "el Claro", "descripcion": "Un claro de prueba."}},
    "eventos": {},
}


def _juego(lineas: list[str]):
    salida: list[str] = []
    juego = Juego(
        AV,
        dificultad=CAMINO,
        semilla=7,
        entrada=EntradaTipeada(list(lineas)),
        salida=salida.append,
        color=False,
    )
    return juego, salida


# ── descubrimiento ───────────────────────────────────────────────────────

def test_las_aventuras_del_paquete_se_registran_solas():
    assert "corazon_ceniza" in AVENTURAS
    assert obtener_aventura("corazon_ceniza").titulo == "El Corazón de Ceniza"


def test_un_json_nuevo_en_el_directorio_se_descubre_solo(tmp_path, monkeypatch):
    ruta = tmp_path / "aventura_de_prueba.json"
    ruta.write_text(json.dumps(AVENTURA_MINIMA, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "notas.txt").write_text("esto no es una aventura y no molesta")

    capturadas = []
    monkeypatch.setattr(cargador, "registrar", capturadas.append)
    cargar_todas(raiz=tmp_path)

    assert [av.id for av in capturadas] == ["aventura_de_prueba"]
    assert capturadas[0].titulo == "La Prueba"


def test_el_id_duplicado_se_rechaza():
    duplicada = cargar_aventura(TEXTO_CORAZON, "corazon_ceniza.json")
    with pytest.raises(ValueError, match="ya está registrada"):
        registrar(duplicada)


# ── validación ───────────────────────────────────────────────────────────

def test_falta_un_campo_obligatorio():
    datos = copy.deepcopy(AVENTURA_MINIMA)
    del datos["titulo"]
    with pytest.raises(AventuraInvalida, match="titulo"):
        cargar_aventura_dict(datos, "prueba.json")


def test_un_campo_del_tipo_equivocado():
    datos = copy.deepcopy(AVENTURA_MINIMA)
    datos["epilogos"]["muerte"] = 7
    with pytest.raises(AventuraInvalida, match="muerte"):
        cargar_aventura_dict(datos, "prueba.json")


def test_el_json_roto_da_error_claro():
    with pytest.raises(AventuraInvalida, match="JSON"):
        cargar_aventura("{no soy json", "roto.json")


@pytest.mark.parametrize(
    "mutacion, pista",
    [
        (lambda d: d["lugares"]["claro"].update(salidas={"este": "lejos"}), "lejos"),
        (lambda d: d["lugares"]["claro"].update(objetos=["fantasma"]), "fantasma"),
        (lambda d: d["lugares"]["claro"].update(enemigos=["dragon"]), "dragon"),
        (lambda d: d["lugares"]["claro"].update(npcs={"mercedes": "charla"}), "charla"),
        (lambda d: d["lugares"]["claro"].update(evento="milagro"), "milagro"),
        (lambda d: d["lugares"]["claro"].update(tienda=True), "stock"),
        (lambda d: d["lugares"]["claro"].update(requiere="llave_maestra"), "llave_maestra"),
        (lambda d: d["personajes"]["ana"].update(inventario=["fantasma"]), "fantasma"),
        (lambda d: d["personajes"]["ana"].update(rasgos=["alas"]), "alas"),
        (lambda d: d.update(jugador_inicial="nadie"), "nadie"),
        (lambda d: d.update(lugar_inicial="lejos"), "lejos"),
        (
            lambda d: d["eventos"].update(
                {"regalo": {"tipo": "otorgar", "item": "fantasma", "texto": "Tomá."}}
            ),
            "fantasma",
        ),
        (lambda d: d["eventos"].update({"raro": {"tipo": "levitar"}}), "levitar"),
    ],
)
def test_las_referencias_rotas_se_reportan_con_nombre_y_campo(mutacion, pista):
    datos = copy.deepcopy(AVENTURA_MINIMA)
    mutacion(datos)
    with pytest.raises(AventuraInvalida, match=pista):
        cargar_aventura_dict(datos, "prueba.json")


def test_el_final_exige_un_desenlace_por_defecto():
    datos = copy.deepcopy(AVENTURA_MINIMA)
    datos["eventos"] = {
        "final": {
            "tipo": "final",
            "texto": "El fin.",
            "pregunta": "¿Qué haces?",
            "opciones": [
                {"clave": "a", "titulo": "A", "epilogo": "Epi A.", "final": "a"},
                {"clave": "b", "titulo": "B", "epilogo": "Epi B.", "final": "b"},
            ],
            "umbral_tentado": 60,
            "epilogo_puro": "puro",
            "final_puro": "puro",
            "epilogo_tentado": "tentado",
            "final_tentado": "tentado",
        }
    }
    with pytest.raises(AventuraInvalida, match="desenlace por defecto"):
        cargar_aventura_dict(datos, "prueba.json")


# ── los eventos declarativos se comportan como deben ────────────────────

def test_el_consejo_entrega_el_estandarte_una_sola_vez():
    juego, salida = _juego([])
    juego.av.eventos["consejo"](juego, juego.aqui())
    juego.av.eventos["consejo"](juego, juego.aqui())
    assert juego.jugador.inventario.count("estandarte") == 1
    assert juego.flags == {"consejo": True}
    assert "Recibes: estandarte del consejo." in "\n".join(salida)


def test_el_ritual_cura_resucita_y_alivia_la_grieta():
    juego, salida = _juego([])
    juego.jugador.vida = 5
    juego.jugador.corruptear(40)
    juego.jugador.companeros.append(
        Companero(clave="aldric", nombre="Sir Aldric de Valoria", vida=0,
                  vida_max=26, ataque=5, defensa=1, viva=False)
    )
    juego.av.eventos["ritual"](juego, juego.aqui())
    assert juego.jugador.vida == juego.jugador.vida_max
    aldric = juego.jugador.companeros[0]
    assert aldric.viva and aldric.vida == aldric.vida_max
    assert juego.jugador.corrupcion == 25
    assert "(-15 corrupción)" in "\n".join(salida)


def test_la_niebla_de_las_cienagas_corrompe_cada_vez():
    juego, salida = _juego([])
    juego.av.eventos["corrupcion"](juego, juego.aqui())
    juego.av.eventos["corrupcion"](juego, juego.aqui())
    assert juego.jugador.corrupcion == 16  # 8 y 8: no lleva bandera
    assert "La niebla" in "\n".join(salida)


def test_el_final_destruir_limpio_nombra_a_los_companeros():
    juego, salida = _juego(["destruir"])
    juego.jugador.companeros.append(
        Companero(clave="sylvana", nombre="Sylvana de los Faroles", vida=10,
                  vida_max=18, ataque=5)
    )
    juego.av.eventos["final"](juego, juego.aqui())
    plano = " ".join("\n".join(salida).split())
    assert juego.fin and juego.final == "victoria pura"
    assert "Junto a ti, al alba: Sylvana de los Faroles." in plano
    assert "El Jardín que venció a la Sombra" in plano


def test_el_final_destruir_con_la_grieta_avanzada_da_victoria_con_cicatriz():
    juego, _ = _juego(["destruir"])
    juego.jugador.corruptear(CORRUPCION_TENTADO)
    juego.av.eventos["final"](juego, juego.aqui())
    assert juego.fin and juego.final == "victoria con cicatriz"


def test_reclamar_tiene_su_propio_epilogo():
    juego, salida = _juego(["reclamar"])
    juego.av.eventos["final"](juego, juego.aqui())
    assert juego.fin and juego.final == "la Sombra nueva"
    assert "trono vacío" in "\n".join(salida)


def test_el_golpe_del_corazon_aplica_la_formula_exacta():
    juego, salida = _juego([])
    juego.jugador.corruptear(33)
    custodio = juego.av.crear_enemigo("custodio", CAMINO)
    juego.av.ataque_especial(juego, custodio)
    # la fórmula declarada: 12 + 33 // 3 = 23 de daño, −1 por la defensa
    assert custodio.vida == custodio.vida_max - 22
    assert juego.jugador.corrupcion == 48
    assert "−22" in "\n".join(salida)


# ── gameplay completo sobre la aventura cargada del JSON ────────────────

def test_la_partida_scripted_corre_sobre_la_aventura_del_json():
    juego, salida = _juego(RUTA_BASE + ["destruir"])
    juego.ciclo()
    assert juego.fin
    assert juego.final and "victoria" in juego.final
    assert "El Jardín que venció a la Sombra" in " ".join("\n".join(salida).split())

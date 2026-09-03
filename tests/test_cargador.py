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

from aldamar import datos  # noqa: F401  (descubre y registra las de datos/)
from aldamar.contenido import cargador
from aldamar.contenido.aventura import AVENTURAS, obtener_aventura, registrar
from aldamar.contenido.cargador import AventuraInvalida, cargar_aventura, cargar_aventura_dict, cargar_todas
from aldamar.motor.dificultad import obtener_dificultad
from aldamar.motor.juego import Juego
from aldamar.contenido.personajes import CORRUPCION_TENTADO, Companero
from conftest import EntradaTipeada
from test_flujo import RUTA_BASE

CAMINO = obtener_dificultad("camino")
TEXTO_CORAZON = (
    resources.files("aldamar")
    .joinpath("datos", "aventuras", "corazon_ceniza.json")
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

def test_las_aventuras_de_datos_se_registran_solas():
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
        (lambda d: d["lugares"]["claro"].update(eventos=["milagro"]), "milagro"),
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


# ── los eventos nuevos del vocabulario ──────────────────────────────────

def _minima_con_evento(evento: dict, **extras):
    datos = copy.deepcopy(AVENTURA_MINIMA)
    datos.update(extras)
    datos["eventos"] = {"prueba": evento}
    return datos


def test_la_decision_rechaza_items_fantasma():
    datos = _minima_con_evento({
        "tipo": "decision",
        "texto": "Elige.",
        "pregunta": "¿Qué haces?",
        "opciones": [
            {"clave": "a", "titulo": "A", "item": "fantasma"},
        ],
    })
    with pytest.raises(AventuraInvalida, match="fantasma"):
        cargar_aventura_dict(datos, "prueba.json")


def test_la_decision_rechaza_claves_repetidas():
    datos = _minima_con_evento({
        "tipo": "decision",
        "texto": "Elige.",
        "pregunta": "¿Qué haces?",
        "opciones": [
            {"clave": "a", "titulo": "A"},
            {"clave": "a", "titulo": "B"},
        ],
    })
    with pytest.raises(AventuraInvalida, match="repetida"):
        cargar_aventura_dict(datos, "prueba.json")


def test_la_emboscada_rechaza_enemigos_fantasma():
    datos = _minima_con_evento({
        "tipo": "emboscar",
        "enemigos": ["dragon"],
        "texto": "¡Sorpresa!",
    })
    with pytest.raises(AventuraInvalida, match="dragon"):
        cargar_aventura_dict(datos, "prueba.json")


def test_la_emboscada_exige_al_menos_un_enemigo():
    datos = _minima_con_evento({"tipo": "emboscar", "enemigos": [], "texto": "..."})
    with pytest.raises(AventuraInvalida, match="al menos un enemigo"):
        cargar_aventura_dict(datos, "prueba.json")


def test_narrar_exige_su_texto():
    datos = _minima_con_evento({"tipo": "narrar"})
    with pytest.raises(AventuraInvalida, match="texto"):
        cargar_aventura_dict(datos, "prueba.json")


def test_el_desenlace_por_defecto_no_puede_exigir_bandera():
    datos = _minima_con_evento({
        "tipo": "final",
        "texto": "El fin.",
        "pregunta": "¿Qué haces?",
        "opciones": [
            {"clave": "a", "titulo": "A", "requiere_flag": "x"},
            {"clave": "b", "titulo": "B", "epilogo": "Epi B.", "final": "b"},
        ],
        "umbral_tentado": 60,
        "epilogo_puro": "puro",
        "final_puro": "puro",
        "epilogo_tentado": "tentado",
        "final_tentado": "tentado",
    })
    with pytest.raises(AventuraInvalida, match="requiere_flag"):
        cargar_aventura_dict(datos, "prueba.json")


def test_el_orden_invalido_se_rechaza():
    datos = copy.deepcopy(AVENTURA_MINIMA)
    datos["orden"] = "primera"
    with pytest.raises(AventuraInvalida, match="orden"):
        cargar_aventura_dict(datos, "prueba.json")


# ── el vocabulario de combate: experiencia, habilidades y fases ─────────

def _minima_con_enemigo(enemigo: dict):
    datos = copy.deepcopy(AVENTURA_MINIMA)
    datos["enemigos"] = {"bestia": enemigo}
    return datos


def test_la_experiencia_negativa_se_rechaza():
    datos = _minima_con_enemigo({"nombre": "bestia", "vida": 5, "ataque": 1, "experiencia": -1})
    with pytest.raises(AventuraInvalida, match="experiencia"):
        cargar_aventura_dict(datos, "prueba.json")


def test_la_experiencia_es_opcional_y_sale_a_cero():
    datos = _minima_con_enemigo({"nombre": "bestia", "vida": 5, "ataque": 1})
    av = cargar_aventura_dict(datos, "prueba.json")
    assert "experiencia" not in av.enemigos["bestia"]  # el JSON queda tal cual


def test_un_tipo_de_habilidad_desconocido_se_rechaza():
    datos = _minima_con_enemigo({
        "nombre": "bestia", "vida": 5, "ataque": 1,
        "habilidades": [{"tipo": "convertirse_en_dragon"}],
    })
    with pytest.raises(AventuraInvalida, match="convertirse_en_dragon"):
        cargar_aventura_dict(datos, "prueba.json")


@pytest.mark.parametrize(
    "mutacion, pista",
    [
        # veneno mal declarado
        (lambda e: e["habilidades"][0].pop("dano"), "dano"),
        (lambda e: e["habilidades"][0].update(turnos=0), "turnos"),
        (lambda e: e["habilidades"][0].pop("texto"), "texto"),
        # curarse sin puntos
        (lambda e: e["habilidades"][0].update(tipo="curarse", puntos=0), "puntos"),
        # refuerzo fantasma, a sí mismo o sin veces razonables
        (lambda e: e["habilidades"][0].update(tipo="refuerzo", enemigo="fantasma"), "fantasma"),
        (lambda e: e["habilidades"][0].update(tipo="refuerzo", enemigo="bestia"), "sí mismo"),
        (lambda e: e["habilidades"][0].update(tipo="refuerzo", enemigo="eco", veces=0), "veces"),
        # golpe fuerte sin su telegrafía, sin golpe o sin {efectivo}
        (lambda e: e["habilidades"][0].update(tipo="golpe_fuerte", dano_extra=0), "dano_extra"),
        (lambda e: e["habilidades"][0].update(
            tipo="golpe_fuerte", texto_aviso="Tensa…", texto_golpe="cae", dano_extra=3
        ), "texto_golpe"),
        # peso y condición
        (lambda e: e["habilidades"][0].update(peso=0), "peso"),
        (lambda e: e["habilidades"][0].update(condicion={"vida_menor_que": 150}), "porcentaje"),
        (lambda e: e["habilidades"][0].update(condicion={"cada_n_turnos": -1}), "cada_n_turnos"),
    ],
)
def test_las_habilidades_rotas_se_reportan_con_nombre_y_campo(mutacion, pista):
    enemigo = {
        "nombre": "bestia", "vida": 5, "ataque": 1,
        "habilidades": [{
            "tipo": "veneno", "texto": "Pica", "dano": 2, "turnos": 2,
        }],
    }
    mutacion(enemigo)
    datos = _minima_con_enemigo(enemigo)
    if "eco" in json.dumps(datos):
        datos["enemigos"]["eco"] = {"nombre": "eco", "vida": 3, "ataque": 1}
    with pytest.raises(AventuraInvalida, match=pista):
        cargar_aventura_dict(datos, "prueba.json")


def test_el_refuerzo_a_un_enemigo_existente_se_acepta():
    datos = _minima_con_enemigo({
        "nombre": "bestia", "vida": 5, "ataque": 1,
        "habilidades": [{
            "tipo": "refuerzo", "texto": "Llama:", "enemigo": "eco", "veces": 2,
        }],
    })
    datos["enemigos"]["eco"] = {"nombre": "eco", "vida": 3, "ataque": 1}
    av = cargar_aventura_dict(datos, "prueba.json")
    enemigo = av.crear_enemigo("bestia", CAMINO)
    assert enemigo.habilidades[0].enemigo == "eco"
    assert enemigo.habilidades[0].veces == 2


@pytest.mark.parametrize(
    "mutacion, pista",
    [
        (lambda f: f.pop("vida_menor_que"), "vida_menor_que"),
        (lambda f: f.update(vida_menor_que=0), "porcentaje"),
        (lambda f: f.pop("texto"), "texto"),
        (lambda f: f.update(ataque=-2), "ataque"),
        (
            lambda f: f.update(habilidades=[{"tipo": "levitarse"}]),
            "levitarse",
        ),  # las habilidades de una fase se validan igual
    ],
)
def test_las_fases_rotas_se_reportan_con_nombre_y_campo(mutacion, pista):
    fase = {
        "vida_menor_que": 50,
        "texto": "Cambia la piel.",
        "ataque": 8,
    }
    mutacion(fase)
    datos = _minima_con_enemigo({"nombre": "jefe", "vida": 20, "ataque": 5, "fases": [fase]})
    with pytest.raises(AventuraInvalida, match=pista):
        cargar_aventura_dict(datos, "prueba.json")


def test_un_jefe_con_fases_se_carga_y_se_arma():
    datos = _minima_con_enemigo({
        "nombre": "jefe", "vida": 40, "ataque": 6, "experiencia": 45,
        "habilidades": [{"tipo": "curarse", "texto": "Se recompone", "puntos": 3}],
        "fases": [
            {
                "vida_menor_que": 60, "texto": "Se encrespa.", "nombre": "jefe airado",
                "ataque": 8, "defensa": 1,
                "habilidades": [{"tipo": "golpe_fuerte", "texto_aviso": "Tensa…",
                                 "texto_golpe": "Cae: −{efectivo}.", "dano_extra": 5}],
            },
            {"vida_menor_que": 25, "texto": "Se deshace.", "ataque": 10},
        ],
    })
    av = cargar_aventura_dict(datos, "prueba.json")
    jefe = av.crear_enemigo("bestia", CAMINO)
    assert [f.umbral for f in jefe.fases] == [60, 25]  # el cargador ordena de mayor a menor
    assert jefe.habilidades[0].tipo == "curarse"
    jefe.vida = 20
    assert jefe.avanzar_fase() == "Se encrespa."
    assert jefe.ataque == 8 and jefe.defensa == 1
    assert jefe.habilidades[0].tipo == "golpe_fuerte"
    jefe.vida = 5  # por debajo también del 25% de 40
    assert jefe.avanzar_fase() == "Se deshace."
    assert jefe.ataque == 10


def test_el_orden_de_registro_lo_fija_el_campo_orden(tmp_path, monkeypatch):
    segunda = copy.deepcopy(AVENTURA_MINIMA)
    segunda.update(id="segunda", titulo="La Segunda", orden=1)
    primera = copy.deepcopy(AVENTURA_MINIMA)
    primera.update(id="primera", titulo="La Primera", orden=0)
    ultima = copy.deepcopy(AVENTURA_MINIMA)
    ultima.update(id="ultima", titulo="La Última")  # sin orden: al final
    (tmp_path / "c_segunda.json").write_text(json.dumps(segunda, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "a_primera.json").write_text(json.dumps(primera, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "b_ultima.json").write_text(json.dumps(ultima, ensure_ascii=False), encoding="utf-8")

    capturadas = []
    monkeypatch.setattr(cargador, "registrar", capturadas.append)
    cargar_todas(raiz=tmp_path)

    assert [av.id for av in capturadas] == ["primera", "segunda", "ultima"]


# ── los eventos declarativos se comportan como deben ────────────────────

def test_el_consejo_entrega_el_estandarte_una_sola_vez():
    juego, salida = _juego(["alianza"])
    juego.av.eventos["consejo"](juego, juego.aqui())
    juego.av.eventos["consejo"](juego, juego.aqui())
    assert juego.jugador.inventario.count("estandarte") == 1
    assert juego.flags == {"consejo": True, "alianza": True}
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
    assert juego.fin and juego.final == "victoria pura"
    # el epílogo no se imprime: queda guardado para la pantalla de cierre
    epilogo = " ".join(juego.epilogo.split())
    assert "Junto a ti, al alba: Sylvana de los Faroles." in epilogo
    assert "El Jardín que venció a la Sombra" in epilogo


def test_el_final_destruir_con_la_grieta_avanzada_da_victoria_con_cicatriz():
    juego, _ = _juego(["destruir"])
    juego.jugador.corruptear(CORRUPCION_TENTADO)
    juego.av.eventos["final"](juego, juego.aqui())
    assert juego.fin and juego.final == "victoria con cicatriz"


def test_reclamar_tiene_su_propio_epilogo():
    juego, salida = _juego(["reclamar"])
    juego.av.eventos["final"](juego, juego.aqui())
    assert juego.fin and juego.final == "la Sombra nueva"
    assert "trono vacío" in juego.epilogo
    assert "trono vacío" not in "\n".join(salida)  # no se imprime: lo dirá el cierre


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


# ── narrar con condiciones y grieta; lugares con varios eventos ─────────

def test_un_narrar_con_texto_de_grieta_sin_umbral_se_rechaza():
    datos = copy.deepcopy(AVENTURA_MINIMA)
    datos["eventos"] = {"eco": {"tipo": "narrar", "texto": "Algo.", "texto_grieta": "Humo."}}
    with pytest.raises(AventuraInvalida, match="grieta_desde"):
        cargar_aventura_dict(datos, "prueba.json")


def test_un_narrar_con_umbral_fuera_de_rango_se_rechaza():
    datos = copy.deepcopy(AVENTURA_MINIMA)
    datos["eventos"] = {
        "eco": {
            "tipo": "narrar",
            "texto": "Algo.",
            "texto_grieta": "Humo.",
            "grieta_desde": 0,
        }
    }
    with pytest.raises(AventuraInvalida, match="grieta_desde"):
        cargar_aventura_dict(datos, "prueba.json")


def test_un_narrar_con_condicion_y_grieta_se_carga():
    datos = copy.deepcopy(AVENTURA_MINIMA)
    datos["eventos"] = {
        "eco": {
            "tipo": "narrar",
            "texto": "Algo.",
            "texto_grieta": "Humo.",
            "grieta_desde": 40,
            "condicion": {"flag": "juramento"},
        }
    }
    av = cargar_aventura_dict(datos, "prueba.json")
    assert callable(av.eventos["eco"])


def test_un_lugar_con_varios_eventos_los_guarda_en_orden():
    datos = copy.deepcopy(AVENTURA_MINIMA)
    datos["eventos"] = {
        "uno": {"tipo": "narrar", "texto": "Uno."},
        "dos": {"tipo": "narrar", "texto": "Dos."},
    }
    datos["lugares"]["claro"]["eventos"] = ["uno", "dos"]
    av = cargar_aventura_dict(datos, "prueba.json")
    assert av.lugares["claro"].eventos == ["uno", "dos"]


def test_un_legado_mal_tipado_se_rechaza():
    datos = copy.deepcopy(AVENTURA_MINIMA)
    datos["legado"] = {"heroe": "sí"}
    with pytest.raises(AventuraInvalida, match="heroe"):
        cargar_aventura_dict(datos, "prueba.json")


def test_un_legado_que_exporta_banderas_de_decision_se_carga():
    datos = copy.deepcopy(AVENTURA_MINIMA)
    datos["eventos"] = {
        "elegir": {
            "tipo": "decision",
            "texto": "Uno u otro.",
            "pregunta": "¿Qué haces?",
            "opciones": [{"clave": "a", "titulo": "Lo uno", "flag": "juramento"}],
        }
    }
    datos["legado"] = {"exporta": {"juramento": "juramento"}, "importa": ["juramento"]}
    av = cargar_aventura_dict(datos, "prueba.json")
    assert av.legado.exporta == {"juramento": "juramento"}
    assert av.legado.cruza


def test_dialogos_valida_str_y_lista_de_str():
    datos = copy.deepcopy(AVENTURA_MINIMA)
    datos["dialogos"] = {
        "simple": "Texto simple.",
        "capas": ["Capa 1", "Capa 2"],
    }
    av = cargar_aventura_dict(datos, "prueba.json")
    assert av.dialogos["simple"] == "Texto simple."
    assert av.dialogos["capas"] == ["Capa 1", "Capa 2"]

    # Inválido: no str ni list
    mal = copy.deepcopy(AVENTURA_MINIMA)
    mal["dialogos"] = {"err": 123}
    with pytest.raises(AventuraInvalida, match="dialogos\\['err'\\].*debe ser un texto o una lista"):
        cargar_aventura_dict(mal, "prueba.json")

    # Inválido: lista vacía
    mal_vacia = copy.deepcopy(AVENTURA_MINIMA)
    mal_vacia["dialogos"] = {"err": []}
    with pytest.raises(AventuraInvalida, match="dialogos\\['err'\\].*debe ser un texto o una lista no vacía"):
        cargar_aventura_dict(mal_vacia, "prueba.json")

    # Inválido: elemento no string
    mal_elem = copy.deepcopy(AVENTURA_MINIMA)
    mal_elem["dialogos"] = {"err": ["ok", 456]}
    with pytest.raises(AventuraInvalida, match="dialogos\\['err'\\].*debe ser un texto o una lista no vacía de textos"):
        cargar_aventura_dict(mal_elem, "prueba.json")


def test_items_valida_texto_uso_opcional():
    datos = copy.deepcopy(AVENTURA_MINIMA)
    datos["items"] = {
        "reliquia": {
            "nombre": "reliquia",
            "tipo": "clave",
            "precio": None,
            "texto_uso": "Sientes un cosquilleo antiguo al rozar la superficie.",
        }
    }
    av = cargar_aventura_dict(datos, "prueba.json")
    assert av.items["reliquia"]["texto_uso"] == "Sientes un cosquilleo antiguo al rozar la superficie."

    mal = copy.deepcopy(AVENTURA_MINIMA)
    mal["items"] = {
        "reliquia": {
            "nombre": "reliquia",
            "tipo": "clave",
            "precio": None,
            "texto_uso": 12345,
        }
    }
    with pytest.raises(AventuraInvalida, match="items\\['reliquia'\\].*el campo 'texto_uso' debe ser texto"):
        cargar_aventura_dict(mal, "prueba.json")


def test_secretos_valida_y_carga_instancias_secreto():
    datos = copy.deepcopy(AVENTURA_MINIMA)
    datos["secretos"] = {
        "cuervo": {
            "comando": "cuervo",
            "textos": ["Caw 1", "Caw 2"],
            "texto_combate": "El cuervo mira la pelea.",
            "semillas": {"42": "Pluma mágica"},
            "alias": ["cuervos", "pajaro"],
        }
    }
    av = cargar_aventura_dict(datos, "prueba.json")
    assert "cuervo" in av.secretos
    sec = av.secretos["cuervo"]
    assert sec.comando == "cuervo"
    assert sec.textos == ["Caw 1", "Caw 2"]
    assert sec.texto_combate == "El cuervo mira la pelea."
    assert sec.semillas == {42: "Pluma mágica"}
    assert sec.alias == ["cuervos", "pajaro"]


def test_secretos_rechaza_todas_las_estructuras_invalidas():
    # 1. secretos no es dict
    mal1 = copy.deepcopy(AVENTURA_MINIMA)
    mal1["secretos"] = ["no_dict"]
    with pytest.raises(AventuraInvalida, match="el campo 'secretos' debe ser un objeto"):
        cargar_aventura_dict(mal1, "prueba.json")

    # 2. secreto individual no es dict
    mal2 = copy.deepcopy(AVENTURA_MINIMA)
    mal2["secretos"] = {"sec": "no_dict"}
    with pytest.raises(AventuraInvalida, match="secretos\\['sec'\\] debe ser un objeto"):
        cargar_aventura_dict(mal2, "prueba.json")

    # 3. textos no es str ni list
    mal3 = copy.deepcopy(AVENTURA_MINIMA)
    mal3["secretos"] = {"sec": {"textos": 99}}
    with pytest.raises(AventuraInvalida, match="textos debe ser texto o una lista no vacía"):
        cargar_aventura_dict(mal3, "prueba.json")

    # 4. textos es lista vacía
    mal4 = copy.deepcopy(AVENTURA_MINIMA)
    mal4["secretos"] = {"sec": {"textos": []}}
    with pytest.raises(AventuraInvalida, match="textos debe ser texto o una lista no vacía"):
        cargar_aventura_dict(mal4, "prueba.json")

    # 5. texto_combate no es str
    mal5 = copy.deepcopy(AVENTURA_MINIMA)
    mal5["secretos"] = {"sec": {"textos": "ok", "texto_combate": 123}}
    with pytest.raises(AventuraInvalida, match="texto_combate debe ser texto"):
        cargar_aventura_dict(mal5, "prueba.json")

    # 6. alias no es lista
    mal6 = copy.deepcopy(AVENTURA_MINIMA)
    mal6["secretos"] = {"sec": {"textos": "ok", "alias": "no_lista"}}
    with pytest.raises(AventuraInvalida, match="alias debe ser una lista de textos"):
        cargar_aventura_dict(mal6, "prueba.json")

    # 7. alias con elementos no str
    mal7 = copy.deepcopy(AVENTURA_MINIMA)
    mal7["secretos"] = {"sec": {"textos": "ok", "alias": ["ok", 123]}}
    with pytest.raises(AventuraInvalida, match="alias debe ser una lista de textos"):
        cargar_aventura_dict(mal7, "prueba.json")

    # 8. semillas no es dict
    mal8 = copy.deepcopy(AVENTURA_MINIMA)
    mal8["secretos"] = {"sec": {"textos": "ok", "semillas": [42]}}
    with pytest.raises(AventuraInvalida, match="semillas debe ser un objeto"):
        cargar_aventura_dict(mal8, "prueba.json")

    # 9. semillas con clave no entera
    mal9 = copy.deepcopy(AVENTURA_MINIMA)
    mal9["secretos"] = {"sec": {"textos": "ok", "semillas": {"abc": "texto"}}}
    with pytest.raises(AventuraInvalida, match="debe representar un número entero"):
        cargar_aventura_dict(mal9, "prueba.json")

    # 10. semillas con valor no str
    mal10 = copy.deepcopy(AVENTURA_MINIMA)
    mal10["secretos"] = {"sec": {"textos": "ok", "semillas": {"42": 999}}}
    with pytest.raises(AventuraInvalida, match="debe ser texto"):
        cargar_aventura_dict(mal10, "prueba.json")

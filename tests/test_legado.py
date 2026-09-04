"""El legado de la serie «Las Ascuas del Corazón» (issue 19).

Lo que una aventura escribe al terminar (`legado.json`), lo que la
siguiente enciende al empezar, el gesto de fama del prólogo y las
reacciones declaradas: la serie jugada como campaña, no como lista.
"""

from __future__ import annotations

import json
from importlib import resources

import pytest
from conftest import AVENTURA, EntradaTipeada
from test_cargador import AVENTURA_MINIMA

from aldamar.contenido import cargador
from aldamar.contenido.aventura import obtener_aventura
from aldamar.contenido.cargador import AventuraInvalida, cargar_aventura_dict, cargar_todas
from aldamar.motor.juego import Juego, _escribir_legado
from aldamar.motor.legado import escribir, leer

CORAZON = obtener_aventura("corazon_ceniza")
BRASA = obtener_aventura("brasa_vegaverde")
SAL = obtener_aventura("sal_y_ceniza")
AGUJA = obtener_aventura("aguja_sin_sombra")


def _juego(av, lineas=None, salida=None, **kw):
    return Juego(
        av,
        semilla=7,
        entrada=EntradaTipeada(list(lineas or [])),
        salida=salida or (lambda _t: None),
        color=False,
        **kw,
    )


def _datos_aventura(nombre: str) -> dict:
    texto = (
        resources.files("aldamar")
        .joinpath("datos", "aventuras", nombre)
        .read_text(encoding="utf-8")
    )
    return json.loads(texto)


# ── escribir el legado ───────────────────────────────────────────────────

def test_escribir_exporta_solo_las_banderas_encendidas(tmp_path):
    ruta = str(tmp_path / "legado.json")
    juego = _juego(SAL, ["encender"])
    juego.flags["faro_encendido"] = True

    legado = escribir(SAL, juego, ruta)

    # juramento encendido, grieta apagada; con heroe, nombre y rasgo
    assert legado == {
        "aventura": "sal_y_ceniza",
        "juramento": True,
        "nombre": "Bruna de la Colmena",
        "rasgo": "piel_piedra",
    }
    datos = json.loads((tmp_path / "legado.json").read_text(encoding="utf-8"))
    assert "grieta" not in datos  # el farol no fue robado: esa canónica calla


def test_escribir_exporta_grieta_y_heroe(tmp_path):
    ruta = str(tmp_path / "legado.json")
    juego = _juego(CORAZON, personaje="ithel")
    juego.flags["coronado"] = True
    juego.jugador.nombre = "Juana del Vado"

    legado = escribir(CORAZON, juego, ruta)

    assert legado["grieta"] is True
    assert "juramento" not in legado  # no juró la Alianza: esa canónica calla
    assert legado["nombre"] == "Juana del Vado"
    assert legado["rasgo"] == "ojo_halcon"


def test_muertes_y_suspendidas_no_dejan_legado(tmp_path):
    ruta = str(tmp_path / "legado.json")
    juego = _juego(CORAZON)
    juego.flags["alianza"] = True
    for final in (None, "suspendida", "muerte", "caida"):
        juego.final = final
        _escribir_legado(juego, ruta, lambda _t: None)
    assert leer(ruta) is None


def test_terminar_sin_banderas_deja_un_legado_minimo(tmp_path):
    juego = _juego(BRASA, personaje="enebro")
    juego.final = "la brasa ahogada en agua limpia"  # sin aceptar a Bruna
    legado = escribir(BRASA, juego, str(tmp_path / "legado.json"))
    assert legado == {
        "aventura": "brasa_vegaverde",
        "nombre": "Enebro Panverde",
        "rasgo": "piel_piedra",
    }


def test_cada_aventura_cuida_sus_claves_y_respeta_las_ajenas(tmp_path):
    ruta = str(tmp_path / "legado.json")
    # el Corazón deja juramento y grieta…
    juego = _juego(CORAZON, personaje="ithel")
    juego.flags["alianza"] = juego.flags["coronado"] = True
    escribir(CORAZON, juego, ruta)
    # …y la brasa, que no exporta grieta, la respeta aunque apague el suyo
    juego2 = _juego(BRASA, personaje="enebro")
    escribir(BRASA, juego2, ruta)
    legado = leer(ruta)
    assert legado["grieta"] is True  # la canónica del Corazón sigue viva
    assert "juramento" not in legado  # la de la brasa, apagada, se apaga fuera


# ── leer el legado ───────────────────────────────────────────────────────

def test_leer_sin_archivo_o_roto_devuelve_none(tmp_path):
    assert leer(str(tmp_path / "nada.json")) is None
    roto = tmp_path / "roto.json"
    roto.write_text("{no soy json", encoding="utf-8")
    assert leer(str(roto)) is None
    raro = tmp_path / "raro.json"
    raro.write_text("[1, 2, 3]", encoding="utf-8")  # JSON válido, pero no objeto
    assert leer(str(raro)) is None


def test_empezar_otra_aventura_enciende_las_banderas_importadas():
    juego = _juego(SAL, legado={"juramento": True, "grieta": True})
    assert juego.flags["juramento"] and juego.flags["grieta"]

    # solo se enciende lo que la aventura importa: la Aguja también lee
    # las dos canónicas, pero el Corazón no importa nada (es la primera)
    assert _juego(AGUJA, legado={"grieta": True}).flags == {"grieta": True}
    assert _juego(CORAZON, legado={"juramento": True}).flags == {}


def test_sin_legado_no_se_enciende_nada():
    assert _juego(SAL).flags == {}
    assert _juego(SAL, legado={}).flags == {}


# ── el gesto de fama y las reacciones ────────────────────────────────────

def test_el_prologo_anuncia_la_fama_si_hay_legado():
    salida: list[str] = []
    juego = _juego(BRASA, [""], salida=salida.append, legado={"juramento": True})
    juego._prologo()
    texto = "\n".join(salida)
    assert "Tu fama te precede" in texto
    assert "fama se sirve en porciones" in texto  # el texto_fama de la brasa


def test_sin_legado_el_prologo_no_anuncia_nada():
    salida: list[str] = []
    juego = _juego(BRASA, [""], salida=salida.append)
    juego._prologo()
    assert "Tu fama te precede" not in "\n".join(salida)


def test_el_final_de_una_aventura_colorea_la_siguiente(tmp_path):
    # la brasa ahogada con cera deja juramento; la costa lo recuerda
    ruta = str(tmp_path / "legado.json")
    juego_brasa = _juego(BRASA, ["aceptar"], personaje="enebro")
    juego_brasa.flags["bruna"] = True
    escribir(BRASA, juego_brasa, ruta)

    salida: list[str] = []
    juego_sal = _juego(SAL, [""], salida=salida.append, legado=leer(ruta))
    juego_sal.av.eventos["cadena_en_el_vado"](juego_sal, juego_sal.av.lugares["vado"])
    assert "velo de cera del tejo" in "\n".join(salida)
    assert juego_sal.flags["cadena_en_el_vado"]  # la escena se cuenta una vez


def test_el_legado_corrupto_trae_textos_alternativos():
    # con grieta, el mar de la sal reconoce al farol ajeno…
    juego_sal = _juego(SAL, legado={"grieta": True})
    salida_sal: list[str] = []
    juego_sal.salida = salida_sal.append
    juego_sal.av.eventos["hilo_gris"](juego_sal, juego_sal.av.lugares["esteros"])
    assert "faroles que cambian de mano" in "\n".join(salida_sal)

    # …y la Aguja canta la deuda en el puente
    juego_aguja = _juego(AGUJA, legado={"grieta": True})
    salida_aguja: list[str] = []
    juego_aguja.salida = salida_aguja.append
    juego_aguja.av.eventos["hilos_en_el_agua"](juego_aguja, juego_aguja.av.lugares["puente"])
    assert "La Aguja canta deudas" in "\n".join(salida_aguja)

    # con un legado limpio (juramento, no grieta), ninguna se cuenta
    juego_limpio = _juego(SAL, legado={"juramento": True})
    juego_limpio.av.eventos["hilo_gris"](juego_limpio, juego_limpio.av.lugares["esteros"])
    juego_limpio2 = _juego(AGUJA, legado={"juramento": True})
    juego_limpio2.av.eventos["hilos_en_el_agua"](juego_limpio2, juego_limpio2.av.lugares["puente"])
    assert "hilo_gris" not in juego_limpio.flags
    assert "hilos_en_el_agua" not in juego_limpio2.flags


# ── la cadena entera de la serie, de punta a punta ──────────────────────

def test_la_serie_completa_cose_su_legado(tmp_path):
    ruta = str(tmp_path / "legado.json")

    # I: el Corazón, jurado la Alianza y coronado (sí: un héroe puede ser
    # las dos cosas) — deja juramento, grieta y el nombre del héroe
    juego = _juego(CORAZON, personaje="ithel")
    juego.flags["alianza"] = juego.flags["coronado"] = True
    juego.jugador.nombre = "Ithel de los Faroles"
    juego.final = "victoria con cicatriz"
    _escribir_legado(juego, ruta, lambda _t: None)

    # II: la brasa lee la fama y la grieta, y añade su juramento
    juego2 = _juego(BRASA, [""], personaje="enebro", legado=leer(ruta))
    assert juego2.flags == {"juramento": True, "grieta": True}
    juego2.flags["bruna"] = True
    juego2.final = "la brasa ahogada con cera"
    _escribir_legado(juego2, ruta, lambda _t: None)

    # III: la sal mantiene juramento y grieta (llegan de la brasa)
    juego3 = _juego(SAL, legado=leer(ruta))
    assert juego3.flags["juramento"] and juego3.flags["grieta"]


# ── validación del contrato en el cargador ──────────────────────────────

def test_exportar_hacia_una_bandera_que_nadie_decide_se_rechaza():
    datos = _datos_aventura("corazon_ceniza.json")
    datos["id"] = "corazon_de_prueba"
    for opcion in datos["eventos"]["consejo"]["opciones"]:
        opcion.pop("flag", None)  # nadie enciende ya "alianza"
    with pytest.raises(AventuraInvalida, match="alianza"):
        cargar_aventura_dict(datos, "prueba.json")


def test_una_canonica_importada_sin_exportador_se_rechaza(tmp_path):
    primera = json.loads(json.dumps(AVENTURA_MINIMA))
    primera["id"] = "sin_legado"
    segunda = json.loads(json.dumps(AVENTURA_MINIMA))
    segunda["id"] = "con_legado"
    segunda["legado"] = {"importa": ["juramento"]}
    (tmp_path / "a_sin_legado.json").write_text(json.dumps(primera), encoding="utf-8")
    (tmp_path / "b_con_legado.json").write_text(json.dumps(segunda), encoding="utf-8")

    with pytest.raises(AventuraInvalida, match="juramento"):
        cargar_todas(raiz=tmp_path)


def test_una_canonica_importada_con_exportador_se_acepta(tmp_path, monkeypatch):
    primera = json.loads(json.dumps(AVENTURA_MINIMA))
    primera["id"] = "exportadora"
    primera["legado"] = {"exporta": {"juramento": "juramento"}}
    primera["eventos"] = {
        "elegir": {
            "tipo": "decision",
            "texto": "Uno u otro.",
            "pregunta": "¿Qué haces?",
            "opciones": [{"clave": "a", "titulo": "Lo uno", "flag": "juramento"}],
        }
    }
    primera["lugares"]["claro"]["eventos"] = ["elegir"]
    segunda = json.loads(json.dumps(AVENTURA_MINIMA))
    segunda["id"] = "importadora"
    segunda["legado"] = {"importa": ["juramento"]}
    (tmp_path / "a_exportadora.json").write_text(json.dumps(primera), encoding="utf-8")
    (tmp_path / "b_importadora.json").write_text(json.dumps(segunda), encoding="utf-8")

    capturadas = []
    monkeypatch.setattr(cargador, "registrar", capturadas.append)
    cargar_todas(raiz=tmp_path)
    assert {av.id for av in capturadas} == {"exportadora", "importadora"}


def test_el_legado_del_paquete_valida_a_la_primera():
    # la serie entera, tal y como se reparte, cumple su propio contrato:
    # nada importado sin exportador (la carga del paquete ya lo hace,
    # este test lo dice en voz alta para leerlo en caso de fallo)
    assert CORAZON.legado.exporta == {"juramento": "alianza", "grieta": "coronado"}
    assert BRASA.legado.importa == ["juramento", "grieta"]
    assert AGUJA.legado.exporta == {"juramento": "consejo", "grieta": "guardia"}
    assert AVENTURA.legado.exporta  # corazon_ceniza exporta

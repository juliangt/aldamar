"""El director del modo vivo: esqueleto válido, determinista y sin cronista.

La garantía central del Nivel 1 (issue 22): con tablas y una semilla
solos — sin modelo — la aventura completa nace válida y se rellena
entera con plantillas. Si esto falla, el piso procedural no existe.
"""

from __future__ import annotations

import json
import random

import pytest

from aldamar.contenido.cargador import cargar_aventura_dict
from aldamar.viva import director
from aldamar.viva.cronista import ProveedorFalso
from aldamar.viva.sesion import SesionViva, sanea_fragmento


def _todas_las_semillas() -> list[int | None]:
    return [None, 1, 7, 42]


@pytest.mark.parametrize("premisa", director.PREMISAS, ids=lambda p: p.clave)
@pytest.mark.parametrize("semilla", _todas_las_semillas())
def test_el_esqueleto_nace_valido(premisa, semilla):
    esqueleto = director.esqueleto(premisa, semilla)
    av = cargar_aventura_dict(esqueleto.aventura, "esqueleto de prueba")
    assert av.id.startswith("viva_")
    assert len(av.lugares) == 8
    assert len(esqueleto.stubs) == 7
    assert esqueleto.final == "cima"
    # la cima nace con su jefe y su evento final: la partida tiene fin
    assert "guardian_cima" in av.enemigos
    assert "final_cima" in av.eventos
    assert "final_cima" in av.lugares["cima"].eventos
    # toda salida apunta a un lugar del esqueleto (el validador ya lo
    # dijo, pero la intención del mapa es esta)
    for lugar in av.lugares.values():
        for destino in lugar.salidas.values():
            assert destino in av.lugares


def test_el_esqueleto_es_determinista_con_la_semilla():
    a = json.dumps(director.esqueleto(director.PREMISAS[0], 7).aventura)
    b = json.dumps(director.esqueleto(director.PREMISAS[0], 7).aventura)
    c = json.dumps(director.esqueleto(director.PREMISAS[0], 8).aventura)
    assert a == b
    assert a != c


def test_la_curva_de_actos_suba():
    """Las criaturas del acto 3 pegan y aguantan más que las del acto 1."""
    rng = random.Random(7)
    fragil = director._ficha_enemigo(1, rng)
    duro = director._ficha_enemigo(3, rng)
    assert duro["vida"] > fragil["vida"]
    assert duro["ataque"] > fragil["ataque"]
    assert duro["experiencia"] > fragil["experiencia"]


def test_el_plan_de_p4_embosca_si_hubo_robo():
    rng = random.Random(7)
    sin_robo = director.plan_encuentro("p4", {}, rng)
    con_robo = director.plan_encuentro("p4", {"robo": True}, rng)
    assert sin_robo["emboscada"] is None
    assert con_robo["emboscada"] == {
        "enemigo_local": "e2",
        "condicion": {"flag": "robo"},
    }


def test_la_emboscada_cobra_en_el_ultimo_encuentro_de_cada_tramo():
    """La bandera canónica «robo»: el cobrador espera donde toque, tramo al tras."""
    for clave, tramo in director.tramos().items():
        lugares = tramo["lugares"]
        ultimo = director._ultimo_encuentro(lugares)
        con_robo = director.plan_encuentro(ultimo, {"robo": True}, random.Random(7), tramo=clave)
        assert con_robo["emboscada"] is not None, clave
        for otro in lugares:
            if otro != ultimo and lugares[otro][0] == "encuentro":
                plan = director.plan_encuentro(otro, {"robo": True}, random.Random(7), tramo=clave)
                assert plan["emboscada"] is None, (clave, otro)


def test_rellena_pone_claves_en_su_lugar():
    """Las claves del fragmento viven namespacedas por lugar: sin colisiones."""
    rng = random.Random(7)
    for lid in ("p2", "p4", "p5"):
        plan = director.plan_encuentro(lid, {}, rng)
        fragmento = director.rellena(lid, plan, "Prosa de llegada.", {}, "nombre")
        for seccion in ("items", "enemigos", "eventos"):
            for clave in fragmento[seccion]:
                assert clave.startswith(lid + "_"), (lid, clave)
        for clave in fragmento["enemigos_del_lugar"]:
            assert clave.startswith(lid + "_")


def test_todos_los_stubs_se_rellenan_con_plantilla():
    """El piso procedural completo: una partida jugable sin modelo.

    Cada premisa, con un proveedor vacío: construir rellena p1 y el
    resto de stubs se llena con plantillas; el mundo acumulado valida
    de punta a punta y ningún lugar queda con su descripción de borrador.
    """
    for premisa in director.PREMISAS:
        sesion = SesionViva(
            premisa=premisa,
            heroe="espada",
            proveedor=ProveedorFalso([]),  # vacío: ni una llamada posible
            semilla=11,
        )
        av = sesion.construir()
        assert av is not None
        for lid in list(sesion.stubs):
            sesion._rellena(lid, flags={})
        assert sesion.stubs == set()
        av = cargar_aventura_dict(sesion.aventura_dict, "mundo rellenado")
        for lid, lugar in av.lugares.items():
            assert (
                lugar.descripcion != "Aún no hay nada escrito aquí: el cronista lo hará al llegar."
            ), lid
        # y la decisión con bandera «ofrenda» deja la señal que espera el
        # final, en el lugar que le haya tocado según el tramo
        decisiones = [
            ev
            for ev in sesion.aventura_dict["eventos"].values()
            if isinstance(ev, dict) and ev.get("tipo") == "decision"
        ]
        ofrenda = next(
            op for ev in decisiones for op in ev["opciones"] if op["flag"] == "ofrenda"
        )
        assert ofrenda["clave"] in ("ofrenda", "velar")
        clemencia = next(
            op
            for op in sesion.aventura_dict["eventos"]["final_cima"]["opciones"]
            if op.get("requiere_flag")
        )
        assert clemencia["requiere_flag"] == "ofrenda"


def test_el_jefe_y_el_final_hablan_de_la_premisa():
    esqueleto = director.esqueleto(director.PREMISAS[1], 7)
    jefe = esqueleto.aventura["enemigos"]["guardian_cima"]
    final = esqueleto.aventura["eventos"]["final_cima"]
    assert director.PREMISAS[1].antagonista.capitalize() in jefe["nombre"]
    assert director.PREMISAS[1].corte in final["texto"]
    # exactamente una opción sin epílogo (la del desenlace por defecto)
    sin_epilogo = [op for op in final["opciones"] if "epilogo" not in op]
    assert len(sin_epilogo) == 1


def test_sanea_fragmento_ante_la_plantilla_no_cambia_nada_sustancial():
    """El saneo no rompe lo que ya era sano (idempotente en plantillas)."""
    rng = random.Random(3)
    plan = director.plan_encuentro("p2", {}, rng)
    fragmento = director.plantilla("p2", plan, "la hondonada gris")
    saneado = sanea_fragmento(fragmento)
    assert saneado["lugar"] == fragmento["lugar"]
    assert saneado["descripcion"] == fragmento["descripcion"]


# ── premisas, héroes y planes ─────────────────────────────────────────────


def test_las_premisas_viajan_en_dict_y_vuelven():
    for premisa in director.PREMISAS:
        assert director.premisa_de_diccionario(premisa.diccionario()) == premisa
    # y una premisa escrita por el jugador se reconstruye sin ser de la casa
    propia = director.premisa_de_diccionario({"texto": "algo que soñé", "titulo": "Algo"})
    assert propia.clave == "propia"
    assert propia.texto == "algo que soñé"


def test_arquetipo_desconocido_da_al_primero():
    assert director.arquetipo("nadie") is director.ARQUETIPOS[0]
    assert director.arquetipo("letrada") is director.ARQUETIPOS[2]


def test_los_textos_fijos_del_esqueleto_no_llevan_llaves_ajenas():
    esqueleto = director.esqueleto(director.PREMISAS[0], 7)
    av = esqueleto.aventura
    assert "{" not in av["prologo_base"]  # el prólogo se imprime sin formatear
    for texto in av["epilogos"].values():
        assert "{" not in texto
    final = av["eventos"]["final_cima"]
    assert final["texto_companeros"] == "A tu espalda, con la faena hecha: {nombres}."


def test_cada_lugar_del_tramo_da_su_plan():
    rng = random.Random(3)
    planes = {
        lid: director.plan_encuentro(lid, {"robo": True}, rng)
        for lid in ("p1", "p2", "p3", "p4", "p5", "p6", "p7")
    }
    assert planes["p1"]["enemigos"] == {}  # el arranque, sin colmillos
    assert planes["p2"]["enemigos"] and planes["p2"]["decision"]
    assert planes["p3"]["npc"] and planes["p3"]["decision"]
    assert "e2" in planes["p4"]["enemigos"]  # el cobrador, por el robo en p2
    assert planes["p5"]["botin"] and len(planes["p5"]["enemigos"]) == 2
    assert planes["p6"]["curar"] and planes["p6"]["npc"]
    assert planes["p7"]["corrupcion"] and planes["p7"]["enemigos"]


def test_el_resumen_del_plan_nombra_lo_que_hay():
    rng = random.Random(3)
    resumen = director.resumen_plan(director.plan_encuentro("p2", {}, rng))
    assert "criaturas hostiles" in resumen
    assert "decisión" in resumen
    vacio = director.resumen_plan(
        {
            "enemigos": {},
            "botin": {},
            "monedas": 0,
            "npc": False,
            "curar": False,
            "corrupcion": 0,
            "decision": None,
            "emboscada": None,
        }
    )
    assert "sin nada especial" in vacio


# ── los tramos: el mapa también sale del dato ────────────────────────────


def test_cada_tramo_del_dato_nace_valido_y_conectado():
    premisa = director.PREMISAS[0]
    for clave in director.tramos():
        esqueleto = director.esqueleto(premisa, 7, tramo=clave)
        assert esqueleto.tramo == clave
        av = cargar_aventura_dict(esqueleto.aventura, f"tramo {clave}")
        assert len(av.lugares) == 8
        assert esqueleto.final == "cima"
        # todo el mapa se alcanza a pie desde la entrada
        vistos = {"p1"}
        frontera = ["p1"]
        while frontera:
            aqui = frontera.pop()
            for destino in av.lugares[aqui].salidas.values():
                if destino not in vistos:
                    vistos.add(destino)
                    frontera.append(destino)
        assert vistos == set(av.lugares), clave


def test_el_tramo_lo_elige_la_semilla_y_se_puede_fijar():
    premisa = director.PREMISAS[0]
    assert director.esqueleto(premisa, 5).tramo == "recto"
    assert director.esqueleto(premisa, 1).tramo == "delta"
    # y con la misma semilla, la misma elección
    a = json.dumps(director.esqueleto(premisa, 5).aventura)
    b = json.dumps(director.esqueleto(premisa, 5).aventura)
    assert a == b


# ── banderas canónicas y nombres del cronista ────────────────────────────


def test_la_bandera_canonica_de_la_decision_va_al_fragmento():
    rng = random.Random(3)
    plan = director.plan_encuentro("p2", {}, rng)
    fragmento = director.rellena("p2", plan, "Prosa.", {}, "nombre")
    opciones = fragmento["eventos"]["p2_decision"]["opciones"]
    robar = next(op for op in opciones if op["clave"] == "robar")
    assert robar["flag"] == "robo"  # canónica: la lee el cobrador
    otra = next(op for op in opciones if op["clave"] == "marcar")
    assert otra["flag"] == "p2_marcar"  # las que no cruzan actos, namespacedas


def test_rellena_nombra_enemigos_botin_y_detalles_con_el_cronista():
    rng = random.Random(3)
    plan = director.plan_encuentro("p5", {}, rng)  # ruina: dos enemigos y botín
    datos = {
        "enemigo_1": "una cosa con tijeras",
        "botin_1": "la caja de hierro",
        "botin_1_desc": "Cerrada desde dentro.",
    }
    fragmento = director.rellena("p5", plan, "Prosa.", datos, "la torre roída")
    assert fragmento["enemigos"]["p5_e1"]["nombre"] == "una cosa con tijeras"
    assert fragmento["enemigos"]["p5_e2"]["nombre"]  # sin nombre del cronista: tabla
    assert fragmento["items"]["p5_b1"]["nombre"] == "la caja de hierro"
    assert fragmento["items"]["p5_b1"]["desc"] == "Cerrada desde dentro."
    plan_p2 = director.plan_encuentro("p2", {}, random.Random(3))
    fragmento_p2 = director.rellena(
        "p2",
        plan_p2,
        "Prosa.",
        {"opcion_1": "Quedárselo", "opcion_1_det": "Nadie lo vio."},
        "la hondonada gris",
    )
    primera = fragmento_p2["eventos"]["p2_decision"]["opciones"][0]
    assert primera["titulo"] == "Quedárselo"
    assert primera["detalle"] == "Nadie lo vio."

"""Sanidad de todas las aventuras registradas: conexiones, claves y fichas."""

from __future__ import annotations

import pytest

from aldamar.contenido.aventura import AVENTURAS
from aldamar.contenido.mundo import alcanzables, normaliza


def param_all_aventuras():
    return pytest.mark.parametrize("av", list(AVENTURAS.values()), ids=lambda a: a.id)


def test_hay_al_menos_una_aventura_registrada():
    assert "corazon_ceniza" in AVENTURAS


@param_all_aventuras()
def test_todas_las_salidas_apuntan_a_lugares_existentes(av):
    for lid, lugar in av.lugares.items():
        for palabra, destino in lugar.salidas.items():
            assert destino in av.lugares, f"{lid} --{palabra}--> {destino} no existe"


@param_all_aventuras()
def test_todos_los_lugares_son_alcanzables_desde_el_inicio(av):
    assert alcanzables(av.lugares, av.lugar_inicial) == set(av.lugares)


@param_all_aventuras()
def test_enemigos_objetos_dialogos_y_tiendas_usan_claves_validas(av):
    for lugar in av.lugares.values():
        for e in lugar.enemigos:
            assert e in av.enemigos, f"{lugar.id}: enemigo {e} no existe"
        for o in lugar.objetos:
            assert o in av.items, f"{lugar.id}: objeto {o} no existe"
        for _npc, dialogo in lugar.npcs.items():
            assert dialogo in av.dialogos, f"{lugar.id}: diálogo {dialogo} no existe"
        if lugar.tienda:
            assert lugar.id in av.tiendas, f"{lugar.id} es tienda pero no tiene stock"
    for tienda, stock in av.tiendas.items():
        assert tienda in av.lugares
        for k in stock:
            assert k in av.items


@param_all_aventuras()
def test_los_requisitos_de_entrada_son_conseguibles(av):
    for lugar in av.lugares.values():
        if lugar.requiere:
            assert lugar.requiere in av.items, f"{lugar.id} exige un item inexistente"
            assert lugar.requiere_texto, f"{lugar.id} exige algo pero no explica qué"
            # el requisito se compra en alguna tienda o aparece por el mapa
            en_tienda = any(lugar.requiere in stock for stock in av.tiendas.values())
            en_suelo = any(lugar.requiere in l.objetos for l in av.lugares.values())
            regalado = any(
                lugar.requiere in texto
                for texto in av.dialogos.values()  # no es prueba fuerte, solo pista
            ) or any(l.eventos for l in av.lugares.values())
            assert en_tienda or en_suelo or regalado, (
                f"{lugar.id} exige {lugar.requiere} pero nadie lo provee"
            )


@param_all_aventuras()
def test_la_gente_reclutable_tiene_ficha_y_dialogo(av):
    for clave, companero in av.reclutas.items():
        assert companero.vida_max > 0
        assert clave in av.dialogos, f"{clave} reclutable pero sin diálogo"
        sitios = [l for l in av.lugares.values() if clave in l.npcs]
        assert sitios, f"{clave} no aparece en ningún lugar"


@param_all_aventuras()
def test_el_personaje_inicial_es_valido(av):
    assert av.jugador_inicial in av.personajes
    ficha = av.personajes[av.jugador_inicial]
    assert ficha.vida > 0 and ficha.ataque > 0
    for k in ficha.inventario:
        assert k in av.items
    assert av.prologo.strip() and av.texto_nombre.strip()
    assert av.lugar_inicial in av.lugares
    assert av.epilogo_muerte.strip() and av.epilogo_caida.strip()


@param_all_aventuras()
def test_los_eventos_y_el_ataque_especial_son_llamables(av):
    for clave, evento in av.eventos.items():
        assert callable(evento), f"evento {clave} no es llamable"
    if av.comando_especial:
        assert av.ataque_especial is not None
        assert av.texto_especial_fuera


@param_all_aventuras()
def test_cada_aventura_declara_eventos_propios(av):
    """Toda aventura trae sus propios eventos: sin ellos no hay historia."""
    assert av.eventos, f"{av.id} no declara ningún evento"


def test_normaliza_quita_tildes_y_mayusculas():
    assert normaliza("Ciénagas  ") == "cienagas"
    assert normaliza("CORAZÓN") == "corazon"


@param_all_aventuras()
def test_dialogos_de_todas_las_aventuras_son_validos(av):
    """Todos los diálogos de cada aventura son cadenas o listas no vacías de cadenas."""
    for clave, dialogo in av.dialogos.items():
        if isinstance(dialogo, str):
            assert dialogo.strip(), f"{av.id}: diálogo {clave} es cadena vacía"
        elif isinstance(dialogo, list):
            assert dialogo, f"{av.id}: diálogo {clave} es lista vacía"
            for i, d in enumerate(dialogo):
                assert isinstance(d, str) and d.strip(), f"{av.id}: diálogo {clave}[{i}] no es texto válido"
        else:
            pytest.fail(f"{av.id}: diálogo {clave} no es str ni list")


@param_all_aventuras()
def test_secretos_de_todas_las_aventuras_son_validos(av):
    """Todos los secretos declarados son válidos, no vacíos y con campos bien tipados."""
    for clave, sec in av.secretos.items():
        assert sec.comando and sec.comando.strip(), f"{av.id}: secreto {clave} sin comando"
        assert sec.textos, f"{av.id}: secreto {clave} sin textos"
        for i, t in enumerate(sec.textos):
            assert isinstance(t, str) and t.strip(), f"{av.id}: secreto {clave}.textos[{i}] no es texto"
        if sec.texto_combate is not None:
            assert isinstance(sec.texto_combate, str) and sec.texto_combate.strip()
        for alias in sec.alias:
            assert isinstance(alias, str) and alias.strip()
        for sem, txt in sec.semillas.items():
            assert isinstance(sem, int)
            assert isinstance(txt, str) and txt.strip()


@param_all_aventuras()
def test_items_con_texto_uso_son_cadenas_no_vacias(av):
    """Cualquier item que declare texto_uso tiene una cadena no vacía."""
    for iid, item in av.items.items():
        texto_uso = item.get("texto_uso")
        if texto_uso is not None:
            assert isinstance(texto_uso, str) and texto_uso.strip(), f"{av.id}: item {iid} texto_uso inválido"

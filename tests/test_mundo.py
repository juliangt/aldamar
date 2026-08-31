"""Sanidad del mapa de Aldamar: conexiones, alcanzabilidad y claves válidas."""

from aldamar.datos import DIALOGOS, ENEMIGOS, ITEMS, RECLUTAS, TIENDAS
from aldamar.mundo import LUGARES, LUGAR_INICIAL, alcanzables, normaliza


def test_todas_las_salidas_apuntan_a_lugares_existentes():
    for lid, lugar in LUGARES.items():
        for palabra, destino in lugar.salidas.items():
            assert destino in LUGARES, f"{lid} --{palabra}--> {destino} no existe"


def test_todos_los_lugares_son_alcanzables_desde_el_inicio():
    assert alcanzables(LUGAR_INICIAL) == set(LUGARES)


def test_enemigos_objetos_y_dialogos_usan_claves_validas():
    for lugar in LUGARES.values():
        for e in lugar.enemigos:
            assert e in ENEMIGOS
        for o in lugar.objetos:
            assert o in ITEMS
        for _npc, dialogo in lugar.npcs.items():
            assert dialogo in DIALOGOS


def test_los_requisitos_de_entrada_son_conseguibles():
    assert LUGARES["minas"].requiere == "antorcha"
    # la antorcha se compra en Ríoclaro o se recoge en el bosque, ambos antes de las minas
    assert "antorcha" in TIENDAS["rioclaro"] or "antorcha" in LUGARES["bosque"].objetos
    assert LUGARES["yerma"].requiere == "estandarte"
    # el estandarte lo otorga el consejo de Valoria, que está en el camino a las minas
    assert LUGARES["valoria"].evento == "consejo"


def test_toda_la_gente_reclutable_tiene_ficha_y_dialogo():
    for clave, companero in RECLUTAS.items():
        assert companero.vida_max > 0
        assert clave in DIALOGOS
        sitios = [l for l in LUGARES.values() if clave in l.npcs]
        assert sitios, f"{clave} no aparece en ningún lugar"


def test_normaliza_quita_tildes_y_mayusculas():
    assert normaliza("Ciénagas  ") == "cienagas"
    assert normaliza("CORAZÓN") == "corazon"

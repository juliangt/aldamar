"""Las habilidades de enemigo y las fases de jefe (issue #16).

El combate deja de ser un intercambio de golpes: veneno que pica,
curarse, refuerzos que alargan la cola del lugar y el golpe fuerte que
se anuncia antes de caer. Con semilla fija, la tómbola es determinista.
"""

from __future__ import annotations

import copy

from conftest import EntradaTipeada

from aldamar.contenido.aventura import Aventura, obtener_aventura
from aldamar.contenido.cargador import cargar_aventura_dict
from aldamar.motor.dificultad import obtener_dificultad
from aldamar.motor.juego import Juego

CAMINO = obtener_dificultad("camino")

AVENTURA_BASE = {
    "id": "aventura_de_habilidades",
    "titulo": "La Prueba de Armas",
    "descripcion": "una aventura mínima para probar el combate",
    "texto_nombre": "¿Nombre, probador? ({nombre}): ",
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


def _aventura(enemigos: dict, en_el_claro: list[str] | None = None) -> Aventura:
    datos = copy.deepcopy(AVENTURA_BASE)
    datos["enemigos"] = enemigos
    datos["lugares"]["claro"]["enemigos"] = en_el_claro or []
    return cargar_aventura_dict(datos, "habilidades.json")


def _juego(av: Aventura, lineas: list[str] | None = None, semilla: int = 7):
    salida: list[str] = []
    juego = Juego(
        av, semilla=semilla, entrada=EntradaTipeada(list(lineas or [])),
        salida=salida.append, color=False,
    )
    return juego, salida


def test_el_veneno_muerde_durante_tres_turnos_y_se_apaga():
    av = _aventura({
        "espectro": {
            "nombre": "espectro de ceniza", "vida": 30, "ataque": 2,
            "habilidades": [{
                "tipo": "veneno", "texto": "El toque frío te encuentra",
                "dano": 2, "turnos": 3,
            }],
        }
    })
    juego, _ = _juego(av)
    enemigo = av.crear_enemigo("espectro", CAMINO)
    juego._usa_habilidad(enemigo, enemigo.habilidades[0], 0, {})
    assert juego.jugador.envenenado
    assert juego.jugador.veneno_dano == 2 and juego.jugador.veneno_turnos == 3

    for restante in (2, 1, 0):
        assert not juego._pica_veneno()
        assert juego.jugador.veneno_turnos == restante
        assert juego.jugador.vida == juego.jugador.vida_max - 2 * (3 - restante)
    assert not juego.jugador.envenenado  # el ardor se apaga solo


def test_el_veneno_mas_reciente_manda():
    av = _aventura({"sombra": {"nombre": "sombra", "vida": 5, "ataque": 1}})
    juego, _ = _juego(av)
    juego.jugador.envenenar(2, 3)
    juego.jugador.envenenar(5, 1)
    assert juego.jugador.veneno_dano == 5
    assert juego.jugador.veneno_turnos == 3  # la duración no se acorta


def test_el_veneno_puede_matar():
    av = _aventura({"sombra": {"nombre": "sombra", "vida": 5, "ataque": 1}})
    juego, salida = _juego(av)
    juego.jugador.vida = 1
    juego.jugador.envenenar(2, 3)
    assert juego._pica_veneno()
    assert juego.fin and juego.final == "muerte"
    assert "Ahí quedó." in "\n".join(salida)


def test_los_estados_no_sobreviven_al_duelo():
    av = _aventura({"sombra": {"nombre": "sombra", "vida": 3, "ataque": 1}})
    juego, _ = _juego(av, ["atacar"] * 5)
    juego.jugador.vida = juego.jugador.vida_max = 40
    juego.jugador.envenenar(9, 9)
    assert juego._duelo(av.crear_enemigo("sombra", CAMINO)) == "victoria"
    assert not juego.jugador.envenenado


def test_curarse_sana_y_no_se_pasa_de_vida():
    av = _aventura({
        "custodio": {
            "nombre": "custodio", "vida": 20, "ataque": 3,
            "habilidades": [{"tipo": "curarse", "texto": "El humo lo recompone", "puntos": 50}],
        }
    })
    juego, salida = _juego(av)
    enemigo = av.crear_enemigo("custodio", CAMINO)
    enemigo.vida = 5
    juego._usa_habilidad(enemigo, enemigo.habilidades[0], 0, {})
    assert enemigo.vida == enemigo.vida_max
    assert "recompone" in "\n".join(salida)


def test_el_golpe_fuerte_avisa_un_turno_y_cae_al_siguiente():
    av = _aventura({
        "capitan": {
            "nombre": "capitán", "vida": 30, "ataque": 5,
            "habilidades": [{
                "tipo": "golpe_fuerte",
                "texto_aviso": "Alza el mandoble…",
                "texto_golpe": "¡El mandoble cae: −{efectivo}!",
                "dano_extra": 6,
            }],
        }
    })
    juego, salida = _juego(av)
    enemigo = av.crear_enemigo("capitan", CAMINO)
    vida_antes = juego.jugador.vida

    juego._usa_habilidad(enemigo, enemigo.habilidades[0], 0, {})
    assert enemigo.cargado == 6
    assert juego.jugador.vida == vida_antes  # avisar no es golpear

    juego._turno_enemigo(enemigo, {})
    assert enemigo.cargado == 0
    assert juego.jugador.vida < vida_antes  # el golpe avisado cayó
    assert "mandoble cae" in "\n".join(salida)  # el texto propio, con su {efectivo}


def test_el_refuerzo_entra_en_la_cola_y_se_pelea():
    av = _aventura(
        {
            "jefe": {
                "nombre": "jefe", "vida": 8, "ataque": 2, "experiencia": 5,
                "habilidades": [{
                    "tipo": "refuerzo", "texto": "Llama a su escudero:",
                    "enemigo": "escudero", "veces": 1,
                }],
            },
            "escudero": {"nombre": "escudero", "vida": 5, "ataque": 1, "experiencia": 3},
        },
        en_el_claro=["jefe"],
    )
    juego, _ = _juego(av, ["atacar"] * 20)
    jefe = av.crear_enemigo("jefe", CAMINO)
    juego._usa_habilidad(jefe, jefe.habilidades[0], 0, {})
    assert juego.enemigos["claro"] == ["jefe", "escudero"]

    juego.jugador.vida = juego.jugador.vida_max = 100
    juego._combate()
    assert juego.enemigos["claro"] == []  # el refuerzo también peleó
    assert juego.jugador.experiencia > 0  # y ambos pagaron experiencia


def test_veces_agota_la_habilidad_para_la_tombola():
    av = _aventura({
        "jefe": {
            "nombre": "jefe", "vida": 8, "ataque": 2,
            "habilidades": [{
                "tipo": "refuerzo", "texto": "Llama:", "enemigo": "escudero", "veces": 1,
            }],
        },
        "escudero": {"nombre": "escudero", "vida": 5, "ataque": 1},
    })
    juego, _ = _juego(av)
    jefe = av.crear_enemigo("jefe", CAMINO)
    hab = jefe.habilidades[0]
    assert juego._habilitada(jefe, hab, usada=0)
    assert not juego._habilitada(jefe, hab, usada=1)


def test_las_condiciones_abren_y_cierran_la_tombola():
    av = _aventura({
        "jefe": {
            "nombre": "jefe", "vida": 20, "ataque": 2,
            "habilidades": [
                {
                    "tipo": "curarse", "texto": "Se recompone", "puntos": 2,
                    "condicion": {"vida_menor_que": 50},
                },
                {
                    "tipo": "veneno", "texto": "Escupe bilis", "dano": 1, "turnos": 2,
                    "condicion": {"cada_n_turnos": 3},
                },
            ],
        }
    })
    juego, _ = _juego(av)
    jefe = av.crear_enemigo("jefe", CAMINO)
    curarse, veneno = jefe.habilidades

    # vida_menor_que: cerrada con el enemigo entero, abierta herido
    assert not juego._habilitada(jefe, curarse, usada=0)
    jefe.vida = jefe.vida_max // 2 - 1
    assert juego._habilitada(jefe, curarse, usada=0)

    # cada_n_turnos: solo en los turnos múltiplos de N
    jefe.turno = 1
    assert not juego._habilitada(jefe, veneno, usada=0)
    jefe.turno = 3
    assert juego._habilitada(jefe, veneno, usada=0)


def test_las_fases_cambian_la_ficha_y_no_vuelven_atras():
    av = _aventura({
        "morvath": {
            "nombre": "Morvath, tejido de humo", "vida": 36, "ataque": 9,
            "fases": [{
                "vida_menor_que": 50,
                "texto": "El humo se rasga por dentro.",
                "nombre": "Morvath, la Aguja viva",
                "ataque": 11,
            }],
        }
    })
    _, _ = _juego(av)
    morvath = av.crear_enemigo("morvath", CAMINO)
    assert morvath.fase_actual == -1
    assert morvath.avanzar_fase() is None  # entero: no cruza

    morvath.vida = 17  # por debajo del 50%
    transicion = morvath.avanzar_fase()
    assert transicion == "El humo se rasga por dentro."
    assert morvath.nombre == "Morvath, la Aguja viva"
    assert morvath.ataque == 11

    morvath.curar(100)  # sana por encima del umbral: no hay vuelta atrás
    assert morvath.avanzar_fase() is None
    assert morvath.nombre == "Morvath, la Aguja viva"


def test_la_transicion_de_fase_se_ve_durante_el_duelo():
    av = _aventura({
        "morvath": {
            "nombre": "Morvath", "vida": 10, "ataque": 1,
            "fases": [{"vida_menor_que": 50, "texto": "Cambia la piel.", "ataque": 2}],
        }
    })
    juego, salida = _juego(av, ["atacar"] * 8)
    juego.jugador.vida = juego.jugador.vida_max = 100
    assert juego._duelo(av.crear_enemigo("morvath", CAMINO)) == "victoria"
    assert "Cambia la piel." in "\n".join(salida)


def test_los_umbrales_de_fase_se_cruzan_en_orden():
    av = _aventura({
        "jefe": {
            "nombre": "jefe", "vida": 100, "ataque": 2,
            "fases": [
                {"vida_menor_que": 75, "texto": "Primera.", "ataque": 3},
                {"vida_menor_que": 30, "texto": "Segunda.", "ataque": 4},
            ],
        }
    })
    _, _ = _juego(av)
    jefe = av.crear_enemigo("jefe", CAMINO)
    assert [f.umbral for f in jefe.fases] == [75, 30]  # de mayor a menor

    jefe.vida = 20  # cruza ambos de un golpe, pero de a uno por turno
    assert jefe.avanzar_fase() == "Primera."
    assert jefe.ataque == 3
    assert jefe.avanzar_fase() == "Segunda."
    assert jefe.ataque == 4
    assert jefe.avanzar_fase() is None


def test_la_tombola_es_determinista_bajo_la_misma_semilla():
    enemigos = {
        "jefe": {
            "nombre": "jefe", "vida": 50, "ataque": 3,
            "habilidades": [
                {"tipo": "veneno", "texto": "Veneno", "dano": 1, "turnos": 2, "peso": 3},
                {"tipo": "curarse", "texto": "Cura", "puntos": 3, "peso": 3},
            ],
        }
    }
    huellas = []
    for _ in range(2):
        av = _aventura(enemigos)
        juego, salida = _juego(av, semilla=11)
        jefe = av.crear_enemigo("jefe", CAMINO)
        for _turno in range(12):
            jefe.vida = 10  # condiciones estables: solo decide la tómbola
            juego.jugador.vida = juego.jugador.vida_max = 100
            juego.jugador.veneno_dano = juego.jugador.veneno_turnos = 0
            juego._turno_enemigo(jefe, {})
        huellas.append(" ".join(salida))
    assert huellas[0] == huellas[1]


def test_morvath_pelea_en_fases_en_la_aventura_real():
    av = obtener_aventura("aguja_sin_sombra")
    morvath = av.crear_enemigo("morvath", CAMINO)
    assert morvath.sin_huida
    morvath.vida = morvath.vida_max // 2 - 1
    assert morvath.avanzar_fase()
    tipos = {h.tipo for h in morvath.habilidades}
    assert "curarse" in tipos and "refuerzo" in tipos
    refuerzo = next(h for h in morvath.habilidades if h.tipo == "refuerzo")
    assert refuerzo.enemigo in av.enemigos


def test_el_refuerzo_del_jefe_real_se_pelea_de_punta_a_punta():
    av = obtener_aventura("aguja_sin_sombra")
    juego, salida = _juego(av, ["atacar"] * 80, semilla=3)
    juego.jugador.vida = juego.jugador.vida_max = 300
    juego.enemigos[juego.lugar] = ["morvath"]
    juego._combate()
    texto = "\n".join(salida)
    assert "la Aguja viva" in texto  # cruzó su fase
    assert "entra en combate" in texto  # llamó al refuerzo…
    assert juego.enemigos[juego.lugar] == []  # …y el refuerzo también peleó
    assert juego.jugador.nivel > 1  # la saga también da niveles

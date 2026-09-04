"""Las aventuras de la serie «Las Ascuas del Corazón» (issue #2).

Cada aventura mantiene hilo con la anterior sin depender de ella:
aquí se prueba el hilo mecánico —decisiones que dejan bandera, la
bandera que abre un final distinto, la emboscada que cobra una deuda—
y que las tres se ganan de verdad, de punta a punta.
"""

from __future__ import annotations

import pytest
from conftest import EntradaTipeada

from aldamar.contenido.aventura import obtener_aventura
from aldamar.contenido.personajes import CORRUPCION_TENTADO
from aldamar.motor.dificultad import DIFICULTADES, obtener_dificultad
from aldamar.motor.juego import Juego

BRASA = obtener_aventura("brasa_vegaverde")
SAL = obtener_aventura("sal_y_ceniza")
AGUJA = obtener_aventura("aguja_sin_sombra")

G6 = ["atacar"] * 6
G9 = ["atacar"] * 9
G10 = ["atacar"] * 10
G12 = ["atacar"] * 12


def _jugar(av, lineas: list[str], *, semilla: int = 7, personaje=None, dificultad=None):
    salida: list[str] = []
    juego = Juego(
        av,
        dificultad=dificultad or obtener_dificultad("camino"),
        personaje=personaje,
        semilla=semilla,
        entrada=EntradaTipeada(list(lineas)),
        salida=salida.append,
        color=False,
    )
    juego.ciclo()
    return juego, salida


def _plano(salida: list[str]) -> str:
    return " ".join(" ".join(salida).split())


# ── el hilo conductor se ve en el contenido ──────────────────────────────

def test_la_serie_mantiene_el_hilo_con_la_aventura_anterior():
    # I: la brasa nace del humo que el Corazón escupió al mar
    assert "Corazón de Ceniza" in BRASA.prologo
    # II: la sal recoge lo que la I ahogó y arranca en Ríoclaro
    assert "Vegaverde" in SAL.prologo
    assert "Vegaverde" in SAL.dialogos["noticia_vado"]  # la II menciona la I


def test_el_orden_de_la_serie_lo_fija_el_campo_orden():
    assert BRASA.orden == 2 and SAL.orden == 3


# ── narrar ───────────────────────────────────────────────────────────────

def test_narrar_se_cuenta_una_sola_vez_con_una_vez():
    juego = Juego(SAL, semilla=7, entrada=EntradaTipeada([]), salida=lambda _t: None, color=False)
    juego.av.eventos["noticia"](juego, juego.aqui())
    juego.av.eventos["noticia"](juego, juego.aqui())
    assert juego.flags == {"noticia": True}


# ── decision ─────────────────────────────────────────────────────────────

def test_la_decision_aplica_efectos_y_deja_bandera():
    juego = Juego(BRASA, semilla=7, entrada=EntradaTipeada(["aceptar"]), salida=lambda _t: None, color=False)
    antes = list(juego.jugador.inventario)
    juego.av.eventos["colmena"](juego, juego.aqui())
    assert "panal" in juego.jugador.inventario and "panal" not in antes
    assert juego.flags == {"colmena": True, "bruna": True}

    juego.av.eventos["colmena"](juego, juego.aqui())  # una sola vez
    assert juego.jugador.inventario.count("panal") == 1


def test_la_decision_cancelada_no_decide():
    juego = Juego(BRASA, semilla=7, entrada=EntradaTipeada([]), salida=lambda _t: None, color=False)
    juego.av.eventos["colmena"](juego, juego.aqui())  # EOF: cancela
    assert juego.flags == {}
    assert "panal" not in juego.jugador.inventario


def test_cancelar_con_esc_limpia_la_pantalla_y_la_escena_se_vuelve_a_contar(monkeypatch):
    """Con flechas, Esc sale de la elección limpiando la pantalla (issue 24):
    el relato del lugar se va, pero la decisión sigue abierta y la escena
    se vuelve a contar tal y como era al re-entrar."""
    import aldamar.interfaz.opciones as opciones_mod

    salida: list[str] = []
    juego = Juego(
        BRASA, semilla=7, entrada=EntradaTipeada([]), salida=salida.append,
        color=False, flechas=True,
    )
    escena = "Bruna te alcanza un panal"
    monkeypatch.setattr(opciones_mod, "_leer_tecla", lambda: "\x1b")
    juego.av.eventos["colmena"](juego, juego.aqui())
    assert juego.flags == {}  # Esc no decide
    assert "\x1b[2J\x1b[H" in salida  # …pero la pantalla queda limpia

    monkeypatch.setattr(opciones_mod, "_leer_tecla", lambda: "\r")
    juego.av.eventos["colmena"](juego, juego.aqui())  # re-entrar: se cuenta de nuevo
    assert juego.flags == {"colmena": True, "bruna": True}
    assert "panal" in juego.jugador.inventario
    assert "\n".join(salida).count(escena) == 2


def test_la_decision_puede_costar_corrupcion():
    juego = Juego(SAL, semilla=7, entrada=EntradaTipeada(["quitar"]), salida=lambda _t: None, color=False)
    juego.av.eventos["faro"](juego, juego.aqui())
    assert juego.flags == {"faro": True, "faro_robado": True}
    assert "farol_sal" in juego.jugador.inventario
    assert juego.jugador.corrupcion == 8


# ── emboscar ─────────────────────────────────────────────────────────────

def test_la_emboscada_solo_salta_si_se_cumple_la_condicion():
    juego = Juego(SAL, semilla=7, entrada=EntradaTipeada([]), salida=lambda _t: None, color=False)
    salina = juego.av.lugares["salina_vieja"]
    juego.flags["faro_robado"] = True
    juego.av.eventos["traicion"](juego, salina)
    assert juego.enemigos["salina_vieja"] == ["viuda", "gaviota", "gaviota"]
    # no se repite mientras sigan ahí
    juego.av.eventos["traicion"](juego, salina)
    assert juego.enemigos["salina_vieja"] == ["viuda", "gaviota", "gaviota"]


def test_la_emboscada_se_queda_a_deber_si_la_condicion_no_se_cumple():
    juego = Juego(SAL, semilla=7, entrada=EntradaTipeada([]), salida=lambda _t: None, color=False)
    juego.flags["faro_robado"] = False
    juego.av.eventos["traicion"](juego, juego.av.lugares["salina_vieja"])
    assert juego.enemigos["salina_vieja"] == ["viuda"]


# ── final con opciones condicionales ─────────────────────────────────────

def test_el_final_condicional_exige_la_bandera_de_la_decision():
    juego = Juego(SAL, semilla=7, entrada=EntradaTipeada(["farera"]), salida=lambda _t: None, color=False)
    juego.flags["faro_encendido"] = True
    juego.av.eventos["final"](juego, juego.aqui())
    assert juego.fin and juego.final == "el faro de la ascua"


def test_sin_la_bandera_el_condicional_no_aparece_y_se_va_al_defecto():
    juego = Juego(SAL, semilla=7, entrada=EntradaTipeada(["farera", "salmuera"]), salida=lambda _t: None, color=False)
    juego.av.eventos["final"](juego, juego.aqui())
    # "farera" no se ofrece: el tipeado no la encuentra y elijo "salmuera"
    assert juego.fin and juego.final == "la sal vuelve a ser sal"


def test_el_defecto_del_final_mira_la_corrupcion():
    juego = Juego(SAL, semilla=7, entrada=EntradaTipeada(["salmuera"]), salida=lambda _t: None, color=False)
    juego.jugador.corruptear(CORRUPCION_TENTADO)
    juego.av.eventos["final"](juego, juego.aqui())
    assert juego.fin and juego.final == "la sal limpia, la grieta nadadora"


# ── partidas completas: la serie se gana ─────────────────────────────────

def test_la_brasa_se_gana_con_la_decision_encadenada():
    lineas = (
        ["", "tomar todo"]                                   # carta, hoz
        + ["ir este"] + G6 + ["tomar todo"]                  # ejido: roña + mirlo
        + ["ir sur", "tomar todo", "hablar perpetua"]        # lavadero: capa
        + ["ir oeste", "aceptar", "hablar bruna", "reclutar bruna"]  # colmenar
        + ["ir este", "ir norte"]                            # lavadero → ejido
        + ["ir este"] + G12 + ["usar panal"] + G6            # tejera: el Ahumado
        + ["cera"]                                           # final condicional
    )
    juego, salida = _jugar(BRASA, lineas)
    assert juego.fin and juego.final == "la brasa ahogada con cera"
    assert "Parche de las Dos" in _plano(salida)


def test_la_brasa_se_gana_tambien_sin_la_pastora():
    lineas = (
        ["", "tomar todo"]
        + ["ir este"] + G6 + ["tomar todo"]
        + ["ir sur", "tomar todo"]                            # capa
        + ["ir norte", "ir este"] + G12 + G6                  # el Ahumado
        + ["agua"]                                            # desenlace por defecto
    )
    juego, _ = _jugar(BRASA, lineas, personaje="enebro")
    assert juego.fin and juego.final == "la brasa ahogada en agua limpia"


def test_la_sal_se_gana_con_el_farol_encendido():
    lineas = (
        ["", "comprar pan_sal", "comprar pan_sal", "comprar abrigo", "descansar"]
        + ["ir sur"] + G6 + ["tomar todo"]                    # vado: noticia
        + ["ir sur"] + G6 + ["tomar todo"]                    # calzada
        + ["ir este", "encender", "hablar iseo", "reclutar iseo"]  # faro
        + ["ir oeste", "ir sur"] + G9 + ["tomar todo"]        # esteros: cangrejo
        + ["ir este"] + G9 + ["tomar todo"]                   # salinas: corrupción + mirlo
        + ["ir este"] + G12 + ["usar pan_sal"] + G9           # casa_sal: el Ahogado
        + ["hablar maruxa", "reclutar maruxa", "comprar aguardiente"]
        + ["ir este"] + G12 + ["usar aguardiente"] + G12      # salina_vieja: la Viuda
        + ["farera"]                                          # final condicional
    )
    juego, salida = _jugar(SAL, lineas)
    assert juego.fin and juego.final == "el faro de la ascua"
    assert "farera en la linterna" in _plano(salida)


def test_la_sal_se_gana_con_la_otra_heroa():
    lineas = (
        ["", "comprar cuchillo", "comprar pan_sal", "descansar"]
        + ["ir sur"] + G6 + ["tomar todo"]
        + ["ir sur"] + G6 + ["tomar todo"]
        + ["ir este", "quitar", "reclutar iseo"]              # el farol, robado
        + ["ir oeste", "ir sur"] + G9 + ["tomar todo"]
        + ["ir este"] + G9 + ["tomar todo"]
        + ["ir este"] + G12 + ["usar pan_sal"] + G9           # la robada chisporrotea
        + ["ir este"] + G12 + ["usar pan_sal"] + G12          # Viuda + gaviotas de la traición
        + ["salmuera"]
    )
    juego, _ = _jugar(SAL, lineas, personaje="tamara")
    assert juego.fin and juego.final == "la sal vuelve a ser sal"


@pytest.mark.parametrize("clave", sorted(DIFICULTADES))
@pytest.mark.parametrize("av_id", ["brasa_vegaverde", "sal_y_ceniza", "aguja_sin_sombra"])
def test_todas_las_dificultades_arrancan_la_serie(av_id, clave):
    """Sanidad de balance: cada dificultad respira en el arranque de la serie."""
    juego, salida = _jugar(
        obtener_aventura(av_id),
        ["", "mirar", "estado", "salir"],
        dificultad=obtener_dificultad(clave),
    )
    assert juego.fin  # salió limpio
    assert "Vida:" in _plano(salida)


# ── la saga: decisiones encadenadas, emboscadas y fases ─────────────────

def test_la_saga_hila_las_tres_aventuras():
    assert "Dos ascuas" in AGUJA.prologo          # I y II contadas como hechas
    assert "Corazón" in AGUJA.dialogos["tilo"]     # la I, en la voz de su héroe
    assert "marea gris" in AGUJA.dialogos["dorotea"]  # la II, en Ríoclaro
    assert "Parche de las Dos" in AGUJA.dialogos["enebro"]  # la I, en su huerto


def test_el_consejo_deja_bandera_y_estandarte():
    juego = Juego(AGUJA, semilla=7, entrada=EntradaTipeada(["alianza"]), salida=lambda _t: None, color=False)
    juego.av.eventos["estandarte"](juego, juego.aqui())
    assert juego.flags == {"estandarte": True, "consejo": True}
    assert "estandarte" in juego.jugador.inventario


def test_la_emboscada_del_capitan_castiga_no_jurar():
    juego = Juego(AGUJA, semilla=7, entrada=EntradaTipeada(["guardia"]), salida=lambda _t: None, color=False)
    juego.av.eventos["estandarte"](juego, juego.aqui())
    assert juego.flags == {"estandarte": True, "guardia": True}
    juego.av.eventos["regreso"](juego, juego.av.lugares["aguja_pies"])
    assert juego.enemigos["aguja_pies"] == ["mirlo", "capitan"]
    # con la Alianza jurada, el Capitán no aparece
    juego2 = Juego(AGUJA, semilla=7, entrada=EntradaTipeada(["alianza"]), salida=lambda _t: None, color=False)
    juego2.av.eventos["estandarte"](juego2, juego2.aqui())
    juego2.av.eventos["regreso"](juego2, juego2.av.lugares["aguja_pies"])
    assert juego2.enemigos["aguja_pies"] == ["mirlo"]


def test_el_jefe_final_pelea_en_tres_fases():
    """La cima guarda tres duelos seguidos: la Voz, el Capitán y Morvath."""
    juego = Juego(AGUJA, semilla=7, entrada=EntradaTipeada([]), salida=lambda _t: None, color=False)
    assert juego.av.lugares["aguja_cima"].enemigos == ["eco_voz", "capitan_rehecho", "morvath"]
    for clave in juego.av.lugares["aguja_cima"].enemigos:
        enemigo = juego.av.crear_enemigo(clave, obtener_dificultad("camino"))
        assert enemigo.sin_huida  # un jefe por fases no deja escapar


def test_el_final_de_la_alianza_exige_el_juramento():
    juego = Juego(AGUJA, semilla=7, entrada=EntradaTipeada(["alianza"]), salida=lambda _t: None, color=False)
    juego.flags["consejo"] = True
    juego.av.eventos["final"](juego, juego.aqui())
    assert juego.fin and juego.final == "la Alianza de las Cuatro"


def test_sin_juramento_la_alianza_no_se_ofrece():
    juego = Juego(AGUJA, semilla=7, entrada=EntradaTipeada(["alianza", "quebrar"]), salida=lambda _t: None, color=False)
    juego.av.eventos["final"](juego, juego.aqui())
    assert juego.fin and juego.final == "la Aguja sin Sombra"


def test_el_defecto_de_la_saga_mira_la_corrupcion():
    juego = Juego(AGUJA, semilla=7, entrada=EntradaTipeada(["quebrar"]), salida=lambda _t: None, color=False)
    juego.jugador.corruptear(CORRUPCION_TENTADO)
    juego.av.eventos["final"](juego, juego.aqui())
    assert juego.fin and juego.final == "la Aguja calla, la grieta canta"


def test_la_saga_se_gana_con_la_alianza_jurada():
    lineas = (
        ["", "tomar todo", "hablar oldo", "reclutar enebro"]
        + ["ir este"] + G9 + ["tomar todo", "reclutar tilo"]     # molino: el Capitán
        + ["ir este"] + G9 + ["tomar todo"]                      # encrucijada: sombra
        + ["ir norte", "descansar", "comprar jerba", "comprar jerba",
           "comprar jerba", "reclutar maruxa"]                                    # rioclaro
        + ["ir este", "alianza"]                                 # valoria: juramento
        + ["ir norte"] + G9 + ["tomar todo",
           "comprar coraza", "comprar vino", "comprar vino"]                     # barrok: fragua
        + ["ir este"] + G9 + ["tomar todo"]                      # ciénagas: corrupción
        + ["ir oeste"] + G9 + ["tomar todo"]                     # puente: espectro
        + ["ir norte", "descansar"]                              # refugio: campanilla
        + ["ir sur", "ir este"]                                  # puente → ciénagas
        + ["ir este"] + G9 + ["usar jerba"] + G9 + ["tomar todo"]  # yermos: lóberos
        + ["ir este"] + G9                                       # escalera: mirlo
        + ["ir este"]                                            # cumbre
        + G10 + ["usar jerba"]
        + G10 + ["usar vino"]
        + G12 + ["usar hogaza"] + G12 + ["usar vino", "usar jerba"]                            # tres fases
        + ["alianza"]
    )
    juego, salida = _jugar(AGUJA, lineas)
    assert juego.fin and juego.final == "la Alianza de las Cuatro"
    assert "cuatro nombres, uno por raza" in _plano(salida)


def test_la_saga_se_gana_sin_jurar_y_cobrando_la_emboscada():
    lineas = (
        ["", "tomar todo", "reclutar enebro"]
        + ["ir este"] + G9 + ["tomar todo", "reclutar tilo"]
        + ["ir este"] + G9 + ["tomar todo"]
        + ["ir norte", "descansar", "comprar jerba", "comprar jerba",
           "comprar jerba", "reclutar maruxa"]
        + ["ir este", "guardia"]                                 # sin juramento
        + ["ir norte"] + G9 + ["tomar todo",
           "comprar coraza", "comprar vino", "comprar vino"]
        + ["ir este"] + G9 + ["tomar todo"]
        + ["ir oeste"] + G9 + ["tomar todo"]
        + ["ir norte", "descansar"]
        + ["ir sur", "ir este"]
        + ["ir este"] + G9 + ["usar jerba"] + G9 + ["tomar todo"]
        + ["ir este"] + G12                                      # mirlo + emboscada
        + ["ir este"]
        + G10 + ["usar jerba"]
        + G10 + ["usar vino"]
        + G12 + ["usar hogaza"] + G12 + ["usar vino", "usar jerba"]
        + ["quebrar"]                                            # desenlace por defecto
    )
    juego, _ = _jugar(AGUJA, lineas)
    assert juego.fin and juego.final == "la Aguja sin Sombra"

"""El menú de acciones dentro del juego: flechas, Esc y el tipeado escondido."""

from __future__ import annotations

import aldamar.interfaz.opciones as opciones_mod
from aldamar import __version__
from aldamar.motor.juego import (
    COMPRAR,
    ESCRIBIR,
    HABLAR,
    IR,
    OTRAS,
    RECLUTAR,
    TOMAR,
    USAR,
    Juego,
)

from conftest import AVENTURA, EntradaTipeada

MENU_MINIMO = [
    ("mirar", "Mirar alrededor", ""),
    ("estado", "Estado", ""),
    ("salir", "Salir", ""),
]


def teclado(secuencia):
    """_leer_tecla sintético: consume la secuencia y luego siempre Enter."""
    pendientes = list(secuencia)
    return lambda: pendientes.pop(0) if pendientes else "\r"


def juego_flechas(monkeypatch, secuencia=(), opciones=None, lineas=(" ",)):
    """Partida forzada a flechas: teclas sintéticas + líneas para el tipeado.

    La primera línea es el nombre del héroe en el prólogo (vacío: el de
    siempre); las demás alimentan la opción "Escribir un comando…".
    """
    monkeypatch.setattr(opciones_mod, "_leer_tecla", teclado(secuencia))
    if opciones is not None:
        monkeypatch.setattr(Juego, "_opciones_juego", lambda self: opciones)
    salida: list[str] = []
    juego = Juego(
        AVENTURA,
        semilla=7,
        entrada=EntradaTipeada(list(lineas)),
        salida=salida.append,
        color=False,
        flechas=True,
    )
    return juego, salida


def test_el_menu_refleja_lo_que_hay_en_el_lugar(fabrica):
    juego, _ = fabrica(["ayuda", "salir"])
    claves = [c for c, _e, _d in juego._opciones_juego()]
    assert claves[0] == "mirar"
    assert any(c.startswith("ir ") for c in claves)  # los destinos del lugar
    assert TOMAR in claves  # hay objetos (y monedas) en el suelo de arranque
    assert "hablar belthar" in claves  # un solo npc: el verbo queda directo
    assert claves[-1] == OTRAS  # lo que no es gameplay vive en el submenú
    assert "guardar" not in claves and "estado" not in claves
    otras = [c for c, _e, _d in juego._opciones_otras()]
    assert "estado" in otras and "guardar" in otras and "ayuda" in otras
    assert otras[-1] == "salir"
    assert ESCRIBIR in otras  # el modo tipeado sigue ahí, escondido


def test_los_verbos_se_pandan_cuando_no_tienen_nada(fabrica, monkeypatch):
    juego, _ = fabrica(["salir"])
    l = juego.aqui()
    monkeypatch.setattr(l, "npcs", {})  # sin nadie que hable ni reclute
    juego.tomados.update((l.id, k) for k in l.objetos)
    juego.monedas_tomadas.add(l.id)
    juego.jugador.inventario.clear()
    claves = [c for c, _e, _d in juego._opciones_juego()]
    assert TOMAR not in claves and HABLAR not in claves and RECLUTAR not in claves
    assert USAR not in claves  # sin consumibles en la mochila
    assert COMPRAR not in claves  # vegaverde no es tienda


def test_un_verbo_con_una_sola_opcion_queda_directo(fabrica):
    juego, _ = fabrica(["salir"])
    claves = [c for c, _e, _d in juego._opciones_juego()]
    assert "ir 1" in claves  # vegaverde tiene un solo destino: sin submenú
    assert "hablar belthar" in claves  # y una sola persona a la que hablar
    assert IR not in claves and HABLAR not in claves


def test_el_verbo_abre_su_submenu_y_esc_vuelve(monkeypatch):
    juego, salida = juego_flechas(monkeypatch, ["3", "\r"], lineas=["", ""])
    orden = juego._leer_orden("¿Qué haces?", "> ", juego._opciones_juego())
    assert orden == "tomar todo"  # «3» abre el verbo Tomar; Enter, «Tomar todo»
    assert "Tomar — en Vegaverde" in "\n".join(salida)  # el submenú dice dónde estás

    monkeypatch.setattr(opciones_mod, "_leer_tecla", teclado(["3", "\x1b", "\r"]))
    salida.clear()
    orden = juego._leer_orden("¿Qué haces?", "> ", juego._opciones_juego())
    assert orden == "mirar"  # Esc volvió al menú de acciones, y allí se eligió
    assert "\n".join(salida).count("¿Qué haces?") == 2  # raíz, submenú y raíz otra vez


def test_el_submenu_dice_donde_estas_y_cuantas_cosas_hay(fabrica):
    juego, _ = fabrica(["salir"])
    juego.lugar = "rioclaro"
    titulo, ops = juego._submenu(COMPRAR)
    assert "Ríoclaro" in titulo and "4 cosas en venta" in titulo
    assert [c for c, _e, _d in ops][:4] == [f"comprar {k}" for k in juego.av.tiendas["rioclaro"]]
    titulo_ir, _ops_ir = juego._submenu(IR)
    assert "destinos" in titulo_ir
    juego.jugador.inventario.append("provisiones")
    titulo_usar, ops_usar = juego._submenu(USAR)
    assert "mochila" in titulo_usar and len(ops_usar) == 1  # lo que lleve consumible


def test_elegir_un_destino_del_menu_viaja(monkeypatch):
    juego, _ = juego_flechas(monkeypatch, ["2"], lineas=["", ""])
    juego.jugador.vida = juego.jugador.vida_max = 200
    juego._prologo()
    orden = juego._leer_orden("¿Qué haces?", "> ", juego._opciones_juego())
    assert orden == "ir 1"  # segundo renglón del menú: el primer destino
    juego._ejecutar(orden)
    assert juego.lugar != juego.av.lugar_inicial


def test_esc_avisa_y_el_menu_no_se_apila(monkeypatch):
    juego, salida = juego_flechas(monkeypatch, ["\x1b", "3"], opciones=MENU_MINIMO)
    juego.ciclo()
    texto = "\n".join(salida)
    assert juego.fin
    assert juego.lugar == juego.av.lugar_inicial  # Esc no movió de sitio
    assert "No hay vuelta atrás" in texto  # queda dicho por qué se queda
    assert texto.count("¿Qué haces?") == 1  # el menú no se vuelve a pintar


def test_tras_el_nombre_se_limpia_la_pantalla(monkeypatch):
    juego, salida = juego_flechas(monkeypatch, lineas=["", ""])
    juego._prologo()
    texto = "\n".join(salida)
    presentacion = AVENTURA.personajes[AVENTURA.jugador_inicial].presentacion
    assert texto.count("\x1b[2J\x1b[H") == 1  # una limpieza, la del nombre
    # el prólogo queda antes y la presentación después: se ve sola
    assert texto.index(AVENTURA.prologo[:15]) < texto.index("\x1b[2J\x1b[H") < texto.index(presentacion)


def test_el_estado_abre_cada_menu_de_raiz(monkeypatch):
    """La línea de estado (quién, cómo y dónde) va encima de cada menú
    de raíz; sin anclas: el relato fluye hacia abajo (issue 36)."""
    juego, salida = juego_flechas(monkeypatch, ["\x1b", "3"], opciones=MENU_MINIMO)
    juego._prologo()
    juego.ciclo()
    j = juego.jugador
    lugar = AVENTURA.lugares[AVENTURA.lugar_inicial].nombre
    estado = f"{j.nombre} · Vida {j.vida}/{j.vida_max} · {j.monedas} monedas · {lugar}"
    assert estado in salida  # la línea de estado, antes del menú
    assert salida.count(estado) == 1  # una vez por turno, no en cada redibujado
    assert not any(l.startswith("\x1b[H") for l in salida)  # nada se ancla arriba


def test_al_elegir_el_menu_no_deja_rastro(monkeypatch):
    juego, salida = juego_flechas(monkeypatch, ["3"], opciones=MENU_MINIMO, lineas=["", ""])
    juego._prologo()
    juego.ciclo()  # «3» elige Salir: el menú se borra y la despedida queda debajo
    texto = "\n".join(salida)
    assert "›" not in texto  # ni migas ni decisiones escritas: el resultado narra
    assert texto.count("¿Qué haces?") == 1  # el título se escribió una sola vez
    assert texto.endswith("Guardas las tomillas en el bolsillo y miras atrás una vez. Hasta pronto.")


def test_viajar_abre_la_escena_en_pantalla_limpia(monkeypatch):
    """Modo flechas: viajar es un cambio de escena y la escena se ve sola."""
    juego, salida = juego_flechas(monkeypatch, ["2"], lineas=["", ""])
    juego.jugador.vida = juego.jugador.vida_max = 200
    juego._prologo()
    orden = juego._leer_orden("¿Qué haces?", "> ", juego._opciones_juego())
    juego._ejecutar(orden)
    assert juego.lugar != juego.av.lugar_inicial
    assert salida.count("\x1b[2J\x1b[H") == 2  # la del prólogo y la del viaje


def test_en_modo_tipeado_viajar_deja_una_raya_de_escena(fabrica):
    juego, salida = fabrica(["", "ir 1", "salir"])
    juego.ciclo()
    assert "\n" + "─" * 40 in salida  # el relato tipeado sigue completo, con la raya


def test_el_modo_tipeado_no_lleva_cabecera(fabrica):
    juego, salida = fabrica(["", "ayuda", "salir"])
    juego.ciclo()
    assert not any("Aldamar " in l and __version__ in l for l in salida)


def test_el_estado_se_escribe_solo_cuando_cambia(monkeypatch):
    """Dos turnos sin novedades ni vistas: la línea de estado se escribe
    una sola vez (el segundo turno no la repite)."""
    juego, salida = juego_flechas(monkeypatch, ["2", "3"], opciones=MENU_MINIMO, lineas=["", ""])
    juego._prologo()
    juego.ciclo()  # «estado» (una gestión, no una vista); después, «salir»
    j = juego.jugador
    lugar = AVENTURA.lugares[AVENTURA.lugar_inicial].nombre
    estado = f"{j.nombre} · Vida {j.vida}/{j.vida_max} · {j.monedas} monedas · {lugar}"
    assert estado in salida
    assert salida.count(estado) == 1  # el segundo turno no la repite
    assert sum(l.count("¿Qué haces?") for l in salida) == 2  # y hubo dos menús


def test_las_vistas_abren_limpios_y_renuevan_el_estado(monkeypatch):
    """Mirar es una vista: pantalla limpia y el estado, de vuelta."""
    juego, salida = juego_flechas(monkeypatch, ["\r", "3"], opciones=MENU_MINIMO, lineas=[""])
    juego.ciclo()  # prólogo, «mirar» (limpia y muestra la vista) y «salir»
    j = juego.jugador
    lugar = AVENTURA.lugares[AVENTURA.lugar_inicial].nombre
    estado = f"{j.nombre} · Vida {j.vida}/{j.vida_max} · {j.monedas} monedas · {lugar}"
    assert salida.count(estado) == 2  # al empezar y de nuevo, sobre la vista limpia
    assert salida.count("\x1b[2J\x1b[H") == 2  # la del nombre y la de la vista


def test_hablar_abre_la_conversacion_limpia(monkeypatch):
    juego, salida = juego_flechas(monkeypatch, lineas=["", ""])
    juego._prologo()
    juego._ejecutar("hablar belthar")
    assert salida.count("\x1b[2J\x1b[H") == 2  # la del nombre y la de la conversación
    dialogo = juego.av.dialogos[juego.aqui().npcs["belthar"]]
    assert dialogo[:20] in "\n".join(salida)
    juego._ejecutar("hablar fantasma")  # un error no borra lo que se estaba viendo
    assert salida.count("\x1b[2J\x1b[H") == 2


def test_empezar_la_aventura_no_duplica_la_vista_del_lugar(monkeypatch):
    juego, salida = juego_flechas(monkeypatch, lineas=["", ""])
    juego._prologo()  # presentación y vista del lugar, sobre una sola limpieza
    lugar = AVENTURA.lugares[AVENTURA.lugar_inicial].nombre
    texto = "\n".join(salida)
    assert salida.count("\x1b[2J\x1b[H") == 1
    assert texto.count(lugar) >= 2  # el lugar se presenta una vez (y sus salidas lo citan)


def test_las_otras_acciones_son_un_submenu_de_ida_y_vuelta(monkeypatch):
    opciones = [("mirar", "Mirar alrededor", ""), (OTRAS, "Otras acciones…", "")]
    juego, salida = juego_flechas(monkeypatch, ["2", "\x1b", "2", "7"], opciones=opciones)
    juego.ciclo()
    texto = "\n".join(salida)
    assert juego.fin  # la segunda visita terminó en "salir"
    assert salida.count("\x1b[2KOtras acciones") == 2  # el título del submenú, en cada visita
    assert texto.count("¿Qué haces?") == 2  # el menú del juego, al inicio y al volver


def test_escribir_comando_mantiene_el_tipeado(monkeypatch):
    opciones = MENU_MINIMO[:2] + [(ESCRIBIR, "Escribir un comando…", ""), MENU_MINIMO[2]]
    juego, salida = juego_flechas(monkeypatch, ["3", "4"], opciones=opciones, lineas=["", "estado"])
    juego.ciclo()
    assert any("Vida:" in l for l in salida)  # ejecutó `estado` tipeado
    assert juego.fin


def test_la_ayuda_abre_pantalla_completa_y_esc_la_cierra(monkeypatch):
    juego, salida = juego_flechas(
        monkeypatch,
        ["\r", "\x1b", "2"],
        opciones=[("ayuda", "Ayuda", ""), ("salir", "Salir", "")],
    )
    monkeypatch.setattr(opciones_mod, "_es_interactivo", lambda e, s: True)
    juego.ciclo()
    texto = "\n".join(salida)
    assert "Comandos:" in texto
    assert "\x1b[?1049h" in texto and "\x1b[?1049l" in texto  # entra y sale de la pantalla llena
    assert juego.fin


def test_la_ayuda_tipeada_sale_en_el_diario(fabrica):
    juego, salida = fabrica(["", "ayuda", "salir"])  # la primera línea es el nombre
    juego.ciclo()
    texto = "\n".join(salida)
    assert "Comandos:" in texto
    assert "\x1b" not in texto  # sin terminal real: ni pantalla llena ni esperar teclas


def test_el_combate_se_navega_con_flechas(monkeypatch):
    juego, salida = juego_flechas(monkeypatch, lineas=["", ""])
    juego.jugador.vida = juego.jugador.vida_max = 200
    juego.enemigos[juego.lugar] = ["lobo"]
    juego._combate()
    assert not juego.enemigos[juego.lugar]  # Enter siempre elegía "Atacar"
    texto = "\n".join(salida)
    assert "Atacar" in texto  # el menú de combate ofreció sus opciones
    assert "Escribir un comando…" in texto
    assert "se abalanza" in texto


def test_el_duelo_largo_ocupa_un_bloque_que_no_crece(monkeypatch):
    """Con un enemigo de mucha vida, los turnos no apilan renglones: el
    bloque del duelo (barras y último golpe) se muestra en el sitio."""
    from test_opciones import Terminal

    monkeypatch.setitem(AVENTURA.enemigos["lobo"], "vida", 60)
    monkeypatch.setitem(AVENTURA.enemigos["lobo"], "experiencia", 0)
    term = Terminal()
    capturas: list[str] = []
    teclas = iter(["\r"] * 100)

    def tecla():
        capturas.append(term.texto())
        return next(teclas)

    monkeypatch.setattr(opciones_mod, "_leer_tecla", tecla)
    juego = Juego(
        AVENTURA,
        semilla=7,
        entrada=EntradaTipeada(["", ""]),
        salida=term.escribe,
        color=False,
        flechas=True,
    )
    juego.jugador.vida = juego.jugador.vida_max = 200
    juego.enemigos[juego.lugar] = ["lobo"]
    juego._combate()
    assert not juego.enemigos[juego.lugar]  # el duelo terminó
    assert len(capturas) > 5  # hubo varios turnos
    assert "█" in capturas[0]  # las barras de vida, desde el primer turno
    assert "Golpeas" not in capturas[0]  # el primer bloque aún no tiene turnos
    for captura in capturas[1:-1]:
        assert captura.count("Golpeas a ") == 1  # solo el último golpe, no la historia
    # y la pantalla no crece: misma cantidad de renglones turno a turno
    usadas = lambda t: len([r for r in t.split("\n") if r.strip()])  # noqa: E731
    assert len({usadas(c) for c in capturas[1:-1]}) == 1


def test_en_combate_usar_tiene_su_propio_submenu(monkeypatch):
    juego, salida = juego_flechas(monkeypatch, ["3", "\r"], lineas=["", ""])
    juego.jugador.vida = juego.jugador.vida_max = 200
    juego.jugador.inventario += ["provisiones", "provisiones"]
    juego.enemigos[juego.lugar] = ["lobo"]
    juego._combate()
    assert not juego.enemigos[juego.lugar]  # tras usar, Enter ataqua hasta ganar
    assert juego.jugador.inventario.count("provisiones") == 1  # gastó una sola
    texto = "\n".join(salida)
    assert "Usar — tu mochila (2 provisiones)" in texto  # el verbo, con su cuenta

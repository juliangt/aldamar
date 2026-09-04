"""La sesión viva: sanear, ingerir, reparar, degradar y jugarse entera.

El contrato del modo: todo lo que el cronista escribe pasa por
`cargar_aventura_dict`; el error de validación vuelve al modelo; si el
modelo no está (o insiste), la plantilla del director sostiene la
partida; y una partida viva guardada se carga y se sigue jugando sin
modelo instalado.
"""

from __future__ import annotations

import json

import pytest
from conftest import EntradaTipeada

from aldamar.contenido.cargador import AventuraInvalida, valida_fragmento
from aldamar.motor.juego import Juego
from aldamar.viva import cronista, director, prompts
from aldamar.viva.cronista import ProveedorFalso
from aldamar.viva.director import PREMISAS
from aldamar.viva.memoria import Memoria
from aldamar.viva.sesion import SesionViva, sanea_fragmento, sanea_texto, texto_de_final

PREMISA = PREMISAS[0]

# Respuestas enlatadas de un turno de arranque (prólogo, epílogos y la
# escena inicial: prosa del paso A y nombres del paso B).
PROLOGO = (
    "La historia empieza como empiezan las buenas: tarde y sin avisar.\n\n"
    "Alguien camina hacia ella, y todavía no sabe que la está caminando."
)
EPILOGOS = {
    "muerte": "Cae como cae la gente de bien: en medio de la faena.\n\nEl cantar lo pone a tiempo, que para eso están.",
    "caida": "La grieta lo abraza por dentro y ya no hay manera de distinguir.\n\nEn el lugar del final, ahora hay dos.",
}
PROSA_P1 = (
    "El camino va de tierra y de costumbre, y esta mañana el polvo anda "
    "perezoso entre las piedras.\n\nAl fondo, una señal de madera partida "
    "apunta dos direcciones que no se llevan bien."
)
DATOS_P1 = {
    "nombre": "el Sendero del Agua Parada",
    "hecho": "El héroe dejó la villa y tomó el camino del agua parada.",
    "situacion": "La señal partida ofrece dos caminos y ninguna ayuda.",
    "pregunta": "¿Por dónde se sigue?",
    "opcion_1": "Seguir el agua",
    "opcion_2": "Cortar campo",
}


def sesion_con(respuestas: list, semilla: int = 5) -> SesionViva:
    return SesionViva(
        premisa=PREMISA,
        heroe="espada",
        proveedor=ProveedorFalso(respuestas),
        semilla=semilla,
    )


# ── el saneo: lo que protege al motor de las llaves ──────────────────────


def test_sanea_texto_quita_las_llaves_ajenas_y_deja_las_del_heroe():
    texto = "El oráculo de {kor} dijo: bravo, {trato}, bravo, que {quien} ya sabe."
    assert (
        sanea_texto(texto) == "El oráculo de kor dijo: bravo, {trato}, bravo, que {quien} ya sabe."
    )


def test_sanea_texto_norma_blancos_y_tiene_techo():
    texto = "primera\n\n\n\nsegunda   \ntercera"
    assert sanea_texto(texto) == "primera\n\nsegunda\ntercera"
    assert (
        sanea_texto("x" * 9000, maximo=100).endswith("x")
        and len(sanea_texto("x" * 9000, maximo=100)) <= 100
    )


# ── construir: la aventura lista para jugar ──────────────────────────────


def test_construir_con_cronista_deja_prologo_epilogos_y_escena_inicial():
    sesion = sesion_con([PROLOGO, EPILOGOS, PROSA_P1, DATOS_P1])
    av = sesion.construir()
    assert sesion.aventura_dict["prologo_base"] == PROLOGO
    assert sesion.aventura_dict["epilogos"]["muerte"] == EPILOGOS["muerte"]
    assert sesion.aventura_dict["lugares"]["p1"]["nombre"] == "el Sendero del Agua Parada"
    assert sesion.aventura_dict["lugares"]["p1"]["descripcion"] == PROSA_P1
    assert av.lugares["p1"].descripcion == PROSA_P1
    assert "p1_decision" in sesion.aventura_dict["eventos"]
    assert len(sesion.latencias) == 4  # prólogo, epílogos, prosa y datos
    assert sesion.stubs == {"p2", "p3", "p4", "p5", "p6", "p7"}


def test_construir_sin_cronista_deja_las_plantillas():
    sesion = sesion_con([])
    av = sesion.construir()
    assert av is not None
    assert sesion.aventura_dict["prologo_base"].startswith("Esta historia")
    assert "p1_decision" in sesion.aventura_dict["eventos"]  # la mecánica, en pie
    assert "El camino va de tierra" not in av.lugares["p1"].descripcion


# ── el bucle de reparación y la degradación ──────────────────────────────


def _rellena_que_falla_una_vez(original, llamadas):
    def tibia(lid, plan, prosa, datos, provisional):
        llamadas["n"] += 1
        fragmento = original(lid, plan, prosa, datos, provisional)
        if llamadas["n"] == 1:
            fragmento["eventos"]["roto"] = {
                "tipo": "decision",
                "texto": "t",
                "pregunta": "p",
                "opciones": [{"clave": "a", "titulo": "a", "item": "fantasma_inexistente"}],
            }
        return fragmento

    return tibia


def test_el_error_de_validacion_vuelve_al_modelo_y_la_segunda_pasa(monkeypatch):
    falso = ProveedorFalso([PROLOGO, EPILOGOS, PROSA_P1, DATOS_P1, DATOS_P1])
    sesion = sesion_con([])
    sesion.proveedor = falso
    llamadas = {"n": 0}
    monkeypatch.setattr(director, "rellena", _rellena_que_falla_una_vez(director.rellena, llamadas))
    sesion.construir()
    assert llamadas["n"] == 2  # el roto y el reparado
    assert any("fantasma_inexistente" in pedido for pedido in falso.pedidos)
    assert "roto" not in sesion.aventura_dict["eventos"]
    assert "p1_decision" in sesion.aventura_dict["eventos"]


def test_si_el_modelo_no_repara_se_degrada_a_plantilla(monkeypatch):
    falso = ProveedorFalso([PROLOGO, EPILOGOS, PROSA_P1, DATOS_P1])  # sin reparación
    sesion = sesion_con([])
    sesion.proveedor = falso
    llamadas = {"n": 0}
    monkeypatch.setattr(director, "rellena", _rellena_que_falla_una_vez(director.rellena, llamadas))
    sesion.construir()
    # la cola se agotó reparando: la plantilla sostiene la escena y la partida sigue
    assert "roto" not in sesion.aventura_dict["eventos"]
    assert "p1_decision" in sesion.aventura_dict["eventos"]
    assert "se abre largo y sin sombra" in sesion.aventura_dict["lugares"]["p1"]["descripcion"]


# ── el desenlace: el cronista reescribe el final ─────────────────────────

FINAL_CRONISTA = {
    "texto": (
        "El humo se detiene y toma cara. Al fondo del salón, todo el camino "
        "cabe en el filo que sostienes."
    ),
    "pregunta": "¿Cómo acaba tu historia?",
    "frente": "De frente, sin rodeos",
    "clemencia": "Ofrecer lo guardado",
    "detalle_clemencia": "solo quien dejó algo lo entiende",
    "epilogo_clemencia": (
        "Lo que dejaste al cuidado del lugar pesa más que el filo: el humo se "
        "aparta y el camino se queda en silencio, por fin.\n\nEn las posadas "
        "contarán este final como el raro."
    ),
    "epilogo_puro": (
        "Se pelea, se gana y se vuelve con el sol a la cara.\n\nLo andado es "
        "tuyo, y nadie lo cantará como tú lo anduviste."
    ),
    "epilogo_tentado": (
        "Ganas, pero la grieta viaja contigo.\n\nCada noche, el salón te "
        "espera un poco más cerca."
    ),
    "final_puro": "terminada de frente",
    "final_tentado": "ganada, y encendida por dentro",
}


def _sesion_con_mundo_completo(respuestas: list) -> SesionViva:
    """Una sesión cuyo mundo entero se rellena (prosa de latón por escena).

    Prólogo, epílogos y los dos pasos de cada uno de los siete lugares;
    `respuestas` va detrás, para el desenlace.
    """
    return sesion_con([PROLOGO, EPILOGOS] + [PROSA_P1, DATOS_P1] * 7 + respuestas)


def test_el_cronista_reescribe_el_final_cuando_el_mundo_esta_completo():
    sesion = _sesion_con_mundo_completo([FINAL_CRONISTA])
    sesion.construir()
    # mientras queda mundo por andar, el final sigue siendo el del director
    assert sesion.aventura_dict["eventos"]["final_cima"]["pregunta"] == "¿Cómo termina tu cantar?"
    for lid in list(sesion.stubs):
        sesion._rellena(lid, flags={})
    final = sesion.aventura_dict["eventos"]["final_cima"]
    assert final["texto"] == FINAL_CRONISTA["texto"]
    assert final["pregunta"] == FINAL_CRONISTA["pregunta"]
    sin_epilogo = next(op for op in final["opciones"] if "epilogo" not in op)
    con_epilogo = next(op for op in final["opciones"] if "epilogo" in op)
    assert sin_epilogo["titulo"] == "De frente, sin rodeos"
    assert con_epilogo["titulo"] == "Ofrecer lo guardado"
    # la estructura la pone el director, con modelo o sin él
    assert con_epilogo["requiere_flag"] == "ofrenda"
    assert final["umbral_tentado"] == 60
    assert final["texto_companeros"] == "A tu espalda, con la faena hecha: {nombres}."
    assert "viaja contigo" in final["epilogo_tentado"]
    assert "{" not in final["epilogo_tentado"]


def test_si_el_cronista_no_responde_el_final_de_plantilla_se_queda():
    sesion = sesion_con([])  # seca: todo plantilla, final incluido
    sesion.construir()
    for lid in list(sesion.stubs):
        sesion._rellena(lid, flags={})
    final = sesion.aventura_dict["eventos"]["final_cima"]
    assert final["pregunta"] == "¿Cómo termina tu cantar?"
    assert final["umbral_tentado"] == 60
    assert final["texto_companeros"] == "A tu espalda, con la faena hecha: {nombres}."


def test_el_texto_del_final_no_guarda_ninguna_llave():
    limpio = texto_de_final("Bravo, {trato}: el oráculo de {kor} calla. {quien} lo sabe.", 400)
    assert limpio == "Bravo, : el oráculo de kor calla. lo sabe."


# ── la memoria ────────────────────────────────────────────────────────────


def test_la_memoria_anota_viaja_en_el_guardado_y_vuelve():
    memoria = Memoria()
    memoria.cierra_escena("p1", ["Ruy llegó al camino de tierra", "Tomó la insignia"])
    memoria.anota("Ruy robó lo que no era suyo", "p2")
    assert "camino de tierra" in memoria.para_prompt("p1")
    assert "robó" in memoria.para_prompt("p4")
    clon = Memoria.desde_estado(memoria.estado())
    assert clon.para_prompt("p4") == memoria.para_prompt("p4")


def test_la_condensacion_del_hilo_con_cronista_y_a_lo_bruto_sin_el():
    memoria = Memoria()
    memoria.hilo = "palabra " * 400  # 3200 caracteres: por encima del límite
    memoria.condensa(ProveedorFalso(["resumen corto"]), "sistema")
    assert memoria.hilo == "resumen corto"
    larga = Memoria()
    larga.hilo = "x" * 3000
    larga.condensa(ProveedorFalso([]), "sistema")  # sin cronista: tijera
    assert larga.hilo == "x" * 1500  # se queda con lo último, que es lo vivo
    tranquila = Memoria()
    tranquila.hilo = "nada que condensar"
    tranquila.condensa(ProveedorFalso([]), "sistema")
    assert tranquila.hilo == "nada que condensar"


# ── los ganchos con el motor ──────────────────────────────────────────────


def test_al_entrar_en_un_lugar_rellenado_no_hace_nada():
    sesion = sesion_con([PROLOGO, EPILOGOS, PROSA_P1, DATOS_P1])
    sesion.construir()
    latencias = len(sesion.latencias)
    dict_antes = json.dumps(sesion.aventura_dict)
    sesion.al_entrar(None, "p1")  # p1 ya vive: sin cronista, sin cambios
    assert len(sesion.latencias) == latencias
    assert json.dumps(sesion.aventura_dict) == dict_antes


def test_el_interprete_esta_inerte_en_el_nivel_1():
    sesion = sesion_con([PROLOGO, EPILOGOS, PROSA_P1, DATOS_P1])
    sesion.construir()
    assert sesion.interpretar("hablarle al viento") is None


class _InterpreteFalso:
    """Un viva mínimo que solo responde `interpretar`: para probar el gancho."""

    def __init__(self, comando: str | None) -> None:
        self.comando = comando

    def interpretar(self, linea: str) -> str | None:
        return self.comando

    def al_entrar(self, juego, lid: str) -> None:
        pass


def test_el_gancho_de_entrada_libre_re_despacha_un_comando_real():
    relato: list[str] = []
    juego, _ = _partida_con_dos_escenas(relato)
    juego.viva = _InterpreteFalso("mirar")
    juego._ejecutar("palabrejar con el viento")
    assert any("Puedes ir a" in linea for linea in relato)  # `mirar` corrió


def test_el_gancho_de_entrada_libre_con_nada_que_resolver_avisa_y_sigue():
    relato: list[str] = []
    juego, _ = _partida_con_dos_escenas(relato)
    juego.viva = _InterpreteFalso(None)
    juego._ejecutar("palabrejar con el viento")
    assert any("No entiendo eso" in linea for linea in relato)


# ── el estado de la sesión: guardar y despertar ──────────────────────────


def test_el_estado_de_la_sesion_viaja_y_vuelve():
    sesion = sesion_con([PROLOGO, EPILOGOS, PROSA_P1, DATOS_P1])
    sesion.construir()
    clon = SesionViva.desde_estado(sesion.estado(), proveedor=ProveedorFalso([]))
    assert clon.aventura_dict == sesion.aventura_dict
    assert clon.stubs == sesion.stubs
    assert clon.final == sesion.final
    assert clon.tramo == sesion.tramo
    assert clon.heroe == "espada"
    assert clon.premisa == sesion.premisa
    assert clon.memoria.para_prompt("p1") == sesion.memoria.para_prompt("p1")


def test_un_dict_guardado_sin_final_se_rechaza_al_despertar():
    estado = {
        "aventura_dict": {"eventos": {}, "lugares": {"p1": {"eventos": []}}},
        "rellenados": ["p1"],
    }
    with pytest.raises(AventuraInvalida):
        SesionViva.desde_estado(estado, proveedor=ProveedorFalso([]))


def test_los_conocidos_exponen_las_secciones_vivas():
    sesion = sesion_con([PROLOGO, EPILOGOS, PROSA_P1, DATOS_P1])
    sesion.construir()
    conocidos = sesion._conocidos()
    assert "p1_decision" in conocidos["eventos"]
    assert "insignia" in conocidos["items"]
    assert {"p1", "p2", "p3", "p4", "p5", "p6", "p7", "cima"} <= conocidos["lugares"]


# ── el saneo y las acotaciones ───────────────────────────────────────────


def test_sanea_fragmento_llega_a_todos_los_textos_anidados():
    fragmento = {
        "descripcion": "la casa {del oráculo}",
        "eventos": {"e": {"texto": "el {susurro}"}},
        "dialogos": {"d": ["{lista}", "{trato} queda"]},
        "monedas": 3,
    }
    limpio = sanea_fragmento(fragmento)
    assert limpio["descripcion"] == "la casa del oráculo"
    assert limpio["eventos"]["e"]["texto"] == "el susurro"
    assert limpio["dialogos"]["d"] == ["lista", "{trato} queda"]
    assert limpio["monedas"] == 3  # los números, ajenos al saneo


def test_rellena_acota_los_campos_del_cronista_y_namespacea_el_botin():
    plan = {
        "lid": "pX",
        "sabor": "encuentro",
        "acto": 1,
        "enemigos": {
            "e1": {"nombre": "b", "vida": 10, "ataque": 3, "defensa": 0, "experiencia": 8}
        },
        "botin": {"b1": {"nombre": "la pieza", "tipo": "reliquia", "precio": None, "desc": ""}},
        "monedas": 4,
        "npc": True,
        "curar": False,
        "corrupcion": 0,
        "decision": {"opciones": [{"clave": "tomar", "item": "b1"}, {"clave": "dejar"}]},
        "emboscada": None,
    }
    datos = {
        "nombre": "n" * 60,
        "situacion": "s" * 900,
        "opcion_1": "o" * 60,
        "npc": "N" * 50,
        "dialogo": "d" * 1200,
        "hecho": "h" * 400,
    }
    fragmento = director.rellena("pX", plan, "prosa", datos, "provisional")
    assert len(fragmento["nombre"]) == 40
    assert len(fragmento["eventos"]["pX_decision"]["texto"]) <= 700
    assert len(fragmento["eventos"]["pX_decision"]["opciones"][0]["titulo"]) == 40
    assert len(fragmento["dialogos"]["pX_dlg"]) <= 900
    assert len(fragmento["hechos"][0]) <= 200
    # el botín de la decisión viaja namespacedo y referenciado igual
    assert fragmento["items"]["pX_b1"]["nombre"] == "la pieza"
    assert fragmento["eventos"]["pX_decision"]["opciones"][0]["item"] == "pX_b1"


# ── los prompts: lo que se le pide al modelo ─────────────────────────────


def test_el_schema_del_paso_b_pide_solo_lo_que_el_plan_necesita():
    base = {
        "enemigos": {},
        "botin": {},
        "monedas": 0,
        "npc": False,
        "curar": False,
        "corrupcion": 0,
        "decision": None,
        "emboscada": None,
    }
    assert set(prompts.schema_datos(base)["properties"]) == {"nombre", "hecho"}
    con_todo = dict(base, npc=True, decision={"opciones": [{"clave": "a"}, {"clave": "b"}]})
    schema = prompts.schema_datos(con_todo)
    assert set(schema["properties"]) == {
        "nombre",
        "hecho",
        "situacion",
        "pregunta",
        "opcion_1",
        "opcion_1_det",
        "opcion_2",
        "opcion_2_det",
        "npc",
        "dialogo",
    }
    assert set(schema["required"]) == set(schema["properties"])
    con_nombres = dict(
        base,
        enemigos={"e1": {"nombre": "x"}},
        botin={"b1": {"nombre": "y"}},
        decision={"opciones": [{"clave": "a"}]},
    )
    schema_nombres = prompts.schema_datos(con_nombres)
    assert {"enemigo_1", "botin_1", "botin_1_desc", "opcion_1_det"} <= set(
        schema_nombres["properties"]
    )


def test_el_prompt_de_reparacion_lleva_el_error_al_modelo():
    texto = prompts.repara({}, "{}", "faltó el campo 'x'")
    assert "faltó el campo 'x'" in texto
    assert "mismo formato" in texto


# ── el flujo de punta a punta, con el motor delante ──────────────────────


def _partida_con_dos_escenas(tmp_salida: list[str]) -> tuple[Juego, SesionViva]:
    sesion = sesion_con([PROLOGO, EPILOGOS, PROSA_P1, DATOS_P1, PROSA_P1, DATOS_P1], semilla=5)
    av = sesion.construir()
    juego = Juego(
        aventura=av,
        personaje="espada",
        semilla=5,
        entrada=EntradaTipeada(["Ruy", "ir norte", "1", *["atacar"] * 8, "salir"]),
        salida=tmp_salida.append,
        color=False,
        flechas=False,
        viva=sesion,
    )
    return juego, sesion


def test_partida_viva_se_juega_de_punta_a_punta():
    relato: list[str] = []
    juego, sesion = _partida_con_dos_escenas(relato)
    juego.ciclo()
    # la escena p2 se rellenó al pisarse y el motor la narró
    assert "p2" not in sesion.stubs
    assert "p2_decision" in sesion.aventura_dict["eventos"]
    assert juego.av is sesion.av
    # la decisión elegida («1» = robar) quedó encendida en las banderas
    assert juego.flags.get("robo") is True  # bandera canónica: cruza escenas
    assert juego.jugador.corrupcion == 3  # y su precio, cobrado
    texto = "\n".join(relato)
    assert "hondonada gris" not in texto  # lo que se narra es lo del cronista


def test_partida_viva_guardada_se_carga_y_se_sigue_jugando_sin_modelo(tmp_path, monkeypatch):
    relato: list[str] = []
    juego, sesion = _partida_con_dos_escenas(relato)
    juego.ciclo()
    ruta = str(tmp_path / "partida_viva.json")
    juego._guardar(ruta)

    with open(ruta, encoding="utf-8") as f:
        crudo = json.load(f)
    assert crudo["version"] == 2
    assert crudo["viva"]["rellenados"] == ["p1", "p2"]
    assert set(crudo["viva"]["aventura_dict"]["lugares"]) == {
        "p1",
        "p2",
        "p3",
        "p4",
        "p5",
        "p6",
        "p7",
        "cima",
    }

    # sin modelo instalado: proveedor por defecto sin respuestas y sin servicio
    monkeypatch.setattr(cronista, "proveedor_por_defecto", lambda: ProveedorFalso([]))
    juego2 = Juego.desde_archivo(
        ruta,
        # de p2: «ir sur» a p1 (ahí su decisión se resuelve), «ir este» a
        # p3 (borrador: la plantilla lo rellena), decisión, y fuera
        entrada=EntradaTipeada(["ir sur", "1", "ir este", "1", "salir"]),
        salida=relato.append,
        color=False,
        flechas=False,
    )
    assert juego2.viva is not None
    assert juego2.av.id == sesion.av.id
    assert juego2.viva.stubs == {"p3", "p4", "p5", "p6", "p7"}
    assert juego2.jugador.nombre == "Ruy"
    juego2.ciclo()
    # p3 se pisó sin cronista: la plantilla lo rellenó, la decisión quedó
    # encendida (la tabla exacta la baraja la semilla) y la partida siguió
    assert "p3" not in juego2.viva.stubs
    assert "p3_decision" in juego2.av.eventos
    assert any(clave.startswith("p3_") for clave in juego2.flags)


# ── valida_fragmento: el sandbox temprano ────────────────────────────────


def _lugar_minimo(**cambios) -> dict:
    base = {"nombre": "Algo", "descripcion": "d"}
    base.update(cambios)
    return base


def test_valida_fragmento_acepta_un_fragmento_sano():
    fragmento = {
        "lugares": {"p9": _lugar_minimo(salidas={"sur": "p9"})},
        "enemigos": {"p9_e1": {"nombre": "n", "vida": 5, "ataque": 1}},
    }
    valida_fragmento(
        fragmento, conocidos={"lugares": {"p9"}, "enemigos": {"p9_e1"}}, origen="prueba"
    )


def test_valida_fragmento_rebota_con_lo_que_no_existe():
    fragmento = {"lugares": {"p9": _lugar_minimo(objetos=["fantasma"])}}
    with pytest.raises(AventuraInvalida) as captura:
        valida_fragmento(fragmento, origen="prueba")
    assert "fantasma" in str(captura.value)
    fragmento = {"lugares": {"p9": _lugar_minimo(salidas={"sur": "nunca_jamas"})}}
    with pytest.raises(AventuraInvalida) as captura:
        valida_fragmento(fragmento, origen="prueba")
    assert "nunca_jamas" in str(captura.value)


def test_valida_fragmento_rechaza_secciones_desconocidas():
    with pytest.raises(AventuraInvalida) as captura:
        valida_fragmento({"personajes": {}}, origen="prueba")
    assert "personajes" in str(captura.value)


def test_valida_fragmento_con_lo_conocido_de_la_sesion():
    sesion = sesion_con([PROLOGO, EPILOGOS, PROSA_P1, DATOS_P1])
    sesion.construir()
    fragmento = {
        "dialogos": {"viejo_dlg": "— ¿Y a ti quién te manda? —"},
        "lugares": {"p1": _lugar_minimo(npcs={"el viejo": "viejo_dlg"}, salidas={"norte": "p2"})},
    }
    valida_fragmento(
        fragmento,
        conocidos={"dialogos": {"otro_dlg"}, "lugares": {"p1", "p2"}},
        origen="prueba",
    )


# ── el progreso y el registro de depuración ──────────────────────────────


def test_cada_llamada_al_cronista_avisa_que_hace_y_cuanto_tarda():
    pasos: list[str] = []
    sesion = SesionViva(
        premisa=PREMISA,
        heroe="espada",
        proveedor=ProveedorFalso([PROLOGO, EPILOGOS, PROSA_P1, DATOS_P1]),
        semilla=5,
        avisa=pasos.append,
    )
    sesion.construir()
    texto = "\n".join(pasos)
    assert "Escribiendo el prólogo…" in texto
    assert "Recogiendo los epílogos…" in texto
    assert "Escribiendo la llegada" in texto
    assert "Recogiendo los nombres…" in texto
    # y cada paso, su latencia (0.0 s: el proveedor falso no tarda nada)
    assert texto.count(": 0.0 s") == 4


def test_el_proveedor_agotado_avisa_que_la_escena_sale_de_plantilla():
    pasos: list[str] = []
    sesion = SesionViva(
        premisa=PREMISA,
        heroe="espada",
        proveedor=ProveedorFalso([]),
        semilla=5,
        avisa=pasos.append,
    )
    sesion.construir()
    assert any("no responde" in paso and "plantilla" in paso for paso in pasos)


def test_con_debug_lo_hablado_con_el_modelo_queda_en_el_registro(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    sesion = SesionViva(
        premisa=PREMISA,
        heroe="espada",
        proveedor=ProveedorFalso([PROLOGO, EPILOGOS, PROSA_P1, DATOS_P1]),
        semilla=5,
        debug=True,
    )
    sesion.construir()
    registro = (tmp_path / "cronista_viva.log").read_text(encoding="utf-8")
    assert "PIDEN:" in registro and "DAN:" in registro
    assert "escribiendo el prólogo" in registro
    assert PROLOGO in registro  # la respuesta del modelo, en el acta


def test_sin_debug_no_se_escribe_ningun_registro(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    sesion_con([PROLOGO, EPILOGOS, PROSA_P1, DATOS_P1]).construir()
    assert not (tmp_path / "cronista_viva.log").exists()


def test_con_debug_tambien_queda_en_el_acta_la_llamada_que_falla(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    sesion = SesionViva(
        premisa=PREMISA,
        heroe="espada",
        proveedor=ProveedorFalso([]),  # seca: todo falla
        semilla=5,
        debug=True,
    )
    sesion.construir()
    registro = (tmp_path / "cronista_viva.log").read_text(encoding="utf-8")
    assert "FALLÓ" in registro and "ERROR:" in registro
    assert "se quedó sin respuestas" in registro

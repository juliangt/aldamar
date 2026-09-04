"""El director: tablas + RNG que deciden TODA la mecánica del modo vivo.

El director produce plantillas de evento del vocabulario con huecos de
texto — el cronista solo redacta y nombra.
Lo que aquí se decide (mapa, enemigos, botín, decisiones, curva de
actos) sale de `datos.json` con una `random.Random(semilla)`: el mismo
esqueleto con la misma semilla, con modelo o sin él. `plantilla()` es
el piso de siempre: el relleno completo sin cronista, válido por
construcción.

El mapa de la sesión es fijo y pequeño (8 lugares en tres actos, con
la cima y su evento `final` ya puestos): toda salida apunta siempre a
un lugar existente, así que las validaciones del cargador quedan
intactas y el mundo acumulado es exportable de punta a punta. Hay más
de un tramo (`tramos()`): el esqueleto elige uno con la semilla y la
sesión se lo recuerda a `plan_encuentro`, para que el sabor y el acto
de cada lugar sean siempre los mismos durante la partida. El contrato
del dato: `p1` es la entrada (sin colmillos), `p7` el último camino y
`cima` el clímax.

Las consecuencias que cruzan escenas viajan en banderas canónicas
(`bandera` en la opción de decisión: «robo», «ofrenda»), sin el id del
lugar: la emboscada del cobrador y la clemencia del final las leen
igual en cualquier tramo.
"""

from __future__ import annotations

import functools
import json
import random
from dataclasses import asdict, dataclass
from importlib import resources


@functools.lru_cache(maxsize=1)
def datos() -> dict:
    """El dato del modo (`viva/datos.json`): premisas, tramos, tablas y prosa."""
    texto = resources.files("aldamar").joinpath("viva", "datos.json").read_text(encoding="utf-8")
    return json.loads(texto)


# ── premisas: la semilla de cada historia ────────────────────────────────


@dataclass(frozen=True)
class Premisa:
    """La semilla de una historia: la frase, su título y su enemigo."""

    clave: str
    texto: str  # la semilla tal cual: «una traición en Valoria»
    titulo: str  # forma de título, para el menú y la aventura
    antagonista: str  # quién espera al final, sin artículo capitalizado
    corte: str  # el nombre del lugar donde espera
    tono: str  # una pista de atmósfera para el cronista

    def diccionario(self) -> dict:
        return asdict(self)


def premisa_de_diccionario(datos: dict) -> Premisa:
    """Reconstruye una premisa guardada (o una escrita por el jugador)."""
    return Premisa(
        clave=str(datos.get("clave", "propia")),
        texto=str(datos.get("texto", "una historia sin semilla")),
        titulo=str(datos.get("titulo", "Historia sin nombre")),
        antagonista=str(datos.get("antagonista", "lo que espera al final")),
        corte=str(datos.get("corte", "el lugar del final")),
        tono=str(datos.get("tono", "")),
    )


PREMISAS = tuple(Premisa(**p) for p in datos()["premisas"])


# ── héroes arquetipo: fichas completas, con rasgos reales de RASGOS ──────

ARQUETIPOS = tuple(datos()["arquetipos"])


def arquetipo(clave: str) -> dict:
    """La ficha de un héroe arquetipo por clave (la primera, si no la hay)."""
    for ficha in ARQUETIPOS:
        if ficha["clave"] == clave:
            return ficha
    return ARQUETIPOS[0]


# ── el esqueleto: la aventura completa, válida sin cronista ──────────────


@dataclass(frozen=True)
class Esqueleto:
    """La aventura recién nacida: el dict, sus lugares sin rellenar y el final."""

    aventura: dict
    stubs: frozenset[str]  # lugares que el cronista rellenará al pisarse
    final: str  # el lugar del evento `final` (ya completo desde el esqueleto)
    tramo: str  # la clave del tramo de mapa elegido (la sesión lo recuerda)


def tramos() -> dict:
    """Los tramos de mapa del dato: clave → lugares (sabor, acto) y salidas."""
    return datos()["tramos"]


# La curva de actos: (vida, ataque, experiencia) base de la criatura
# común. La dificultad elegida escala encima (`crear_enemigo` ya lo hace).
_CURVA = {int(acto): tuple(stats) for acto, stats in datos()["curva"].items()}
_CRIATURAS = {int(acto): tuple(nombres) for acto, nombres in datos()["criaturas"].items()}
_RELICUIAS = tuple(datos()["reliquias"])
_ITEMS_BASE = datos()["items"]


def esqueleto(premisa: Premisa, semilla: int | None = None, tramo: str | None = None) -> Esqueleto:
    """La aventura completa en formato JSON, válida por construcción.

    Con la misma semilla sale el mismo esqueleto, con cronista o sin él:
    es la garantía de que el piso procedural (todo plantilla) funciona
    solo, y de que una sesión es reproducible. Sin `tramo`, se elige uno
    del dato con la semilla.
    """
    rng = random.Random(semilla)
    clave_tramo = tramo or rng.choice(sorted(tramos()))
    lugares_tramo = tramos()[clave_tramo]["lugares"]
    salidas_tramo = tramos()[clave_tramo]["salidas"]
    lugares: dict[str, dict] = {}
    for lid, (sabor, _acto) in lugares_tramo.items():
        lugares[lid] = {
            "nombre": _nombre_lugar(sabor, premisa, rng),
            "descripcion": datos()["plantillas"]["descripcion_vacia"],
            "salidas": dict(salidas_tramo[lid]),
            "objetos": [],
            "monedas": 0,
            "enemigos": [],
            "npcs": {},
            "tienda": sabor == "pueblo",
            "descanso": sabor in ("pueblo", "cripta"),
            "eventos": [],
            "requiere": None,
            "requiere_texto": "",
        }
    lugares["p1"]["objetos"] = ["insignia"]
    lugares["cima"]["descripcion"] = _con_premisa(
        datos()["plantillas"]["cima"], premisa
    )
    lugares["cima"]["enemigos"] = ["guardian_cima"]
    lugares["cima"]["eventos"] = ["final_cima"]
    pueblos = [lid for lid, (sabor, _acto) in lugares_tramo.items() if sabor == "pueblo"]
    aventura = {
        "id": f"viva_{rng.randrange(10**6):06d}",
        "titulo": premisa.titulo,
        "descripcion": _con_premisa(datos()["plantillas"]["descripcion_aventura"], premisa),
        "texto_nombre": "¿Cómo te llamas? ({nombre}): ",
        "lugar_inicial": "p1",
        "jugador_inicial": ARQUETIPOS[0]["clave"],
        "lugares": lugares,
        "prologo_base": _con_premisa(datos()["plantillas"]["prologo"], premisa),
        "epilogos": {
            clave: _con_premisa(plantilla, premisa)
            for clave, plantilla in datos()["plantillas"]["epilogos"].items()
        },
        "personajes": {
            ficha["clave"]: {k: v for k, v in ficha.items() if k != "clave"} for ficha in ARQUETIPOS
        },
        "items": dict(_ITEMS_BASE),
        "enemigos": {"guardian_cima": _ficha_jefe(premisa)},
        "reclutas": {},
        "dialogos": {},
        "tiendas": {lid: list(datos()["tienda"]) for lid in pueblos},
        "eventos": {"final_cima": _final_plantilla(premisa)},
    }
    return Esqueleto(
        aventura=aventura,
        stubs=frozenset(lid for lid in lugares_tramo if lid != "cima"),
        final="cima",
        tramo=clave_tramo,
    )


def _con_premisa(plantilla: str, premisa: Premisa) -> str:
    """Una plantilla del dato, con los campos de la premisa en su sitio."""
    campos = premisa.diccionario()
    campos["quien"] = premisa.antagonista.capitalize()
    return plantilla.format(**campos)


def _nombre_lugar(sabor: str, premisa: Premisa, rng: random.Random) -> str:
    """El nombre provisional: por sabor, o el de la premisa en la cima."""
    if sabor == "climax":
        return premisa.corte
    grupos = datos()["nombres_lugares"]
    return rng.choice(grupos.get(sabor, grupos["desconocido"]))


def _ficha_enemigo(acto: int, rng: random.Random, nombre: str | None = None) -> dict:
    """Una criatura común de la curva del acto; el nombre, de tabla."""
    vida, ataque, experiencia = _CURVA[acto]
    return {
        "nombre": nombre or rng.choice(_CRIATURAS[acto]),
        "vida": vida + rng.randint(-2, 2),
        "ataque": ataque,
        "defensa": 0,
        "experiencia": experiencia,
    }


def _ficha_jefe(premisa: Premisa) -> dict:
    """El guardián del final: la cara del antagonista de la premisa."""
    quien = premisa.antagonista.capitalize()
    return {
        "nombre": quien,
        "vida": 46,
        "ataque": 7,
        "defensa": 1,
        "sin_huida": True,
        "experiencia": 45,
        "fases": [
            {
                "vida_menor_que": 50,
                "texto": _con_premisa(datos()["plantillas"]["jefe_fase"], premisa),
                "ataque": 8,
            }
        ],
    }


def _final_plantilla(premisa: Premisa) -> dict:
    """El evento `final`, completo desde el esqueleto (estructura del cargador).

    La opción sin `epilogo` es el desenlace por defecto; la de
    `clemencia` solo aparece si alguna decisión con bandera `ofrenda`
    dejó su señal: la primera consecuencia que cruza actos.
    """
    evento: dict = {}
    for clave, valor in datos()["plantillas"]["final"].items():
        if isinstance(valor, str):
            evento[clave] = _con_premisa(valor, premisa)
        elif clave == "opciones":
            evento[clave] = [
                {
                    k: (_con_premisa(v, premisa) if isinstance(v, str) else v)
                    for k, v in opcion.items()
                }
                for opcion in valor
            ]
        else:
            evento[clave] = valor
    evento["texto_companeros"] = datos()["plantillas"]["texto_companeros"]
    return evento


# ── los planes de encuentro: qué hay mecánicamente en cada lugar ─────────


def _decision_de(sabor: str, rng: random.Random) -> dict:
    """Una de las tablas de decisión del sabor, barajada por la semilla."""
    conjunto = rng.choice(datos()["decisiones"][sabor])
    return {"opciones": [dict(opcion) for opcion in conjunto]}


def _ultimo_encuentro(lugares: dict) -> str:
    """El id del encuentro de acto más alto: donde cobra el cobrador."""
    encuentros = [lid for lid, (sabor, _acto) in lugares.items() if sabor == "encuentro"]
    return max(encuentros, key=lambda lid: lugares[lid][1])


def plan_encuentro(
    lid: str, flags: dict, rng: random.Random, tramo: str = "recto"
) -> dict:
    """El plan mecánico de un lugar: enemigos, botín, decisión y sorpresas.

    Lee las banderas del juego (lo que el héroe ya decidió) para conectar
    escenas: si robó en un encuentro, en el último de todos lo espera la
    emboscada del cobrador. Los stats salen SIEMPRE de la curva; el
    cronista no los toca.
    """
    lugares_tramo = tramos()[tramo]["lugares"]
    sabor, acto = lugares_tramo[lid]
    plan: dict = {
        "lid": lid,
        "sabor": sabor,
        "acto": acto,
        "enemigos": {},
        "botin": {},
        "monedas": 0,
        "npc": False,
        "curar": False,
        "corrupcion": 0,
        "decision": None,
        "emboscada": None,
    }
    if sabor == "camino":
        plan["decision"] = _decision_de(sabor, rng)
        if lid == "p7":  # la subida final: peso y vigilancia
            plan["enemigos"]["e1"] = _ficha_enemigo(acto, rng)
            plan["corrupcion"] = 3
    elif sabor == "encuentro":
        plan["enemigos"]["e1"] = _ficha_enemigo(acto, rng)
        plan["monedas"] = rng.randint(4, 10)
        plan["decision"] = _decision_de(sabor, rng)
        if flags.get("robo") and lid == _ultimo_encuentro(lugares_tramo):
            # lo robado antes cobra aquí su interés
            plan["enemigos"]["e2"] = _ficha_enemigo(
                acto, rng, nombre="el cobrador de viejas deudas"
            )
            plan["emboscada"] = {
                "enemigo_local": "e2",
                "condicion": {"flag": "robo"},
            }
    elif sabor == "pueblo":
        plan["npc"] = True
        plan["decision"] = _decision_de(sabor, rng)
    elif sabor == "ruina":
        plan["enemigos"]["e1"] = _ficha_enemigo(acto, rng)
        plan["enemigos"]["e2"] = _ficha_enemigo(acto, rng)
        plan["botin"]["b1"] = {
            "nombre": rng.choice(_RELICUIAS),
            "tipo": "reliquia",
            "precio": None,
            "desc": datos()["reliquia_desc"],
        }
        plan["monedas"] = rng.randint(0, 6)
    elif sabor == "cripta":
        plan["npc"] = True
        plan["curar"] = True
        plan["decision"] = _decision_de(sabor, rng)
    return plan


def resumen_plan(plan: dict) -> str:
    """El plan, en español: lo que el cronista encuentra en la escena."""
    lineas: list[str] = []
    enemigos = [f["nombre"] for f in plan.get("enemigos", {}).values()]
    if enemigos:
        lineas.append(f"- criaturas hostiles que aparecerán: {', '.join(enemigos)}")
    if plan.get("emboscada"):
        lineas.append("- una emboscada que puede desatarse según lo que el héroe haya hecho antes")
    if plan.get("npc"):
        lineas.append("- alguien vive aquí y hablará con el héroe")
    if plan.get("curar"):
        lineas.append("- un lugar de alivio: el agua o el altar curan las heridas")
    if plan.get("corrupcion"):
        lineas.append("- la corrupción del lugar roza al héroe (frío, grietas, susurros)")
    decision = plan.get("decision")
    if decision:
        pistas = ", ".join(op.get("pista", op["clave"]) for op in decision["opciones"])
        lineas.append(f"- una decisión con estas salidas: {pistas}")
    botin = [f["nombre"] for f in plan.get("botin", {}).values()]
    if botin:
        lineas.append(f"- objetos a la vista: {', '.join(botin)}")
    if plan.get("monedas"):
        lineas.append(f"- {plan['monedas']} monedas olvidadas")
    return "\n".join(lineas) or "- un lugar de paso, sin nada especial"


# ── el relleno: del plan + prosa + nombres, al fragmento del cargador ────


def rellena(lid: str, plan: dict, prosa: str, datos_cronista: dict, nombre_provisional: str) -> dict:
    """Arma el fragmento del lugar con el plan (mecánica), la prosa (llegada)
    y los nombres del cronista, con reserva de tabla para todo lo que falte.

    El cronista nombra también criaturas, botín y el detalle de cada
    salida de la decisión; claves, stats y efectos quedan del director.
    """
    plantillas = datos()["plantillas"]
    fragmento: dict = {
        "lugar": lid,
        "nombre": _campo(datos_cronista, "nombre", nombre_provisional, 40),
        "descripcion": (prosa or "").strip() or plantillas["descripcion"],
        "monedas": plan.get("monedas", 0),
        "items": {},
        "enemigos": {},
        "dialogos": {},
        "eventos": {},
        "npcs": {},
        "enemigos_del_lugar": [],
        "objetos": [],
        "eventos_del_lugar": [],
        "hechos": [],
    }
    for i, (clave_local, ficha) in enumerate(plan.get("enemigos", {}).items(), 1):
        ficha = dict(ficha)
        ficha["nombre"] = _campo(datos_cronista, f"enemigo_{i}", str(ficha.get("nombre", "")), 60)
        clave = f"{lid}_{clave_local}"
        fragmento["enemigos"][clave] = ficha
        if (plan.get("emboscada") or {}).get("enemigo_local") != clave_local:
            fragmento["enemigos_del_lugar"].append(clave)
    for i, (clave_item, ficha) in enumerate(plan.get("botin", {}).items(), 1):
        item = dict(ficha)
        item["nombre"] = _campo(datos_cronista, f"botin_{i}", str(item.get("nombre", "")), 40)
        item["desc"] = _campo(datos_cronista, f"botin_{i}_desc", str(item.get("desc", "")), 200)
        clave = f"{lid}_{clave_item}"
        fragmento["items"][clave] = item
        fragmento["objetos"].append(clave)
    emboscada = plan.get("emboscada") or {}
    if emboscada:
        clave = f"{lid}_{emboscada['enemigo_local']}"
        nombre = fragmento["enemigos"][clave]["nombre"]
        evento: dict = {
            "tipo": "emboscar",
            "texto": plantillas["emboscada"].format(nombre=nombre),
            "enemigos": [clave],
        }
        if emboscada.get("condicion"):
            evento["condicion"] = dict(emboscada["condicion"])
        fragmento["eventos"][f"{lid}_emboscada"] = evento
        fragmento["eventos_del_lugar"].append(f"{lid}_emboscada")
    decision = plan.get("decision")
    if decision:
        opciones = []
        for i, salida in enumerate(decision["opciones"], 1):
            entrada: dict = {
                "clave": salida["clave"],
                "titulo": _campo(datos_cronista, f"opcion_{i}", f"La salida {i}", 40),
                "flag": str(salida.get("bandera") or f"{lid}_{salida['clave']}"),
            }
            detalle = _campo(datos_cronista, f"opcion_{i}_det", str(salida.get("pista", "")), 80)
            if detalle:
                entrada["detalle"] = detalle
            if salida.get("corrupcion"):
                entrada["corrupcion"] = salida["corrupcion"]
            if salida.get("item"):
                entrada["item"] = f"{lid}_{salida['item']}"
            opciones.append(entrada)
        fragmento["eventos"][f"{lid}_decision"] = {
            "tipo": "decision",
            "texto": _campo(datos_cronista, "situacion", plantillas["situacion"], 700),
            "pregunta": _campo(datos_cronista, "pregunta", "¿Qué haces?", 80),
            "opciones": opciones,
        }
        fragmento["eventos_del_lugar"].append(f"{lid}_decision")
    if plan.get("curar"):
        fragmento["eventos"][f"{lid}_alivio"] = {
            "tipo": "curar_grupo",
            "texto": _campo(datos_cronista, "situacion", plantillas["alivio"], 700),
        }
        fragmento["eventos_del_lugar"].append(f"{lid}_alivio")
    if plan.get("corrupcion"):
        fragmento["eventos"][f"{lid}_pesa"] = {
            "tipo": "corrupcion",
            "puntos": plan["corrupcion"],
            "aviso": plantillas["corrupcion_aviso"],
        }
        fragmento["eventos_del_lugar"].append(f"{lid}_pesa")
    if plan.get("npc"):
        nombre_npc = _campo(datos_cronista, "npc", "el guardián del lugar", 40)
        fragmento["dialogos"][f"{lid}_dlg"] = _campo(
            datos_cronista, "dialogo", plantillas["dialogo"], 900
        )
        fragmento["npcs"][nombre_npc] = f"{lid}_dlg"
    hecho_defecto = plantillas["hecho"].format(nombre=fragmento["nombre"])
    fragmento["hechos"].append(_campo(datos_cronista, "hecho", hecho_defecto, 200))
    return fragmento


def plantilla(lid: str, plan: dict, nombre_provisional: str) -> dict:
    """El relleno completo con prosa de tablas: el piso sin cronista."""
    prosa = datos()["plantillas"]["prosa_lugares"].get(
        plan["sabor"], datos()["plantillas"]["descripcion"]
    ).format(nombre=nombre_provisional.capitalize())
    return rellena(lid, plan, prosa, {}, nombre_provisional)


def _campo(datos_cronista: dict, clave: str, defecto: str, maximo: int) -> str:
    """Un campo del cronista, limpio y acotado; sin él, el de tabla."""
    valor = str(datos_cronista.get(clave) or "").strip()
    if len(valor) > maximo:
        valor = valor[:maximo].rstrip()
    return valor or defecto

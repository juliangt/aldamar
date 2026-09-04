"""Lo que el modo vivo le pide al cronista, y cómo se lo pide.

Constructores puros de prompts, sin red. El reparto del trabajo:

- `sistema`: el canon (`canon.md`) + la premisa + la voz del héroe + la
  memoria de la sesión. Cambia por escena solo en la memoria.
- `escena`: el paso A, prosa libre — la llegada al lugar.
- `schema_datos` y `datos_escena`: el paso B, structured outputs — los
  nombres cortos (lugar, criaturas, botín, NPC, opciones de la
  decisión, un hecho).
- `prologo`, `epilogos`, `condensa`, `repara`: las llamadas sueltas del
  encuadre y del mantenimiento.
- `premisa` y `final`: la entrada y la salida de la historia — el
  título y el antagonista de la premisa escrita por el jugador, y el
  desenlace cuando el mundo ya está completo.

La mecánica la decide SIEMPRE el director; al modelo se le pide que
redacte y nombre. Nada de lo que aquí se pide puede cambiar stats,
botín mecánico, banderas o topología.
"""

from __future__ import annotations

import functools
import json
from importlib import resources


@functools.lru_cache(maxsize=1)
def canon() -> str:
    """El canon condensado del mundo (dato del paquete, editado a mano)."""
    return resources.files("aldamar").joinpath("viva", "canon.md").read_text(encoding="utf-8")


# ── el prompt de sistema ─────────────────────────────────────────────────


def sistema(premisa: str, voz: str, memoria: str) -> str:
    """Canon + premisa + voz del héroe + memoria: el encuadre de la sesión."""
    partes = [canon(), f"\n\n## La premisa de esta historia\n\n{premisa.strip()}"]
    if voz:
        partes.append(f"\n\n## El héroe\n\n{voz.strip()}")
    if memoria:
        partes.append(f"\n\n## Lo que ha pasado ya\n\n{memoria.strip()}")
    return "".join(partes)


# ── el paso A: prosa de llegada ──────────────────────────────────────────


def escena(nombre_lugar: str, resumen_plan: str, memoria: str = "") -> str:
    """El prompt de la llegada al lugar (2–3 párrafos, segunda persona)."""
    memoria_txt = f"\n\nLo que el héroe ya sabe:\n{memoria.strip()}\n" if memoria else ""
    return (
        f"Escribe SOLO la prosa de llegada del héroe a este lugar: 2 o 3 párrafos "
        f"cortos, en segunda persona, en español.\n\n"
        f"Lugar: {nombre_lugar}.\n"
        f"Lo que hay aquí, ya decidido (no lo cambies, encuéntralo en la escena):\n"
        f"{resumen_plan.strip()}"
        f"{memoria_txt}\n\n"
        "No resuelvas nada: deja el lugar abierto ante quien llega."
    )


# ── el paso B: nombres y campos cortos, con structured outputs ───────────


def schema_datos(plan: dict) -> dict:
    """El JSON schema del paso B: solo los campos que este plan necesita."""
    propiedades: dict[str, dict] = {
        "nombre": {"type": "string"},
        "hecho": {"type": "string"},
    }
    for i in range(len(plan.get("enemigos", {}))):
        propiedades[f"enemigo_{i + 1}"] = {"type": "string"}
    for i in range(len(plan.get("botin", {}))):
        propiedades[f"botin_{i + 1}"] = {"type": "string"}
        propiedades[f"botin_{i + 1}_desc"] = {"type": "string"}
    if plan.get("decision"):
        propiedades["situacion"] = {"type": "string"}
        propiedades["pregunta"] = {"type": "string"}
        for i in range(len(plan["decision"]["opciones"])):
            propiedades[f"opcion_{i + 1}"] = {"type": "string"}
            propiedades[f"opcion_{i + 1}_det"] = {"type": "string"}
    if plan.get("npc"):
        propiedades["npc"] = {"type": "string"}
        propiedades["dialogo"] = {"type": "string"}
    return {"type": "object", "properties": propiedades, "required": list(propiedades)}


def datos_escena(plan: dict, nombre_lugar: str) -> str:
    """El prompt del paso B: cada campo, con su tamaño y su tono."""
    lineas = [
        "Responde SOLO con un objeto JSON con estos campos exactos:",
        "- nombre: nombre propio y evocador para el lugar, máximo 4 palabras",
        "- hecho: una frase corta en pasado con lo esencial que acaba de pasar",
    ]
    for i in range(len(plan.get("enemigos", {}))):
        lineas.append(
            f"- enemigo_{i + 1}: nombre corto de la criatura hostil, con artículo "
            "indeterminado y en minúscula («una sombra con dientes»), máximo 6 palabras"
        )
    for i in range(len(plan.get("botin", {}))):
        lineas += [
            f"- botin_{i + 1}: nombre corto y evocador del objeto a la vista",
            (
                f"- botin_{i + 1}_desc: una frase sobre qué es y por qué importa, "
                "aunque no sirva para pelear"
            ),
        ]
    if plan.get("decision"):
        lineas += [
            "- situacion: 2 o 3 frases que planteen la decisión en escena, sin resolverla",
            "- pregunta: la pregunta corta que abre la elección",
        ]
        for i, opcion in enumerate(plan["decision"]["opciones"]):
            pista = opcion.get("pista", "")
            linea = f"- opcion_{i + 1}: título corto (máx 5 palabras) de una opción"
            if pista:
                linea += f"; debe tratarse de {pista}"
            lineas.append(linea)
            if pista:
                lineas.append(
                    f"- opcion_{i + 1}_det: una línea que insinúe qué implica esa "
                    f"opción; debe ir con «{pista}»"
                )
            else:
                lineas.append(f"- opcion_{i + 1}_det: una línea sobre qué implica esa opción")
    if plan.get("npc"):
        lineas += [
            "- npc: nombre corto de quien vive este lugar (máx 3 palabras)",
            (
                "- dialogo: lo que esa persona le dice al héroe al verlo llegar "
                "(3 a 6 frases, entre comillas latinas)"
            ),
        ]
    lineas += [
        "",
        (
            f"El lugar se llama provisionalmente «{nombre_lugar}»; su `nombre` "
            "puede afinarlo, no reemplazarlo por otra cosa."
        ),
        "Nada de JSON aparte, ni comentarios, ni texto fuera del objeto.",
    ]
    return "\n".join(lineas)


def repara(plan: dict, fragmento_roto: str, error: str) -> str:
    """El error del validador, de vuelta al modelo (bucle de reparación)."""
    return (
        "Tu respuesta anterior produjo un fragmento que no superó la validación "
        f"del juego:\n\n{error.strip()}\n\n"
        f"El fragmento rechazado era:\n{fragmento_roto}\n\n"
        "Devuelve de nuevo TODOS los campos pedidos (mismo formato), corregidos: "
        "sin campos vacíos, sin inventar nombres de objetos o enemigos que no te "
        "di, respetando lo que ya estaba decidido."
    )


# ── las llamadas sueltas del encuadre ────────────────────────────────────

SCHEMA_EPILOGOS = {
    "type": "object",
    "properties": {"muerte": {"type": "string"}, "caida": {"type": "string"}},
    "required": ["muerte", "caida"],
}


def prologo(premisa: str) -> str:
    """El prólogo de la partida: la premisa hecha cantar."""
    return (
        "Escribe el prólogo de esta historia: 2 párrafos cortos en español. "
        "El primero cuenta la premisa como la contarían en las posadas; el "
        "segundo anuncia que alguien (el héroe) va a caminar hacia ella. "
        "No nombres al héroe, no reveles cómo acaba, no uses llaves."
    )


def epilogos(premisa: str) -> str:
    """Los dos epílogos del juego: caer en combate o dejarse llevar por la grieta."""
    return (
        "Responde SOLO con un objeto JSON con los campos `muerte` y `caida`: "
        "dos epílogos de esta historia, 3 o 4 frases cada uno, en español. "
        "`muerte`: el héroe cae en su última pelea y el mundo lo entierra con "
        "honor. `caida`: la corrupción (la grieta) se lo lleva y el lugar donde "
        "espera el enemigo estrena guardián. Puedes usar {trato} para tratar al "
        "héroe; nada más de llaves."
    )


def condensa(hilo: str) -> str:
    """La condensación del hilo rodante: la mitad, con nombres y deudas."""
    return (
        "Resume el siguiente resumen de una historia en juego en su mitad, en "
        "español. Conserva SIEMPRE nombres propios, promesas hechas, deudas "
        "pendientes y enemigos hechos; suelta adornos.\n\n" + hilo.strip()
    )


def como_json(schema: dict) -> str:
    """El schema, serializado: para los mensajes de reparación."""
    return json.dumps(schema, ensure_ascii=False)


# ── la entrada: la premisa propia, completada por el cronista ────────────

SISTEMA_PREMISA = (
    "Eres el cronista de Aldamar: das nombre a las historias que todavía "
    "no existen. Respondes solo con lo pedido, en español."
)

SCHEMA_PREMISA = {
    "type": "object",
    "properties": {
        "titulo": {"type": "string"},
        "antagonista": {"type": "string"},
        "corte": {"type": "string"},
        "tono": {"type": "string"},
    },
    "required": ["titulo", "antagonista", "corte", "tono"],
}


def premisa(texto: str) -> str:
    """Los campos que faltan de una premisa escrita por el jugador.

    El director los necesita todos para armar jefe, final y encuadre;
    sin cronista caen los genéricos de siempre.
    """
    return (
        "Un jugador quiere que esta historia nazca de su frase:\n\n"
        f"{texto.strip()}\n\n"
        "Responde SOLO con un objeto JSON con estos campos exactos:\n"
        "- titulo: el nombre de la historia, con forma de título (máximo 6 palabras)\n"
        "- antagonista: quién o qué espera al final del camino, con artículo y en "
        "minúscula («el traidor coronado»)\n"
        "- corte: el nombre propio del lugar donde espera, con artículo "
        "(«el Salón del Trono Pudrido»)\n"
        "- tono: una línea de atmósfera para quien redacte las escenas\n"
        "Nada de JSON aparte, ni comentarios, ni texto fuera del objeto."
    )


# ── la salida: el desenlace, cuando el mundo ya está completo ────────────

SCHEMA_FINAL = {
    "type": "object",
    "properties": {
        "texto": {"type": "string"},
        "pregunta": {"type": "string"},
        "frente": {"type": "string"},
        "clemencia": {"type": "string"},
        "detalle_clemencia": {"type": "string"},
        "epilogo_clemencia": {"type": "string"},
        "epilogo_puro": {"type": "string"},
        "epilogo_tentado": {"type": "string"},
        "final_puro": {"type": "string"},
        "final_tentado": {"type": "string"},
    },
    "required": [
        "texto",
        "pregunta",
        "frente",
        "clemencia",
        "detalle_clemencia",
        "epilogo_clemencia",
        "epilogo_puro",
        "epilogo_tentado",
        "final_puro",
        "final_tentado",
    ],
}


def final(premisa: str, corte: str, antagonista: str) -> str:
    """El desenlace de la historia: la escena final y sus dos salidas.

    La estructura de la decisión la pone el director (la opción de
    frente está siempre; la de clemencia, solo si el héroe dejó ofrenda
    al cuidado de un lugar sagrado): aquí solo se piden los textos.
    """
    return (
        "El héroe ha llegado al final de esta historia, con todo el camino "
        f"a la espalda. En {corte} espera {antagonista}, y ahí se decide el "
        "cantar.\n\n"
        "Responde SOLO con un objeto JSON con estos campos exactos:\n"
        "- texto: la escena del enfrentamiento, 2 o 3 frases en segunda persona\n"
        "- pregunta: la pregunta corta que abre la última decisión\n"
        f"- frente: título corto (máx 5 palabras) de la opción de acabar con "
        f"{antagonista} de un modo u otro, pero de frente\n"
        "- clemencia: título corto (máx 5 palabras) de la opción de ofrecer lo "
        "que el héroe dejó al cuidado de un lugar sagrado del camino\n"
        "- detalle_clemencia: una línea que insinúe que solo quien dejó algo lo "
        "entiende\n"
        "- epilogo_clemencia: el desenlace raro, el que no se ganó peleando "
        "(3 o 4 frases, en español)\n"
        "- epilogo_puro: se pelea, se gana y se vuelve (3 o 4 frases)\n"
        "- epilogo_tentado: gana, pero la corrupción viaja con él a casa "
        "(3 o 4 frases)\n"
        "- final_puro: nombre corto (máx 6 palabras) para el final limpio\n"
        "- final_tentado: nombre corto (máx 6 palabras) para el final con la "
        "grieta encima\n"
        "No uses llaves de ningún tipo."
    )

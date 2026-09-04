"""Las pantallas del modo «Aventura Viva»: premisa, héroe, arranque.

Reutiliza `elegir_opcion` y `pantalla_completa` de la interfaz del
juego. La detección de Ollama falla rápido y sin traceback: sin
modelo, la pantalla explica cómo activarlo y el menú vuelve sin crear
nada — el camino por defecto del juego queda intacto.
"""

from __future__ import annotations

import random

from ..interfaz.opciones import elegir_opcion, pantalla_completa
from ..motor.dificultad import DIFICULTADES, Dificultad, obtener_dificultad
from ..motor.juego import Juego
from . import cronista, director, prompts
from .director import Premisa
from .sesion import SesionViva, sanea_texto

SIN_OLLAMA = """\
El modo «Aventura Viva» necesita un modelo local y no hay ninguno a la vista.

Cómo se enciende:

  1. Instala Ollama (https://ollama.com) y déjalo corriendo
     (el juego solo habla con tu propia máquina, 127.0.0.1).
  2. Bájate un modelo, por ejemplo:  ollama pull llama3.1:8b
     (los 7–8B en español van bien para prosa corta).
  3. Vuelve al menú y entra de nuevo en «Aventura Viva…».

Si prefieres otro modelo, ponlo en configuracion.json
("modelo_viva") o exporta ALDAMAR_MODELO. Para un cronista externo
(una API con el protocolo de OpenAI), configura "viva_proveedor",
"viva_host" y "viva_api_key". Sin modelo, el juego completo funciona
igual que siempre: este modo es opcional.
"""

SIN_MODELO = """\
Ollama está corriendo, pero no tiene ningún modelo instalado.

Bájate uno y vuelve al menú:

    ollama pull llama3.1:8b

(los 7–8B en español van bien para prosa corta; el juego solo habla
con tu propia máquina). Si prefieres otro, ponlo en
configuracion.json ("modelo_viva") o exporta ALDAMAR_MODELO.
"""

SIN_SERVICIO_API = """\
El modo «Aventura Viva» va con un cronista externo y no hay servicio a la vista.

Revisa, en configuracion.json o en el entorno:

  1. "viva_host" (o ALDAMAR_HOST): la base del servidor, con su
     versión incluida — p. ej. https://api.openai.com/v1
  2. "viva_api_key" (o ALDAMAR_API_KEY): tu clave, si el servidor la pide.
  3. Que el servidor esté vivo y acepte el protocolo de OpenAI
     (/chat/completions).

Sin cronista, el juego completo funciona igual que siempre: este modo
es opcional.
"""

SIN_MODELO_API = """\
El cronista externo responde, pero no hay ningún modelo a la vista.

Revisa que "modelo_viva" (o ALDAMAR_MODELO) nombre un modelo que
exista en ese servidor, y que la clave ("viva_api_key" o
ALDAMAR_API_KEY) sea válida. Sin cronista, el juego completo funciona
igual que siempre.
"""


def _pantalla_sin_servicio(proveedor: cronista.Proveedor, entrada, salida, color: bool) -> None:
    """El aviso de «no hay cronista», con la ayuda del tipo que toque."""
    texto = SIN_SERVICIO_API if isinstance(proveedor, cronista.ApiCompatible) else SIN_OLLAMA
    pantalla_completa(texto, entrada=entrada, salida=salida, color=color)


def partida_viva(
    *,
    entrada,
    salida,
    color: bool | None,
    flechas: bool | None,
    semilla: int | None,
    audio: bool = True,
    debug: bool = False,
) -> Juego | None:
    """El flujo completo del modo: detección, modelo, premisa, héroe y arranque.

    Devuelve el `Juego` listo para `ciclo()`, o None si no se juega
    (sin Ollama, sin modelo instalado, o el jugador se arrepiente en
    alguna pantalla): en todos los casos, de vuelta al menú.
    Con `debug`, lo hablado con el modelo queda en `cronista_viva.log`.
    """
    proveedor = cronista.proveedor_por_defecto()
    es_api = isinstance(proveedor, cronista.ApiCompatible)
    if not proveedor.disponible():
        _pantalla_sin_servicio(proveedor, entrada, salida, bool(color))
        return None
    if not proveedor.modelos():
        # el servicio vive pero no hay nada que narre: aviso y fuera
        texto = SIN_MODELO_API if es_api else SIN_MODELO
        pantalla_completa(texto, entrada=entrada, salida=salida, color=bool(color))
        return None
    menu_color = bool(color)
    elegido = _elegir_modelo(entrada, salida, menu_color, flechas, proveedor)
    if elegido is None:
        return None
    proveedor = elegido
    premisa = _elegir_premisa(entrada, salida, menu_color, flechas, semilla, proveedor)
    if premisa is None:
        return None
    heroe = _elegir_heroe(entrada, salida, menu_color, flechas)
    if heroe is None:
        return None
    dificultad = _elegir_dificultad(entrada, salida, menu_color, flechas)
    if dificultad is None:
        return None
    sesion = SesionViva(
        premisa=premisa,
        heroe=heroe,
        proveedor=proveedor,
        semilla=semilla,
        avisa=salida,
        debug=debug,
    )
    salida(f"El cronista ({proveedor.modelo}) afila la pluma…")
    aventura = sesion.construir()
    salida(f"(Historia preparada en {sum(sesion.latencias) / 1000:.1f} s de cronista.)")
    return Juego(
        aventura=aventura,
        dificultad=dificultad,
        personaje=heroe,
        semilla=semilla,
        entrada=entrada,
        salida=salida,
        color=color,
        flechas=flechas,
        viva=sesion,
        audio=audio,
    )


def _elegir_modelo(
    entrada, salida, color: bool, flechas: bool | None, proveedor: cronista.Proveedor
) -> cronista.Proveedor | None:
    """El modelo que narra: el fijado por el jugador, o el que elija aquí.

    Con un solo modelo instalado (o uno fijado en `ALDAMAR_MODELO` /
    `configuracion.json`) ni pregunta. La opción de fijar escribe la
    preferencia en `configuracion.json`, como el resto de las gestiones.
    """
    fijado = cronista.modelo_fijado()
    instalados = proveedor.modelos()
    if fijado or len(instalados) <= 1:
        return proveedor
    opciones = [
        (m, m, "el que llevaba elegido" if m == proveedor.modelo else "") for m in instalados
    ] + [("fijar", "Fijar uno por defecto…", "Lo escribe en configuracion.json")]
    clave = elegir_opcion(
        "¿Quién narra la historia?",
        opciones,
        entrada=entrada,
        salida=salida,
        color=color,
        flechas=flechas,
    )
    if clave is None:
        return None
    if clave != "fijar":
        return _con_modelo(proveedor, clave)
    clave = elegir_opcion(
        "¿Cuál queda por defecto?",
        [(m, m, "") for m in instalados],
        entrada=entrada,
        salida=salida,
        color=color,
        flechas=flechas,
    )
    if clave is None:
        return proveedor
    from ..motor import configuracion

    config = configuracion.cargar()
    config.modelo_viva = clave
    configuracion.guardar(config)
    salida(f"Queda fijado en {configuracion.ARCHIVO_CONFIGURACION}: {clave}")
    return _con_modelo(proveedor, clave)


def _con_modelo(proveedor: cronista.Proveedor, modelo: str) -> cronista.Proveedor:
    """El mismo proveedor, con otro modelo (mismo hospedaje y clave)."""
    if isinstance(proveedor, cronista.ApiCompatible):
        return cronista.ApiCompatible(
            modelo=modelo, hospedaje=proveedor.hospedaje, api_key=proveedor.api_key
        )
    if isinstance(proveedor, cronista.Ollama):
        return cronista.Ollama(
            modelo=modelo,
            hospedaje=proveedor.hospedaje,
            num_ctx=getattr(proveedor, "num_ctx", cronista.NUM_CTX_DEFECTO),
        )
    proveedor.modelo = modelo  # los falsos de los tests son mudables
    return proveedor


def _elegir_premisa(
    entrada, salida, color: bool, flechas: bool | None, semilla: int | None,
    proveedor: cronista.Proveedor,
) -> Premisa | None:
    """Tres semillas de la casa, barajadas, o la que escriba el jugador."""
    muestra = random.Random(semilla).sample(director.PREMISAS, 3)
    clave = elegir_opcion(
        "¿De qué nace la historia?",
        [(p.clave, p.titulo, f"Semilla: «{p.texto}»") for p in muestra]
        + [("propia", "Escribir una premisa propia", "La historia que tú digas")],
        entrada=entrada,
        salida=salida,
        color=color,
        flechas=flechas,
    )
    if clave is None:
        return None
    if clave != "propia":
        return next(p for p in director.PREMISAS if p.clave == clave)
    try:
        texto = entrada("Describe tu premisa en una frase: ").strip()
    except EOFError:
        texto = ""
    if not texto:
        texto = "una historia que nadie escribió"
    return _premisa_propia(texto, proveedor, salida)


def _premisa_propia(
    texto: str, proveedor: cronista.Proveedor, salida
) -> Premisa:
    """La frase del jugador, completada por el cronista (o a secas).

    El director necesita título, antagonista y corte para armar jefe,
    final y encuadre; sin cronista, los genéricos de siempre.
    """
    defecto = Premisa(
        clave="propia",
        texto=texto,
        titulo=texto[:1].upper() + texto[1:],
        antagonista="lo que espera al final del camino",
        corte="el lugar del final",
        tono="",
    )
    salida("El cronista completa tu premisa…")
    try:
        datos = proveedor.generar_json(
            prompts.SISTEMA_PREMISA, prompts.premisa(texto), prompts.SCHEMA_PREMISA
        )
    except cronista.CronistaError:
        salida("El cronista no responde: tu premisa va tal cual.")
        return defecto

    def campo(clave: str, de_reserva: str, maximo: int) -> str:
        valor = sanea_texto(str(datos.get(clave, "")), maximo)
        return valor or de_reserva

    return Premisa(
        clave="propia",
        texto=texto,
        titulo=campo("titulo", defecto.titulo, 60),
        antagonista=campo("antagonista", defecto.antagonista, 60),
        corte=campo("corte", defecto.corte, 60),
        tono=campo("tono", "", 100),
    )


def _elegir_heroe(entrada, salida, color: bool, flechas: bool | None) -> str | None:
    """Uno de los tres arquetipos del director (voz y rasgo reales)."""
    return elegir_opcion(
        "¿Quién camina esta historia?",
        [
            (
                str(ficha["clave"]),
                f"{ficha['nombre']}, {ficha['titulo']}",
                str(ficha["presentacion"]),
            )
            for ficha in director.ARQUETIPOS
        ],
        entrada=entrada,
        salida=salida,
        color=color,
        flechas=flechas,
    )


def _elegir_dificultad(entrada, salida, color: bool, flechas: bool | None) -> Dificultad | None:
    """El mismo paso de dificultad del menú clásico."""
    clave = elegir_opcion(
        "¿A qué ritmo quieres caminar?",
        [(d.clave, d.nombre, d.descripcion) for d in DIFICULTADES.values()],
        entrada=entrada,
        salida=salida,
        color=color,
        flechas=flechas,
    )
    if clave is None:
        return None
    return obtener_dificultad(clave)

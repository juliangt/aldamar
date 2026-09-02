"""Carga y validación de aventuras definidas en archivos JSON.

Cada aventura de Aldamar es un `*.json` dentro de `aldamar.aventuras`:
este módulo lo lee, valida el contrato —campos obligatorios, tipos y
referencias entre secciones, además del vocabulario de eventos de
`eventos.py`— y arma el objeto `Aventura` que el motor consume.

Sumar una aventura al juego = soltar su JSON en el paquete: el
descubrimiento (`cargar_todas`) es automático y el orden de registro —
el del menú— lo fija el campo opcional `orden` (a igualdad o ausencia,
alfabético por nombre de archivo). Ante un archivo roto, el error
`AventuraInvalida` nombra el archivo y el campo de la culpa.
"""

from __future__ import annotations

import json
from importlib import resources
from typing import Any

from .aventura import Aventura, PersonajeInicial, registrar
from .eventos import TIPOS_EVENTOS, ataque_especial_desde, evento_desde
from .mundo import Lugar
from .personajes import RASGOS, Companero

_FALTA = object()  # sentinel: el campo no vino y no tiene valor por defecto


class AventuraInvalida(ValueError):
    """El JSON de una aventura no cumple el contrato."""


def _mal(origen: str, problema: str) -> AventuraInvalida:
    return AventuraInvalida(f"{origen}: {problema}")


def _texto(datos: dict, campo: str, donde: str) -> str:
    valor = datos.get(campo, _FALTA)
    if valor is _FALTA:
        raise _mal(donde, f"falta el campo obligatorio {campo!r}")
    if not isinstance(valor, str):
        raise _mal(donde, f"el campo {campo!r} debe ser texto (llegó {type(valor).__name__})")
    return valor


def _texto_opcional(datos: dict, campo: str, donde: str) -> str | None:
    valor = datos.get(campo)
    if valor is None:
        return None
    if not isinstance(valor, str):
        raise _mal(donde, f"el campo {campo!r} debe ser texto o null (llegó {type(valor).__name__})")
    return valor


def _entero(datos: dict, campo: str, donde: str, defecto: int | object = _FALTA) -> int:
    valor = datos.get(campo, _FALTA)
    if valor is _FALTA or valor is None:
        if defecto is _FALTA:
            raise _mal(donde, f"falta el campo obligatorio {campo!r}")
        return defecto  # type: ignore[return-value]
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise _mal(donde, f"el campo {campo!r} debe ser entero (llegó {type(valor).__name__})")
    return valor


def _booleano(datos: dict, campo: str, donde: str, defecto: bool) -> bool:
    valor = datos.get(campo)
    if valor is None:
        return defecto
    if not isinstance(valor, bool):
        raise _mal(donde, f"el campo {campo!r} debe ser true o false (llegó {type(valor).__name__})")
    return valor


def _lista_textos(datos: dict, campo: str, donde: str) -> list[str]:
    valor = datos.get(campo, [])
    if not isinstance(valor, list) or any(not isinstance(t, str) for t in valor):
        raise _mal(donde, f"el campo {campo!r} debe ser una lista de textos")
    return valor


def _diccionario(datos: dict, campo: str, donde: str) -> dict:
    valor = datos.get(campo, _FALTA)
    if valor is _FALTA:
        raise _mal(donde, f"falta el campo obligatorio {campo!r}")
    if not isinstance(valor, dict):
        raise _mal(donde, f"el campo {campo!r} debe ser un objeto (llegó {type(valor).__name__})")
    return valor


def _dicc_de_textos(datos: dict, campo: str, donde: str) -> dict[str, str]:
    valor = datos.get(campo, {})
    if not isinstance(valor, dict) or any(not isinstance(v, str) for v in valor.values()):
        raise _mal(donde, f"el campo {campo!r} debe ser un objeto de textos")
    return valor


# ── secciones del archivo ────────────────────────────────────────────────

def _items(datos: dict, origen: str) -> dict[str, dict]:
    crudos = _diccionario(datos, "items", origen)
    for clave, item in crudos.items():
        po = f"items[{clave!r}]"
        if not isinstance(item, dict):
            raise _mal(origen, f"{po} debe ser un objeto")
        _texto(item, "nombre", po)
        tipo = _texto(item, "tipo", po)
        if tipo in ("arma", "armadura"):
            _entero(item, "bonus", po)
        elif tipo == "consumible":
            _entero(item, "curacion", po)
        precio = item.get("precio", _FALTA)
        if precio is _FALTA:
            raise _mal(po, "falta el campo obligatorio 'precio'")
        if precio is not None and (isinstance(precio, bool) or not isinstance(precio, int)):
            raise _mal(po, "el campo 'precio' debe ser entero o null")
    return crudos


def _enemigos(datos: dict, origen: str) -> dict[str, dict]:
    crudos = _diccionario(datos, "enemigos", origen)
    for clave, enemigo in crudos.items():
        po = f"enemigos[{clave!r}]"
        if not isinstance(enemigo, dict):
            raise _mal(origen, f"{po} debe ser un objeto")
        _texto(enemigo, "nombre", po)
        if _entero(enemigo, "vida", po) <= 0:
            raise _mal(po, "'vida' debe ser mayor a cero")
        _entero(enemigo, "ataque", po)
        _entero(enemigo, "defensa", po, defecto=0)
        _booleano(enemigo, "sin_huida", po, defecto=False)
    return crudos


def _reclutas(datos: dict, origen: str) -> dict[str, Companero]:
    crudos = _diccionario(datos, "reclutas", origen)
    reclutas: dict[str, Companero] = {}
    for clave, ficha in crudos.items():
        po = f"reclutas[{clave!r}]"
        if not isinstance(ficha, dict):
            raise _mal(origen, f"{po} debe ser un objeto")
        vida = _entero(ficha, "vida", po)
        reclutas[clave] = Companero(
            clave=clave,
            nombre=_texto(ficha, "nombre", po),
            vida=vida,
            vida_max=_entero(ficha, "vida_max", po, defecto=vida),
            ataque=_entero(ficha, "ataque", po),
            defensa=_entero(ficha, "defensa", po, defecto=0),
        )
    return reclutas


def _personaje(clave: str, datos: dict, prologo_base: str, origen: str) -> PersonajeInicial:
    po = f"personajes[{clave!r}]"
    rasgos = _lista_textos(datos, "rasgos", po)
    desconocidos = [r for r in rasgos if r not in RASGOS]
    if desconocidos:
        raise _mal(
            origen,
            f"{po}: rasgos desconocidos: {', '.join(desconocidos)}; "
            f"válidos: {', '.join(RASGOS)}",
        )
    trato = _texto_opcional(datos, "trato", po) or "caminante"
    quien = _texto_opcional(datos, "quien", po) or "el caminante"
    return PersonajeInicial(
        clave=clave,
        nombre=_texto(datos, "nombre", po),
        titulo=_texto(datos, "titulo", po),
        presentacion=_texto(datos, "presentacion", po),
        vida=_entero(datos, "vida", po, defecto=45),
        ataque=_entero(datos, "ataque", po, defecto=4),
        monedas=_entero(datos, "monedas", po, defecto=10),
        inventario=_lista_textos(datos, "inventario", po),
        rasgos=rasgos,
        # el prólogo efectivo: el mito de la aventura más la voz del héroe
        prologo=prologo_base + (_texto_opcional(datos, "prologo_extra", po) or ""),
        texto_nombre=_texto_opcional(datos, "texto_nombre", po),
        trato=trato,
        quien=quien,
    )


def _lugar(lid: str, datos: dict, origen: str) -> Lugar:
    po = f"lugares[{lid!r}]"
    return Lugar(
        id=lid,
        nombre=_texto(datos, "nombre", po),
        descripcion=_texto(datos, "descripcion", po),
        salidas=_dicc_de_textos(datos, "salidas", po),
        objetos=_lista_textos(datos, "objetos", po),
        monedas=_entero(datos, "monedas", po, defecto=0),
        enemigos=_lista_textos(datos, "enemigos", po),
        npcs=_dicc_de_textos(datos, "npcs", po),
        tienda=_booleano(datos, "tienda", po, defecto=False),
        descanso=_booleano(datos, "descanso", po, defecto=False),
        evento=_texto_opcional(datos, "evento", po),
        requiere=_texto_opcional(datos, "requiere", po),
        requiere_texto=_texto_opcional(datos, "requiere_texto", po) or "",
    )


def _valida_opciones_decision(
    datos: dict, items: dict[str, dict], po: str, origen: str
) -> None:
    opciones = datos.get("opciones")
    if not isinstance(opciones, list) or not opciones:
        raise _mal(origen, f"{po}: 'opciones' debe ser una lista con al menos una opción")
    vistas: set[str] = set()
    for i, opcion in enumerate(opciones):
        opo = f"{po}.opciones[{i}]"
        if not isinstance(opcion, dict):
            raise _mal(origen, f"{opo} debe ser un objeto")
        clave = _texto(opcion, "clave", opo)
        if clave in vistas:
            raise _mal(origen, f"{opo}: la clave {clave!r} está repetida")
        vistas.add(clave)
        _texto(opcion, "titulo", opo)
        _texto_opcional(opcion, "detalle", opo)
        _texto_opcional(opcion, "texto", opo)
        _texto_opcional(opcion, "flag", opo)
        item = opcion.get("item")
        if item is not None:
            _texto(opcion, "item", opo)
            if item not in items:
                raise _mal(origen, f"{opo}: otorga el item {item!r}, que no existe")
        _entero(opcion, "corrupcion", opo, defecto=0)


def _valida_condicion(datos: dict, po: str, origen: str) -> None:
    condicion = datos.get("condicion")
    if condicion is None:
        return
    if not isinstance(condicion, dict):
        raise _mal(origen, f"{po}: 'condicion' debe ser un objeto o null")
    _texto_opcional(condicion, "flag", f"{po}.condicion")
    _texto_opcional(condicion, "no_flag", f"{po}.condicion")


def _evento(
    clave: str,
    datos: dict,
    items: dict[str, dict],
    claves_enemigos: set[str],
    origen: str,
):
    po = f"eventos[{clave!r}]"
    if not isinstance(datos, dict):
        raise _mal(origen, f"{po} debe ser un objeto")
    tipo = _texto(datos, "tipo", po)
    if tipo not in TIPOS_EVENTOS:
        raise _mal(
            origen,
            f"{po}: tipo de evento desconocido {tipo!r}; "
            f"válidos: {', '.join(sorted(TIPOS_EVENTOS))}",
        )
    if tipo == "otorgar":
        item = _texto(datos, "item", po)
        if item not in items:
            raise _mal(origen, f"{po}: otorga el item {item!r}, que no existe")
        _texto(datos, "texto", po)
        _texto_opcional(datos, "una_vez", po)
    elif tipo == "curar_grupo":
        _texto(datos, "texto", po)
        _entero(datos, "corrupcion", po, defecto=0)
        _texto_opcional(datos, "una_vez", po)
    elif tipo == "corrupcion":
        _entero(datos, "puntos", po)
        _texto_opcional(datos, "aviso", po)
    elif tipo == "narrar":
        _texto(datos, "texto", po)
        _texto_opcional(datos, "una_vez", po)
    elif tipo == "decision":
        _texto(datos, "texto", po)
        _texto(datos, "pregunta", po)
        _valida_opciones_decision(datos, items, po, origen)
    elif tipo == "emboscar":
        _texto(datos, "texto", po)
        enemigos = datos.get("enemigos")
        if not isinstance(enemigos, list) or not enemigos:
            raise _mal(origen, f"{po}: 'enemigos' debe ser una lista con al menos un enemigo")
        for enemigo in enemigos:
            if enemigo not in claves_enemigos:
                raise _mal(origen, f"{po}: embosca al enemigo {enemigo!r}, que no existe")
        _valida_condicion(datos, po, origen)
    elif tipo == "final":
        _valida_final(datos, po, origen)
    try:
        return evento_desde(datos, clave)
    except (KeyError, ValueError) as e:
        raise _mal(origen, f"{po}: {e}") from e


def _valida_final(datos: dict, po: str, origen: str) -> None:
    _texto(datos, "texto", po)
    _texto(datos, "pregunta", po)
    opciones = datos.get("opciones")
    if not isinstance(opciones, list) or not opciones:
        raise _mal(origen, f"{po}: 'opciones' debe ser una lista con al menos una opción")
    vistas: set[str] = set()
    por_defecto = 0
    for i, opcion in enumerate(opciones):
        opo = f"{po}.opciones[{i}]"
        if not isinstance(opcion, dict):
            raise _mal(origen, f"{opo} debe ser un objeto")
        clave = _texto(opcion, "clave", opo)
        if clave in vistas:
            raise _mal(origen, f"{opo}: la clave {clave!r} está repetida")
        vistas.add(clave)
        _texto(opcion, "titulo", opo)
        _texto_opcional(opcion, "detalle", opo)
        estilo = _texto_opcional(opcion, "estilo", opo) or "aviso"
        if estilo not in ("aviso", "epico"):
            raise _mal(origen, f"{opo}: 'estilo' debe ser 'aviso' o 'epico'")
        _texto_opcional(opcion, "requiere_flag", opo)
        if "epilogo" in opcion:
            _texto(opcion, "epilogo", opo)
            _texto(opcion, "final", opo)
        else:
            por_defecto += 1
            if opcion.get("requiere_flag"):
                raise _mal(
                    origen,
                    f"{opo}: el desenlace por defecto no puede exigir "
                    f"'requiere_flag' (tendría que estar siempre disponible)",
                )
    if por_defecto != 1:
        raise _mal(
            origen,
            f"{po}: exactamente una opción debe quedarse sin 'epilogo' "
            f"(es el desenlace por defecto); hay {por_defecto}",
        )
    _entero(datos, "umbral_tentado", po)
    _texto(datos, "epilogo_puro", po)
    _texto(datos, "final_puro", po)
    _texto(datos, "epilogo_tentado", po)
    _texto(datos, "final_tentado", po)
    _texto_opcional(datos, "texto_companeros", po)


def _comando_especial(datos: dict, origen: str):
    """Devuelve (comando, texto_fuera, ataque) para la Aventura."""
    crudo = datos.get("comando_especial")
    if crudo is None:
        return None, "", None
    po = "comando_especial"
    if not isinstance(crudo, dict):
        raise _mal(origen, f"{po} debe ser un objeto o null")
    comando = _texto(crudo, "comando", po)
    texto_fuera = _texto(crudo, "texto_fuera", po)
    efecto = crudo.get("efecto", _FALTA)
    if efecto is _FALTA or not isinstance(efecto, dict):
        raise _mal(origen, f"{po}: falta el objeto 'efecto'")
    pe = f"{po}.efecto"
    divisor = _entero(efecto, "dano_por_corrupcion", pe)
    if divisor <= 0:
        raise _mal(origen, f"{pe}: 'dano_por_corrupcion' debe ser mayor a cero")
    mensaje = _texto(efecto, "mensaje", pe)
    if "{efectivo}" not in mensaje:
        raise _mal(origen, f"{pe}: 'mensaje' debe mencionar {{efectivo}}")
    ataque = ataque_especial_desde(efecto)
    return comando, texto_fuera, ataque


def _chequea_referencias(
    av: Aventura, tiendas: dict[str, list[str]], origen: str
) -> None:
    """Toda clave usada tiene que existir: el error se nombra en el acto."""
    for lid, lugar in av.lugares.items():
        for palabra, destino in lugar.salidas.items():
            if destino not in av.lugares:
                raise _mal(origen, f"lugares[{lid!r}]: la salida {palabra!r} apunta a {destino!r}, que no existe")
        for objeto in lugar.objetos:
            if objeto not in av.items:
                raise _mal(origen, f"lugares[{lid!r}]: el objeto {objeto!r} no existe en items")
        for enemigo in lugar.enemigos:
            if enemigo not in av.enemigos:
                raise _mal(origen, f"lugares[{lid!r}]: el enemigo {enemigo!r} no existe en enemigos")
        for _npc, dialogo in lugar.npcs.items():
            if dialogo not in av.dialogos:
                raise _mal(origen, f"lugares[{lid!r}]: el diálogo {dialogo!r} no existe en dialogos")
        if lugar.evento and lugar.evento not in av.eventos:
            raise _mal(origen, f"lugares[{lid!r}]: el evento {lugar.evento!r} no existe en eventos")
        if lugar.requiere and lugar.requiere not in av.items:
            raise _mal(origen, f"lugares[{lid!r}]: exige el item {lugar.requiere!r}, que no existe")
        if lugar.tienda and lid not in tiendas:
            raise _mal(origen, f"lugares[{lid!r}] es tienda pero no tiene stock en 'tiendas'")
    for tienda, stock in tiendas.items():
        if tienda not in av.lugares:
            raise _mal(origen, f"tiendas[{tienda!r}] no corresponde a ningún lugar")
        for item in stock:
            if item not in av.items:
                raise _mal(origen, f"tiendas[{tienda!r}]: vende {item!r}, que no existe en items")
    for clave, ficha in av.personajes.items():
        for item in ficha.inventario:
            if item not in av.items:
                raise _mal(origen, f"personajes[{clave!r}]: lleva {item!r}, que no existe en items")


# ── carga propiamente dicha ──────────────────────────────────────────────

def cargar_aventura_dict(datos: Any, origen: str = "<aventura>") -> Aventura:
    """Valida los datos de una aventura y arma el objeto `Aventura`."""
    if not isinstance(datos, dict):
        raise _mal(origen, "la raíz del archivo debe ser un objeto JSON")

    id_ = _texto(datos, "id", origen)
    titulo = _texto(datos, "titulo", origen)
    descripcion = _texto(datos, "descripcion", origen)
    texto_nombre = _texto(datos, "texto_nombre", origen)
    prologo_base = _texto_opcional(datos, "prologo_base", origen) or ""
    lugar_inicial = _texto(datos, "lugar_inicial", origen)
    jugador_inicial = _texto(datos, "jugador_inicial", origen)

    epilogos = _diccionario(datos, "epilogos", origen)
    epilogo_muerte = _texto(epilogos, "muerte", f"{origen}.epilogos")
    epilogo_caida = _texto(epilogos, "caida", f"{origen}.epilogos")

    items = _items(datos, origen)
    enemigos = _enemigos(datos, origen)
    reclutas = _reclutas(datos, origen)
    tiendas_raw = datos.get("tiendas", {})
    if not isinstance(tiendas_raw, dict) or any(
        not isinstance(stock, list) or any(not isinstance(t, str) for t in stock)
        for stock in tiendas_raw.values()
    ):
        raise _mal(origen, "el campo 'tiendas' debe ser un objeto de listas de textos")
    dialogos = _dicc_de_textos(datos, "dialogos", origen)

    personajes_datos = _diccionario(datos, "personajes", origen)
    if not personajes_datos:
        raise _mal(origen, "'personajes' debe traer al menos un héroe")
    lugares_datos = _diccionario(datos, "lugares", origen)
    if not lugares_datos:
        raise _mal(origen, "'lugares' debe traer al menos un lugar")

    personajes = {
        clave: _personaje(clave, ficha, prologo_base, origen)
        for clave, ficha in personajes_datos.items()
    }
    if jugador_inicial not in personajes:
        raise _mal(origen, f"jugador_inicial {jugador_inicial!r} no está en 'personajes'")

    lugares = {lid: _lugar(lid, datos_lugar, origen) for lid, datos_lugar in lugares_datos.items()}
    if lugar_inicial not in lugares:
        raise _mal(origen, f"lugar_inicial {lugar_inicial!r} no está en 'lugares'")

    eventos_crudos = datos.get("eventos", {})
    if not isinstance(eventos_crudos, dict):
        raise _mal(origen, "el campo 'eventos' debe ser un objeto")
    eventos = {
        clave: _evento(clave, ev, items, set(enemigos), origen)
        for clave, ev in eventos_crudos.items()
    }

    orden = datos.get("orden")
    if orden is not None and (isinstance(orden, bool) or not isinstance(orden, int)):
        raise _mal(origen, "el campo 'orden' debe ser entero o null")

    comando, texto_fuera, ataque = _comando_especial(datos, origen)

    av = Aventura(
        id=id_,
        titulo=titulo,
        descripcion=descripcion,
        prologo=personajes[jugador_inicial].prologo,
        texto_nombre=texto_nombre,
        lugares=lugares,
        lugar_inicial=lugar_inicial,
        items=items,
        enemigos=enemigos,
        reclutas=reclutas,
        tiendas=tiendas_raw,
        dialogos=dialogos,
        personajes=personajes,
        jugador_inicial=jugador_inicial,
        epilogo_muerte=epilogo_muerte,
        epilogo_caida=epilogo_caida,
        comando_especial=comando,
        texto_especial_fuera=texto_fuera,
        ataque_especial=ataque,
        eventos=eventos,
        orden=orden,
    )
    _chequea_referencias(av, tiendas_raw, origen)
    return av


def cargar_aventura(texto: str, origen: str) -> Aventura:
    """Lee y valida un JSON de aventura; no lo registra."""
    try:
        datos = json.loads(texto)
    except json.JSONDecodeError as e:
        raise _mal(origen, f"no es JSON válido: {e}") from e
    return cargar_aventura_dict(datos, origen)


def cargar_todas(raiz: Any | None = None) -> None:
    """Descubre y registra todos los `*.json` del paquete de aventuras.

    `raiz` permite apuntar a otro directorio (los tests); por defecto es
    `aldamar.aventuras`. El orden de registro —el del menú— lo fija el
    campo opcional `orden` (menor primero, y antes que quien no lo
    declara); a igualdad, alfabético por nombre de archivo.
    """
    if raiz is None:
        raiz = resources.files("aldamar.aventuras")
    cargadas = []
    for entrada in raiz.iterdir():
        if not entrada.name.endswith(".json"):
            continue
        av = cargar_aventura(entrada.read_text(encoding="utf-8"), f"aventuras/{entrada.name}")
        cargadas.append((av.orden if av.orden is not None else float("inf"), entrada.name, av))
    for _orden, _nombre, av in sorted(cargadas, key=lambda t: (t[0], t[1])):
        registrar(av)

"""La carga propiamente dicha: del JSON al objeto `Aventura` registrado.

`cargar_aventura_dict` valida y arma la aventura completa llamando a
las secciones de `secciones.py`; `valida_fragmento` valida piezas
sueltas para el modo «Aventura Viva»; `cargar_todas` descubre y
registra los `*.json` del paquete de datos.
"""

from __future__ import annotations

import json
from importlib import resources
from typing import Any

from ..aventura import Aventura, registrar
from .campos import _dialogos, _diccionario, _mal, _texto, _texto_opcional
from .secciones import (
    _chequea_referencias,
    _comando_especial,
    _enemigos,
    _evento,
    _items,
    _legado,
    _lugar,
    _personaje,
    _reclutas,
    _secretos,
)

# ── fragmentos (el modo «Aventura Viva» y el autor offline) ───────────────

def valida_fragmento(
    fragmento: Any,
    conocidos: dict[str, set[str]] | None = None,
    origen: str = "<fragmento>",
) -> None:
    """Valida las secciones de un fragmento de aventura de forma aislada.

    Un fragmento es un pedazo de aventura — `items`, `enemigos`,
    `dialogos`, `lugares` o `eventos`, en cualquier combinación — que
    todavía no vive en un archivo entero. La validación de sección es
    exactamente la de `cargar_aventura_dict`; la diferencia está en las
    referencias: aquí se admite lo que `conocidos` declara ya existente
    (los ids vivos de la partida en marcha), porque el fragmento completa
    un mundo, no lo empieza.

    `conocidos` es un diccionario por sección: `{"items": {...},
    "enemigos": {...}, "dialogos": {...}, "eventos": {...},
    "lugares": {...}}`. Ante cualquier culpa lanza `AventuraInvalida`
    que nombra `origen` y el campo. La validación final y autoritaria es
    siempre la de la aventura completa; esta es la pasada temprana que
    atribuye el error al fragmento antes de fusionarlo.
    """
    if not isinstance(fragmento, dict):
        raise _mal(origen, "el fragmento debe ser un objeto JSON")
    conocidos = conocidos or {}
    permitidas = ("items", "enemigos", "dialogos", "lugares", "eventos")
    desconocidas = [c for c in fragmento if c not in permitidas]
    if desconocidas:
        raise _mal(
            origen,
            f"secciones desconocidas: {', '.join(sorted(desconocidas))}; "
            f"válidas: {', '.join(permitidas)}",
        )
    items = set(conocidos.get("items", ()))
    if "items" in fragmento:
        items.update(_items({"items": fragmento["items"]}, origen))
    enemigos = set(conocidos.get("enemigos", ()))
    if "enemigos" in fragmento:
        enemigos.update(_enemigos({"enemigos": fragmento["enemigos"]}, origen))
    dialogos = set(conocidos.get("dialogos", ()))
    if "dialogos" in fragmento:
        dialogos.update(_dialogos({"dialogos": fragmento["dialogos"]}, origen))
    eventos = set(conocidos.get("eventos", ()))
    for clave, ev in fragmento.get("eventos", {}).items():
        _evento(clave, ev, {k: {} for k in items}, enemigos, origen)
        eventos.add(clave)
    lugares = set(conocidos.get("lugares", ())) | set(fragmento.get("lugares", {}))
    for lid, datos_lugar in fragmento.get("lugares", {}).items():
        lugar = _lugar(lid, datos_lugar, origen)
        po = f"lugares[{lid!r}]"
        for palabra, destino in lugar.salidas.items():
            if destino not in lugares:
                raise _mal(origen, f"{po}: la salida {palabra!r} apunta a {destino!r}, que no existe")
        for objeto in lugar.objetos:
            if objeto not in items:
                raise _mal(origen, f"{po}: el objeto {objeto!r} no existe en items")
        for enemigo in lugar.enemigos:
            if enemigo not in enemigos:
                raise _mal(origen, f"{po}: el enemigo {enemigo!r} no existe en enemigos")
        for dialogo in lugar.npcs.values():
            if dialogo not in dialogos:
                raise _mal(origen, f"{po}: el diálogo {dialogo!r} no existe en dialogos")
        for clave_evento in lugar.eventos:
            if clave_evento not in eventos:
                raise _mal(origen, f"{po}: el evento {clave_evento!r} no existe en eventos")
        if lugar.requiere and lugar.requiere not in items:
            raise _mal(origen, f"{po}: exige el item {lugar.requiere!r}, que no existe")
    # el stock de tiendas y el inventario de los héroes quedan para la
    # validación de la aventura completa, que es la autoritaria.


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
    dialogos = _dialogos(datos, origen)

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
    eventos = {}
    banderas_de_decision: set[str] = set()
    for clave, ev in eventos_crudos.items():
        eventos[clave] = _evento(clave, ev, items, set(enemigos), origen)
        if isinstance(ev, dict) and ev.get("tipo") == "decision":
            for opcion in ev.get("opciones", []):
                if isinstance(opcion, dict) and opcion.get("flag"):
                    banderas_de_decision.add(opcion["flag"])

    legado_av = _legado(datos, origen, banderas_de_decision)

    orden = datos.get("orden")
    if orden is not None and (isinstance(orden, bool) or not isinstance(orden, int)):
        raise _mal(origen, "el campo 'orden' debe ser entero o null")

    comando, texto_fuera, ataque = _comando_especial(datos, origen)
    secretos = _secretos(datos, origen)

    av = Aventura(
        id=id_,
        titulo=titulo,
        descripcion=descripcion,
        prologo=personajes[jugador_inicial].prologo or prologo_base,
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
        secretos=secretos,
        eventos=eventos,
        legado=legado_av,
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
    """Descubre y registra todos los `*.json` de `datos/aventuras`.

    `raiz` permite apuntar a otro directorio (los tests); por defecto es
    `aldamar.datos.aventuras`. El orden de registro —el del menú— lo fija el
    campo opcional `orden` (menor primero, y antes que quien no lo
    declara); a igualdad, alfabético por nombre de archivo.
    """
    if raiz is None:
        raiz = resources.files("aldamar").joinpath("datos", "aventuras")
    cargadas = []
    for entrada in raiz.iterdir():
        if not entrada.name.endswith(".json"):
            continue
        av = cargar_aventura(entrada.read_text(encoding="utf-8"), f"datos/aventuras/{entrada.name}")
        cargadas.append((av.orden if av.orden is not None else float("inf"), entrada.name, av))
    # el legado cruza aventuras: toda canónica importada tiene que
    # exportarla alguna (el error nombra el archivo que la espera)
    canonicas: set[str] = set()
    for _orden, _nombre, av in cargadas:
        canonicas.update(av.legado.exporta)
    for _orden, nombre, av in cargadas:
        for canonica in av.legado.importa:
            if canonica not in canonicas:
                raise _mal(
                    f"datos/aventuras/{nombre}",
                    f"legado.importa: la bandera canónica {canonica!r} "
                    f"no la exporta ninguna aventura",
                )
    for _orden, _nombre, av in sorted(cargadas, key=lambda t: (t[0], t[1])):
        registrar(av)

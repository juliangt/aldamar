"""Las secciones del JSON de aventura: validación y armado de fichas.

Cada función toma su sección cruda (`items`, `enemigos`, `lugares`,
`eventos`…), exige el contrato campo a campo y devuelve la ficha que
`carga.cargar_aventura_dict` junta en el objeto `Aventura`. Las
referencias cruzadas entre secciones las cierra `_chequea_referencias`.
"""

from __future__ import annotations

from ..aventura import Aventura, Legado, PersonajeInicial, Secreto
from ..eventos import TIPOS_EVENTOS, ataque_especial_desde, evento_desde
from ..mundo import Lugar
from ..personajes import TIPOS_HABILIDAD, Companero
from ..rasgos import RASGOS
from .campos import (
    _FALTA,
    _booleano,
    _dicc_de_textos,
    _diccionario,
    _entero,
    _entero_opcional,
    _lista_textos,
    _mal,
    _texto,
    _texto_opcional,
)

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
        if "texto_uso" in item:
            _texto(item, "texto_uso", po)
    return crudos


def _enemigos(datos: dict, origen: str) -> dict[str, dict]:
    crudos = _diccionario(datos, "enemigos", origen)
    claves = set(crudos)
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
        experiencia = _entero(enemigo, "experiencia", po, defecto=0)
        if experiencia < 0:
            raise _mal(po, "'experiencia' no puede ser negativa")
        _valida_habilidades(enemigo.get("habilidades", []), po, claves, clave, origen)
        _valida_fases(enemigo, po, claves, clave, origen)
    return crudos


def _valida_habilidades(
    lista: object, po: str, claves_enemigos: set[str], clave_enemigo: str, origen: str
) -> None:
    """El vocabulario de habilidades, sea del enemigo o de una de sus fases."""
    if not isinstance(lista, list):
        raise _mal(origen, f"{po}: 'habilidades' debe ser una lista")
    for i, hab in enumerate(lista):
        hp = f"{po}.habilidades[{i}]"
        if not isinstance(hab, dict):
            raise _mal(origen, f"{hp} debe ser un objeto")
        tipo = _texto(hab, "tipo", hp)
        if tipo not in TIPOS_HABILIDAD:
            raise _mal(
                origen,
                f"{hp}: tipo de habilidad desconocido {tipo!r}; "
                f"válidos: {', '.join(sorted(TIPOS_HABILIDAD))}",
            )
        if tipo == "veneno":
            if _entero(hab, "dano", hp) <= 0:
                raise _mal(origen, f"{hp}: 'dano' debe ser mayor a cero")
            if _entero(hab, "turnos", hp) <= 0:
                raise _mal(origen, f"{hp}: 'turnos' debe ser mayor a cero")
            _texto(hab, "texto", hp)
        elif tipo == "curarse":
            if _entero(hab, "puntos", hp) <= 0:
                raise _mal(origen, f"{hp}: 'puntos' debe ser mayor a cero")
            _texto(hab, "texto", hp)
        elif tipo == "refuerzo":
            convocado = _texto(hab, "enemigo", hp)
            if convocado not in claves_enemigos:
                raise _mal(origen, f"{hp}: convoca al enemigo {convocado!r}, que no existe")
            if convocado == clave_enemigo:
                raise _mal(
                    origen, f"{hp}: no puede convocarse a sí mismo (la pelea no acabaría nunca)"
                )
            if _entero(hab, "veces", hp, defecto=1) < 1:
                raise _mal(origen, f"{hp}: 'veces' debe ser mayor a cero")
            _texto(hab, "texto", hp)
        elif tipo == "golpe_fuerte":
            if _entero(hab, "dano_extra", hp) <= 0:
                raise _mal(origen, f"{hp}: 'dano_extra' debe ser mayor a cero")
            _texto(hab, "texto_aviso", hp)
            mensaje = _texto(hab, "texto_golpe", hp)
            if "{efectivo}" not in mensaje:
                raise _mal(origen, f"{hp}: 'texto_golpe' debe mencionar {{efectivo}}")
        if _entero(hab, "peso", hp, defecto=1) < 1:
            raise _mal(origen, f"{hp}: 'peso' debe ser mayor a cero")
        condicion = hab.get("condicion")
        if condicion is None:
            continue
        if not isinstance(condicion, dict):
            raise _mal(origen, f"{hp}: 'condicion' debe ser un objeto o null")
        vida = condicion.get("vida_menor_que")
        if vida is not None and (
            isinstance(vida, bool) or not isinstance(vida, int) or not 1 <= vida <= 99
        ):
            raise _mal(
                origen, f"{hp}.condicion: 'vida_menor_que' debe ser un porcentaje entre 1 y 99"
            )
        cada = condicion.get("cada_n_turnos")
        if cada is not None and (
            isinstance(cada, bool) or not isinstance(cada, int) or cada < 1
        ):
            raise _mal(origen, f"{hp}.condicion: 'cada_n_turnos' debe ser entero mayor a cero")


def _valida_fases(
    datos: dict, po: str, claves_enemigos: set[str], clave_enemigo: str, origen: str
) -> None:
    """Cada fase: umbral de vida, ficha nueva y, si quiere, habilidades."""
    fases = datos.get("fases", [])
    if not isinstance(fases, list):
        raise _mal(origen, f"{po}: 'fases' debe ser una lista")
    for i, fase in enumerate(fases):
        fp = f"{po}.fases[{i}]"
        if not isinstance(fase, dict):
            raise _mal(origen, f"{fp} debe ser un objeto")
        umbral = _entero(fase, "vida_menor_que", fp)
        if not 1 <= umbral <= 99:
            raise _mal(origen, f"{fp}: 'vida_menor_que' debe ser un porcentaje entre 1 y 99")
        _texto(fase, "texto", fp)
        _texto_opcional(fase, "nombre", fp)
        for campo in ("ataque", "defensa"):
            valor = _entero_opcional(fase, campo, fp)
            if valor is not None and valor < 0:
                raise _mal(origen, f"{fp}: {campo!r} no puede ser negativo")
        _valida_habilidades(fase.get("habilidades", []), fp, claves_enemigos, clave_enemigo, origen)


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
    eventos = datos.get("eventos", [])
    if not isinstance(eventos, list) or any(not isinstance(e, str) for e in eventos):
        raise _mal(origen, f"{po}: 'eventos' debe ser una lista de claves de eventos")
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
        eventos=eventos,
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
        _valida_condicion(datos, po, origen)
        if datos.get("texto_grieta") is not None:
            _texto(datos, "texto_grieta", po)
            grieta = _entero(datos, "grieta_desde", po)
            if not 1 <= grieta <= 99:
                raise _mal(origen, f"{po}: 'grieta_desde' debe ser un porcentaje entre 1 y 99")
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


def _legado(datos: dict, origen: str, banderas_de_decision: set[str]) -> Legado:
    """El hilo de la serie: qué exporta esta aventura y qué importa.

    Las canónicas exportadas tienen que apuntar a banderas que una
    decisión de esta aventura deja encendidas: el legado cuenta lo que
    se hizo, no lo que se fue a decir.
    """
    crudo = datos.get("legado")
    if crudo is None:
        return Legado()
    if not isinstance(crudo, dict):
        raise _mal(origen, "el campo 'legado' debe ser un objeto")
    exporta = crudo.get("exporta", {})
    if not isinstance(exporta, dict) or any(
        not isinstance(c, str) or not isinstance(v, str) for c, v in exporta.items()
    ):
        raise _mal(
            origen, "legado.exporta debe ser un objeto de canónica → bandera local"
        )
    for canonica, local in exporta.items():
        if local not in banderas_de_decision:
            raise _mal(
                origen,
                f"legado.exporta: la canónica {canonica!r} apunta a la bandera "
                f"{local!r}, que ninguna decisión de esta aventura enciende",
            )
    importa = crudo.get("importa", [])
    if not isinstance(importa, list) or any(not isinstance(c, str) for c in importa):
        raise _mal(origen, "legado.importa debe ser una lista de banderas canónicas")
    texto_fama = crudo.get("texto_fama")
    if texto_fama is not None and not isinstance(texto_fama, str):
        raise _mal(origen, "legado.texto_fama debe ser texto")
    heroe = crudo.get("heroe", False)
    if not isinstance(heroe, bool):
        raise _mal(origen, "legado.heroe debe ser true o false")
    return Legado(
        exporta=dict(exporta),
        importa=list(importa),
        texto_fama=texto_fama,
        heroe=heroe,
    )


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


def _secretos(datos: dict, origen: str) -> dict[str, Secreto]:
    crudos = datos.get("secretos")
    if crudos is None:
        return {}
    if not isinstance(crudos, dict):
        raise _mal(origen, "el campo 'secretos' debe ser un objeto o null")
    resultado: dict[str, Secreto] = {}
    for clave, sec in crudos.items():
        po = f"secretos[{clave!r}]"
        if not isinstance(sec, dict):
            raise _mal(origen, f"{po} debe ser un objeto")
        comando = sec.get("comando", clave)
        if not isinstance(comando, str) or not comando:
            raise _mal(origen, f"{po}.comando debe ser texto no vacío")
        textos_raw = sec.get("textos")
        if isinstance(textos_raw, str):
            textos = [textos_raw] if textos_raw else []
        elif isinstance(textos_raw, list):
            textos = textos_raw
        else:
            raise _mal(origen, f"{po}.textos debe ser texto o una lista no vacía de textos")
        if not textos or any(not isinstance(t, str) or not t for t in textos):
            raise _mal(origen, f"{po}.textos debe ser texto o una lista no vacía de textos")

        texto_combate = sec.get("texto_combate")
        if texto_combate is not None and (not isinstance(texto_combate, str) or not texto_combate):
            raise _mal(origen, f"{po}.texto_combate debe ser texto o null")

        semillas_raw = sec.get("semillas", {})
        if not isinstance(semillas_raw, dict):
            raise _mal(origen, f"{po}.semillas debe ser un objeto")
        semillas: dict[int, str] = {}
        for s_k, s_v in semillas_raw.items():
            try:
                s_int = int(s_k)
            except (ValueError, TypeError):
                raise _mal(origen, f"{po}.semillas: la clave {s_k!r} debe representar un número entero")
            if not isinstance(s_v, str) or not s_v:
                raise _mal(origen, f"{po}.semillas[{s_k!r}] debe ser texto no vacío")
            semillas[s_int] = s_v

        alias_raw = sec.get("alias", [])
        if not isinstance(alias_raw, list) or any(not isinstance(a, str) or not a for a in alias_raw):
            raise _mal(origen, f"{po}.alias debe ser una lista de textos")

        resultado[clave] = Secreto(
            comando=comando,
            textos=textos,
            texto_combate=texto_combate,
            semillas=semillas,
            alias=alias_raw,
        )
    return resultado


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
        for dialogo in lugar.npcs.values():
            if dialogo not in av.dialogos:
                raise _mal(origen, f"lugares[{lid!r}]: el diálogo {dialogo!r} no existe en dialogos")
        for clave_evento in lugar.eventos:
            if clave_evento not in av.eventos:
                raise _mal(origen, f"lugares[{lid!r}]: el evento {clave_evento!r} no existe en eventos")
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

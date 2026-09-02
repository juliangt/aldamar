"""El catálogo de los dones de héroe: datos en `rasgos.json`, no código.

Cada rasgo declara su nombre, su descripción y su efecto mecánico con
un vocabulario de modificadores genéricos; el motor (`juego.py`) suma
los de los dones del héroe y los aplica por un único camino, sin saber
nada de ningún don en concreto. Sumar un don que reutilice el
vocabulario = una entrada nueva en `rasgos.json` (cero Python).

El vocabulario de efectos:
- "dano_extra": daño extra en cada golpe del héroe.
- "dano_recibido_menos": puntos que se restan de cada golpe recibido.
- "descuento_compra": monedas menos en cada compra (el precio nunca
  baja de 1).
- "condicion": opcional, para todo el efecto; por ahora solo
  "vida_enemigo_mayor_que" (porcentaje de la vida_max del enemigo: el
  efecto alcanza mientras la supere).

Si un don futuro necesita una mecánica que el vocabulario no alcanza,
se extiende el vocabulario de forma genérica —un campo nuevo aquí y su
interpretación en el motor—, nunca con conocimiento de un don concreto.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources

# Los modificadores que el motor sabe aplicar, con la condición opcional
# aparte: el nombre de todo campo fuera de estos es un error del JSON.
MODIFICADORES = ("dano_extra", "dano_recibido_menos", "descuento_compra")
CONDICIONES = ("vida_enemigo_mayor_que",)


@dataclass(frozen=True)
class Rasgo:
    """Un don declarado en `rasgos.json`.

    Los modificadores valen 0 cuando el don no los usa;
    `cond_vida_enemigo` es el porcentaje de vida_max del enemigo por
    encima del cual aplica su efecto (None = siempre).
    """

    clave: str
    nombre: str
    descripcion: str
    dano_extra: int = 0
    dano_recibido_menos: int = 0
    descuento_compra: int = 0
    cond_vida_enemigo: int | None = None


def _mal(origen: str, problema: str) -> ValueError:
    return ValueError(f"{origen}: {problema}")


def _entero(pos: str, valor: object) -> int:
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise _mal("rasgos.json", f"{pos}: debe ser entero (llegó {type(valor).__name__})")
    return valor


def _efecto(clave: str, ficha: dict) -> tuple[int, int, int, int | None]:
    """Lee el objeto `efecto` y devuelve (extra, menos, descuento, condición)."""
    crudo = ficha.get("efecto")
    if crudo is None:
        return 0, 0, 0, None
    po = f"{clave!r}.efecto"
    if not isinstance(crudo, dict):
        raise _mal("rasgos.json", f"{po}: debe ser un objeto")
    desconocidos = [c for c in crudo if c not in MODIFICADORES and c != "condicion"]
    if desconocidos:
        raise _mal(
            "rasgos.json",
            f"{po}: campos de efecto desconocidos: {', '.join(desconocidos)}; "
            f"válidos: {', '.join((*MODIFICADORES, 'condicion'))}",
        )
    valores = []
    for campo in MODIFICADORES:
        if campo not in crudo:
            valores.append(0)
            continue
        valor = _entero(f"{po}: {campo!r}", crudo[campo])
        if valor <= 0:
            raise _mal("rasgos.json", f"{po}: {campo!r} debe ser mayor a cero")
        valores.append(valor)
    if "condicion" in crudo and not any(valores):
        raise _mal("rasgos.json", f"{po}: declara 'condicion' pero ningún efecto al que aplicarla")
    condicion = crudo.get("condicion")
    if condicion is None:
        return *valores, None
    pc = f"{po}.condicion"
    if not isinstance(condicion, dict):
        raise _mal("rasgos.json", f"{pc}: debe ser un objeto")
    desconocidas = [c for c in condicion if c not in CONDICIONES]
    if desconocidas:
        raise _mal(
            "rasgos.json",
            f"{pc}: condiciones desconocidas: {', '.join(desconocidas)}; "
            f"válidas: {', '.join(CONDICIONES)}",
        )
    umbral = _entero(f"{pc}: 'vida_enemigo_mayor_que'", condicion.get("vida_enemigo_mayor_que"))
    if not 1 <= umbral <= 99:
        raise _mal(
            "rasgos.json", f"{pc}: 'vida_enemigo_mayor_que' debe ser un porcentaje entre 1 y 99"
        )
    return *valores, umbral


def cargar_rasgos(datos: object, origen: str = "rasgos.json") -> dict[str, Rasgo]:
    """Valida los datos de `rasgos.json` y arma el catálogo."""
    if not isinstance(datos, dict):
        raise _mal(origen, "la raíz del archivo debe ser un objeto JSON")
    catalogo: dict[str, Rasgo] = {}
    for clave, ficha in datos.items():
        po = f"{clave!r}"
        if not isinstance(ficha, dict):
            raise _mal(origen, f"{po} debe ser un objeto")
        nombre = ficha.get("nombre")
        descripcion = ficha.get("descripcion")
        if not isinstance(nombre, str) or not nombre.strip():
            raise _mal(origen, f"{po}: falta el campo 'nombre' (debe ser texto)")
        if not isinstance(descripcion, str) or not descripcion.strip():
            raise _mal(origen, f"{po}: falta el campo 'descripcion' (debe ser texto)")
        extra, menos, descuento, condicion = _efecto(clave, ficha)
        catalogo[clave] = Rasgo(
            clave=clave,
            nombre=nombre,
            descripcion=descripcion,
            dano_extra=extra,
            dano_recibido_menos=menos,
            descuento_compra=descuento,
            cond_vida_enemigo=condicion,
        )
    return catalogo


def cargar_catalogo() -> dict[str, Rasgo]:
    """Lee el `rasgos.json` del paquete; el catálogo vivo del juego."""
    texto = resources.files("aldamar").joinpath("rasgos.json").read_text(encoding="utf-8")
    return cargar_rasgos(json.loads(texto), "rasgos.json")


# El catálogo con el que juegan el cargador (valida las claves que las
# fichas de héroe referencian) y el motor (aplica sus efectos).
RASGOS: dict[str, Rasgo] = cargar_catalogo()

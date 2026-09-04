"""Dificultades: perfiles de balance que se aplican sin tocar el motor.

Una Dificultad es solo un juego de multiplicadores sobre el balance con
el que se escribió el contenido de cada aventura (1.0 = tal cual). El
catálogo vive en `datos/dificultades.json` —esta dataclass es solo su
representación interna—: sumar una dificultad nueva = agregar una
entrada al JSON, y el menú y la CLI (`--dificultad`) la listan solas.

El formato del archivo: un objeto con `por_defecto` (la clave con la
que juega quien no elige) y `dificultades` (los perfiles, con la clave
como nombre del objeto, como en `rasgos.json`). Cada perfil declara
`nombre`, `descripcion`, los multiplicadores que quiera (los que
faltan valen 1.0) y una `nota` opcional para el porqué del balance. El
orden del menú es el del archivo. Ante un JSON roto, el error nombra
archivo y campo, como siempre.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources

# Los multiplicadores que el motor sabe aplicar (el campo de más en el
# JSON es un error, como en rasgos.json).
MULTIPLICADORES = (
    "vida_jugador",
    "ataque_jugador",
    "monedas",
    "vida_enemigos",
    "ataque_enemigos",
    "corrupcion",
    "curacion",
    "experiencia",
)


@dataclass(frozen=True)
class Dificultad:
    clave: str
    nombre: str
    descripcion: str
    nota: str | None = None  # el porqué del balance, para quien edite el JSON
    vida_jugador: float = 1.0
    ataque_jugador: float = 1.0
    monedas: float = 1.0
    vida_enemigos: float = 1.0
    ataque_enemigos: float = 1.0
    corrupcion: float = 1.0
    curacion: float = 1.0
    experiencia: float = 1.0


def _mal(origen: str, problema: str) -> ValueError:
    return ValueError(f"{origen}: {problema}")


def _numero(pos: str, valor: object) -> float:
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise _mal("dificultades.json", f"{pos}: debe ser un número (llegó {type(valor).__name__})")
    if valor <= 0:
        raise _mal("dificultades.json", f"{pos}: debe ser mayor a cero")
    return float(valor)


def cargar_dificultades(
    datos: object, origen: str = "dificultades.json"
) -> tuple[dict[str, Dificultad], str]:
    """Valida los datos de `dificultades.json` y arma (catálogo, por defecto)."""
    if not isinstance(datos, dict):
        raise _mal(origen, "la raíz del archivo debe ser un objeto JSON")
    desconocidos = [c for c in datos if c not in ("por_defecto", "dificultades")]
    if desconocidos:
        raise _mal(
            origen,
            f"campos desconocidos: {', '.join(desconocidos)}; "
            f"válidos: 'por_defecto' y 'dificultades'",
        )
    perfiles = datos.get("dificultades")
    if not isinstance(perfiles, dict) or not perfiles:
        raise _mal(origen, "el campo 'dificultades' debe ser un objeto con al menos un perfil")
    catalogo: dict[str, Dificultad] = {}
    for clave, ficha in perfiles.items():
        po = f"{clave!r}"
        if not isinstance(ficha, dict):
            raise _mal(origen, f"{po} debe ser un objeto")
        nombre = ficha.get("nombre")
        descripcion = ficha.get("descripcion")
        if not isinstance(nombre, str) or not nombre.strip():
            raise _mal(origen, f"{po}: falta el campo 'nombre' (debe ser texto)")
        if not isinstance(descripcion, str) or not descripcion.strip():
            raise _mal(origen, f"{po}: falta el campo 'descripcion' (debe ser texto)")
        nota = ficha.get("nota")
        if nota is not None and not isinstance(nota, str):
            raise _mal(origen, f"{po}: el campo 'nota' debe ser texto o null")
        valores = {campo: 1.0 for campo in MULTIPLICADORES}
        for campo, valor in ficha.items():
            if campo in ("nombre", "descripcion", "nota"):
                continue
            if campo not in MULTIPLICADORES:
                raise _mal(
                    origen,
                    f"{po}: multiplicador desconocido {campo!r}; "
                    f"válidos: {', '.join(MULTIPLICADORES)}",
                )
            valores[campo] = _numero(f"{po}: {campo!r}", valor)
        catalogo[clave] = Dificultad(
            clave=clave,
            nombre=nombre,
            descripcion=descripcion,
            nota=nota,
            **valores,
        )
    por_defecto = datos.get("por_defecto")
    if not isinstance(por_defecto, str) or not por_defecto:
        raise _mal(origen, "falta el campo 'por_defecto' (debe ser la clave de un perfil)")
    if por_defecto not in catalogo:
        raise _mal(
            origen,
            f"'por_defecto' apunta a {por_defecto!r}, que no está en 'dificultades'; "
            f"válidas: {', '.join(catalogo)}",
        )
    return catalogo, por_defecto


def cargar_catalogo() -> tuple[dict[str, Dificultad], str]:
    """Lee el `dificultades.json` de `aldamar.datos`; el catálogo vivo del juego."""
    texto = (
        resources.files("aldamar").joinpath("datos", "dificultades.json").read_text(encoding="utf-8")
    )
    try:
        datos = json.loads(texto)
    except json.JSONDecodeError as e:
        raise _mal("dificultades.json", f"no es JSON válido: {e}") from e
    return cargar_dificultades(datos)


def ajusta(valor: int, multiplicador: float) -> int:
    """Escala un valor de balance y lo devuelve como entero razonable."""
    return max(1, round(valor * multiplicador))


def obtener_dificultad(clave: str | None = None) -> Dificultad:
    """Resuelve una dificultad por clave; None devuelve la por defecto."""
    if clave is None:
        clave = DIFICULTAD_POR_DEFECTO
    if clave not in DIFICULTADES:
        raise KeyError(
            f"No existe la dificultad {clave!r}; válidas: {', '.join(DIFICULTADES)}"
        )
    return DIFICULTADES[clave]


# El catálogo con el que juegan el menú (el orden del archivo), la CLI
# (`--dificultad`) y el motor (crear_jugador / crear_enemigo / ajusta).
DIFICULTADES, DIFICULTAD_POR_DEFECTO = cargar_catalogo()

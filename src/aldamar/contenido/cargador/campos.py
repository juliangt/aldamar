"""Primitivas de validación de los JSON de aventura.

Cada campo del contrato se lee por aquí: las funciones exigen el tipo
declarado y, ante la culpa, lanzan `AventuraInvalida` que nombra el
archivo y el campo (`origen`, `donde`).
"""

from __future__ import annotations

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


def _entero_opcional(datos: dict, campo: str, donde: str) -> int | None:
    valor = datos.get(campo)
    if valor is None:
        return None
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise _mal(donde, f"el campo {campo!r} debe ser entero o null (llegó {type(valor).__name__})")
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


def _dialogos(datos: dict, origen: str) -> dict[str, str | list[str]]:
    crudos = _diccionario(datos, "dialogos", origen)
    for clave, v in crudos.items():
        po = f"dialogos[{clave!r}]"
        if isinstance(v, str):
            if not v:
                raise _mal(origen, f"{po} no puede ser un texto vacío")
        elif isinstance(v, list):
            if not v or any(not isinstance(item, str) or not item for item in v):
                raise _mal(origen, f"{po} debe ser un texto o una lista no vacía de textos")
        else:
            raise _mal(origen, f"{po} debe ser un texto o una lista de textos (llegó {type(v).__name__})")
    return crudos

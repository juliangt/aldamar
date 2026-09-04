"""El cronista: cliente del modelo local (Ollama) con la biblioteca estándar.

El modo «Aventura Viva» (issue 22) habla con un Ollama en la propia
máquina: `urllib` de stdlib, cero dependencias y cero red — el único
hospedaje es localhost (u `OLLAMA_HOST`). `Proveedor` es la costura para
los tests: `ProveedorFalso` responde enlatado y en CI jamás se llama a
un modelo real.

Dos detalles que no son negociables:

- `num_ctx` se fija siempre en `options`: el default de Ollama (2048)
  trunca el canon en silencio.
- Todo fallo de red, HTTP o JSON se traduce a `CronistaError`: quien
  llama (la sesión) decide degradar a plantilla; nunca hay traceback.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections.abc import Callable
from http.client import HTTPResponse
from typing import Protocol

HOSPEDAJE_DEFECTO = "http://127.0.0.1:11434"
TIMEOUT_DETECTAR = 1.0
TIMEOUT_GENERAR = 300.0
NUM_CTX_DEFECTO = 16384  # el default de Ollama (2048) trunca el canon en silencio

# El streaming de prosa (token a token) llega por aquí, trozo a trozo.
EnStreaming = Callable[[str], None]


class CronistaError(RuntimeError):
    """El modelo local no respondió, o respondió basura."""


class Proveedor(Protocol):
    """Lo que la sesión le pide a un modelo; Ollama y el falso la cumplen."""

    modelo: str
    hospedaje: str

    def disponible(self) -> bool: ...

    def modelos(self) -> list[str]: ...

    def generar(
        self,
        sistema: str,
        prompt: str,
        *,
        temperatura: float = 0.9,
        stream_en: EnStreaming | None = None,
        num_predict: int | None = None,
    ) -> str: ...

    def generar_json(
        self, sistema: str, prompt: str, schema: dict, *, num_predict: int | None = None
    ) -> dict: ...


def hospedaje_por_defecto() -> str:
    """El hospedaje del modelo: `OLLAMA_HOST` si existe, o el local de siempre."""
    bruto = os.environ.get("OLLAMA_HOST", "").strip()
    if not bruto:
        return HOSPEDAJE_DEFECTO
    if "://" not in bruto:  # OLLAMA_HOST admite «localhost:11434» a secas
        bruto = "http://" + bruto
    return bruto


class Ollama:
    """El proveedor real: `POST /api/generate` contra un Ollama local."""

    def __init__(
        self,
        modelo: str,
        hospedaje: str | None = None,
        num_ctx: int = NUM_CTX_DEFECTO,
    ) -> None:
        self.modelo = modelo
        self.hospedaje = hospedaje or hospedaje_por_defecto()
        self.num_ctx = num_ctx
        self._capacidades: dict[str, list[str]] | None = None

    def __repr__(self) -> str:  # para el informe de la sesión, sin sorpresas
        return f"Ollama({self.modelo!r} en {self.hospedaje})"

    def disponible(self) -> bool:
        try:
            with urllib.request.urlopen(
                self.hospedaje + "/api/tags", timeout=TIMEOUT_DETECTAR
            ) as respuesta:
                respuesta.read()
            return True
        except (urllib.error.URLError, OSError):
            return False

    def _tags(self) -> dict:
        """El catálogo de `/api/tags`, o vacío si no hay servicio."""
        try:
            with urllib.request.urlopen(
                self.hospedaje + "/api/tags", timeout=TIMEOUT_DETECTAR
            ) as respuesta:
                datos = json.loads(respuesta.read())
        except (urllib.error.URLError, OSError, json.JSONDecodeError):
            return {}
        return datos if isinstance(datos, dict) else {}

    def modelos(self) -> list[str]:
        """Los nombres instalados (`ollama list`); vacío si no hay servicio."""
        return [
            m["name"]
            for m in self._tags().get("models", [])
            if isinstance(m, dict) and isinstance(m.get("name"), str) and m["name"]
        ]

    def _piensa(self) -> bool:
        """¿El modelo razona en voz alta (qwen3 y compañía)?

        Los modelos «thinking» gastan el presupuesto en monólogo interior
        que aquí no queremos (y con structured outputs se atascan y
        responden vacío): si el propio Ollama declara la capacidad,
        les pedimos que no piensen (`think: false`). Se mira una sola
        vez por cliente.
        """
        if self._capacidades is None:
            self._capacidades = {
                m.get("name", ""): [str(c) for c in m.get("capabilities", []) or []]
                for m in self._tags().get("models", [])
                if isinstance(m, dict)
            }
        return "thinking" in self._capacidades.get(self.modelo, ())

    def generar(
        self,
        sistema: str,
        prompt: str,
        *,
        temperatura: float = 0.9,
        stream_en: EnStreaming | None = None,
        num_predict: int | None = None,
    ) -> str:
        """Prosa del modelo; con `stream_en`, token a token mientras llega.

        `num_predict` acota la generación (un modelo pequeño que divaga
        puede irse minutos); None usa el default del servidor.
        """
        opciones = {"num_ctx": self.num_ctx, "temperature": temperatura}
        if num_predict is not None:
            opciones["num_predict"] = num_predict
        carga: dict = {
            "model": self.modelo,
            "system": sistema,
            "prompt": prompt,
            "stream": stream_en is not None,
            "options": opciones,
        }
        if self._piensa():
            carga["think"] = False  # la prosa no necesita monólogo interior
        trozos: list[str] = []
        with self._post(carga) as respuesta:
            for linea in respuesta:
                if not linea.strip():
                    continue
                try:
                    pieza = json.loads(linea)
                except json.JSONDecodeError as e:
                    raise CronistaError(f"el modelo devolvió basura: {e}") from e
                if "error" in pieza:
                    raise CronistaError(f"el modelo devolvió un error: {pieza['error']}")
                trozo = pieza.get("response", "")
                if trozo:
                    trozos.append(trozo)
                    if stream_en is not None:
                        stream_en(trozo)
        return "".join(trozos)

    def generar_json(
        self, sistema: str, prompt: str, schema: dict, *, num_predict: int | None = None
    ) -> dict:
        """JSON del modelo forzado con structured outputs (`format` = schema)."""
        opciones = {"num_ctx": self.num_ctx, "temperature": 0.7}
        if num_predict is not None:
            opciones["num_predict"] = num_predict
        carga: dict = {
            "model": self.modelo,
            "system": sistema,
            "prompt": prompt,
            "stream": False,
            "format": schema,
            "options": opciones,
        }
        if self._piensa():
            carga["think"] = False  # y el JSON, mucho menos
        with self._post(carga) as respuesta:
            texto = respuesta.read().decode("utf-8")
        try:
            pieza = json.loads(texto)
        except json.JSONDecodeError as e:
            raise CronistaError(f"el modelo no devolvió JSON: {e}") from e
        if "error" in pieza:
            raise CronistaError(f"el modelo devolvió un error: {pieza['error']}")
        datos = pieza.get("response", "")
        try:
            resultado = json.loads(datos)
        except json.JSONDecodeError as e:
            raise CronistaError(f"el modelo no devolvió JSON válido: {e}") from e
        if not isinstance(resultado, dict):
            raise CronistaError("el modelo no devolvió un objeto JSON")
        return resultado

    def _post(self, carga: dict) -> HTTPResponse:
        """El POST de `/api/generate`, como contexto de lectura."""
        pedido = urllib.request.Request(
            self.hospedaje.rstrip("/") + "/api/generate",
            data=json.dumps(carga).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            return urllib.request.urlopen(pedido, timeout=TIMEOUT_GENERAR)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise CronistaError(f"el modelo no respondió: {e}") from e


class ProveedorFalso:
    """Respuestas enlatadas, para los tests (CI jamás llama a un modelo real).

    Cada llamada consume la siguiente respuesta de la cola — prosa para
    `generar`, dict para `generar_json` — y queda grabada en `pedidos`
    (el bucle de reparación se prueba mirando qué se le devolvió al
    modelo). Agotada la cola, `CronistaError`: la sesión debe degradar
    a plantilla, y el test lo comprueba.
    """

    def __init__(
        self,
        respuestas: list[str | dict],
        *,
        disponible: bool = True,
        instalados: list[str] | None = None,
    ) -> None:
        self.respuestas = list(respuestas)
        self._disponible = disponible
        self.modelo = "proveedor-falso"
        self.hospedaje = "http://127.0.0.1:9"
        self.pedidos: list[str] = []
        self.instalados = instalados if instalados is not None else ["proveedor-falso"]

    def disponible(self) -> bool:
        return self._disponible

    def modelos(self) -> list[str]:
        return list(self.instalados)

    def generar(
        self,
        sistema: str,
        prompt: str,
        *,
        temperatura: float = 0.9,
        stream_en: EnStreaming | None = None,
        num_predict: int | None = None,
    ) -> str:
        self.pedidos.append(prompt)
        respuesta = self._siguiente()
        if not isinstance(respuesta, str):
            raise CronistaError("el proveedor falso tenía un JSON donde tocaba prosa")
        return respuesta

    def generar_json(
        self, sistema: str, prompt: str, schema: dict, *, num_predict: int | None = None
    ) -> dict:
        self.pedidos.append(prompt)
        respuesta = self._siguiente()
        if not isinstance(respuesta, dict):
            raise CronistaError("el proveedor falso tenía prosa donde tocaba JSON")
        return respuesta

    def _siguiente(self) -> str | dict:
        if not self.respuestas:
            raise CronistaError("el proveedor falso se quedó sin respuestas")
        return self.respuestas.pop(0)


def modelo_fijado() -> str:
    """El modelo que el jugador fijó, o vacío si dejó que se eligiera solo.

    La precedencia de siempre del juego: `ALDAMAR_MODELO` en el entorno
    y, si no, `modelo_viva` en `configuracion.json`.
    """
    from ..motor import configuracion

    return (
        os.environ.get("ALDAMAR_MODELO", "").strip()
        or (configuracion.cargar().modelo_viva or "").strip()
    )


def proveedor_por_defecto() -> Proveedor:
    """El proveedor del jugador: el fijado, o el primero que haya instalado.

    Si no hay Ollama, el proveedor que sale de aquí simplemente no está
    `disponible()`: la interfaz explica cómo activarlo y nada se rompe.
    El contexto (`num_ctx`) sale de `contexto_viva` en configuracion.json:
    el default de 16384 es el seguro, pero en máquinas sin GPU bajarlo
    (p. ej. 8192) alivia mucho la generación.
    """
    from ..motor import configuracion

    modelo = modelo_fijado()
    if not modelo:
        instalados = Ollama(modelo="").modelos()
        modelo = instalados[0] if instalados else ""
    contexto = configuracion.cargar().contexto_viva
    num_ctx = (
        contexto
        if isinstance(contexto, int) and not isinstance(contexto, bool)
        else NUM_CTX_DEFECTO
    )
    return Ollama(modelo=modelo, num_ctx=num_ctx)

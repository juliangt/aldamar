"""El cronista: el cliente del modelo, con la biblioteca estándar.

El modo «Aventura Viva» habla con un cronista local (Ollama en la
propia máquina, u `OLLAMA_HOST`) o externo (cualquier API con el
protocolo de OpenAI: `viva_host` + `viva_api_key`). En ambos casos:
`urllib` de stdlib, cero dependencias. `Proveedor` es la costura para
los tests: `ProveedorFalso` responde enlatado y en CI jamás se llama a
un modelo real.

Dos detalles que no son negociables:

- En Ollama, `num_ctx` se fija siempre en `options`: el default (2048)
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


class ApiCompatible:
    """El cronista externo: cualquier servidor con el protocolo de OpenAI.

    `/chat/completions` y `/models` con `Authorization: Bearer` cubren
    OpenAI, OpenRouter, Groq, Mistral, LM Studio, vLLM… El JSON va con
    `response_format: json_object` y el schema dentro del prompt (no
    todos los compatibles aceptan `json_schema`); si el servidor
    rechaza `response_format`, se deja de mandar. El contexto lo
    gestiona el servidor: `num_ctx` aquí no aplica.
    """

    def __init__(self, modelo: str, hospedaje: str = "", api_key: str = "") -> None:
        self.modelo = modelo
        self.hospedaje = (hospedaje or "").rstrip("/")
        self.api_key = api_key
        self._sin_response_format = False  # ya nos dijo que no lo quiere

    def __repr__(self) -> str:  # para el informe de la sesión, sin la clave
        return f"ApiCompatible({self.modelo!r} en {self.hospedaje})"

    def _cabeceras(self) -> dict:
        cabeceras = {"Content-Type": "application/json"}
        if self.api_key:
            cabeceras["Authorization"] = f"Bearer {self.api_key}"
        return cabeceras

    def disponible(self) -> bool:
        """¿Hay servicio? Clave rechazada cuenta como no (es config rota)."""
        if not self.hospedaje:
            return False
        try:
            with urllib.request.urlopen(
                urllib.request.Request(self.hospedaje + "/models", headers=self._cabeceras()),
                timeout=TIMEOUT_DETECTAR,
            ) as respuesta:
                respuesta.read()
            return True
        except urllib.error.HTTPError as e:
            return e.code not in (401, 403)
        except (urllib.error.URLError, OSError):
            return False

    def modelos(self) -> list[str]:
        """Los nombres que el servidor lista en `/models`; vacío si no hay."""
        if not self.hospedaje:
            return []
        try:
            with urllib.request.urlopen(
                urllib.request.Request(self.hospedaje + "/models", headers=self._cabeceras()),
                timeout=TIMEOUT_DETECTAR,
            ) as respuesta:
                datos = json.loads(respuesta.read())
        except (urllib.error.URLError, urllib.error.HTTPError, OSError, json.JSONDecodeError):
            return []
        if not isinstance(datos, dict):
            return []
        return [
            m["id"]
            for m in datos.get("data", [])
            if isinstance(m, dict) and isinstance(m.get("id"), str) and m["id"]
        ]

    def generar(
        self,
        sistema: str,
        prompt: str,
        *,
        temperatura: float = 0.9,
        stream_en: EnStreaming | None = None,
        num_predict: int | None = None,
    ) -> str:
        """Prosa del modelo por `/chat/completions`; con `stream_en`, SSE."""
        carga: dict = {
            "model": self.modelo,
            "messages": [
                {"role": "system", "content": sistema},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperatura,
            "stream": stream_en is not None,
        }
        if num_predict is not None:
            carga["max_tokens"] = num_predict
        trozos: list[str] = []
        with self._post(carga) as respuesta:
            if stream_en is None:
                trozos.append(self._contenido(json.loads(respuesta.read().decode("utf-8"))))
            else:
                for linea in respuesta:
                    pieza = linea.decode("utf-8").strip()
                    if not pieza.startswith("data:"):
                        continue
                    pieza = pieza[5:].strip()
                    if pieza == "[DONE]":
                        break
                    try:
                        trozo = self._delta(json.loads(pieza))
                    except json.JSONDecodeError as e:
                        raise CronistaError(f"el modelo devolvió basura: {e}") from e
                    if trozo:
                        trozos.append(trozo)
                        stream_en(trozo)
        return "".join(trozos)

    def generar_json(
        self, sistema: str, prompt: str, schema: dict, *, num_predict: int | None = None
    ) -> dict:
        """JSON del modelo: `response_format` si el servidor lo acepta.

        El schema viaja dentro del prompt: con que el servidor respete
        el `json_object` basta, y el bucle de reparación de la sesión
        cubre lo demás.
        """
        carga: dict = {
            "model": self.modelo,
            "messages": [
                {"role": "system", "content": sistema},
                {
                    "role": "user",
                    "content": (
                        prompt
                        + "\n\nEl objeto debe cumplir exactamente este esquema JSON:\n"
                        + json.dumps(schema, ensure_ascii=False)
                    ),
                },
            ],
            "temperature": 0.7,
            "stream": False,
        }
        if num_predict is not None:
            carga["max_tokens"] = num_predict
        if not self._sin_response_format:
            carga["response_format"] = {"type": "json_object"}
        try:
            with self._post(carga) as respuesta:
                texto = self._contenido(json.loads(respuesta.read().decode("utf-8")))
        except CronistaError:
            if self._sin_response_format or "response_format" not in carga:
                raise
            self._sin_response_format = True  # este servidor no lo quiere
            del carga["response_format"]
            with self._post(carga) as respuesta:
                texto = self._contenido(json.loads(respuesta.read().decode("utf-8")))
        if not texto:
            raise CronistaError("el modelo devolvió una respuesta vacía")
        try:
            resultado = json.loads(texto)
        except json.JSONDecodeError as e:
            raise CronistaError(f"el modelo no devolvió JSON válido: {e}") from e
        if not isinstance(resultado, dict):
            raise CronistaError("el modelo no devolvió un objeto JSON")
        return resultado

    @staticmethod
    def _contenido(respuesta: dict) -> str:
        """El texto de la respuesta de chat, o CronistaError con culpa."""
        if "error" in respuesta:
            raise CronistaError(f"el modelo devolvió un error: {respuesta['error']}")
        try:
            contenido = respuesta["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise CronistaError(f"respuesta de chat sin contenido: {e}") from e
        return contenido or ""

    @staticmethod
    def _delta(pieza: dict) -> str:
        """El trozo de texto de un evento SSE de streaming."""
        try:
            return pieza["choices"][0]["delta"].get("content") or ""
        except (KeyError, IndexError, TypeError):
            return ""

    def _post(self, carga: dict) -> HTTPResponse:
        """El POST de `/chat/completions`, como contexto de lectura."""
        pedido = urllib.request.Request(
            self.hospedaje + "/chat/completions",
            data=json.dumps(carga).encode("utf-8"),
            headers=self._cabeceras(),
        )
        try:
            return urllib.request.urlopen(pedido, timeout=TIMEOUT_GENERAR)
        except urllib.error.HTTPError as e:
            try:
                detalle = e.read()[:200].decode("utf-8", errors="replace").strip()
            except OSError:
                detalle = ""
            raise _HttpError(f"el servidor rechazó el pedido (HTTP {e.code}): {detalle}") from e
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise CronistaError(f"el modelo no respondió: {e}") from e


class _HttpError(CronistaError):
    """Un 4xx/5xx del servidor. A quien llama le llega como el
    CronistaError de siempre; la clase solo distingue el caso para el
    reintento sin `response_format`."""


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


def host_fijado() -> str:
    """El servidor del cronista, o vacío si va por su sitio de siempre.

    `ALDAMAR_HOST` en el entorno y, si no, `viva_host` en
    configuracion.json. Para el Ollama local basta `OLLAMA_HOST` (o
    nada); para una API externa, la base del servidor
    («https://api.openai.com/v1», con su `/v1` incluido).
    """
    from ..motor import configuracion

    return (
        os.environ.get("ALDAMAR_HOST", "").strip()
        or (configuracion.cargar().viva_host or "").strip()
    )


def clave_fijada() -> str:
    """La clave del cronista externo, o vacía si no hace falta.

    `ALDAMAR_API_KEY` en el entorno y, si no, `viva_api_key` en
    configuracion.json — donde queda en claro, así que para secretos de
    verdad manda la variable de entorno.
    """
    from ..motor import configuracion

    return (
        os.environ.get("ALDAMAR_API_KEY", "").strip()
        or (configuracion.cargar().viva_api_key or "").strip()
    )


def proveedor_fijado() -> str:
    """«ollama» o «api»: el tipo de cronista que el jugador pidió.

    `ALDAMAR_PROVEEDOR` en el entorno y, si no, `viva_proveedor` en
    configuracion.json. Si nadie fijó nada, se infiere: hay clave de
    API → «api»; si no, el Ollama local de toda la vida.
    """
    from ..motor import configuracion

    fijado = (
        os.environ.get("ALDAMAR_PROVEEDOR", "").strip().lower()
        or (configuracion.cargar().viva_proveedor or "").strip().lower()
    )
    if fijado in ("ollama", "api"):
        return fijado
    return "api" if clave_fijada() else "ollama"


def hospedaje_por_defecto() -> str:
    """El hospedaje del Ollama: `ALDAMAR_HOST` > `viva_host` >
    `OLLAMA_HOST` > el local de siempre (`http://127.0.0.1:11434`)."""
    bruto = host_fijado() or os.environ.get("OLLAMA_HOST", "").strip()
    if not bruto:
        return HOSPEDAJE_DEFECTO
    if "://" not in bruto:  # OLLAMA_HOST admite «localhost:11434» a secas
        bruto = "http://" + bruto
    return bruto


def proveedor_por_defecto() -> Proveedor:
    """El proveedor del jugador: Ollama local o una API compatible.

    El tipo lo da `proveedor_fijado()`; el modelo, el fijado o el
    primero que el servidor liste. Si no hay servicio, el proveedor que
    sale de aquí simplemente no está `disponible()`: la interfaz
    explica cómo activarlo y nada se rompe. El contexto (`num_ctx`)
    sale de `contexto_viva` y solo importa en Ollama: el resto de
    servidores gestiona el suyo.
    """
    from ..motor import configuracion

    modelo = modelo_fijado()
    if proveedor_fijado() == "api":
        if not modelo:
            instalados = ApiCompatible(
                modelo="", hospedaje=host_fijado(), api_key=clave_fijada()
            ).modelos()
            modelo = instalados[0] if instalados else ""
        return ApiCompatible(modelo=modelo, hospedaje=host_fijado(), api_key=clave_fijada())
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

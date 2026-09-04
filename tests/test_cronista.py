"""El cronista contra un Ollama falso sobre HTTP local (stdlib, sin red real).

El servidor falso vive en un hilo del test, escucha en 127.0.0.1 en un
puerto efímero y responde lo que cada test le prepara: el cliente se
prueba de verdad — NDJSON, structured outputs, errores HTTP — pero en
CI jamás se llama a un modelo real.
"""

from __future__ import annotations

import http.server
import json
import socket
import threading

import pytest

from aldamar.motor import configuracion
from aldamar.viva import cronista


class _Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):  # silencio: los tests miran `srv.pedidos`
        pass

    def do_GET(self):
        estado, cuerpo = self.server.respuestas.get(("GET", self.path), (200, b"{}"))
        self.send_response(estado)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_POST(self):
        largo = int(self.headers.get("Content-Length", 0))
        self.server.pedidos.append((self.path, json.loads(self.rfile.read(largo) or b"{}")))
        estado, cuerpo = self.server.respuestas.get(("POST", self.path), (200, b"{}"))
        self.send_response(estado)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(cuerpo)


class _Servidor(http.server.ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


@pytest.fixture
def servidor():
    srv = _Servidor(("127.0.0.1", 0), _Handler)
    srv.respuestas = {}
    srv.pedidos = []
    hilo = threading.Thread(target=srv.serve_forever, daemon=True)
    hilo.start()
    try:
        yield srv
    finally:
        srv.shutdown()
        srv.server_close()


def hospedaje(srv) -> str:
    return f"http://127.0.0.1:{srv.server_address[1]}"


def _puerto_apagado() -> str:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    puerto = s.getsockname()[1]
    s.close()
    return f"http://127.0.0.1:{puerto}"


def cliente(srv, modelo: str = "llama3.1:8b") -> cronista.Ollama:
    return cronista.Ollama(modelo=modelo, hospedaje=hospedaje(srv))


# ── detección y catálogo ─────────────────────────────────────────────────


def test_disponible_y_modelos_leen_api_tags(servidor):
    servidor.respuestas[("GET", "/api/tags")] = (
        200,
        json.dumps({"models": [{"name": "llama3.1:8b"}, {"name": "qwen2.5:7b"}]}).encode(),
    )
    assert cliente(servidor).disponible()
    assert cliente(servidor).modelos() == ["llama3.1:8b", "qwen2.5:7b"]


def test_sin_servicio_no_hay_disponibilidad_ni_modelos():
    apagado = _puerto_apagado()
    cliente_frio = cronista.Ollama(modelo="x", hospedaje=apagado)
    assert not cliente_frio.disponible()
    assert cliente_frio.modelos() == []


def test_tags_con_basura_da_lista_vacia_y_no_explota(servidor):
    servidor.respuestas[("GET", "/api/tags")] = (200, b"esto no es json")
    assert cliente(servidor).modelos() == []


# ── generar: prosa ───────────────────────────────────────────────────────


def test_generar_concatena_el_ndjson_y_fija_num_ctx(servidor):
    servidor.respuestas[("POST", "/api/generate")] = (
        200,
        b'{"response":"hola "}\n{"response":"mundo","done":true}\n',
    )
    assert cliente(servidor).generar("sistema", "prompt") == "hola mundo"
    ((ruta, carga),) = servidor.pedidos
    assert ruta == "/api/generate"
    assert carga["model"] == "llama3.1:8b"
    assert carga["system"] == "sistema" and carga["prompt"] == "prompt"
    assert carga["stream"] is False
    assert carga["options"]["num_ctx"] == 16384  # el truncado silencioso, evitado


def test_generar_en_stream_entrega_trozo_a_trozo(servidor):
    servidor.respuestas[("POST", "/api/generate")] = (
        200,
        b'{"response":"un "}\n{"response":"trozo "}\n{"response":"y otro"}\n',
    )
    trozos: list[str] = []
    texto = cliente(servidor).generar("s", "p", stream_en=trozos.append)
    assert texto == "un trozo y otro"
    assert trozos == ["un ", "trozo ", "y otro"]
    ((_, carga),) = servidor.pedidos
    assert carga["stream"] is True


def test_el_error_del_modelo_da_cronista_error(servidor):
    error = json.dumps({"error": "el modelo está resfriado"}, ensure_ascii=False).encode()
    servidor.respuestas[("POST", "/api/generate")] = (200, error)
    with pytest.raises(cronista.CronistaError) as captura:
        cliente(servidor).generar("s", "p")
    assert "resfriado" in str(captura.value)


def test_un_http_500_da_cronista_error(servidor):
    servidor.respuestas[("POST", "/api/generate")] = (500, b"{}")
    with pytest.raises(cronista.CronistaError):
        cliente(servidor).generar("s", "p")


def test_conexion_rechazada_da_cronista_error():
    with pytest.raises(cronista.CronistaError):
        cronista.Ollama(modelo="m", hospedaje=_puerto_apagado()).generar("s", "p")


# ── generar_json: structured outputs ─────────────────────────────────────


def test_generar_json_manda_el_schema_y_devuelve_el_objeto(servidor):
    servidor.respuestas[("POST", "/api/generate")] = (
        200,
        json.dumps({"response": json.dumps({"vida": 3, "nombre": "el eco"})}).encode(),
    )
    schema = {"type": "object", "properties": {"vida": {"type": "integer"}}}
    assert cliente(servidor).generar_json("s", "p", schema) == {"vida": 3, "nombre": "el eco"}
    ((_, carga),) = servidor.pedidos
    assert carga["format"] == schema


def test_generar_json_con_basura_da_cronista_error(servidor):
    servidor.respuestas[("POST", "/api/generate")] = (
        200,
        json.dumps({"response": "no soy json"}).encode(),
    )
    with pytest.raises(cronista.CronistaError):
        cliente(servidor).generar_json("s", "p", {})


def test_generar_json_con_algo_que_no_es_objeto_da_cronista_error(servidor):
    servidor.respuestas[("POST", "/api/generate")] = (
        200,
        json.dumps({"response": "[1, 2, 3]"}).encode(),
    )
    with pytest.raises(cronista.CronistaError):
        cliente(servidor).generar_json("s", "p", {})


# ── la configuración de hospedaje y modelo ───────────────────────────────


def test_el_hospedaje_honra_ollama_host(monkeypatch):
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    assert cronista.hospedaje_por_defecto() == "http://127.0.0.1:11434"
    monkeypatch.setenv("OLLAMA_HOST", "192.168.1.5:11434")
    assert cronista.hospedaje_por_defecto() == "http://192.168.1.5:11434"
    monkeypatch.setenv("OLLAMA_HOST", "http://casero:11434")
    assert cronista.hospedaje_por_defecto() == "http://casero:11434"


def test_el_modelo_fijado_viene_del_entorno_o_de_la_configuracion(monkeypatch, tmp_path):
    monkeypatch.delenv("ALDAMAR_MODELO", raising=False)
    monkeypatch.chdir(tmp_path)
    assert cronista.modelo_fijado() == ""
    config = configuracion.cargar()
    config.modelo_viva = "qwen2.5:7b"
    configuracion.guardar(config)
    assert cronista.modelo_fijado() == "qwen2.5:7b"
    monkeypatch.setenv("ALDAMAR_MODELO", "llama3.1:8b")
    assert cronista.modelo_fijado() == "llama3.1:8b"  # el entorno manda


def test_proveedor_por_defecto_honra_al_modelo_del_entorno(monkeypatch):
    monkeypatch.setenv("ALDAMAR_MODELO", "mifijo:8b")
    proveedor = cronista.proveedor_por_defecto()
    assert isinstance(proveedor, cronista.Ollama)
    assert proveedor.modelo == "mifijo:8b"


# ── el proveedor falso: el contrato de los tests ─────────────────────────


def test_el_proveedor_falso_graba_pedidos_y_se_agota_con_cronista_error():
    falso = cronista.ProveedorFalso(["prosa", {"vida": 1}])
    assert falso.disponible()
    assert falso.modelos() == ["proveedor-falso"]
    assert falso.generar("s", "el prompt uno") == "prosa"
    assert falso.generar_json("s", "el prompt dos", {}) == {"vida": 1}
    assert "el prompt uno" in falso.pedidos[0] and "el prompt dos" in falso.pedidos[1]
    with pytest.raises(cronista.CronistaError):
        falso.generar("s", "tercero")
    apagado = cronista.ProveedorFalso([], disponible=False)
    assert not apagado.disponible()


def test_el_proveedor_falso_protesta_si_el_tipo_no_es_el_esperado():
    with pytest.raises(cronista.CronistaError):
        cronista.ProveedorFalso([{"soy": "dict"}]).generar("s", "p")
    with pytest.raises(cronista.CronistaError):
        cronista.ProveedorFalso(["soy prosa"]).generar_json("s", "p", {})


def test_el_contexto_viva_sale_de_la_configuracion(monkeypatch, tmp_path):
    monkeypatch.setenv("ALDAMAR_MODELO", "mifijo:8b")
    monkeypatch.chdir(tmp_path)
    assert cronista.proveedor_por_defecto().num_ctx == cronista.NUM_CTX_DEFECTO
    config = configuracion.cargar()
    config.contexto_viva = 8192
    configuracion.guardar(config)
    assert cronista.proveedor_por_defecto().num_ctx == 8192


def test_el_presupuesto_de_tokens_viaja_en_las_opciones(servidor):
    servidor.respuestas[("POST", "/api/generate")] = (200, b'{"response":"poco"}\n')
    cliente = cronista.Ollama(modelo="m", hospedaje=hospedaje(servidor))
    assert cliente.generar("s", "p", num_predict=600) == "poco"
    ((_, carga),) = servidor.pedidos
    assert carga["options"]["num_predict"] == 600
    cliente.generar("s", "p")  # sin presupuesto: el default del servidor
    _, carga = servidor.pedidos[-1]
    assert "num_predict" not in carga["options"]


def test_un_modelo_thinking_se_le_pide_que_no_piense(servidor):
    """qwen3 y compañía: sin `think: false`, gastan el presupuesto en
    monólogo interior y devuelven respuestas vacías."""
    servidor.respuestas[("GET", "/api/tags")] = (
        200,
        json.dumps(
            {
                "models": [
                    {
                        "name": "qwen3.5:0.8b",
                        "capabilities": ["completion", "tools", "thinking"],
                    },
                    {"name": "llama3.1:8b", "capabilities": ["completion"]},
                ]
            }
        ).encode(),
    )
    servidor.respuestas[("POST", "/api/generate")] = (200, b'{"response":"ok"}\n')
    piensa = cronista.Ollama(modelo="qwen3.5:0.8b", hospedaje=hospedaje(servidor))
    calla = cronista.Ollama(modelo="llama3.1:8b", hospedaje=hospedaje(servidor))
    piensa.generar("s", "p")
    calla.generar("s", "p")
    assert servidor.pedidos[0][1].get("think") is False  # el thinking, callado
    assert "think" not in servidor.pedidos[1][1]  # el que no piensa, tal cual

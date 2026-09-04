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


def _sacar(server, metodo: str, ruta: str):
    """La respuesta enlatada; si es una lista, va soltando en orden."""
    dato = server.respuestas.get((metodo, ruta), (200, b"{}"))
    if isinstance(dato, list):
        dato = dato.pop(0) if dato else (200, b"{}")
    return dato


class _Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):  # silencio: los tests miran `srv.pedidos`
        pass

    def do_GET(self):
        estado, cuerpo = _sacar(self.server, "GET", self.path)
        self.send_response(estado)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_POST(self):
        largo = int(self.headers.get("Content-Length", 0))
        self.server.cabeceras.append(dict(self.headers))
        self.server.pedidos.append((self.path, json.loads(self.rfile.read(largo) or b"{}")))
        estado, cuerpo = _sacar(self.server, "POST", self.path)
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
    srv.cabeceras = []
    hilo = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
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


def test_el_hospedaje_honra_ollama_host(monkeypatch, tmp_path):
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    monkeypatch.delenv("ALDAMAR_HOST", raising=False)
    monkeypatch.chdir(tmp_path)  # sin configuracion.json ajeno en medio
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


def test_proveedor_por_defecto_honra_al_modelo_del_entorno(monkeypatch, tmp_path):
    monkeypatch.setenv("ALDAMAR_MODELO", "mifijo:8b")
    monkeypatch.delenv("ALDAMAR_HOST", raising=False)
    monkeypatch.delenv("ALDAMAR_API_KEY", raising=False)
    monkeypatch.delenv("ALDAMAR_PROVEEDOR", raising=False)
    monkeypatch.chdir(tmp_path)  # sin configuracion.json ajeno en medio
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


# ── el cronista externo: el protocolo de OpenAI ──────────────────────────

CHAT = {"choices": [{"message": {"content": "hola mundo"}}]}


def cliente_api(
    srv, modelo: str = "nemo-remoto", clave: str = "sk-prueba"
) -> cronista.ApiCompatible:
    return cronista.ApiCompatible(modelo=modelo, hospedaje=hospedaje(srv), api_key=clave)


def test_la_api_lista_modelos_y_esta_disponible(servidor):
    servidor.respuestas[("GET", "/models")] = (
        200,
        json.dumps({"data": [{"id": "m-uno"}, {"id": "m-dos"}]}).encode(),
    )
    assert cliente_api(servidor).disponible()
    assert cliente_api(servidor).modelos() == ["m-uno", "m-dos"]


def test_la_api_con_clave_rechazada_no_esta_disponible(servidor):
    servidor.respuestas[("GET", "/models")] = (401, b'{"error": "clave mala"}')
    assert not cliente_api(servidor).disponible()
    assert cliente_api(servidor).modelos() == []


def test_la_api_sin_servicio_no_esta_disponible():
    fria = cronista.ApiCompatible(modelo="m", hospedaje=_puerto_apagado(), api_key="sk")
    assert not fria.disponible()
    assert fria.modelos() == []


def test_la_api_sin_host_tampoco_esta_disponible():
    desnuda = cronista.ApiCompatible(modelo="m")
    assert not desnuda.disponible()
    assert desnuda.modelos() == []


def test_la_api_genera_prosa_por_chat_completions(servidor):
    servidor.respuestas[("POST", "/chat/completions")] = (200, json.dumps(CHAT).encode())
    texto = cliente_api(servidor).generar("sistema", "prompt", num_predict=600)
    assert texto == "hola mundo"
    ((ruta, carga),) = servidor.pedidos
    assert ruta == "/chat/completions"
    assert carga["model"] == "nemo-remoto"
    assert carga["messages"][0] == {"role": "system", "content": "sistema"}
    assert carga["messages"][1]["content"] == "prompt"
    assert carga["temperature"] == 0.9
    assert carga["max_tokens"] == 600
    assert carga["stream"] is False
    assert servidor.cabeceras[0].get("Authorization") == "Bearer sk-prueba"


def test_la_api_sin_clave_no_manda_autorizacion(servidor):
    servidor.respuestas[("POST", "/chat/completions")] = (200, json.dumps(CHAT).encode())
    desnuda = cronista.ApiCompatible(modelo="m", hospedaje=hospedaje(servidor))
    assert desnuda.generar("s", "p") == "hola mundo"
    assert "Authorization" not in servidor.cabeceras[0]


def test_la_api_hace_streaming_sse(servidor):
    servidor.respuestas[("POST", "/chat/completions")] = (
        200,
        (
            b'data: {"choices":[{"delta":{"content":"un "}}]}\n\n'
            b'data: {"choices":[{"delta":{"content":"trozo"}}]}\n\n'
            b"data: [DONE]\n\n"
        ),
    )
    trozos: list[str] = []
    texto = cliente_api(servidor).generar("s", "p", stream_en=trozos.append)
    assert texto == "un trozo"
    assert trozos == ["un ", "trozo"]
    assert servidor.pedidos[0][1]["stream"] is True


def test_la_api_genera_json_con_response_format_y_schema_en_el_prompt(servidor):
    servidor.respuestas[("POST", "/chat/completions")] = (
        200,
        json.dumps({"choices": [{"message": {"content": '{"vida": 3}'}}]}).encode(),
    )
    schema = {"type": "object", "properties": {"vida": {"type": "integer"}}}
    assert cliente_api(servidor).generar_json("s", "p", schema) == {"vida": 3}
    ((_, carga),) = servidor.pedidos
    assert carga["response_format"] == {"type": "json_object"}
    assert '"vida"' in carga["messages"][1]["content"]  # el schema, dentro del prompt


def test_la_api_reintenta_sin_response_format_si_el_servidor_lo_rechaza(servidor):
    servidor.respuestas[("POST", "/chat/completions")] = [
        (400, b'{"error": "response_format no soportado"}'),
        (200, json.dumps({"choices": [{"message": {"content": '{"ok": true}'}}]}).encode()),
    ]
    cliente = cliente_api(servidor)
    assert cliente.generar_json("s", "p", {}) == {"ok": True}
    assert servidor.pedidos[0][1].get("response_format")
    assert "response_format" not in servidor.pedidos[1][1]
    # y a partir de aquí, ni lo intenta de nuevo
    servidor.respuestas[("POST", "/chat/completions")] = (
        200,
        json.dumps({"choices": [{"message": {"content": '{"mas": 1}'}}]}).encode(),
    )
    assert cliente.generar_json("s", "p", {}) == {"mas": 1}
    assert "response_format" not in servidor.pedidos[2][1]


def test_la_api_con_json_basura_da_cronista_error(servidor):
    servidor.respuestas[("POST", "/chat/completions")] = (
        200,
        json.dumps({"choices": [{"message": {"content": "no soy json"}}]}).encode(),
    )
    with pytest.raises(cronista.CronistaError):
        cliente_api(servidor).generar_json("s", "p", {})


def test_un_http_400_agotado_da_cronista_error(servidor):
    servidor.respuestas[("POST", "/chat/completions")] = (400, b'{"error": "nada"}')
    with pytest.raises(cronista.CronistaError):
        cliente_api(servidor).generar_json("s", "p", {})


# ── local o externo: la resolución del proveedor ─────────────────────────


def _sin_entorno_cronista(monkeypatch) -> None:
    for clave in (
        "ALDAMAR_MODELO",
        "ALDAMAR_HOST",
        "ALDAMAR_API_KEY",
        "ALDAMAR_PROVEEDOR",
        "OLLAMA_HOST",
    ):
        monkeypatch.delenv(clave, raising=False)


def test_sin_configuracion_el_proveedor_es_el_ollama_local(monkeypatch, tmp_path):
    _sin_entorno_cronista(monkeypatch)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ALDAMAR_MODELO", "mifijo:8b")  # sin mirar /api/tags
    proveedor = cronista.proveedor_por_defecto()
    assert isinstance(proveedor, cronista.Ollama)
    assert proveedor.hospedaje == cronista.HOSPEDAJE_DEFECTO


def test_con_host_y_clave_en_el_entorno_el_cronista_es_externo(monkeypatch, tmp_path):
    _sin_entorno_cronista(monkeypatch)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ALDAMAR_HOST", "https://api.example.com/v1")
    monkeypatch.setenv("ALDAMAR_API_KEY", "sk-entorno")
    monkeypatch.setenv("ALDAMAR_MODELO", "nemo")
    proveedor = cronista.proveedor_por_defecto()
    assert isinstance(proveedor, cronista.ApiCompatible)
    assert proveedor.hospedaje == "https://api.example.com/v1"
    assert proveedor.api_key == "sk-entorno"
    assert proveedor.modelo == "nemo"


def test_el_proveedor_api_sale_de_la_configuracion(monkeypatch, tmp_path):
    _sin_entorno_cronista(monkeypatch)
    monkeypatch.chdir(tmp_path)
    config = configuracion.cargar()
    config.viva_proveedor = "api"
    config.viva_host = "https://openrouter.example/api/v1"
    config.viva_api_key = "sk-archivo"
    config.modelo_viva = "nemo-remoto"
    configuracion.guardar(config)
    proveedor = cronista.proveedor_por_defecto()
    assert isinstance(proveedor, cronista.ApiCompatible)
    assert proveedor.hospedaje == "https://openrouter.example/api/v1"
    assert proveedor.api_key == "sk-archivo"
    assert proveedor.modelo == "nemo-remoto"


def test_la_clave_sola_infiere_el_proveedor_externo(monkeypatch, tmp_path):
    _sin_entorno_cronista(monkeypatch)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ALDAMAR_API_KEY", "sk-solo")
    assert cronista.proveedor_fijado() == "api"
    # sin host no hay a dónde llamar: disponible False, pero sin explotar
    proveedor = cronista.proveedor_por_defecto()
    assert isinstance(proveedor, cronista.ApiCompatible)
    assert not proveedor.disponible()


def test_viva_proveedor_ollama_manda_sobre_la_clave(monkeypatch, tmp_path):
    _sin_entorno_cronista(monkeypatch)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ALDAMAR_API_KEY", "sk-solo")
    monkeypatch.setenv("ALDAMAR_MODELO", "mifijo:8b")  # sin mirar /api/tags
    config = configuracion.cargar()
    config.viva_proveedor = "ollama"
    configuracion.guardar(config)
    assert cronista.proveedor_fijado() == "ollama"
    assert isinstance(cronista.proveedor_por_defecto(), cronista.Ollama)


def test_el_hospedaje_por_defecto_prefiere_aldamar_host_a_viva_host(monkeypatch, tmp_path):
    _sin_entorno_cronista(monkeypatch)
    monkeypatch.chdir(tmp_path)
    assert cronista.hospedaje_por_defecto() == cronista.HOSPEDAJE_DEFECTO
    config = configuracion.cargar()
    config.viva_host = "http://192.168.1.5:11434"
    configuracion.guardar(config)
    assert cronista.hospedaje_por_defecto() == "http://192.168.1.5:11434"
    monkeypatch.setenv("ALDAMAR_HOST", "http://otro:11434")
    assert cronista.hospedaje_por_defecto() == "http://otro:11434"

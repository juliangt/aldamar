"""La presentación y el jingle: arte que solo sale cuando toca, audio que
jamás estorba."""

from __future__ import annotations

import io
import os
import wave

from conftest import EntradaTipeada

import aldamar.interfaz.presentacion as presentacion_mod
import aldamar.motor.juego as juego_mod
from aldamar.interfaz import audio
from aldamar.interfaz.opciones import LIMPIAR
from aldamar.motor.configuracion import ARCHIVO_CONFIGURACION, Configuracion
from aldamar.motor.juego import main

# ── el jingle ────────────────────────────────────────────────────────────

def test_el_jingle_es_un_wav_de_ocho_bits_y_dos_segundos():
    with wave.open(io.BytesIO(audio.bytes_jingle())) as onda:
        assert onda.getnchannels() == 1
        assert onda.getsampwidth() == 1  # 8 bits, el sonido de la época
        assert 1.9 <= onda.getnframes() / onda.getframerate() <= 2.1


def test_el_jingle_es_siempre_el_mismo_archivo():
    # la presentación y el cierre comparten pieza (issue 34)
    assert audio.bytes_jingle() == audio.bytes_jingle()


def test_el_jingle_no_suena_en_tuberias_ni_en_tests(monkeypatch):
    sonados: list[bool] = []
    monkeypatch.setattr(audio, "_sonar", lambda: sonados.append(True))
    audio.reproducir(entrada=EntradaTipeada([]), salida=lambda _t: None)
    assert sonados == []


def test_un_reproductor_que_explota_no_corta_la_partida(monkeypatch):
    monkeypatch.setattr(audio, "_es_interactivo", lambda entrada, salida: True)
    def explota() -> None:
        raise RuntimeError("no hay audio que valga")
    monkeypatch.setattr(audio, "_sonar", explota)
    audio.reproducir(entrada=input, salida=print)  # silencio, y a seguir


def test_en_posix_el_jingle_viaja_a_un_reproductor_del_sistema(monkeypatch, tmp_path):
    monkeypatch.setattr(audio.os, "name", "posix")
    monkeypatch.setattr(audio.sys, "platform", "darwin")
    ruta = str(tmp_path / "jingle.wav")
    def falso_mkstemp(suffix: str = "", prefix: str = ""):
        descriptor = os.open(ruta, os.O_WRONLY | os.O_CREAT)
        return descriptor, ruta
    monkeypatch.setattr(audio.tempfile, "mkstemp", falso_mkstemp)
    procesos: list[list[str]] = []

    class FalsoProceso:
        def wait(self) -> int:
            return 0

    def falso_popen(comando, **_):
        procesos.append(comando)
        return FalsoProceso()
    monkeypatch.setattr(audio.subprocess, "Popen", falso_popen)
    limpiadores: list = []

    class FalsoHilo:
        def __init__(self, target, args=(), daemon=False, **_) -> None:
            self.target = target
            self.args = args
            self.daemon = daemon
        def start(self) -> None:
            limpiadores.append(self)

    monkeypatch.setattr(audio.threading, "Thread", FalsoHilo)

    audio._sonar()

    assert procesos[0][0] == "afplay"  # el reproductor del sistema
    assert procesos[0][1].endswith(".wav")
    assert len(limpiadores) == 1
    # daemon: el limpiador jamás retiene la salida del juego
    assert limpiadores[0].daemon is True
    for limpiador in limpiadores:
        limpiador.target(*limpiador.args)  # el archivo no se queda tirado
    assert not os.path.exists(ruta)


def test_sin_ningun_reproductor_silencio_y_archivo_limpio(monkeypatch, tmp_path):
    monkeypatch.setattr(audio.os, "name", "posix")
    monkeypatch.setattr(audio.sys, "platform", "linux")
    ruta = str(tmp_path / "jingle.wav")
    def falso_mkstemp(suffix: str = "", prefix: str = ""):
        descriptor = os.open(ruta, os.O_WRONLY | os.O_CREAT)
        return descriptor, ruta
    monkeypatch.setattr(audio.tempfile, "mkstemp", falso_mkstemp)
    def explota(_comando, **_):
        raise OSError("no hay reproductor")
    monkeypatch.setattr(audio.subprocess, "Popen", explota)

    audio._sonar()  # ni se queja

    assert not os.path.exists(ruta)


# ── la presentación ──────────────────────────────────────────────────────

def test_en_tuberia_la_presentacion_no_existe():
    salida: list[str] = []
    presentacion_mod.presentar(entrada=EntradaTipeada([]), salida=salida.append)
    assert salida == []


def test_en_sesion_de_verdad_hay_sello_jingle_y_tecla(monkeypatch):
    monkeypatch.setattr(presentacion_mod, "_es_interactivo", lambda entrada, salida: True)
    monkeypatch.setattr(presentacion_mod, "_leer_tecla", lambda: " ")
    sonados: list[bool] = []
    monkeypatch.setattr(
        presentacion_mod.modulo_audio, "reproducir", lambda **_: sonados.append(True)
    )
    salida: list[str] = []
    presentacion_mod.presentar(entrada=input, salida=salida.append)
    texto = "\n".join(salida)
    assert salida[0] == LIMPIAR  # el sello se ve solo
    assert "el amuleto que durmió veinte generaciones" in texto
    assert "####" in texto  # el título en letras grandes
    assert "Presiona cualquier tecla para comenzar" in texto
    assert sonados == [True]  # el jingle suena con el sello en pantalla
    assert salida[-1] == LIMPIAR  # al continuar, lo que sigue se ve solo


def test_sin_audio_la_presentacion_es_muda(monkeypatch):
    monkeypatch.setattr(presentacion_mod, "_es_interactivo", lambda entrada, salida: True)
    monkeypatch.setattr(presentacion_mod, "_leer_tecla", lambda: " ")
    sonados: list[bool] = []
    monkeypatch.setattr(
        presentacion_mod.modulo_audio, "reproducir", lambda **_: sonados.append(True)
    )
    presentacion_mod.presentar(entrada=input, salida=lambda _t: None, sonar=False)
    assert sonados == []


# ── el arranque decide cuándo hay presentación ───────────────────────────

def _arrancar_con_presentacion_espia(monkeypatch, argv: list[str]) -> list[dict]:
    """Corre main() hasta «salir» y devuelve las veces que se presentó."""
    monkeypatch.setattr(juego_mod, "_es_interactivo", lambda entrada, salida: True)
    presentadas: list[dict] = []
    monkeypatch.setattr(
        juego_mod.presentacion, "presentar", lambda **llamada: presentadas.append(llamada)
    )
    main(argv, entrada=EntradaTipeada(["salir"]), salida=lambda _t: None)
    return presentadas


def test_el_arranque_por_menu_presenta_el_sello(monkeypatch):
    # preferencias por defecto: el archivo configuracion.json de verdad
    # no ha de decidir aquí (si el jugador lo apagó, el sello sigue)
    monkeypatch.setattr(
        juego_mod.configuracion, "cargar", lambda *_, **__: Configuracion()
    )
    presentadas = _arrancar_con_presentacion_espia(monkeypatch, ["--sin-flechas"])
    assert len(presentadas) == 1
    assert presentadas[0]["sonar"] is True


def test_sin_splash_o_sin_audio_por_flag_no_hay_de_eso(monkeypatch):
    assert _arrancar_con_presentacion_espia(monkeypatch, ["--sin-flechas", "--sin-splash"]) == []
    mudas = _arrancar_con_presentacion_espia(monkeypatch, ["--sin-flechas", "--sin-audio"])
    assert len(mudas) == 1 and mudas[0]["sonar"] is False


def test_los_atajos_de_cli_van_directos_sin_presentacion(monkeypatch):
    # --cargar no pasa por el menú: la presentación no pinta nada ahí
    presentadas = _arrancar_con_presentacion_espia(
        monkeypatch, ["--sin-flechas", "--cargar", "no-existe.json"]
    )
    assert presentadas == []


def test_el_archivo_de_configuracion_manda_si_no_hay_flags(monkeypatch):
    monkeypatch.setattr(
        juego_mod.configuracion, "cargar", lambda *_, **__: Configuracion(splash=False, audio=False)
    )
    monkeypatch.setattr(juego_mod.configuracion, "asegurar", lambda *_: False)
    presentadas = _arrancar_con_presentacion_espia(monkeypatch, ["--sin-flechas"])
    assert presentadas == []  # el archivo apagó el splash entero


def test_el_flag_de_cli_le_gana_al_archivo_de_configuracion(monkeypatch):
    monkeypatch.setattr(
        juego_mod.configuracion, "cargar", lambda *_, **__: Configuracion(splash=True, audio=False)
    )
    monkeypatch.setattr(juego_mod.configuracion, "asegurar", lambda *_: False)
    presentadas = _arrancar_con_presentacion_espia(
        monkeypatch, ["--sin-flechas", "--sin-splash"]
    )
    assert presentadas == []  # el flag apagó lo que el archivo prendía
    presentadas = _arrancar_con_presentacion_espia(
        monkeypatch, ["--sin-flechas", "--sin-audio"]
    )
    # el splash sigue (lo manda el archivo) pero mudo (lo manda el flag)
    assert len(presentadas) == 1 and presentadas[0]["sonar"] is False


def test_en_tests_nadie_estrena_un_configuracion_json(monkeypatch):
    # aunque el arranque se crea interactivo, la escritura del archivo es
    # de las sesiones de verdad: aquí no queda basura en el directorio
    estrenados: list[str] = []
    monkeypatch.setattr(
        juego_mod.configuracion, "asegurar", lambda ruta=ARCHIVO_CONFIGURACION: estrenados.append(ruta)
    )
    _arrancar_con_presentacion_espia(monkeypatch, ["--sin-flechas"])
    assert estrenados == []

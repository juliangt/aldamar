"""El versionado del esquema de partidas (issue 15).

La pieza central es un guardado real del esquema pre-versionado
(`datos/partida_v0.json`, una partida auténtica de antes del campo
`version`): cargarlo migra a la versión actual campo a campo, sin
perder nada. Alrededor, el resto del contrato: el guardado nuevo
lleva su versión, la versión actual migra a sí misma y lo que no
sirve se rechaza nombrando archivo y campo, sin traceback.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aldamar.motor import guardado
from aldamar.motor.guardado import PartidaInvalida, migrar, preparar

FIXTURE = str(Path(__file__).parent / "datos" / "partida_v0.json")


def leejason(ruta: str) -> dict:
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


# ── la migración del guardado real ──────────────────────────────────────

def test_el_guardado_real_sin_version_migra_a_la_actual():
    estado = preparar(leejason(FIXTURE), FIXTURE)
    assert estado["version"] == guardado.VERSION


def test_la_migracion_va_campo_a_campo():
    crudo = leejason(FIXTURE)
    estado = migrar(dict(crudo), 0)
    # lo que la versión 1 trae de nuevo, con su valor para un héroe
    # que entonces no tenía progresión ni huella de viaje
    assert estado["version"] == 1
    assert estado["experiencia"] == 0
    assert estado["nivel"] == 1
    assert estado["equipado"] is None  # «vestía siempre lo mejor»
    assert estado["derrotados"] == []
    assert estado["visitados"] == ["rioclaro"]
    # y lo que el guardado traía queda tal cual
    for campo in ("aventura", "dificultad", "personaje", "nombre", "vida",
                  "monedas", "corrupcion", "inventario", "companeros",
                  "lugar", "lugar_previo", "flags", "enemigos", "tomados",
                  "monedas_tomadas", "final"):
        assert estado[campo] == crudo[campo], campo


def test_el_guardado_migrado_se_juega(tmp_path):
    """La partida real pre-versionada se carga, se viste sola y sigue."""
    from aldamar.motor.juego import Juego

    juego = Juego.desde_archivo(
        FIXTURE,
        entrada=lambda _p: (_ for _ in ()).throw(EOFError),
        salida=lambda _t: None,
        color=False,
    )
    assert juego.av.id == "corazon_ceniza"
    assert juego.personaje == "tilo"
    assert juego.lugar == "rioclaro"
    assert juego.jugador.nivel == 1
    assert juego.jugador.experiencia == 0
    # el autoequip del guardado viejo: la capa gris del inventario, puesta
    assert juego.jugador.equipado == {"armadura": "capa_gris"}
    assert juego.reanudada


# ── el guardado de la versión actual ────────────────────────────────────

def test_guardar_escribe_la_version(tmp_path, fabrica):
    from aldamar.motor.juego import Juego

    ruta = str(tmp_path / "partida.json")
    juego, _ = fabrica(["", f"guardar {ruta}", "salir"], semilla=5)
    juego.ciclo()
    guardado_crudo = leejason(ruta)
    assert guardado_crudo["version"] == guardado.VERSION == 1


def test_la_version_actual_migra_a_si_misma(tmp_path, fabrica):
    ruta = str(tmp_path / "partida.json")
    juego, _ = fabrica(["", "tomar todo", f"guardar {ruta}", "salir"], semilla=9)
    juego.ciclo()
    crudo = leejason(ruta)
    assert preparar(leejason(ruta), ruta) == crudo  # ni un campo tocad


def test_migrar_no_encuentra_pasos_ausentes(monkeypatch):
    # una versión sin paso declarado sería una culpa de programación,
    # no de datos: el error lo dice
    pasos = {k: v for k, v in guardado._PASOS.items() if k != 0}
    monkeypatch.setattr(guardado, "_PASOS", pasos)
    with pytest.raises(PartidaInvalida):
        migrar({}, 0)


# ── los rechazos, con nombre y apellido ─────────────────────────────────

def test_rechaza_una_version_futura():
    estado = preparar(leejason(FIXTURE), FIXTURE)
    estado["version"] = guardado.VERSION + 1
    try:
        preparar(estado, "futuro.json")
    except PartidaInvalida as e:
        mensaje = str(e)
        assert "futuro.json" in mensaje
        assert "más nueva" in mensaje
        assert str(guardado.VERSION) in mensaje
    else:
        raise AssertionError("debió rechazar la versión futura")


def test_la_version_futura_no_da_traceback_en_el_juego(tmp_path, fabrica):
    ruta = str(tmp_path / "del_futuro.json")
    estado = preparar(leejason(FIXTURE), FIXTURE)
    estado["version"] = guardado.VERSION + 3
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False)

    juego, salida = fabrica(["", f"cargar {ruta}", "salir"], semilla=1)
    juego.ciclo()
    texto = "\n".join(salida)
    assert "versión más nueva" in texto
    assert "Traceback" not in texto


def test_rechaza_version_que_no_es_entero(tmp_path):
    ruta = str(tmp_path / "rara.json")
    estado = preparar(leejason(FIXTURE), FIXTURE)
    estado["version"] = "la del año pasado"
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False)
    try:
        guardado.cargar(ruta)
    except PartidaInvalida as e:
        assert "rara.json" in str(e)
        assert "'version'" in str(e)
    else:
        raise AssertionError("debió rechazar la versión no entera")


def test_el_error_nombra_archivo_y_campo(tmp_path):
    ruta = str(tmp_path / "coja.json")
    estado = preparar(leejason(FIXTURE), FIXTURE)
    del estado["monedas"]
    del estado["visitados"]
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False)
    try:
        guardado.cargar(ruta)
    except PartidaInvalida as e:
        mensaje = str(e)
        assert "coja.json" in mensaje
        assert "monedas" in mensaje  # falta de la base: no se puede migrar
    else:
        raise AssertionError("debió nombrar el campo que falta")


def test_lo_que_no_es_partida_se_rechaza(tmp_path):
    ruta = str(tmp_path / "lista.json")
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(["no", "soy", "una", "partida"], f)
    try:
        guardado.cargar(ruta)
    except PartidaInvalida as e:
        assert "lista.json" in str(e)
    else:
        raise AssertionError("debió rechazar una lista")


def test_archivo_roto_o_ausente_mensaje_claro(tmp_path):
    roto = tmp_path / "roto.json"
    roto.write_text("{esto no es json", encoding="utf-8")
    try:
        guardado.cargar(str(roto))
    except PartidaInvalida as e:
        assert "roto.json" in str(e)
    else:
        raise AssertionError("debió rechazar el JSON roto")
    try:
        guardado.cargar(str(tmp_path / "nunca_fue.json"))
    except PartidaInvalida as e:
        assert "nunca_fue.json" in str(e)
    else:
        raise AssertionError("debió nombrar el archivo ausente")

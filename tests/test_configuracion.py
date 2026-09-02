"""El archivo configuracion.json: defaults, lectura tolerante y escritura."""

from __future__ import annotations

from aldamar.motor import configuracion


def test_por_defecto_todo_esta_prendido_y_sin_semilla():
    config = configuracion.defecto()
    assert config.audio and config.color and config.flechas and config.splash
    assert not config.debug
    assert config.semilla is None


def test_un_archivo_que_falta_da_los_valores_por_defecto(tmp_path):
    config = configuracion.cargar(str(tmp_path / "configuracion.json"))
    assert config == configuracion.defecto()


def test_el_archivo_se_lee_y_lo_que_trae_se_respeta(tmp_path):
    ruta = tmp_path / "configuracion.json"
    ruta.write_text('{"audio": false, "debug": true, "semilla": 7}', encoding="utf-8")
    config = configuracion.cargar(str(ruta))
    assert not config.audio
    assert config.debug
    assert config.semilla == 7
    # lo que el archivo no trae queda por defecto, campo por campo
    assert config.color and config.flechas and config.splash


def test_un_archivo_roto_o_con_otra_cosa_no_para_la_partida(tmp_path):
    roto = tmp_path / "roto.json"
    roto.write_text("{no soy json", encoding="utf-8")
    assert configuracion.cargar(str(roto)) == configuracion.defecto()
    basura = tmp_path / "basura.json"
    basura.write_text('["una lista", "no un objeto"]', encoding="utf-8")
    assert configuracion.cargar(str(basura)) == configuracion.defecto()


def test_los_valores_con_tipo_equivocado_vuelven_a_su_default(tmp_path):
    ruta = tmp_path / "configuracion.json"
    ruta.write_text(
        '{"audio": "sí", "debug": 1, "color": null, "semilla": true}', encoding="utf-8"
    )
    config = configuracion.cargar(str(ruta))
    # solo true/false de verdad prenden y apagan; la semilla no acepta bool
    assert config.audio and not config.debug and config.color
    assert config.semilla is None


def test_las_claves_desconocidas_se_ignoran(tmp_path):
    ruta = tmp_path / "configuracion.json"
    ruta.write_text('{"audio": false, "volumen": 11, "trucos": true}', encoding="utf-8")
    config = configuracion.cargar(str(ruta))
    assert config == configuracion.Configuracion(audio=False)


def test_guardar_y_cargar_viajan_redondos(tmp_path):
    ruta = str(tmp_path / "configuracion.json")
    config = configuracion.Configuracion(
        audio=False, debug=True, color=False, flechas=False, splash=False, semilla=42
    )
    configuracion.guardar(config, ruta)
    assert configuracion.cargar(ruta) == config


def test_asegurar_estrena_el_archivo_y_luego_no_lo_toca(tmp_path):
    ruta = str(tmp_path / "configuracion.json")
    assert configuracion.asegurar(ruta)  # nace con los defaults
    assert configuracion.cargar(ruta) == configuracion.defecto()
    editada = configuracion.Configuracion(audio=False, semilla=3)
    configuracion.guardar(editada, ruta)
    assert not configuracion.asegurar(ruta)  # lo editado a mano se queda
    assert configuracion.cargar(ruta) == editada

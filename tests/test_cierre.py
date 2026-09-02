"""La pantalla de cierre: remate, epílogo, balance del héroe y «¿y ahora qué?»."""

from __future__ import annotations

import pytest

import aldamar.motor.juego as juego_mod
from aldamar.motor.juego import Juego, main
from aldamar.contenido.personajes import Companero

from conftest import AVENTURA, EntradaTipeada
from test_flujo import RUTA_BASE


def _jugar(lineas: list[str], personaje: str | None = None):
    salida: list[str] = []
    juego = Juego(
        AVENTURA,
        personaje=personaje,
        semilla=7,
        entrada=EntradaTipeada(list(lineas)),
        salida=salida.append,
        color=False,
    )
    eleccion = juego.ciclo()
    return juego, salida, eleccion


# ── el jingle de la despedida ────────────────────────────────────────────

def test_el_cierre_suena_con_el_jingle_y_se_puede_apagar(fabrica, monkeypatch):
    sonados: list[dict] = []
    monkeypatch.setattr(
        juego_mod.modulo_audio, "reproducir", lambda **llamada: sonados.append(llamada)
    )
    juego, _ = fabrica([])
    juego.fin = True
    juego.final = "victoria pura"
    juego._cierre()
    assert len(sonados) == 1  # la despedida suena
    juego.audio = False
    juego._cierre()
    assert len(sonados) == 1  # con el audio apagado, no repite


# ── el remate y el epílogo ───────────────────────────────────────────────

@pytest.mark.parametrize(
    "final,remate",
    [
        ("muerte", "Aquí se apaga tu historia"),
        ("caida", "La grieta te alcanzó"),
        ("suspendida", "La historia queda a medias"),
        ("victoria pura", "¡La noche retrocede!"),
        ("victoria con cicatriz", "Ganaste… y la marca se queda"),
        ("la Sombra nueva", "Así acaba este cantar"),
    ],
)
def test_el_remate_segun_como_acabo(fabrica, final, remate):
    juego, _ = fabrica([])
    juego.fin = True
    juego.final = final
    assert remate in juego._texto_cierre()


def test_el_cierre_presenta_epilogo_y_nombre_del_final():
    juego, salida, eleccion = _jugar(RUTA_BASE + ["destruir", "3"])
    assert eleccion == "salir"  # «Salir» en el menú de cierre acaba la sesión
    texto = "\n".join(salida)
    plano = " ".join(texto.split())
    assert "¡La noche retrocede!" in texto
    assert "Tu historia queda contada: «victoria pura»" in texto
    assert "El Jardín que venció a la Sombra" in plano  # el epílogo, con aire
    assert "¿Y ahora qué?" in texto


def test_el_cierre_no_duplica_el_epilogo_de_la_muerte(fabrica):
    """La muerte se cuenta en el momento, en el relato; el cierre no la repite."""
    juego, salida = fabrica(["atacar"] * 10, personaje="dagna", semilla=2)
    juego.jugador.vida = 1  # sentencia anticipada: el contraataque la tumba
    juego._duelo(juego.crear_enemigo("custodio"))  # aquí suena el epílogo de muerte
    juego.ciclo()  # ya está acabada: solo presenta la pantalla de cierre
    texto = " ".join("\n".join(salida).split())
    assert juego.final == "muerte"
    assert texto.count("la guerrera que se atrevió") == 1
    assert "Aquí se apaga tu historia" in texto


# ── el balance del héroe ─────────────────────────────────────────────────

def test_el_balance_del_heroe_en_el_cierre(fabrica):
    juego, _ = fabrica([])
    juego.fin = True
    juego.final = "victoria pura"
    juego.jugador.nombre = "Solmar"
    juego.jugador.nivel = 3
    juego.jugador.monedas = 23
    juego.jugador.companeros.append(
        Companero(clave="sylvana", nombre="Sylvana de los Faroles",
                  vida=10, vida_max=18, ataque=5)
    )
    juego.jugador.companeros.append(
        Companero(clave="torkan", nombre="Torkan Hachagris",
                  vida=0, vida_max=20, ataque=6, viva=False)
    )
    texto = juego._texto_cierre()
    assert "Solmar," in texto  # el nombre puesto
    assert "Nivel 3" in texto and "Vida" in texto and "Monedas: 23" in texto
    assert "Sylvana de los Faroles (10/18)" in texto
    assert "Torkan Hachagris (cayó)" in texto


def test_la_huella_cuenta_derrotados_lugares_y_decisiones(fabrica):
    juego, _ = fabrica([])
    juego.fin = True
    juego.final = "victoria pura"
    juego.derrotados += ["lobo", "espectro", "espectro"]
    juego.visitados += ["molino", "puente"]
    juego.flags["juramento"] = True
    texto = juego._texto_cierre()
    assert "lobo de sombra" in texto
    assert "espectro de ceniza ×2" in texto  # los repetidos se cuentan, no se listan dos veces
    assert "Lugares visitados: 3" in texto
    assert "juramento" in texto  # las decisiones (banderas) quedan dichas


# ── el bucle de sesión ───────────────────────────────────────────────────

def _sesion(lineas: list[str]) -> str:
    salida: list[str] = []
    main(
        ["--semilla", "7", "--sin-color"],
        entrada=EntradaTipeada(list(lineas)),
        salida=salida.append,
    )
    return "\n".join(salida)


def test_jugar_otra_vez_repite_sin_reiniciar_y_conserva_el_nombre():
    # el héroe se llama "Solmar" en la primera partida; el cierre ofrece
    # «Jugar otra vez» y la segunda partida corre con el nombre heredado
    lineas = ["1", "1", "1", "2", "Solmar"] + RUTA_BASE[1:] + ["destruir", "1", "estado"]
    texto = _sesion(lineas)
    assert texto.count("¿Y ahora qué?") == 1
    assert texto.count("Hace mil lunas") == 2  # el prólogo sonó en ambas partidas
    assert "Guardas las tomillas" in texto  # la segunda acabó con «salir» (EOF)
    assert "— Solmar ·" in texto  # el nombre puesto viaja a la partida nueva


def test_elegir_otra_aventura_devuelve_al_menu_principal():
    texto = _sesion(["1", "1", "1", "2"] + RUTA_BASE + ["destruir", "2", "salir"])
    assert texto.count("¿Y ahora qué?") == 1
    assert texto.count("A L D A M A R") == 2  # la portada, de vuelta en el menú
    assert "Hasta pronto." in texto


def test_salir_en_el_cierre_termina_la_sesion():
    texto = _sesion(["1", "1", "1", "2"] + RUTA_BASE + ["destruir", "3"])
    assert texto.count("¿Y ahora qué?") == 1
    assert "A L D A M A R" not in texto[texto.index("¿Y ahora qué?"):]  # no hay menú después


# ── la huella viaja en el guardado ───────────────────────────────────────

def test_derrotados_y_lugares_viajan_en_el_guardado(tmp_path, fabrica):
    ruta = str(tmp_path / "partida.json")
    juego, _ = fabrica(["", "tomar todo", f"guardar {ruta}", "salir"], semilla=9)
    juego.derrotados.append("lobo")
    juego.visitados.append("molino")
    juego.ciclo()

    juego2 = Juego.desde_archivo(
        ruta, entrada=EntradaTipeada([]), salida=lambda _t: None, color=False
    )
    assert juego2.derrotados == ["lobo"]
    assert juego2.visitados == ["vegaverde", "molino"]

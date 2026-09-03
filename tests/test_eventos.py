import pytest
from unittest.mock import MagicMock
from aldamar.contenido.eventos import ataque_con_corrupcion

def test_ataque_con_corrupcion_happy_path():
    ataque = ataque_con_corrupcion(
        dano_base=10,
        dano_por_corrupcion=5,
        corrupcion_coste=2,
        mensaje="Hiciste {efectivo} de daño"
    )

    juego = MagicMock()
    juego.jugador.corrupcion = 15
    enemigo = MagicMock()
    enemigo.recibir.return_value = 13 # Effective damage

    ataque(juego, enemigo)

    enemigo.recibir.assert_called_once_with(10 + 15 // 5) # 13
    juego.aviso.assert_called_once_with("Hiciste 13 de daño")
    juego.corruptear.assert_called_once_with(2)

def test_ataque_con_corrupcion_cero_corrupcion():
    ataque = ataque_con_corrupcion(
        dano_base=10,
        dano_por_corrupcion=5,
        corrupcion_coste=2,
        mensaje="Hiciste {efectivo} de daño"
    )

    juego = MagicMock()
    juego.jugador.corrupcion = 0
    enemigo = MagicMock()
    enemigo.recibir.return_value = 10

    ataque(juego, enemigo)

    enemigo.recibir.assert_called_once_with(10)
    juego.aviso.assert_called_once_with("Hiciste 10 de daño")
    juego.corruptear.assert_called_once_with(2)

def test_ataque_con_corrupcion_division_entera():
    ataque = ataque_con_corrupcion(
        dano_base=10,
        dano_por_corrupcion=5,
        corrupcion_coste=2,
        mensaje="Hiciste {efectivo} de daño"
    )

    juego = MagicMock()
    juego.jugador.corrupcion = 14 # 14 // 5 = 2
    enemigo = MagicMock()
    enemigo.recibir.return_value = 12

    ataque(juego, enemigo)

    enemigo.recibir.assert_called_once_with(12)
    juego.aviso.assert_called_once_with("Hiciste 12 de daño")
    juego.corruptear.assert_called_once_with(2)

def test_ataque_con_corrupcion_division_por_cero():
    ataque = ataque_con_corrupcion(
        dano_base=10,
        dano_por_corrupcion=0,
        corrupcion_coste=2,
        mensaje="Hiciste {efectivo} de daño"
    )

    juego = MagicMock()
    juego.jugador.corrupcion = 10
    enemigo = MagicMock()

    with pytest.raises(ZeroDivisionError):
        ataque(juego, enemigo)

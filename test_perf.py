import timeit
import cProfile
import pstats
from src.aldamar.motor.juego import Juego
from src.aldamar.contenido.personajes import Jugador, Enemigo

setup_code = """
from src.aldamar.motor.juego import Juego
from src.aldamar.contenido.personajes import Jugador, Enemigo
import timeit

class DummyEnemigo:
    def __init__(self):
        pass

class DummyLegado:
    def __init__(self):
        self.importa = []

class DummyLugar:
    def __init__(self):
        self.enemigos = []

class DummyAventura:
    def __init__(self):
        self.jugador_inicial = "dummy"
        self.lugar_inicial = "dummy"
        self.items = {
            f"item_{i}": {"tipo": "basura"} for i in range(100)
        }
        self.items["consumible_1"] = {"tipo": "consumible", "nombre": "c1", "curacion": 1}
        self.items["cuerno_1"] = {"tipo": "cuerno"}
        self.comando_especial = "especial"
        self.ataque_especial = True
        self.legado = DummyLegado()
        self.lugares = {"dummy": DummyLugar()}
    def crear_jugador(self, p, d):
        j = Jugador("dummy")
        j.inventario = [f"item_{i}" for i in range(100)] + ["consumible_1", "cuerno_1"]
        return j

av = DummyAventura()
juego = Juego(av, None, "dummy", None, lambda: "", lambda x: None)

enemigo = DummyEnemigo()
"""

test_code = """
juego._opciones_combate(enemigo)
"""

print(timeit.timeit(test_code, setup=setup_code, number=100000))

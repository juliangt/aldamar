import timeit

def run_benchmark():
    setup_code_juego = """
from src.aldamar.motor.juego import Juego
from src.aldamar.contenido.personajes import Jugador, Enemigo

class DummyEnemigo:
    def __init__(self):
        pass

class DummyLegado:
    def __init__(self):
        self.importa = []

class DummyLugar:
    def __init__(self):
        self.enemigos = []
        self.id = "dummy"
        self.monedas = 0
        self.salidas = {}
        self.objetos = []
        self.npcs = {}
        self.tienda = False
        self.descanso = False

class DummyAventura:
    def __init__(self):
        self.jugador_inicial = "dummy"
        self.lugar_inicial = "dummy"
        self.items = {
            f"item_{i}": {"tipo": "basura"} for i in range(200)
        }
        self.items["consumible_1"] = {"tipo": "consumible", "nombre": "c1", "curacion": 1}
        self.items["cuerno_1"] = {"tipo": "cuerno"}
        self.comando_especial = "especial"
        self.ataque_especial = True
        self.legado = DummyLegado()
        self.lugares = {"dummy": DummyLugar()}
    def crear_jugador(self, p, d):
        j = Jugador("dummy")
        j.inventario = [f"item_{i}" for i in range(200)] + ["consumible_1", "cuerno_1"]
        return j

av = DummyAventura()
juego = Juego(av, None, "dummy", None, lambda: "", lambda x: None)
enemigo = DummyEnemigo()
    """

    test_combate = "juego._opciones_combate(enemigo)"
    test_juego = "juego._opciones_juego()"

    print("Baseline (opciones_combate):", timeit.timeit(test_combate, setup=setup_code_juego, number=100000))
    print("Baseline (opciones_juego):", timeit.timeit(test_juego, setup=setup_code_juego, number=100000))

run_benchmark()

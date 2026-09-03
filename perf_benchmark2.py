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

class TestJuego(Juego):
    def _opciones_combate(self, enemigo: Enemigo) -> list[tuple[str, str, str]]:
        ops = [("atacar", "Atacar", "Golpe a golpe")]
        if self.av.comando_especial and self.av.ataque_especial:
            ops.append((
                "especial",
                self.av.comando_especial,
                "El golpe especial de la aventura",
            ))

        tipos_inv = {self.av.items[k].get("tipo") for k in self.jugador.inventario}
        if "consumible" in tipos_inv:
            ops.append(self._entrada_usar())
        if "cuerno" in tipos_inv:
            ops.append(("cuerno", "Tocar el cuerno", "Pone en fuga a las criaturas menores"))

        ops += [
            ("huir", "Huir", "Retirada al lugar anterior"),
            ("estado", "Estado", ""),
            ("inventario", "Inventario", ""),
            (">", "Escribir un comando...", ""),
        ]
        return ops

av = DummyAventura()
juego = Juego(av, None, "dummy", None, lambda: "", lambda x: None)
juego_opt = TestJuego(av, None, "dummy", None, lambda: "", lambda x: None)
enemigo = DummyEnemigo()
    """

    test_combate = "juego._opciones_combate(enemigo)"
    test_combate_opt = "juego_opt._opciones_combate(enemigo)"

    print("Baseline (opciones_combate):", timeit.timeit(test_combate, setup=setup_code_juego, number=100000))
    print("Optimized (opciones_combate set):", timeit.timeit(test_combate_opt, setup=setup_code_juego, number=100000))

run_benchmark()

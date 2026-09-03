import timeit

setup_code = """
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

class TestJuego(Juego):
    def _opciones_combate(self, enemigo: Enemigo) -> list[tuple[str, str, str]]:
        ops = [("atacar", "Atacar", "Golpe a golpe")]
        if self.av.comando_especial and self.av.ataque_especial:
            ops.append((
                "especial",
                self.av.comando_especial,
                "El golpe especial de la aventura",
            ))

        tiene_consumible = False
        tiene_cuerno = False
        for k in self.jugador.inventario:
            tipo = self.av.items[k]["tipo"]
            if not tiene_consumible and tipo == "consumible":
                tiene_consumible = True
            elif not tiene_cuerno and tipo == "cuerno":
                tiene_cuerno = True
            if tiene_consumible and tiene_cuerno:
                break

        if tiene_consumible:
            ops.append(self._entrada_usar())
        if tiene_cuerno:
            ops.append(("cuerno", "Tocar el cuerno", "Pone en fuga a las criaturas menores"))

        ops += [
            ("huir", "Huir", "Retirada al lugar anterior"),
            ("estado", "Estado", ""),
            ("inventario", "Inventario", ""),
            (">", "Escribir un comando...", ""),
        ]
        return ops

av = DummyAventura()
juego = TestJuego(av, None, "dummy", None, lambda: "", lambda x: None)
enemigo = DummyEnemigo()
"""

test_code = """
juego._opciones_combate(enemigo)
"""

print(timeit.timeit(test_code, setup=setup_code, number=100000))

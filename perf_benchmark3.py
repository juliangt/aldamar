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

    def _opciones_juego(self) -> list[tuple[str, str, str]]:
        l = self.aqui()
        ops = [
            ("mirar", "Mirar alrededor", "El lugar, lo que hay y a dónde ir"),
        ]
        destinos = self.destinos(l)
        if len(destinos) == 1:
            ops.append(("ir 1", f"Ir a: {destinos[0][2]}", ""))
        elif destinos:
            ops.append(("ir", "Ir a…", f"{len(destinos)} destinos"))
        en_suelo = self.restantes(l)
        hay_monedas = bool(l.monedas) and l.id not in self.monedas_tomadas
        if len(en_suelo) == 1 and not hay_monedas:
            ops.append((f"tomar {en_suelo[0]}", f"Tomar: {self.av.items[en_suelo[0]]['nombre']}", ""))
        elif en_suelo or hay_monedas:
            ops.append(("tomar", "Tomar…", self._cuenta_tomar(l)))
        npcs = list(l.npcs)
        if len(npcs) == 1:
            ops.append((f"hablar {npcs[0]}", f"Hablar: {npcs[0]}", ""))
        elif npcs:
            ops.append(("hablar", "Hablar…", f"{len(npcs)} personas aquí"))
        aliados = [npc for npc, clave in l.npcs.items() if clave in self.av.reclutas]
        if len(aliados) == 1:
            ops.append((f"reclutar {aliados[0]}", f"Reclutar: {aliados[0]}", "Se suma a tu grupo"))
        elif aliados:
            ops.append(("reclutar", "Reclutar…", f"{len(aliados)} aliados"))
        if l.tienda:
            stock = self.av.tiendas[l.id]
            if len(stock) == 1 and not self._opciones_equipo():
                item = self.av.items[stock[0]]
                ops.append((f"comprar {stock[0]}", f"Comprar: {item['nombre']}", f"{item['precio']} monedas"))
            else:
                ops.append(("comprar", "Comprar…", f"{len(stock)} cosas en venta"))

        tipos_inv = {self.av.items[k].get("tipo") for k in self.jugador.inventario}
        if "consumible" in tipos_inv:
            ops.append(self._entrada_usar())

        if l.descanso:
            ops.append(("descansar", "Descansar", "Curar heridas y reponer fuerzas"))

        ops.append(("otras", "Otras gestiones…", "Inventario, equipo y sistema"))
        return ops

av = DummyAventura()
juego = Juego(av, None, "dummy", None, lambda: "", lambda x: None)
juego_opt = TestJuego(av, None, "dummy", None, lambda: "", lambda x: None)
enemigo = DummyEnemigo()
    """

    test_juego = "juego._opciones_juego()"
    test_juego_opt = "juego_opt._opciones_juego()"

    print("Baseline (opciones_juego):", timeit.timeit(test_juego, setup=setup_code_juego, number=100000))
    print("Optimized (opciones_juego set):", timeit.timeit(test_juego_opt, setup=setup_code_juego, number=100000))

run_benchmark()

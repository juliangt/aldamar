"""Modelos de personajes: jugador, compañeros y enemigos."""

from __future__ import annotations

from dataclasses import dataclass, field

CORRUPCION_MAXIMA = 100
CORRUPCION_TENTADO = 60


@dataclass(frozen=True)
class Rasgo:
    """El don de un héroe: nombre y efecto mecánico, documentado en su ficha."""

    clave: str
    nombre: str
    descripcion: str


# Los dones que el motor sabe aplicar. Sumar uno = agregar la entrada y
# darle efecto en `juego.py` (son mecánicas simples y compartidas).
RASGOS: dict[str, Rasgo] = {
    "ojo_halcon": Rasgo(
        clave="ojo_halcon",
        nombre="Ojo de halcón",
        descripcion="+1 de daño mientras el enemigo conserve más de la mitad de su vida",
    ),
    "piel_piedra": Rasgo(
        clave="piel_piedra",
        nombre="Piel de piedra",
        descripcion="recibes 1 punto menos de daño de cualquier golpe",
    ),
    "lengua_mercado": Rasgo(
        clave="lengua_mercado",
        nombre="Lengua de mercado",
        descripcion="pagas 1 moneda menos en cada compra",
    ),
}


@dataclass
class Combatiente:
    """Base de todo el que puede pelear."""

    nombre: str
    vida: int
    vida_max: int
    ataque: int
    defensa: int = 0

    @property
    def vivo(self) -> bool:
        return self.vida > 0

    def recibir(self, dano: int) -> int:
        """Aplica daño tras la defensa; devuelve el daño efectivo."""
        efectivo = max(1, dano - self.defensa)
        self.vida = max(0, self.vida - efectivo)
        return efectivo

    def curar(self, puntos: int) -> None:
        self.vida = min(self.vida_max, self.vida + max(0, puntos))


@dataclass
class Enemigo(Combatiente):
    """Criatura hostil controlada por el juego."""

    clave: str = ""
    sin_huida: bool = False  # los guardianes no dejan escapar


@dataclass
class Companero:
    """Aliado que viaja y pelea con el jugador."""

    clave: str
    nombre: str
    vida: int
    vida_max: int
    ataque: int
    defensa: int = 0
    viva: bool = True

    @property
    def vivo(self) -> bool:
        return self.vida > 0

    def recibir(self, dano: int) -> int:
        efectivo = max(1, dano - self.defensa)
        self.vida = max(0, self.vida - efectivo)
        return efectivo

    def como_combatiente(self) -> Combatiente:
        return Combatiente(self.nombre, self.vida, self.vida_max, self.ataque, self.defensa)


@dataclass
class Jugador:
    """El héroe elegido: lleva los rasgos de su ficha sobre sus hombros."""

    nombre: str
    vida: int = 45
    vida_max: int = 45
    ataque: int = 4
    corrupcion: int = 0
    monedas: int = 10
    inventario: list[str] = field(default_factory=list)
    companeros: list[Companero] = field(default_factory=list)
    rasgos: list[str] = field(default_factory=list)  # claves de RASGOS

    @property
    def vivo(self) -> bool:
        return self.vida > 0

    def tiene(self, rasgo: str) -> bool:
        return rasgo in self.rasgos

    def companeras_vivas(self) -> list[Companero]:
        return [c for c in self.companeros if c.viva]

    def curar(self, puntos: int) -> None:
        self.vida = min(self.vida_max, self.vida + max(0, puntos))

    def corruptear(self, puntos: int) -> None:
        self.corrupcion = max(0, min(CORRUPCION_MAXIMA, self.corrupcion + puntos))

    def recepcion(self) -> str:
        """Barra de corrupción para el estado."""
        lleno = round(self.corrupcion / 10)
        return "[" + "▓" * lleno + "░" * (10 - lleno) + "]"

"""El combate: duelos por turnos, la tómbola del enemigo, venenos y XP.

Un lugar con enemigos resuelve sus duelos uno a uno (`_combate`); cada
duelo alterna el turno del jugador (menú de combate, issue 36) con el
del enemigo, cuya acción sale de una tómbola ponderada entre el golpe
normal y sus habilidades declarativas. Ensambla `nucleo.Juego`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...contenido.aventura import Aventura
from ...contenido.mundo import normaliza
from ...contenido.personajes import (
    SUBIDA_ATAQUE,
    SUBIDA_VIDA,
    XP_NIVEL,
    Combatiente,
    Companero,
    Enemigo,
    Habilidad,
    Jugador,
)
from ..dificultad import ajusta
from .constantes import AMARILLO, DIM, PESO_GOLPE, ROJO, VERDE

if TYPE_CHECKING:
    from .nucleo import Juego


def _titulo_combate(self: Juego, enemigo: Enemigo) -> str:
    """El bloque del duelo, como título del menú (issue 36).

    La vida de todos en barras y los renglones del último turno,
    en el mismo sitio: los duelos largos no apilan líneas. En modo
    tipeado, el título de siempre — el turno se cuenta entero.
    """
    if not self._usa_flechas():
        return f"¡{enemigo.nombre}! ¿Qué haces?"
    lineas = [f"¡{enemigo.nombre}! ¿Qué haces?"]
    margen = max(
        [len(enemigo.nombre), len(self.jugador.nombre)]
        + [len(c.nombre) for c in self.jugador.companeros]
    )
    filas: list[tuple[str, int, int, str | None]] = [
        (enemigo.nombre, enemigo.vida, enemigo.vida_max, ROJO)
    ]
    filas.append((self.jugador.nombre, self.jugador.vida, self.jugador.vida_max, VERDE))
    filas += [
        (c.nombre, c.vida, c.vida_max, None if c.viva else DIM)
        for c in self.jugador.companeros
    ]
    for nombre, vida, vida_max, color in filas:
        barra = f"{self._barra(vida, vida_max)} {vida}/{vida_max}"
        linea = f"  {nombre:<{margen}}  {barra}"
        lineas.append(self._c(linea, color) if color else linea)
    if self.jugador.envenenado:
        lineas.append(
            self._c(
                f"  Envenenado: −{self.jugador.veneno_dano} por turno ({self.jugador.veneno_turnos} turnos).",
                AMARILLO,
            )
        )
    if self._turno_lineas:  # el último turno, debajo del estado; nada se repite
        lineas += self._turno_lineas[-4:]
        self._turno_lineas.clear()
    return "\n".join(lineas)


def _objetivo(self: Juego) -> Combatiente:
    vivas = self.jugador.companeras_vivas()
    if vivas and self.rng.random() < 0.5:
        return self.rng.choice(vivas)
    return self.jugador


def _recibe(self: Juego, objetivo: Combatiente, dano: int) -> int:
    """Aplica daño a un combatiente o al jugador (defensa según armadura)."""
    if isinstance(objetivo, Jugador):
        mitigacion = self.bonus_armadura() + self._modificador("dano_recibido_menos")
        efectivo = max(1, dano - mitigacion)
        self.jugador.vida = max(0, self.jugador.vida - efectivo)
        return efectivo
    return objetivo.recibir(dano)


def _golpea(self: Juego, atacante: Combatiente, objetivo: Combatiente, extra: int = 3) -> int:
    ataque = self.ataque_total() if atacante is self.jugador else atacante.ataque
    dano = self.rng.randint(max(1, ataque), ataque + extra)
    if atacante is self.jugador:
        dano += self._modificador("dano_extra", objetivo=objetivo)
    return self._recibe(objetivo, dano)


def _duelo(self: Juego, enemigo: Enemigo) -> str:
    """Un enemigo por vez. Devuelve victoria | huida | muerte."""
    self.peligro(f"\n¡{enemigo.nombre} se abalanza!")
    # los estados alterados viven lo que vive el combate
    self._limpiar_estados(enemigo)
    self.stats.empieza_combate(self.lugar, enemigo.clave, enemigo.nombre)
    usos: dict[int, int] = {}  # cuántas veces usó cada habilidad
    try:
        while not self.fin:
            accion = self._turno_jugador(enemigo)
            self.stats.cuenta_turno()
            if accion == "huida":
                return "huida"
            if accion == "cuerno":
                self.exito(f"{enemigo.nombre} huye con los demás. Combate resuelto.")
                return "victoria"
            if self.fin:
                return "muerte"
            if not enemigo.vivo:
                self.exito(f"{enemigo.nombre} cae y se deshace en humo pardo.")
                return "victoria"
            # el turno del enemigo también va al bloque del duelo
            self._bloque_activo = self._usa_flechas()
            try:
                self._turno_enemigo(enemigo, usos)
            finally:
                self._bloque_activo = False
    finally:
        self._limpiar_estados(enemigo)
        if self.fin:  # muerte o partida suspendida: lo del bloque, al relato
            self._vuelca_bloque()
    return "muerte"


def _limpiar_estados(self: Juego, enemigo: Enemigo) -> None:
    self.jugador.veneno_dano = self.jugador.veneno_turnos = 0
    enemigo.cargado = 0
    enemigo.texto_cargado = ""


def _turno_enemigo(self: Juego, enemigo: Enemigo, usos: dict[int, int]) -> None:
    """El turno del enemigo: fase pendiente, veneno y su acción.

    Si el héroe cae aquí dentro, deja `fin`/`final` puestos, como el
    resto del motor.
    """
    enemigo.turno += 1
    transicion = enemigo.avanzar_fase()
    if transicion:
        self.peligro("\n" + transicion)
    if self._pica_veneno():
        return
    if enemigo.cargado:  # el golpe avisado cae sí o sí
        self._ataca_enemigo(
            enemigo,
            extra=enemigo.cargado,
            texto=enemigo.texto_cargado or f"{enemigo.nombre} suelta el golpe que venía tensando",
        )
        enemigo.cargado = 0
        enemigo.texto_cargado = ""
        return
    candidatos: list[str | int] = ["golpe"]
    pesos = [PESO_GOLPE]
    for i, hab in enumerate(enemigo.habilidades):
        if self._habilitada(enemigo, hab, usos.get(i, 0)):
            candidatos.append(i)
            pesos.append(hab.peso)
    eleccion = self.rng.choices(candidatos, pesos)[0]
    if isinstance(eleccion, str):  # "golpe": el ataque normal gana la tómbola
        self._ataca_enemigo(enemigo)
    else:
        self._usa_habilidad(enemigo, enemigo.habilidades[eleccion], eleccion, usos)


def _habilitada(self: Juego, enemigo: Enemigo, hab: Habilidad, usada: int) -> bool:
    """La habilidad entra en la tómbola de este turno."""
    if hab.veces and usada >= hab.veces:
        return False
    if hab.cond_vida is not None and enemigo.vida >= enemigo.vida_max * hab.cond_vida / 100:
        return False
    return hab.cond_turnos is None or enemigo.turno % hab.cond_turnos == 0


def _usa_habilidad(
    self: Juego, enemigo: Enemigo, hab: Habilidad, indice: int, usos: dict[int, int]
) -> None:
    """Ejecuta la habilidad elegida: cada tipo, su efecto y su texto."""
    usos[indice] = usos.get(indice, 0) + 1
    if hab.tipo == "veneno":
        self.jugador.envenenar(hab.dano, hab.turnos)
        self.peligro(f"{hab.texto} (−{hab.dano} por turno durante {hab.turnos} turnos).")
    elif hab.tipo == "curarse":
        antes = enemigo.vida
        enemigo.curar(hab.puntos)
        self.aviso(
            f"{hab.texto} (+{enemigo.vida - antes} vida: {enemigo.vida}/{enemigo.vida_max})."
        )
    elif hab.tipo == "refuerzo":
        self.enemigos[self.lugar].append(hab.enemigo)
        nombre = self.av.enemigos[hab.enemigo]["nombre"]
        self.peligro(f"{hab.texto} ¡{nombre} entra en combate!")
    elif hab.tipo == "golpe_fuerte":
        enemigo.cargado = hab.dano_extra
        enemigo.texto_cargado = hab.texto_golpe
        self.aviso(hab.texto_aviso)


def _pica_veneno(self: Juego) -> bool:
    """El veneno cobra su turno al empezar el del enemigo.

    Devuelve True si el héroe cayó envenenado: la partida se acaba.
    """
    j = self.jugador
    if not j.envenenado:
        return False
    j.veneno_turnos -= 1
    j.vida = max(0, j.vida - j.veneno_dano)
    self.stats.golpe_recibido(j.veneno_dano)
    self.peligro(f"El veneno arde: −{j.veneno_dano} ({j.vida}/{j.vida_max}).")
    if j.veneno_turnos <= 0:
        j.veneno_dano = j.veneno_turnos = 0
        self.tenue("El ardor del veneno se apaga.")
    if not j.vivo:
        self.aviso("\n" + self._texto_heroe(self.av.epilogo_muerte))
        self.fin = True
        self.final = "muerte"
        return True
    return False


def _ataca_enemigo(self: Juego, enemigo: Enemigo, extra: int = 0, texto: str = "") -> None:
    """El enemigo pega a su objetivo: el golpe normal, o el cargado
    (que llega con `extra` de daño y su `texto` propio)."""
    objetivo = self._objetivo()
    dano = self.rng.randint(max(1, enemigo.ataque), enemigo.ataque + 3) + extra
    efectivo = self._recibe(objetivo, dano)
    self.stats.golpe_recibido(efectivo)
    if texto:
        linea = texto.format(efectivo=efectivo)
    elif isinstance(objetivo, Companero):
        linea = f"{enemigo.nombre} golpea a {objetivo.nombre}: −{efectivo}"
    else:
        linea = f"{enemigo.nombre} te golpea: −{efectivo}"
    if isinstance(objetivo, Companero):
        self.peligro(f"{linea} ({objetivo.vida}/{objetivo.vida_max}).")
        if not objetivo.vivo:
            objetivo.viva = False
            self.peligro(f"{objetivo.nombre} cae…")
    else:
        self.peligro(f"{linea} ({self.jugador.vida}/{self.jugador.vida_max}).")
        if not self.jugador.vivo:
            self.aviso("\n" + self._texto_heroe(self.av.epilogo_muerte))
            self.fin = True
            self.final = "muerte"


def _turno_jugador(self: Juego, enemigo: Enemigo) -> str:
    """Acción del jugador y contraataque de los compañeros.

    Devuelve: "seguir" (turno normal), "huida" o "cuerno" (combate resuelto).
    """
    especial = normaliza(self.av.comando_especial) if self.av.comando_especial else None
    while True:
        try:
            linea = self._leer_orden(
                self._titulo_combate(enemigo),
                self._c("combate> ", DIM),
                self._opciones_combate(enemigo),
                aviso_esc="En combate no hay vuelta atrás: lucha, usa algo o huye.",
            )
        except EOFError:
            # se acabó la entrada: suspendemos la partida en vez de colgarnos
            self.fin = True
            self.final = self.final or "suspendida"
            return "seguir"
        partes = normaliza(linea).split(maxsplit=1)
        cmd = partes[0] if partes else ""
        arg = partes[1] if len(partes) > 1 else ""
        if not cmd:
            continue  # Esc en el menú: se espera otra orden
        # el turno se anota en el bloque del duelo, no en el relato
        self._bloque_activo = self._usa_flechas()
        try:
            if cmd == "atacar":
                efectivo = self._golpea(self.jugador, enemigo)
                self.stats.golpe_infligido(efectivo)
                self.escribir(f"Golpeas a {enemigo.nombre}: −{efectivo} ({enemigo.vida}/{enemigo.vida_max}).")
            elif cmd == "usar":
                clave = self._buscar_item(arg, self.jugador.inventario)
                if clave and self.av.items[clave]["tipo"] == "consumible":
                    self.jugador.inventario.remove(clave)
                    antes = self.jugador.vida
                    curacion = round(self.av.items[clave]["curacion"] * self.dificultad.curacion)
                    self.jugador.curar(curacion)
                    self.exito(f"{self.av.items[clave]['nombre']}: vida {antes} → {self.jugador.vida}.")
                else:
                    self.tenue("Eso no se puede usar en combate.")
                    continue
            elif especial and cmd == especial and self.av.ataque_especial:
                # el daño del especial ocurre dentro del evento: se mide
                # por la vida que pierde el enemigo en la llamada
                antes = enemigo.vida
                self.av.ataque_especial(self, enemigo)
                self.stats.golpe_infligido(antes - enemigo.vida)
                if self.fin:
                    return "seguir"
            elif cmd == "cuerno":
                clave = next(
                    (k for k in self.jugador.inventario if self.av.items[k]["tipo"] == "cuerno"),
                    None,
                )
                if clave:
                    if enemigo.sin_huida:
                        self.aviso("El toque resuena… y el guardián ni parpadea.")
                        continue
                    self.jugador.inventario.remove(clave)
                    self.epico("El cuerno retumba en el aire: las criaturas menores huyen despavoridas.")
                    self.enemigos[self.lugar].clear()
                    return "cuerno"
                self.tenue("No llevas ningún cuerno.")
                continue
            elif (secreto := self._buscar_secreto(cmd)) is not None:
                if secreto.texto_combate:
                    self.aviso(self._texto_heroe(secreto.texto_combate))
                else:
                    self.tenue("No es momento para eso.")
                continue
            elif cmd == "huir":
                if enemigo.sin_huida:
                    self.aviso("No hay a dónde ir: el guardián cierra el paso.")
                    continue
                if self.rng.random() < 0.55:
                    self.escribir("Retrocedes con el corazón en la garganta…")
                    return "huida"
                self.peligro("El enemigo te corta la retirada.")
            elif cmd == "estado":
                self._estado()
                continue
            elif cmd in ("inventario", "inv"):
                self._inventario()
                continue
            else:
                self.tenue(ayuda_combate(self.av))
                continue

            # acción válida: los compañeros golpean también
            for c in self.jugador.companeras_vivas():
                dano = self.rng.randint(c.ataque, c.ataque + 2)
                efectivo = enemigo.recibir(dano)
                self.stats.golpe_infligido(efectivo)
                self.escribir(f"{c.nombre} ataca: −{efectivo} ({enemigo.vida}/{enemigo.vida_max}).")
                if not enemigo.vivo:
                    break
        finally:
            self._bloque_activo = False
        return "seguir"


def _combate(self: Juego) -> None:
    """Resuelve los duelos del lugar, uno a uno, mientras haya cola.

    Los refuerzos que entren en plena pelea se suman a la cola y
    también pelean antes de que el lugar quede libre.
    """
    self.en_combate = True
    pendientes = self.enemigos[self.lugar]
    while pendientes and not self.fin:
        clave = pendientes[0]
        enemigo = self.crear_enemigo(clave)
        resultado = self._duelo(enemigo)
        self.stats.cierra_combate(resultado)
        if self.fin:
            break
        if resultado == "victoria":
            # el cuerno vacía la cola entera: ya no está quien huyó
            if clave in pendientes:
                pendientes.remove(clave)
                self.derrotados.append(clave)
            self._conceder_experiencia(clave)
            if not pendientes:
                self.exito("El aire vuelve a moverse. El camino queda libre.")
        else:  # huida
            self.lugar = self.lugar_previo
            self.aviso(
                f"Vuelves a {self.av.lugares[self.lugar].nombre}. Los enemigos siguen ahí, esperando."
            )
            break
    self.en_combate = False


def _conceder_experiencia(self: Juego, clave: str) -> None:
    """La XP del caído y, si toca, las subidas de nivel."""
    base = self.av.enemigos[clave].get("experiencia", 0)
    if base <= 0:
        return
    j = self.jugador
    j.experiencia += ajusta(base, self.dificultad.experiencia)
    self.exito(f"Ganas experiencia: {j.experiencia}.")
    while j.nivel <= len(XP_NIVEL) and j.experiencia >= XP_NIVEL[j.nivel - 1]:
        j.nivel += 1
        j.ataque += SUBIDA_ATAQUE
        j.vida_max += SUBIDA_VIDA
        j.curar(SUBIDA_VIDA)  # el aliento nuevo llega con vida nueva
        self.epico(
            f"\n¡{j.nombre} alcanza el nivel {j.nivel}! "
            f"(+{SUBIDA_ATAQUE} ataque, +{SUBIDA_VIDA} vida máxima)"
        )


def ayuda_combate(av: Aventura) -> str:
    """Recordatorio de comandos de combate para la línea de órdenes."""
    especial = f" · {av.comando_especial}" if av.comando_especial else ""
    return f"En combate: atacar · usar <cosa>{especial} · cuerno · huir · estado"

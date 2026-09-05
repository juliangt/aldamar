"""La salida en pantalla: colores, marcos de terminal y las pantallas fijas.

Aquí vive todo lo que escribe el juego fuera de la mecánica: los tonos
(`epico`, `exito`, `peligro`…), la cabecera de estado anclada a la
primera fila, el marco de scroll (issue 36), el prólogo y la pantalla
de cierre. Las funciones reciben la partida como `self: Juego` y las
ensambla `nucleo.Juego`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...interfaz import audio as modulo_audio
from ...interfaz.opciones import LIMPIAR, _es_interactivo, elegir_opcion
from .. import legado as modulo_legado
from .constantes import AMARILLO, DIM, ROJO, TITULO, VERDE

if TYPE_CHECKING:
    from .nucleo import Juego


def _c(self: Juego, texto: str, *codigos: str) -> str:
    if not self.color or not codigos:
        return texto
    return "\033[" + ";".join(codigos) + "m" + texto + "\033[0m"


def escribir(self: Juego, texto: str = "", *codigos: str) -> None:
    if self._bloque_activo:  # en pleno duelo: el turno va al bloque, no al relato
        self._turno_lineas.append(self._c(texto, *codigos))
        return
    self.salida(self._c(texto, *codigos))


def epico(self: Juego, texto: str) -> None:
    self.escribir(texto, TITULO)


def exito(self: Juego, texto: str) -> None:
    self.escribir(texto, VERDE)


def peligro(self: Juego, texto: str) -> None:
    self.escribir(texto, ROJO)


def aviso(self: Juego, texto: str) -> None:
    self.escribir(texto, AMARILLO)


def tenue(self: Juego, texto: str) -> None:
    self.escribir(texto, DIM)


def _texto_heroe(self: Juego, texto: str) -> str:
    """Sustituye {trato} y {quien} por los apodos del héroe en marcha."""
    ficha = self.av.personajes[self.personaje]
    return texto.format(trato=ficha.trato, quien=ficha.quien)


def _usa_flechas(self: Juego) -> bool:
    """Menús navegables solo con teclado y pantalla reales (o forzados)."""
    if self.flechas is None:
        return _es_interactivo(self.entrada, self.salida)
    return self.flechas


def _estado_linea(self: Juego) -> str:
    """Quién, cómo y dónde: lo que vive en la primera fila (issue 36)."""
    j = self.jugador
    return (
        f"{j.nombre} · Vida {j.vida}/{j.vida_max} · {j.monedas} monedas · {self.aqui().nombre}"
    )


def _cabecera(self: Juego) -> None:
    """Reescribe la primera fila con el estado del héroe, en el sitio.

    Guarda el cursor, ancla la fila 1 y lo restaura: no importa
    dónde esté el relato, la cabecera no lo mueve ni se mueve.
    """
    if not self._usa_flechas():
        return
    self.salida(
        "\x1b7\x1b[1;1H\x1b[2K" + self._c(self._estado_linea(), TITULO) + "\x1b8"
    )


def _activa_marco(self: Juego) -> None:
    """El marco de la partida: fila 1 fija para la cabecera, la
    historia vive de la fila 2 para abajo (issue 36)."""
    if not self._usa_flechas():
        return
    self._marco_activo = True
    self.salida("\x1b[2r\x1b[2;1H")  # el scroll pasa a vivir bajo la cabecera
    self._cabecera()
    self._estado_mostrado = self._estado_linea()


def _desactiva_marco(self: Juego) -> None:
    """Libera la región de scroll: la terminal queda como estaba."""
    if self._marco_activo:
        self._marco_activo = False
        self.salida("\x1b[r")


def _limpiar(self: Juego) -> None:
    """Una vista nueva: la pantalla limpia en modo navegable (issue 36).

    Las vistas —mirar, una conversación, un lugar nuevo— se ven
    solas; lo que no es una vista (tomar, usar, comprar…) se anota
    debajo de lo anterior hasta que llegue la próxima. En modo
    tipeado el relato es completo y no se limpia nunca.
    """
    if self._usa_flechas():
        self.salida(LIMPIAR)
        self._cabecera()
        self.salida("\x1b[2;1H")  # la vista arranca bajo la cabecera
        self._estado_mostrado = self._estado_linea()
    else:
        self._estado_mostrado = None


def _barra(self: Juego, vida: int, vida_max: int, ancho: int = 16) -> str:
    llenos = round(ancho * max(0, min(vida, vida_max)) / max(1, vida_max))
    return "█" * llenos + "░" * (ancho - llenos)


def _vuelca_bloque(self: Juego) -> None:
    """Los renglones que quedaban en el bloque del duelo, al relato."""
    for linea in self._turno_lineas:
        self.salida(linea)
    self._turno_lineas.clear()


def _prologo(self: Juego) -> None:
    ficha = self.av.personajes[self.personaje]
    self.epico(ficha.prologo or self.av.prologo)
    if self.legado and self.av.legado.importa:
        # la serie recuerda: el gesto de la fama, con la voz del héroe
        texto = self.av.legado.texto_fama or modulo_legado.FAMA
        self.epico(
            "\n"
            + texto.format(
                nombre=self.legado.get("nombre") or ficha.nombre,
                trato=ficha.trato,
                quien=ficha.quien,
            )
        )
    if not self.nombre_dado:  # «jugar otra vez» conserva el nombre puesto
        try:
            pregunta = ficha.texto_nombre or self.av.texto_nombre
            nombre = self.entrada(pregunta.format(nombre=ficha.nombre)).strip()
        except EOFError:
            nombre = ""
        if nombre:
            self.jugador.nombre = nombre
    # el nombre también es "avanzar": la presentación y la vista del
    # lugar se ven solas, sobre la pantalla recién limpiada
    self._limpiar()
    self.escribir("\n" + ficha.presentacion)
    self._mirar(limpiar=False)
    self.tenue(self._pista())


# ── la pantalla de cierre ────────────────────────────────────────
def _remate(self: Juego) -> str:
    """El título grande de la despedida, según cómo acabó."""
    final = self.final or ""
    if final == "muerte":
        return "Aquí se apaga tu historia"
    if final == "caida":
        return "La grieta te alcanzó"
    if final == "suspendida":
        return "La historia queda a medias"
    if "victoria" in final:
        if "cicatriz" in final:
            return "Ganaste… y la marca se queda"
        return "¡La noche retrocede!"
    return "Así acaba este cantar"


def _texto_cierre(self: Juego) -> str:
    """Remate, final, epílogo, balance del héroe y huella del viaje."""
    j = self.jugador
    ficha = self.av.personajes[self.personaje]
    lineas = ["═" * 66, self._remate().center(66), "═" * 66]
    if self.final not in (None, "muerte", "caida", "suspendida"):
        lineas.append(f"\nTu historia queda contada: «{self.final}».")
    if self.epilogo:
        lineas.append(f"\n{self.epilogo}")
    lineas.append("\n— El balance del héroe —")
    lineas.append(f"{j.nombre}, {ficha.titulo}")
    lineas.append(
        f"Nivel {j.nivel} · {j.experiencia} XP · Vida {j.vida}/{j.vida_max}"
        f" · Corrupción {j.corrupcion}% · Monedas: {j.monedas}"
    )
    if j.inventario:
        lineas.append("Llevabas: " + ", ".join(self.av.items[k]["nombre"] for k in j.inventario))
    if j.companeros:
        lineas.append("Compañeros: " + ", ".join(
            f"{c.nombre} ({c.vida}/{c.vida_max})" if c.viva else f"{c.nombre} (cayó)"
            for c in j.companeros
        ))
    if self.derrotados:
        cuenta: dict[str, int] = {}
        for clave in self.derrotados:
            cuenta[clave] = cuenta.get(clave, 0) + 1
        lineas.append("Enemigos derrotados: " + ", ".join(
            self.av.enemigos[clave]["nombre"] if n == 1 else f"{self.av.enemigos[clave]['nombre']} ×{n}"
            for clave, n in cuenta.items()
        ))
    if len(self.visitados) > 1:
        lineas.append(
            f"Lugares visitados: {len(self.visitados)} — "
            + ", ".join(self.av.lugares[lid].nombre for lid in self.visitados)
        )
    if self.flags:
        lineas.append("Decisiones: " + ", ".join(k.replace("_", " ") for k in self.flags))
    return "\n".join(lineas)


def _cierre(self: Juego) -> str | None:
    """La despedida a pantalla completa y el menú de «¿y ahora qué?».

    Devuelve la decisión: "otra", "menu" o None/salir.
    """
    self._desactiva_marco()  # el cierre es pantalla completa, sin marco
    if self._usa_flechas():
        self.salida(LIMPIAR)  # el cierre se ve solo, fuera del relato
    if self.audio:
        # el mismo jingle de la presentación (issue 34): la despedida
        # suena, victoria o desgracia
        modulo_audio.reproducir(entrada=self.entrada, salida=self.salida)
    lineas = self._texto_cierre().splitlines()
    for linea in lineas[:3]:
        self.epico(linea)  # el remate, en grande
    self.escribir("\n".join(lineas[3:]))
    return elegir_opcion(
        "¿Y ahora qué?",
        [
            ("otra", "Jugar otra vez", "Misma aventura, mismo héroe y dificultad"),
            ("menu", "Elegir otra aventura", "De vuelta al menú principal"),
            ("salir", "Salir", "Hasta pronto"),
        ],
        entrada=self.entrada,
        salida=self.salida,
        color=self.color,
        flechas=self.flechas,
        aviso_esc="Elige a dónde ir: otra partida, el menú o salir.",
    )

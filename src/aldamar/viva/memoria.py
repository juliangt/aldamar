"""La memoria de la sesión: hilo rodante y hechos atómicos (issue 22).

Los flags del motor recuerdan lo mecánico; esto recuerda lo narrable.
Los `hechos` son frases cortas en pasado («Ruy prometió llevar la
carta») con el lugar donde pasaron; el `hilo` es un resumen que se
condensa con el cronista cuando crece demasiado — y a lo bruto, si el
cronista no está. `para_prompt()` ordena: lo de este lugar primero,
lo reciente después, el hilo al final.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import cronista, prompts

MAX_HECHOS = 40
HILO_LIMITE = 1500  # caracteres: a partir de aquí, toca condensar


@dataclass
class Hecho:
    """Una frase atómica en pasado, con el lugar donde pasó."""

    texto: str
    lugar: str
    npc: str = ""

    def diccionario(self) -> dict:
        return {"texto": self.texto, "lugar": self.lugar, "npc": self.npc}


class Memoria:
    """Lo que la sesión va sabiendo de sí misma, para los prompts."""

    def __init__(self) -> None:
        self.hilo: str = ""
        self.hechos: list[Hecho] = []

    def anota(self, texto: str, lugar: str, npc: str = "") -> None:
        texto = texto.strip()[:200]
        if not texto:
            return
        self.hechos.append(Hecho(texto=texto, lugar=lugar, npc=npc))
        if len(self.hechos) > MAX_HECHOS:
            self.hechos = self.hechos[-MAX_HECHOS:]

    def cierra_escena(self, lugar: str, hechos: list[str], npc: str = "") -> None:
        """El cierre de una escena recién jugada: los hechos nuevos, dentro."""
        for texto in hechos:
            self.anota(texto, lugar, npc)
        # el hilo crece con lo reciente; la condensación llega cuando pesa
        ultimos = " ".join(h.strip() for h in hechos[-3:] if h.strip())
        if ultimos:
            self.hilo = (self.hilo + "\n" + ultimos).strip()

    def condensa(self, proveedor: cronista.Proveedor, sistema: str) -> None:
        """Reescribe el hilo si quedó largo; sin cronista, recorta a lo bruto."""
        if len(self.hilo) <= HILO_LIMITE:
            return
        try:
            condensado = proveedor.generar(sistema, prompts.condensa(self.hilo))
            condensado = condensado.strip()
            self.hilo = condensado[:HILO_LIMITE] if condensado else self.hilo[-HILO_LIMITE:]
        except cronista.CronistaError:
            self.hilo = self.hilo[-HILO_LIMITE:]

    def para_prompt(self, lugar_actual: str, ultimos: int = 8) -> str:
        """La memoria acotada para el prompt: este lugar, lo reciente, el hilo."""
        partes: list[str] = []
        aqui = [h.texto for h in self.hechos if h.lugar == lugar_actual]
        resto = [h.texto for h in self.hechos if h.lugar != lugar_actual][-ultimos:]
        if aqui:
            partes.append("Hechos de este lugar:\n" + "\n".join(f"- {t}" for t in aqui))
        if resto:
            partes.append("Hechos recientes:\n" + "\n".join(f"- {t}" for t in resto))
        if self.hilo:
            partes.append("Hasta ahora:\n" + self.hilo.strip())
        return "\n\n".join(partes)

    def estado(self) -> dict:
        return {
            "hilo": self.hilo,
            "hechos": [h.diccionario() for h in self.hechos],
        }

    @classmethod
    def desde_estado(cls, estado: dict) -> Memoria:
        memoria = cls()
        if not isinstance(estado, dict):
            return memoria
        memoria.hilo = str(estado.get("hilo", ""))
        for crudo in estado.get("hechos", []):
            if not isinstance(crudo, dict):
                continue
            memoria.anota(
                str(crudo.get("texto", "")),
                str(crudo.get("lugar", "")),
                str(crudo.get("npc", "")),
            )
        return memoria

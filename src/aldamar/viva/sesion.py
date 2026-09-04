"""La sesión viva: el orquestador del modo.

El único módulo que habla con cronista, director y memoria a la vez, y
la única puerta por la que entra contenido generado al juego:

    respuesta del cronista → sanear → fusionar en el dict acumulado →
    cargar_aventura_dict (la MISMA validación del contenido a mano) → commit

Si la validación rebota, el error vuelve al modelo (2 reintentos) y,
agotados, se degrada a la plantilla del director: la partida nunca se
rompe y el motor jamás ve nada que no haya pasado por aquí.
"""

from __future__ import annotations

import copy
import random
import re
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, cast

from ..contenido.aventura import Aventura
from ..contenido.cargador import AventuraInvalida, cargar_aventura_dict, valida_fragmento
from . import cronista, director, prompts
from .director import Premisa, premisa_de_diccionario
from .memoria import Memoria

if TYPE_CHECKING:  # solo anotaciones
    from ..motor.juego import Juego

# ── sanitización: lo que el modelo escribió, apto para el motor ──────────

_LLAVES = re.compile(r"\{([^{}]*)\}")

# El registro de depuración del cronista (--debug), junto a partida.json.
ARCHIVO_CRONISTA_LOG = "cronista_viva.log"

# Presupuesto de tokens por llamada: sin él, un modelo pequeño que divaga
# (los «thinking» sobre todo) puede irse minutos y agotar el timeout.
# Sobran para lo pedido (2-3 párrafos ≈ 250 tokens); lo que cortan es la
# divagación. El paso B pide más campos desde que nombra criaturas y
# botín; 450 lo cubre con holgura.
PRESUPUESTO_PROSA = 600
PRESUPUESTO_DATOS = 450


def sanea_texto(texto: str, maximo: int = 4000) -> str:
    """Llaves ajenas fuera, blancos normados y un techo de longitud.

    El motor formatea algunos textos con `.format(trato=..., quien=...)`
    (`_texto_heroe`): cualquier llave que no sea exactamente `{trato}` o
    `{quien}` revienta la partida — por eso se sanea por ingestión, no
    en el momento de imprimir.
    """
    # las dos llaves del héroe, a salvo; el resto: desenvueltas o fuera
    texto = texto.replace("{trato}", "\x00t").replace("{quien}", "\x00q")
    texto = _LLAVES.sub(lambda m: m.group(1), texto)
    texto = texto.replace("{", "").replace("}", "")
    texto = texto.replace("\x00t", "{trato}").replace("\x00q", "{quien}")
    texto = "\n".join(linea.rstrip() for linea in texto.splitlines())
    texto = re.sub(r"\n{3,}", "\n\n", texto).strip()
    if len(texto) > maximo:
        corte = texto.rfind("\n\n", 0, maximo)
        texto = texto[: corte if corte > 0 else maximo].rstrip()
    return texto


def sanea_fragmento(fragmento: dict) -> dict:
    """`sanea_texto` por todo texto del fragmento (datos puros, recursivo)."""

    def recorre(x: object) -> object:
        if isinstance(x, str):
            return sanea_texto(x)
        if isinstance(x, list):
            return [recorre(i) for i in x]
        if isinstance(x, dict):
            return {k: recorre(v) for k, v in x.items()}
        return x

    return recorre(fragmento)  # type: ignore[return-value]


def texto_de_final(texto: str, maximo: int) -> str:
    """El saneo de siempre, y encima sin las llaves del héroe.

    El epílogo del final viaja a la pantalla de cierre sin formatear:
    ahí cualquier llave se imprimiría tal cual.
    """
    return (
        sanea_texto(texto, maximo)
        .replace("{trato}", "")
        .replace("{quien}", "")
        .replace("  ", " ")
        .strip()
    )


# ── la sesión ─────────────────────────────────────────────────────────────


class SesionViva:
    """Una partida generada al vuelo: el dict acumulado, su memoria y el piso.

    `self.aventura_dict` es la verdad serializable (lo que viaja en el
    guardado); `self.av` es el objeto `Aventura` ya validado que el
    motor consume. Cada relleno de lugar reemplaza `self.av` entera.
    """

    def __init__(
        self,
        *,
        premisa: Premisa,
        heroe: str,
        proveedor: cronista.Proveedor,
        semilla: int | None = None,
        avisa: Callable[[str], None] | None = None,
        debug: bool = False,
    ) -> None:
        self.premisa = premisa
        self.heroe = heroe or str(director.ARQUETIPOS[0]["clave"])
        self.proveedor = proveedor
        self.semilla = semilla
        self.rng = random.Random(semilla)
        # el progreso paso a paso (qué le pide al modelo y cuánto tarda);
        # en partida real es `salida`, en los tests, una lista
        self.avisa = avisa or (lambda _texto: None)
        self.debug = debug  # con él, lo hablado con el modelo queda en cronista_viva.log
        esqueleto = director.esqueleto(premisa, semilla)
        self.aventura_dict: dict = esqueleto.aventura
        self.stubs: set[str] = set(esqueleto.stubs)
        self.final: str = esqueleto.final
        self.tramo: str = esqueleto.tramo
        self.memoria = Memoria()
        self.latencias: list[int] = []  # ms por llamada al cronista
        self.segundos_ultimo: float = 0.0
        self.av: Aventura | None = None

    # ── ciclo de vida ────────────────────────────────────────────────

    def construir(self) -> Aventura:
        """Prólogo, epílogos y escena inicial: la aventura lista para jugar."""
        self._afina_encuadre()
        self._rellena("p1", flags={})
        assert self.av is not None  # _ingiere la deja puesta
        return self.av

    def al_entrar(self, juego: Juego, lid: str) -> None:
        """El gancho del motor: rellena el lugar si aún era un borrador.

        Puede reemplazar `juego.av` entera (el motor vuelve a pedir el
        lugar tras la llamada) y deja los enemigos del lugar puestos.
        """
        if lid not in self.stubs:
            return
        juego.tenue("\nEl cronista toma la pluma…")
        self._rellena(lid, dict(juego.flags))
        assert self.av is not None
        juego.av = self.av
        juego.enemigos[lid] = list(self.av.lugares[lid].enemigos)
        for lugar_id, lugar in self.av.lugares.items():
            juego.enemigos.setdefault(lugar_id, list(lugar.enemigos))
        self.memoria.condensa(
            self.proveedor,
            prompts.sistema(self.premisa.texto, self._voz(), ""),
        )

    def interpretar(self, linea: str) -> str | None:
        """La entrada libre traducida a un comando del motor.

        Pendiente: sin intérprete, la línea que no corresponde a ningún
        comando queda en el aviso de siempre.
        """
        return None

    # ── el relleno de un lugar ───────────────────────────────────────

    def _rellena(self, lid: str, flags: dict) -> None:
        empieza = time.monotonic()
        plan = director.plan_encuentro(lid, flags, self.rng, tramo=self.tramo)
        fragmento = self._con_cronista(lid, plan)
        self._ingiere(fragmento, lid)
        self.stubs.discard(lid)
        self.memoria.cierra_escena(lid, list(fragmento["hechos"]))
        if not self.stubs:  # el mundo está completo: toca el desenlace
            self._afina_final()
        self.segundos_ultimo = time.monotonic() - empieza

    def _con_cronista(self, lid: str, plan: dict) -> dict:
        """Prosa y nombres del cronista; sin él o mal, plantilla del director."""
        nombre_provisional = self.aventura_dict["lugares"][lid]["nombre"]
        memoria_txt = self.memoria.para_prompt(lid)
        sistema = prompts.sistema(self.premisa.texto, self._voz(), memoria_txt)
        try:
            prosa = self._generar(
                sistema,
                prompts.escena(nombre_provisional, director.resumen_plan(plan), memoria_txt),
                f"escribiendo la llegada a {nombre_provisional}",
            )
            datos = self._generar_json(
                sistema,
                prompts.datos_escena(plan, nombre_provisional),
                prompts.schema_datos(plan),
                "recogiendo los nombres",
            )
        except cronista.CronistaError:
            self.avisa("El cronista no responde: esta escena sale de plantilla.")
            return director.plantilla(lid, plan, nombre_provisional)
        fragmento = director.rellena(lid, plan, prosa, datos, nombre_provisional)
        for intento in range(3):  # el original y hasta 2 reparaciones
            error = self._prueba(fragmento)
            if error is None:
                return fragmento
            if intento == 2:
                break
            try:
                datos = self._generar_json(
                    sistema,
                    prompts.repara(plan, prompts.como_json(fragmento), error),
                    prompts.schema_datos(plan),
                    "reparando los nombres",
                )
            except cronista.CronistaError:
                break
            fragmento = director.rellena(lid, plan, prosa, datos, nombre_provisional)
        return director.plantilla(lid, plan, nombre_provisional)

    def _afina_encuadre(self) -> None:
        """Prólogo y epílogos del cronista, con la plantilla de reserva."""
        sistema = prompts.sistema(self.premisa.texto, self._voz(), "")
        try:
            prologo = sanea_texto(
                self._generar(sistema, prompts.prologo(self.premisa.texto), "escribiendo el prólogo"),
                2200,
            )
            if len(prologo) > 80:
                self.aventura_dict["prologo_base"] = prologo
        except cronista.CronistaError:
            pass
        try:
            epilogos = self._generar_json(
                sistema,
                prompts.epilogos(self.premisa.texto),
                prompts.SCHEMA_EPILOGOS,
                "recogiendo los epílogos",
            )
            for clave in ("muerte", "caida"):
                texto = sanea_texto(str(epilogos.get(clave, "")), 1200)
                if len(texto) > 80:
                    self.aventura_dict["epilogos"][clave] = texto
        except cronista.CronistaError:
            pass

    def _afina_final(self) -> None:
        """El clímax, reescrito por el cronista cuando el mundo está completo.

        La estructura del evento final es del director (una opción sin
        epílogo, la clemencia atada a su bandera, el umbral de
        tentación): aquí solo se cambian los textos, y solo los que
        llegan con substancia. Si el cronista no responde o lo que trae
        no valida, el final de plantilla se queda tal cual.
        """
        evento = self.aventura_dict["eventos"][f"final_{self.final}"]
        sin_epilogo = next(op for op in evento["opciones"] if "epilogo" not in op)
        con_epilogo = next(op for op in evento["opciones"] if "epilogo" in op)
        sistema = prompts.sistema(
            self.premisa.texto, self._voz(), self.memoria.para_prompt(self.final)
        )
        try:
            respuesta = self._generar_json(
                sistema,
                prompts.final(
                    self.premisa.texto, self.premisa.corte, self.premisa.antagonista
                ),
                prompts.SCHEMA_FINAL,
                "escribiendo el final",
            )
        except cronista.CronistaError:
            return

        def texto(clave: str, minimo: int, maximo: int) -> str | None:
            limpio = texto_de_final(str(respuesta.get(clave, "")), maximo)
            return limpio if len(limpio) >= minimo else None

        antes = copy.deepcopy(self.aventura_dict)
        cambios = (
            (evento, "texto", texto("texto", 80, 700)),
            (evento, "pregunta", texto("pregunta", 10, 80)),
            (sin_epilogo, "titulo", texto("frente", 8, 60)),
            (con_epilogo, "titulo", texto("clemencia", 8, 60)),
            (con_epilogo, "detalle", texto("detalle_clemencia", 8, 80)),
            (con_epilogo, "epilogo", texto("epilogo_clemencia", 80, 1200)),
            (evento, "epilogo_puro", texto("epilogo_puro", 80, 1200)),
            (evento, "final_puro", texto("final_puro", 8, 80)),
            (evento, "epilogo_tentado", texto("epilogo_tentado", 80, 1200)),
            (evento, "final_tentado", texto("final_tentado", 8, 80)),
        )
        for objeto, clave, nuevo in cambios:
            if nuevo:
                objeto[clave] = nuevo
        try:
            self.av = cargar_aventura_dict(self.aventura_dict, f"aventura viva ({self.final})")
        except AventuraInvalida as e:
            self.aventura_dict = antes
            self.avisa(f"El final del cronista no validó ({e}): se queda el de plantilla.")

    # ── la única puerta: sanear → fusionar → validar → commit ───────

    def _ingiere(self, fragmento: dict, lid: str) -> None:
        fragmento = sanea_fragmento(fragmento)
        intento = copy.deepcopy(self.aventura_dict)
        self._fusiona(intento, fragmento)
        self.av = cargar_aventura_dict(intento, f"aventura viva ({lid})")
        self.aventura_dict = intento

    def _prueba(self, fragmento: dict) -> str | None:
        """El fragmento contra el validador de secciones y contra el mundo.

        Devuelve None si todo pasa; si no, el error que se le devuelve al
        modelo para reparar (primero atribuido al fragmento, después al
        mundo completo, que es la validación autoritaria).
        """
        try:
            secciones = {
                clave: fragmento[clave]
                for clave in ("items", "enemigos", "dialogos", "eventos")
                if fragmento.get(clave)
            }
            valida_fragmento(
                secciones,
                conocidos=self._conocidos(),
                origen=f"fragmento de {fragmento['lugar']}",
            )
            intento = copy.deepcopy(self.aventura_dict)
            self._fusiona(intento, fragmento)
            cargar_aventura_dict(intento, f"aventura viva ({fragmento['lugar']})")
        except AventuraInvalida as e:
            return str(e)
        return None

    @staticmethod
    def _fusiona(aventura: dict, fragmento: dict) -> None:
        """El fragmento, dentro del dict acumulado (muta `aventura`)."""
        lid = fragmento["lugar"]
        lugar = aventura["lugares"][lid]
        lugar["nombre"] = fragmento["nombre"]
        lugar["descripcion"] = fragmento["descripcion"]
        lugar["monedas"] = fragmento.get("monedas", 0)
        lugar["enemigos"] = list(fragmento.get("enemigos_del_lugar", []))
        lugar["objetos"] = list(fragmento.get("objetos", []))
        lugar["eventos"] = list(fragmento.get("eventos_del_lugar", []))
        for nombre_npc, clave_dlg in fragmento.get("npcs", {}).items():
            lugar["npcs"][nombre_npc] = clave_dlg
        for seccion in ("items", "enemigos", "dialogos", "eventos"):
            aventura.setdefault(seccion, {}).update(fragmento.get(seccion, {}))

    def _conocidos(self) -> dict[str, set[str]]:
        """Los ids ya vivos del mundo, por sección: el contexto del fragmento."""
        return {
            "items": set(self.aventura_dict["items"]),
            "enemigos": set(self.aventura_dict["enemigos"]),
            "dialogos": set(self.aventura_dict["dialogos"]),
            "eventos": set(self.aventura_dict["eventos"]),
            "lugares": set(self.aventura_dict["lugares"]),
        }

    def _generar(self, sistema: str, prompt: str, etiqueta: str) -> str:
        return cast(
            "str",
            self._llama(
                etiqueta,
                prompt,
                lambda: self.proveedor.generar(sistema, prompt, num_predict=PRESUPUESTO_PROSA),
            ),
        )

    def _generar_json(self, sistema: str, prompt: str, schema: dict, etiqueta: str) -> dict:
        return cast(
            "dict",
            self._llama(
                etiqueta,
                prompt,
                lambda: self.proveedor.generar_json(
                    sistema, prompt, schema, num_predict=PRESUPUESTO_DATOS
                ),
            ),
        )

    def _llama(self, etiqueta: str, prompt: str, llamada: Callable[[], object]) -> object:
        """Una llamada al cronista, con progreso en pantalla y memoria de latencia.

        Sin el modo en marcha, una llamada al modelo puede tardar minutos
        (y la primera, cargarlo en RAM): por eso cada paso avisa qué está
        haciendo y cuánto tardó. Con `debug`, lo hablado queda además en
        `cronista_viva.log` — qué se le pidió y qué contestó.
        """
        self.avisa(f"{etiqueta.capitalize()}…")
        empieza = time.monotonic()
        try:
            respuesta = llamada()
        except Exception as e:
            if self.debug:
                tarde = time.monotonic() - empieza
                self._a_log(
                    f"── {etiqueta} — FALLÓ tras {tarde:.1f} s\nPIDEN:\n{prompt}\n\nERROR: {e}"
                )
            raise
        finally:
            ms = round((time.monotonic() - empieza) * 1000)
            self.latencias.append(ms)
            self.avisa(f"  {etiqueta.capitalize()}: {ms / 1000:.1f} s")
        if self.debug:
            self._a_log(f"── {etiqueta} ({ms} ms)\nPIDEN:\n{prompt}\n\nDAN:\n{respuesta}")
        return respuesta

    def _a_log(self, texto: str) -> None:
        """El registro de depuración: junto al resto de archivos de partida."""
        try:
            with open(ARCHIVO_CRONISTA_LOG, "a", encoding="utf-8") as f:
                f.write(texto + "\n\n")
        except OSError:
            pass  # un registro que no nace no estorba a la partida

    def _voz(self) -> str:
        ficha = director.arquetipo(self.heroe)
        return (
            f"Se llama (de momento) {ficha['nombre']}, {ficha['titulo']}. Los "
            f"textos pueden tratarlo como «{ficha['trato']}» y referirse a él "
            f"como {ficha['quien']}."
        )

    # ── guardado: la sesión viaja en el campo `viva` (guardado v2) ───

    def estado(self) -> dict:
        """Lo que la partida guarda de la sesión: el mundo completo dentro."""
        rellenados = sorted(
            lid
            for lid in self.aventura_dict["lugares"]
            if lid != self.final and lid not in self.stubs
        )
        return {
            "premisa": self.premisa.diccionario(),
            "heroe": self.heroe,
            "tramo": self.tramo,
            "modelo": getattr(self.proveedor, "modelo", ""),
            "aventura_dict": self.aventura_dict,
            "memoria": self.memoria.estado(),
            "rellenados": rellenados,
            "latencias": self.latencias[-50:],
        }

    @classmethod
    def aventura_de_estado(cls, estado: dict, ruta: str = "<partida>") -> Aventura:
        """Solo la aventura, reconstruida del guardado: sin modelo, sin sesión."""
        return cargar_aventura_dict(estado["aventura_dict"], f"{ruta} (viva)")

    @classmethod
    def desde_estado(cls, estado: dict, proveedor: cronista.Proveedor | None = None) -> SesionViva:
        """Despierta la sesión de un guardado; los borradores siguen jugando.

        Sin modelo instalado, los lugares ya rellenados se juegan tal
        cual (viven en el dict) y los pendientes caen a plantilla.
        """
        av_dict = estado["aventura_dict"]
        final = cls._lugar_final(av_dict)
        rellenados = set(estado.get("rellenados", []))
        sesion = cls(
            premisa=premisa_de_diccionario(estado.get("premisa") or {}),
            heroe=str(estado.get("heroe") or ""),
            proveedor=proveedor or cronista.proveedor_por_defecto(),
        )
        sesion.aventura_dict = av_dict
        sesion.final = final
        sesion.tramo = str(estado.get("tramo") or "recto")
        sesion.stubs = {lid for lid in av_dict["lugares"] if lid != final} - rellenados
        sesion.memoria = Memoria.desde_estado(estado.get("memoria") or {})
        sesion.latencias = [int(x) for x in estado.get("latencias", [])]
        sesion.av = cargar_aventura_dict(av_dict, "<partida viva>")
        return sesion

    @staticmethod
    def _lugar_final(av_dict: dict) -> str:
        """El lugar que lleva el evento `final`, desde el dict del guardado."""
        for clave, ev in av_dict["eventos"].items():
            if isinstance(ev, dict) and ev.get("tipo") == "final":
                for lid, lugar in av_dict["lugares"].items():
                    if clave in lugar["eventos"]:
                        return lid
        raise AventuraInvalida("la aventura viva guardada no tiene lugar de final")

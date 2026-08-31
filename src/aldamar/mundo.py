"""El mapa de Aldamar: lugares, conexiones y contenido de cada sitio."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Lugar:
    id: str
    nombre: str
    descripcion: str
    salidas: dict[str, str] = field(default_factory=dict)  # palabra -> id destino
    objetos: list[str] = field(default_factory=list)  # claves de ITEMS
    monedas: int = 0
    enemigos: list[str] = field(default_factory=list)  # claves de ENEMIGOS
    npcs: dict[str, str] = field(default_factory=dict)  # clave npc -> clave diálogo
    tienda: bool = False
    descanso: bool = False
    evento: str | None = None  # consejo | ritual | corrupcion | final
    requiere: str | None = None  # clave de item necesaria para entrar
    requiere_texto: str = ""


def _l(
    id_: str,
    nombre: str,
    descripcion: str,
    *,
    salidas: dict[str, str] | None = None,
    **kw,
) -> Lugar:
    return Lugar(id=id_, nombre=nombre, descripcion=descripcion, salidas=salidas or {}, **kw)


LUGARES: dict[str, Lugar] = {
    "vegaverde": _l(
        "vegaverde",
        "Vegaverde",
        "Hileras de huertos, tolvaneras mecidas por el viento y la casa-redil de\n"
        "tu tío Oldo. El aire huele a tierra mojada y a pan. Hacia el este, el\n"
        "camino del molino se escabulle entre los cercos.",
        salidas={"este": "molino", "molino": "molino", "camino": "molino"},
        objetos=["provisiones", "capa_gris"],
        monedas=6,
        npcs={"belthar": "belthar_vegaverde"},
        descanso=True,
    ),
    "molino": _l(
        "molino",
        "el Camino del Molino",
        "El viejo molino chirría como una puerta que aprendió a quejarse. Los\n"
        "remolinos de polvo dorado bailan en la vereda; más allá, el Río Plata\n"
        "brilla entre sauces.",
        salidas={"oeste": "vegaverde", "vegaverde": "vegaverde", "este": "puente", "puente": "puente"},
        objetos=["provisiones"],
        monedas=6,
    ),
    "puente": _l(
        "puente",
        "el Puente de Piedra",
        "El puente cruza el Río Plata con la solemnidad de quien ha visto pasar\n"
        "siglos. Las aguas cantan abajo. Un aullido largo rasga la orilla norte\n"
        "y los sauces se encogen.",
        salidas={
            "oeste": "molino",
            "molino": "molino",
            "norte": "bosque",
            "bosque": "bosque",
            "sur": "rioclaro",
            "rioclaro": "rioclaro",
        },
        monedas=8,
        enemigos=["lobo"],
    ),
    "bosque": _l(
        "bosque",
        "el Bosque Umbrío",
        "Los del bosque colgaron faroles de musgo en las ramas altas y debajo\n"
        "de ellos el día es verde y tibio. Flechas antiguas señalan senderos;\n"
        "algo se mueve entre la espesura con un sonido de viento que suspira\n"
        "palabras.",
        salidas={"sur": "puente", "puente": "puente", "este": "valoria", "valoria": "valoria"},
        objetos=["hierbas", "antorcha"],
        monedas=6,
        enemigos=["espectro"],
        npcs={"sylvana": "sylvana"},
    ),
    "rioclaro": _l(
        "rioclaro",
        "la Aldea de Ríoclaro",
        "Casitas de piedra junto al vado, gallinas opinando sobre todo y la\n"
        "posadera de Dorotea, donde el estofado es ley. De aquí parte el camino\n"
        "real hacia Valoria, la Ciudad Dorada.",
        salidas={"norte": "puente", "puente": "puente", "sur": "valoria", "valoria": "valoria"},
        tienda=True,
        descanso=True,
        npcs={"dorotea": "dorotea"},
    ),
    "valoria": _l(
        "valoria",
        "la Ciudad Dorada de Valoria",
        "Torres blancas sobre la colina y el estandarte del Sol Levantado\n"
        "ondeando en la plaza. El Consejo del Sol te espera en la gran sala;\n"
        "hacia el este, las puertas de piedra dan a las minas goran.",
        salidas={
            "oeste": "bosque",
            "bosque": "bosque",
            "norte": "rioclaro",
            "rioclaro": "rioclaro",
            "este": "minas",
            "minas": "minas",
        },
        tienda=True,
        descanso=True,
        evento="consejo",
        npcs={"aldric": "aldric"},
    ),
    "minas": _l(
        "minas",
        "las Profundidades de Barrok",
        "Galerías de piedra azul donde los goran forjaron maravillas y ahora\n"
        "resuenan golpes que no son martillos. La antorcha escupe sombras\n"
        "propias en cada recodo.",
        salidas={"oeste": "valoria", "valoria": "valoria", "este": "cienagas", "cienagas": "cienagas"},
        requiere="antorcha",
        requiere_texto="La boca de la mina es negra como pozo: necesitas una antorcha.",
        objetos=["hacha_goran"],
        monedas=12,
        enemigos=["trasgo", "trasgo"],
        npcs={"torkan": "torkan"},
    ),
    "cienagas": _l(
        "cienagas",
        "las Ciénagas del Olvido",
        "El barro guarda caras de los que dudaron demasiado. Aquí el Corazón\n"
        "palpita contra tu pecho como un pájaro impaciente, y la niebla\n"
        "susurra lo que quieres oír.",
        salidas={"oeste": "minas", "minas": "minas", "norte": "refugio", "refugio": "refugio", "este": "yerma", "yerma": "yerma"},
        evento="corrupcion",
        enemigos=["espectro", "espectro"],
    ),
    "refugio": _l(
        "refugio",
        "la Torre de Belthar",
        "Un dedo de piedra sobre un islote seco en medio del fango. Dentro,\n"
        "libros polvorientos, pan bajo un paño y una fuente de agua clara que\n"
        "suena más vieja que la torre.",
        salidas={"sur": "cienagas", "cienagas": "cienagas"},
        evento="ritual",
        descanso=True,
        npcs={"belthar": "belthar_refugio"},
    ),
    "yerma": _l(
        "yerma",
        "los Yermos de Ceniza",
        "La tierra acaba y empieza el reino del polvo. Grietas rojas pulsan al\n"
        "compás de algo muy lejos; al noreste se alza la Aguja Pálida y al este,\n"
        "el Monte Umbak fuma como una chimenea del fin del mundo.",
        salidas={"oeste": "cienagas", "cienagas": "cienagas", "norte": "aguja", "aguja": "aguja", "este": "umbak", "umbak": "umbak"},
        requiere="estandarte",
        requiere_texto="El aire de ceniza te empuja hacia atrás: los Yermos solo se cruzan bajo el estandarte del consejo.",
        enemigos=["lobero", "lobero"],
    ),
    "aguja": _l(
        "aguja",
        "la Aguja Pálida",
        "La atalaya de Morvath, alta y vacía como una promesa rota. Escaleras\n"
        "de caracol, ecos que llegan tarde, y un frío que te conoce por tu\n"
        "nombre. Algo custodia la cima.",
        salidas={"sur": "yerma", "yerma": "yerma"},
        objetos=["corona_plata"],
        monedas=20,
        enemigos=["capitan"],
    ),
    "umbak": _l(
        "umbak",
        "el Monte Umbak",
        "La montaña respira fuego por sus heridas. La escalera de la cumbre\n"
        "sube hacia la Forja Eterna, y el Corazón de Ceniza tira del cuello\n"
        "hacia arriba, hacia casa, hacia su nacimiento.",
        salidas={"oeste": "yerma", "yerma": "yerma"},
        evento="final",
        enemigos=["custodio"],
    ),
}

LUGAR_INICIAL = "vegaverde"


def normaliza(texto: str) -> str:
    """Minúsculas sin tildes, para comparar lo que escribe el jugador."""
    import unicodedata

    sin = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in sin if not unicodedata.combining(c)).strip()


def alcanzables(desde: str = LUGAR_INICIAL) -> set[str]:
    """Conjunto de lugares alcanzables desde `desde` (sin mirar requisitos)."""
    vistos = {desde}
    pila = [desde]
    while pila:
        actual = pila.pop()
        for destino in LUGARES[actual].salidas.values():
            if destino not in vistos:
                vistos.add(destino)
                pila.append(destino)
    return vistos

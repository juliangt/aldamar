"""El Corazón de Ceniza: la primera aventura de Aldamar.

Todo el contenido narrativo y de balance vive aquí: mapa, objetos,
criaturas, compañeros, tiendas, diálogos, eventos y finales. Sumar otra
aventura = crear un módulo hermano con su propio `Aventura` y registrarlo.

Todo el material narrativo es original.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..aventura import Aventura, PersonajeInicial, registrar
from ..mundo import Lugar, nuevo_lugar as _l
from ..opciones import elegir_opcion
from ..personajes import CORRUPCION_TENTADO, Companero

if TYPE_CHECKING:  # solo anotaciones
    from ..juego import Juego
    from ..personajes import Enemigo

# ── Prólogo y héroes ─────────────────────────────────────────────────────

# El mito compartido: cómo nació el Corazón y por qué no supo morir.
PROLOGO_BASE = """Hace mil lunas, el hechicero Morvath forjó en el corazón ardiente del
Monte Umbak un amuleto al que llamó el Corazón de Ceniza. Con su aliento
oscuro doblegó a los reinos del oeste, y solo la alianza de las razas
libres —humanos, sylvos, goran y falros— logró arrancárselo.

Morvath cayó, pero su obra no supo morir: solo la Forja Eterna que lo
vio nacer puede devolverlo al fuego. Los consejeros de antaño lo
escondieron y juraron olvidar. El olvido cumplió.
"""

# El arranque de cada héroe: cómo llegó hasta él la guarda del amuleto.
PROLOGOS: dict[str, str] = {
    "tilo": """Durante veinte generaciones el amuleto durmió en un baúl de jardinería,
en la aldea falra de Vegaverde, herencia de tu tío Oldo Panverde.

Esta noche los cuervos vuelan hacia el este. Belthar el Errante,
último mago del viejo consejo, acaba de tocar tu puerta.
""",
    "ithel": """Hace una luna llegó a los Faroles una carta de plumas verdes: el viejo
Oldo Panverde, a quien el bosque debe tres siembras de paz, pedía a su
mejor ojo para una última guarda. Fuiste, porque el bosque no pide dos
veces, y llegaste a Vegaverde con el alba de hoy.

Esta noche los cuervos vuelan hacia el este. En la casa-redil, Belthar
el Errante, último mago del viejo consejo, cierra la puerta a su espalda
y asiente hacia ti.
""",
    "dagna": """La carta de un falro subió a Barrok con la última caravana de tomillas:
cien inviernos llevaba el carbón goran calentando Vegaverde, y entre
clanes las deudas no caducan. Oldo Panverde pedía una guardiana para lo
más pesado que ha existido. Bajaste de las minas con tu hacha al hombro.

Esta noche los cuervos vuelan hacia el este. En la casa-redil, Belthar
el Errante, último mago del viejo consejo, cierra la puerta a su espalda
y asiente hacia ti.
""",
    "ruy": """Dos cartas te alcanzaron la misma semana: el bando de Valoria que te
destierra para siempre, y el pliego de un viejo falro que te dio cobijo
un invierno sin preguntar tu nombre. Solo una se contesta caminando.
Llegaste a Vegaverde con el polvo del camino todavía en la capa.

Esta noche los cuervos vuelan hacia el este. En la casa-redil, Belthar
el Errante, último mago del viejo consejo, cierra la puerta a su espalda
y te busca a ti con la mirada.
""",
}

# El prólogo por defecto de la aventura: el del héroe inicial.
PROLOGO = PROLOGO_BASE + PROLOGOS["tilo"]

PERSONAJES: dict[str, PersonajeInicial] = {
    "tilo": PersonajeInicial(
        clave="tilo",
        nombre="Tilo",
        titulo="falro jardinero de Vegaverde",
        presentacion=(
            "Oldo te cuelga el Corazón al cuello con dedos temblorosos y te abraza\n"
            "como se abraza a quien ya está de viaje. Belthar asiente: el este espera."
        ),
        vida=45,
        ataque=4,
        monedas=10,
        inventario=["corazon"],
        trato="jardinero",
        quien="el jardinero",
    ),
    "ithel": PersonajeInicial(
        clave="ithel",
        nombre="Ithel",
        titulo="arquera sylva del Bosque Umbrío",
        presentacion=(
            "Oldo no te pide fuerza: te cuelga el Corazón con manos de hoja seca\n"
            "y te confía el tiro que nadie más puede hacer. «Tú que no fallas un\n"
            "blanco en vuelo, no falles este.» Belthar asiente: el este espera.\n"
            "Rasgo · Ojo de halcón: +1 de daño mientras la bestia conserve más\n"
            "de la mitad de su vida. Golpes certeros, viajeros ligeros."
        ),
        vida=36,
        ataque=4,
        monedas=12,
        inventario=["corazon", "hoja_sylva"],
        rasgos=["ojo_halcon"],
        prologo=PROLOGO_BASE + PROLOGOS["ithel"],
        texto_nombre="¿Cómo te llamas, arquera de los Faroles? ({nombre}): ",
        trato="arquera",
        quien="la arquera",
    ),
    "dagna": PersonajeInicial(
        clave="dagna",
        nombre="Dagna Escudagris",
        titulo="guerrera goran de las Profundidades de Barrok",
        presentacion=(
            "Oldo apenas logra levantar el Corazón: tú lo recibes como se recibe\n"
            "una deuda entre clanes, a dos manos y sin gestos. «Cien inviernos de\n"
            "carbón, viejo. Con esto quedamos en paz.» Belthar asiente: el este espera.\n"
            "Rasgo · Piel de piedra: recibes 1 punto menos de daño de cualquier golpe."
        ),
        vida=60,
        ataque=3,
        monedas=5,
        inventario=["corazon", "capa_gris"],
        rasgos=["piel_piedra"],
        prologo=PROLOGO_BASE + PROLOGOS["dagna"],
        texto_nombre="¿Cómo te llamas, hija de Barrok? ({nombre}): ",
        trato="guerrera",
        quien="la guerrera",
    ),
    "ruy": PersonajeInicial(
        clave="ruy",
        nombre="Ruy",
        titulo="errante proscrito de Valoria",
        presentacion=(
            "Sin título ni blasón llegas a Vegaverde, pero Oldo te reconoce: se lo\n"
            "debes, y los proscritos pagan sus deudas. Te cuelga el Corazón mirándote\n"
            "a los ojos, como se paga. Belthar asiente: el este espera.\n"
            "Rasgo · Lengua de mercado: pagas 1 moneda menos en cada compra. Un\n"
            "proscrito aprende a hacer que el oro rinda."
        ),
        vida=45,
        ataque=4,
        monedas=12,
        inventario=["corazon", "provisiones", "antorcha"],
        rasgos=["lengua_mercado"],
        prologo=PROLOGO_BASE + PROLOGOS["ruy"],
        texto_nombre="¿Cómo te llamas, errante? ({nombre}): ",
        trato="errante",
        quien="el errante",
    ),
}

# ── Objetos ──────────────────────────────────────────────────────────────
# tipo: arma | armadura | consumible | clave | cuerno | reliquia
ITEMS: dict[str, dict] = {
    "corazon": {
        "nombre": "el Corazón de Ceniza",
        "tipo": "reliquia",
        "precio": None,
        "desc": "Cuelga de tu cuello, caliente como una brasa. Solo la Forja Eterna puede recibirlo.",
    },
    "provisiones": {
        "nombre": "provisiones",
        "tipo": "consumible",
        "curacion": 15,
        "precio": 5,
        "desc": "Pan de viaje, queso duro y un puñado de ciruelas.",
    },
    "hierbas": {
        "nombre": "hierbas del bosque",
        "tipo": "consumible",
        "curacion": 8,
        "precio": None,
        "desc": "Hoja de sanjuanera machacada; saben a menta y a tierra.",
    },
    "antorcha": {
        "nombre": "antorcha",
        "tipo": "clave",
        "precio": 8,
        "desc": "Brea y estopa. Sin luz no se cruza la boca de las minas.",
    },
    "espada_corta": {
        "nombre": "espada corta",
        "tipo": "arma",
        "bonus": 2,
        "precio": 12,
        "desc": "Acero sencillo de ferrería valoriana. Fiable.",
    },
    "hoja_sylva": {
        "nombre": "hoja sylva",
        "tipo": "arma",
        "bonus": 4,
        "precio": 25,
        "desc": "Filo claro como agua de deshielo, forjado por los del bosque.",
    },
    "hacha_goran": {
        "nombre": "hacha goran",
        "tipo": "arma",
        "bonus": 6,
        "precio": None,
        "desc": "Pesa como un yunque y corta como la foto de un yunque.",
    },
    "capa_gris": {
        "nombre": "capa gris",
        "tipo": "armadura",
        "bonus": 1,
        "precio": 18,
        "desc": "Lana de tolvanera: abriga, desvía golpes y no se mancha.",
    },
    "corona_plata": {
        "nombre": "corona de plata",
        "tipo": "armadura",
        "bonus": 2,
        "precio": None,
        "desc": "Robada a un rey hace siglos. Sobre tu sien, más un recuerdo que un tesoro.",
    },
    "cuerno_valoria": {
        "nombre": "cuerno de Valoria",
        "tipo": "cuerno",
        "precio": 20,
        "desc": "Un solo toque dispersa a las criaturas menores. Se usa una vez.",
    },
    "estandarte": {
        "nombre": "estandarte del consejo",
        "tipo": "clave",
        "precio": None,
        "desc": "El Sol Levantado bordado en hilo de oro. Los Yermos solo se cruzan bajo su sombra.",
    },
}

# ── Criaturas ────────────────────────────────────────────────────────────
ENEMIGOS: dict[str, dict] = {
    "lobo": {"nombre": "lobo de sombra", "vida": 9, "ataque": 3},
    "espectro": {"nombre": "espectro de ceniza", "vida": 13, "ataque": 5},
    "trasgo": {"nombre": "trasgo de las cavernas", "vida": 11, "ataque": 4},
    "lobero": {"nombre": "lóbero alfa", "vida": 16, "ataque": 6},
    "capitan": {"nombre": "Capitán de Ceniza", "vida": 26, "ataque": 8, "defensa": 1, "sin_huida": True},
    "custodio": {"nombre": "Custodio Pálido", "vida": 38, "ataque": 9, "defensa": 1, "sin_huida": True},
}

# ── Compañeros reclutables ───────────────────────────────────────────────
RECLUTAS: dict[str, Companero] = {
    "sylvana": Companero(
        clave="sylvana",
        nombre="Sylvana de los Faroles",
        vida=18,
        vida_max=18,
        ataque=5,
    ),
    "aldric": Companero(
        clave="aldric",
        nombre="Sir Aldric de Valoria",
        vida=26,
        vida_max=26,
        ataque=5,
        defensa=1,
    ),
    "torkan": Companero(
        clave="torkan",
        nombre="Torkan Hachagris",
        vida=30,
        vida_max=30,
        ataque=6,
    ),
}

# ── Tiendas ──────────────────────────────────────────────────────────────
TIENDAS: dict[str, list[str]] = {
    "rioclaro": ["provisiones", "antorcha", "espada_corta", "capa_gris"],
    "valoria": ["provisiones", "hoja_sylva", "cuerno_valoria", "capa_gris"],
}

# ── Diálogos ─────────────────────────────────────────────────────────────
DIALOGOS: dict[str, str] = {
    "belthar_vegaverde": (
        "Belthar apoya el bastón en el umbral y no pide permiso para entrar.\n"
        "  «No vine por té. El viejo Oldo guardaba en su baúl algo que no era\n"
        "   suyo, ni de nadie de por aquí: el Corazón de Ceniza. Mil lunas\n"
        "   durmió bajo las tomillas y esta noche despertó.»\n"
        "  «Morvath murió, pero su obra no sabe morir. Solo la Forja Eterna,\n"
        "   en la cumbre del Monte Umbak, puede devolverlo al fuego que lo vio\n"
        "   nacer. Es un viaje largo y yo ya soy demasiado viejo para él.»\n"
        "  «Lévatelo al cuello y camina hacia el este. Y escúchame, {trato}:\n"
        "   no lo uses. Cada vez que susurra, deja una grieta. La montaña lo\n"
        "   destruirá; tú solo tienes que llegar.»"
    ),
    "belthar_refugio": (
        "Belthar atiza la fuente de agua clara y te mira como se mira un huerto\n"
        "con heladas: con preocupación contenida.\n"
        "  «Toca el agua si la grieta avanza. Lo que la piedra no puede limpiar,\n"
        "   a veces el agua sí.»"
    ),
    "sylvana": (
        "Entre los faroles de musgo, una arquera baja de la rama sin hacer ruido.\n"
        "  «Sylvana. Escucho tres noches cómo pita ese amuleto que llevas, y a\n"
        "   los espectros del bosque no les gusta nada tu olor. Yo tampoco, la\n"
        "   verdad, pero a ellos les pagan por hacerte daño.»\n"
        "  «Si vas hacia el este, voy contigo. Los del bosque debemos al consejo\n"
        "   una deuda vieja, y a Morvath ninguna.»\n"
        "  (Escribe  reclutar sylvana  si la quieres en tu grupo.)"
    ),
    "aldric": (
        "En la sala del consejo, un caballero de armadura deslustrada te corta el paso\n"
        "con una reverencia exacta.\n"
        "  «Sir Aldric de Valoria. El consejo ha leído las señales: los cuervos, el\n"
        "   humo, los aullidos. Si el Corazón vuelve a la Aguja, volverá también su\n"
        "   amo, y prefiero morir de viaje antes que de espera.»\n"
        "  «Lleva antorcha para las minas goran; la piedra no negocia con la oscuridad.\n"
        "   Y cruza los Yermos bajo el estandarte, o la ceniza te reconocerá.»\n"
        "  (Escribe  reclutar aldric  si lo quieres en tu grupo.)"
    ),
    "torkan": (
        "En la galería azul, un goran fornido aparta escombros con una mano y se\n"
        "enjuga la frente con la otra.\n"
        "  «Torkan Hachagris, última mano de la fragua de Barrok. Los trasgos\n"
        "   ocuparon las minas de mi clan; el hacha quedó sin trabajo.»\n"
        "  «Voy contigo hasta la montaña. No por lástima: por golpes.»\n"
        "  (Escribe  reclutar torkan  si lo quieres en tu grupo.)"
    ),
    "dorotea": (
        "Dorotea, la posadera, llena el cuenco hasta el borde.\n"
        "  «En Ríoclaro se paga justo y se come caliente. Escribe  comprar <cosa>  y\n"
        "   a ver qué te sirve, caminante. El descanso, aquí, va por la casa.»"
    ),
}

# ── Textos de eventos ────────────────────────────────────────────────────
TEXTO_CONSEJO = (
    "El Consejo del Sol Levantado te recibe de pie. Siete voces viejas\n"
    "confirman lo que ya sabes y te entregan un estandarte bordado en oro:\n"
    "  «Los Yermos solo se cruzan bajo la sombra de este paño. Que la ceniza\n"
    "   recuerde que todavía hay quien le hace frente.»\n"
    "(Recibes: estandarte del consejo.)"
)

TEXTO_RITUAL = (
    "Belthar sumerge las manos en la fuente. El agua suena a campana lejana y,\n"
    "por un momento, el Corazón deja de pesar.\n"
    "  «Una limpieza. Ni más ni menos. La grieta no se cierra del todo, pero\n"
    "   hoy respira.»\n"
    "(El grupo se cura por completo; la corrupción baja.)"
)

# ── Finales ──────────────────────────────────────────────────────────────
EPILogo_PURO = (
    "El Corazón de Ceniza cae en la Forja Eterna y el grito que suelta no es\n"
    "de metal sino de memoria: mil lunas de miedo se deshacen en un latido.\n"
    "El monte escupe el humo hacia el mar y, por primera vez en veinte\n"
    "generaciones, las tierras del oeste amanecen sin sombra en el este.\n"
    "\n"
    "En Vegaverde plantan un huerto nuevo y lo llaman El Jardín que venció\n"
    "a la Sombra. Tú solo pides una silla, un poco de sol y que nadie te\n"
    "herede nada jamás."
)

EPILogo_TENTADO = (
    "El Corazón cae y la Forja lo bebe, pero tú ya no eres el que llegó:\n"
    "la grieta quedó. Las noches te saben a humo y los espejos tardan un\n"
    "segundo en reconocerte.\n"
    "\n"
    "Aldamar te llama salvador en las plazas y reserva tu nombre para las\n"
    "veladas tristes. Salvaste el mundo; lo que no pudiste salvar fue el\n"
    "camino de vuelta hasta ti."
)

EPILogo_RECLAMO = (
    "Extiendes la mano y el Corazón ríe. La Forja Eterna se apaga como un\n"
    "ojo que entiende todo: nadie destruirá lo que ya no quiere destruirse.\n"
    "\n"
    "Del otro lado de la ceniza, en la Aguja Pálida, un trono vacío se\n"
    "endereza solo. Morvath tuvo un amuleto; tú tienes un trono que nadie\n"
    "te pidió y todo el tiempo del mundo.\n"
    "El norte aprende a decir tu nombre con la puerta cerrada."
)

EPILogo_CAIDA = (
    "La grieta se abre del todo. Ya no llevas el Corazón: el Corazón te lleva.\n"
    "\n"
    "Los cuervos del este cambian de dirección y van a tu encuentro. En\n"
    "Vegaverde apagan la lámpara de la casa que te abrió, y el viento lleva\n"
    "tu nombre hacia la Aguja Pálida como quien devuelve una carta."
)

EPILogo_MUERTE = (
    "La vista se llena de ceniza. Lo último que ves es el cielo de Aldamar,\n"
    "que sigue ahí, indiferente y hermoso.\n"
    "\n"
    "Los que viajaban contigo cargan la historia de vuelta al oeste: {quien}\n"
    "que se atrevió. El Corazón, en su cadena, espera a otro."
)

# ── El mapa ──────────────────────────────────────────────────────────────
LUGARES: dict[str, Lugar] = {
    "vegaverde": _l(
        "vegaverde",
        "Vegaverde",
        "Hileras de huertos, tolvaneras mecidas por el viento y la casa-redil de\n"
        "Oldo Panverde. El aire huele a tierra mojada y a pan. Hacia el este, el\n"
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


# ── Eventos de lugar ─────────────────────────────────────────────────────
# Reciben el juego y el lugar; usan sus helpers de escritura y corrupción.

def _evento_consejo(j: "Juego", lugar: Lugar) -> None:
    if j.flags.get("consejo"):
        return
    j.flags["consejo"] = True
    j.jugador.inventario.append("estandarte")
    j.epico("\n" + TEXTO_CONSEJO)


def _evento_ritual(j: "Juego", lugar: Lugar) -> None:
    if j.flags.get("ritual"):
        return
    j.flags["ritual"] = True
    j.jugador.curar(j.jugador.vida_max)
    for c in j.jugador.companeros:
        c.viva = True
        c.vida = c.vida_max
    j.epico("\n" + TEXTO_RITUAL)
    j.corruptear(-15)


def _evento_corrupcion(j: "Juego", lugar: Lugar) -> None:
    j.aviso("La niebla te repasa como una mano fría…")
    j.corruptear(8)


def _evento_final(j: "Juego", lugar: Lugar) -> None:
    j.escribir(
        "\nLa Forja Eterna respira frente a ti: una boca de luz lenta y antigua.\n"
        "El Corazón late contra tu pecho como un segundo corazón, y su voz ya\n"
        "no susurra: conversa. Habla de lo fácil que sería que todo el mundo\n"
        "te escuchara, por fin, si tú tuvieras la última palabra."
    )
    clave = elegir_opcion(
        "¿Qué haces?",
        [
            ("destruir", "Destruir el Corazón en la Forja Eterna", "acabar el viaje como prometiste"),
            ("reclamar", "Reclamar el Corazón", "por fin, la última palabra"),
        ],
        entrada=j.entrada,
        salida=j.salida,
        color=j.color,
        flechas=getattr(j, "flechas", None),
    )
    if clave == "reclamar":
        j.aviso("\n" + EPILogo_RECLAMO)
        j.final = "la Sombra nueva"
        j.fin = True
        return
    # destruir (también si cancela: era el desenlace por defecto)
    texto = EPILogo_TENTADO if j.jugador.corrupcion >= CORRUPCION_TENTADO else EPILogo_PURO
    j.epico("\n" + texto)
    vivas = [c.nombre for c in j.jugador.companeras_vivas()]
    if vivas:
        j.escribir(f"Junto a ti, al alba: {', '.join(vivas)}.")
    j.final = "victoria con cicatriz" if texto is EPILogo_TENTADO else "victoria pura"
    j.fin = True


# ── Golpe especial de combate: el Corazón ────────────────────────────────

def _corazon(j: "Juego", enemigo: "Enemigo") -> None:
    dano = 12 + j.jugador.corrupcion // 3
    efectivo = enemigo.recibir(dano)
    j.aviso(f"El Corazón brilla oscuro y golpea por −{efectivo}…")
    j.corruptear(15)


# ── La aventura, registrada ──────────────────────────────────────────────

AVENTURA = Aventura(
    id="corazon_ceniza",
    titulo="El Corazón de Ceniza",
    descripcion=(
        "El amuleto que durmió veinte generaciones acaba de despertar: cruza "
        "medio continente para devolverlo al fuego que lo vio nacer."
    ),
    prologo=PROLOGO,
    texto_nombre="¿Cómo te llamas, heredero de Vegaverde? ({nombre}): ",
    lugares=LUGARES,
    lugar_inicial=LUGAR_INICIAL,
    items=ITEMS,
    enemigos=ENEMIGOS,
    reclutas=RECLUTAS,
    tiendas=TIENDAS,
    dialogos=DIALOGOS,
    personajes=PERSONAJES,
    jugador_inicial="tilo",
    epilogo_muerte=EPILogo_MUERTE,
    epilogo_caida=EPILogo_CAIDA,
    comando_especial="corazon",
    texto_especial_fuera="El Corazón susurra, pero aquí no hay nadie a quien golpear.",
    ataque_especial=_corazon,
    eventos={
        "consejo": _evento_consejo,
        "ritual": _evento_ritual,
        "corrupcion": _evento_corrupcion,
        "final": _evento_final,
    },
)

registrar(AVENTURA)

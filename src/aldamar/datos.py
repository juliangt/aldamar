"""Contenido del juego: objetos, criaturas, tiendas y diálogos.

Todo el material narrativo es original.
"""

from __future__ import annotations

from .personajes import Companero

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


def crear_enemigo(clave: str) -> "object":  # evita import circular en anotaciones
    from .personajes import Enemigo

    d = ENEMIGOS[clave]
    return Enemigo(
        clave=clave,
        nombre=d["nombre"],
        vida=d["vida"],
        vida_max=d["vida"],
        ataque=d["ataque"],
        defensa=d.get("defensa", 0),
        sin_huida=d.get("sin_huida", False),
    )


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
        "  «No vine por té. Tu tío Oldo guardaba en su baúl algo que no era\n"
        "   suyo, ni de tu familia, ni de nadie de por aquí: el Corazón de\n"
        "   Ceniza. Mil lunas durmió bajo las tomillas y esta noche despertó.»\n"
        "  «Morvath murió, pero su obra no sabe morir. Solo la Forja Eterna,\n"
        "   en la cumbre del Monte Umbak, puede devolverlo al fuego que lo vio\n"
        "   nacer. Es un viaje largo y yo ya soy demasiado viejo para él.»\n"
        "  «Lévatelo al cuello y camina hacia el este. Y escúchame, jardinero:\n"
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
    "endereza solo. Morvath tuvo un amuleto; tú tienes un huerto, un nombre\n"
    "y veinte generaciones de espera.\n"
    "El norte aprende a decir tu nombre con la puerta cerrada."
)

EPILogo_CAIDA = (
    "La grieta se abre del todo. Ya no llevas el Corazón: el Corazón te lleva.\n"
    "\n"
    "Los cuervos del este cambian de dirección y van a tu encuentro. En\n"
    "Vegaverde dejan de sembrar tu silla a la mesa, y el viento lleva tu\n"
    "nombre hacia la Aguja Pálida como quien devuelve una carta."
)

EPILogo_MUERTE = (
    "La vista se llena de ceniza. Lo último que ves es el cielo de Aldamar,\n"
    "que sigue ahí, indiferente y hermoso.\n"
    "\n"
    "Los que viajaban contigo cargan la historia de vuelta al oeste: el\n"
    "jardinero que se atrevió. El Corazón, en su cadena, espera a otro."
)

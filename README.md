# Aldamar

[![CI](https://github.com/juliangt/aldamar/actions/workflows/ci.yml/badge.svg)](https://github.com/juliangt/aldamar/actions/workflows/ci.yml)

Aventuras de fantasía épica original para la terminal, en español. Un
motor multi-aventura en Python, sin dependencias: eliges un héroe,
cruzas medio continente y devuelves el amuleto al fuego que lo vio
nacer.

> **La historia del juego** — el mundo, las cuatro aventuras, los
> héroes y el resto del reparto — vive en
> [`docs/historia.md`](docs/historia.md).

> **Nota sobre derechos.** Aldamar es una obra de fantasía original:
> mundo, nombres, razas, textos y mecánicas son propios y están
> inspirados en el género de la fantasía clásica en general, sin usar
> nombres, lugares ni textos de franquicias o libros con derechos.

## Características

- **Cuatro aventuras** en español — campaña, misión, campaña y saga —,
  con la serie «Las Ascuas del Corazón» como hilo conductor.
- **11 héroes jugables**, cada uno con estadísticas, inventario,
  prólogo y don propios.
- **Combate por turnos con oficio**: habilidades enemigas (veneno,
  curación, refuerzos, golpe anunciado) y jefes que pelean por fases.
- **Progresión**: experiencia y niveles, equipo que se elige y se
  cambia, tiendas, monedas y llaves de paso.
- **Corrupción con consecuencias** en el camino y **seis finales**.
- **Legado entre aventuras**: decisiones y fama cruzan la serie.
- **Guardado** en JSON, versionado y con migración automática.
- **Reproducible por semilla**: misma semilla, misma partida.
- **Menús navegables** con flechas o texto; colores ANSI, sello ASCII
  y jingle 8-bit opcionales.
- **Cero dependencias** en tiempo de ejecución: solo la stdlib de
  Python.

## Requisitos

- [`uv`](https://docs.astral.sh/uv/) (recomendado), o Python 3.11 o
  superior para jugar desde el código.
- Una terminal. Con teclado y pantalla reales, los menús se navegan
  con flechas; en tuberías o tests, responden a texto.

## Instalación

Sin clonar nada, desde cualquier sitio:

```bash
uv tool install git+https://github.com/juliangt/aldamar.git
aldamar
```

(o descarga el wheel de una
[release](https://github.com/juliangt/aldamar/releases) y ejecuta
`uv tool install aldamar-*.whl`.)

Para jugar con el código delante, clona el repositorio y:

```bash
uv sync
uv run aldamar            # arranca el menú principal
uv run aldamar --cargar   # retomar partida.json sin pasar por el menú
uv run python -m aldamar  # también funciona sin instalar
```

## Uso

El menú de arranque pide **aventura**, **héroe** y **dificultad**, y
también permite cargar una partida guardada o leer la ayuda. Dentro
del juego, cada turno ofrece un menú con las acciones del mundo aquí y
ahora — viajar, tomar, hablar, comprar, luchar… — y `ayuda` se abre a
pantalla completa (**Esc** la cierra). No hay que memorizar verbos:
el menú es la interfaz, y el modo tipeado («Escribir un comando…»)
sigue disponible para quien prefiera escribir.

### El teclado

| Tecla | Dónde | Qué hace |
| ----- | ----- | -------- |
| ↑ / ↓ | menús | mover la selección |
| Enter | menús | confirmar la opción marcada |
| 1–9 | menús | elegir al vuelo, sin navegar |
| Esc | menús y ayudas | volver atrás / cerrar |
| cualquier tecla | presentación y cierre | avanzar |

Las gestiones (estado, inventario, equipar, guardar y cargar, ayuda)
viven en el submenú **«Otras acciones…»**, de donde se vuelve con
**Esc**.

### Comandos

| Comando             | Qué hace                                    |
| ------------------- | ------------------------------------------- |
| `mirar`             | Describe el sitio, objetos, gente y salidas |
| `ir 1` / `ir este`  | Viajar (número, dirección o nombre)         |
| `estado`            | Vida, nivel, corrupción, equipo y compañeros|
| `inventario`        | Lo que llevas                               |
| `tomar <cosa>`      | Recoger (`tomar todo`)                      |
| `comprar <cosa>`    | En tiendas                                  |
| `usar <cosa>`       | Consumir provisiones o hierbas              |
| `equipar <cosa>`    | Empuñar un arma o ponerte una armadura      |
| `desequipar <cosa>` | Guardar lo llevado puesto (`desequipar arma`)|
| `hablar <quién>`    | Escuchar a los NPCs                         |
| `reclutar <quién>`  | Sumar un aliado                             |
| `descansar`         | Curación completa donde haya cama           |
| `guardar` / `cargar`| Partidas en JSON (`partida.json`)           |
| `ayuda` / `salir`   | Ayuda y salida                              |

En combate: `atacar`, `usar <cosa>`, `corazon` (si la aventura te dejó
el amuleto), `cuerno`, `huir`, `estado`.

### Atajos de línea de comandos

Todas las flags se combinan entre sí:

| Flag | Qué hace |
| ---- | -------- |
| `--aventura <id>` | arranca directo en una aventura (`--aventura corazon_ceniza`) |
| `--dificultad <id>` | fija la dificultad (`paseo`, `camino`, `ceniza`) |
| `--personaje <id>` | elige el héroe sin pasar por el menú |
| `--cargar [archivo]` | retoma una partida guardada (`partida.json` por defecto) |
| `--semilla N` | semilla aleatoria: misma partida, mismas sorpresas |
| `--sin-color` | apaga los colores ANSI |
| `--sin-flechas` | menús respondiendo a texto, sin flechas |
| `--sin-splash` | directo al menú, sin presentación |
| `--sin-audio` | sin el jingle de entrada y de salida |
| `--stats [archivo]` | al terminar, escribe estadísticas de la partida (`estadisticas.json`) |
| `--legado <archivo>` | escribe el legado de la serie en otra ruta |
| `--debug` | conserva lo que el lanzador escribió antes del juego |
| `--version` | la versión instalada |

### Dificultades

| Perfil | Para quién | Qué ajusta |
| ------ | ---------- | ---------- |
| **Paseo por el huerto** | disfrutar la historia | más vida y monedas, enemigos flojos, corrupción lenta |
| **El camino** | el balance original | tal cual se escribió la aventura: ni más ni menos |
| **Yermos de Ceniza** | quien ya conoce el camino | menos vida, enemigos duros, corrupción ávida |

La partida guardada recuerda aventura, héroe y dificultad.

## Configuración

La primera partida de verdad deja en el directorio un
`configuracion.json` listo para editar a mano:

| Clave     | Default | Qué hace                                                       |
| --------- | ------- | -------------------------------------------------------------- |
| `audio`   | `true`  | el jingle de la presentación y del cierre                       |
| `splash`  | `true`  | la pantalla de presentación con el sello y «cualquier tecla…»   |
| `color`   | `true`  | códigos ANSI (lo contrario de `--sin-color`)                    |
| `flechas` | `true`  | menús navegables con ↑/↓ (lo contrario de `--sin-flechas`)      |
| `debug`   | `false` | conservar el informe del lanzador (como `--debug`)              |
| `semilla` | `null`  | semilla de cada partida, para una campaña repetible por defecto |

La precedencia es siempre la misma: **flag de CLI > variable de
entorno > `configuracion.json` > valores por defecto**. El archivo solo
nace en sesiones de verdad: tuberías y tests no dejan nada a su paso,
y ante un archivo roto se juega igual, con los defaults.

Para diagnosticar el arranque (si `uv` contó su build en pantalla, el
juego la limpia al empezar; en modo debug se conserva):

```bash
uv run aldamar --debug            # no limpiar: deja visible el informe del build
ALDAMAR_DEBUG=1 uv run aldamar    # lo mismo, sin tocar el comando
```

## Desarrollo

```bash
uv run pytest          # suite completa: 443 tests
uv run ruff check .    # estilo y errores baratos
uv run mypy src        # tipos
uv run python -m aldamar --semilla 7
```

La suite cubre mapa, combate, cargador, menús, habilidades, guardado,
legado, configuración y easter eggs — e incluye **una partida completa
scripted** de Vegaverde a la cumbre, posible porque el juego es
determinista bajo semilla. La sanidad del mapa corre sobre cada
aventura registrada, y en tuberías los menús responden a texto, así
que toda la interfaz se prueba sin teclado.

### Arquitectura

Tres capas, con el contenido fuera del código:

- **`contenido/`** — el modelo y la carga: el contrato `Aventura`,
  el cargador que lee y valida los JSON, los personajes, el mundo y
  el vocabulario de eventos.
- **`motor/`** — las reglas y el estado: el bucle de juego, el
  combate, el guardado, el legado, la dificultad y las preferencias.
- **`interfaz/`** — la entrada del usuario: menú principal, selector
  de opciones (flechas o texto), la presentación y el audio.

La idea central: **el motor no sabe nada de ninguna aventura en
concreto**. Lee el mapa, los objetos, los textos y los eventos desde
un objeto `Aventura`. El contenido de cada aventura vive entero en su
propio JSON; los eventos se declaran con el vocabulario de
`eventos.py` y el cargador los convierte en funciones del motor.
Añadir una aventura no toca una línea de Python.

### Decisiones de diseño

1. **El contenido vive en datos, no en código.** Aventuras, dones y
   dificultades son JSON descubiertos, validados y registrados al
   soltarlos en su directorio. El motor es genérico: no conoce
   Morvath, conoce «jefe con fases».
2. **Los eventos son un vocabulario declarativo.** Una escena, una
   decisión, una emboscada se escriben en el JSON; si un efecto nuevo
   hace falta, se extiende el vocabulario de forma genérica —nunca con
   conocimiento de un caso concreto— y el JSON sigue siendo puro dato.
3. **La semilla hace el juego reproducible.** Misma semilla, mismas
   decisiones, misma pelea. De ahí nace la prueba más fuerte de la
   suite: una partida completa scripted de Vegaverde a la cumbre.
4. **Los errores nombran archivo y campo.** El cargador verifica
   referencias (salidas, objetos, enemigos, diálogos, tiendas,
   eventos) y ante un JSON roto dice exactamente dónde.
5. **Cero dependencias en tiempo de ejecución.** Solo la stdlib: los
   colores son ANSI a mano y el jingle es un WAV generado al vuelo.
6. **El guardado está versionado y migra solo.** Los guardados viejos
   se actualizan al cargar, sin rituales.
7. **La configuración tiene una precedencia única**: flag de CLI >
   variable de entorno > `configuracion.json` > defaults. Y solo una
   sesión de verdad estrena el archivo.
8. **El legado separa lo que hereda de lo que no.** Cruzan aventuras
   las decisiones y la fama; el inventario, los niveles y las monedas
   empiezan de cero, porque cada aventura está balanceada para eso.
9. **El balance se ajusta con datos, no a ojo.** `--stats` escribe el
   informe de la partida y el [protocolo de
   playtesting](docs/playtesting.md) convierte sesiones en ajustes con
   memoria.
10. **Terminal primero, pero terminal bien.** Flechas con teclado
    real, texto en tuberías, pantallas que se limpian solas y una
    cabecera anclada: la interfaz cuida qué queda escrito, porque la
    pantalla es el relato.

### Estructura

```
src/aldamar/
├── __main__.py               # punto de entrada: python -m aldamar
├── contenido/                # el modelo y la carga del contenido
│   ├── aventura.py           # el contrato Aventura + registro de aventuras
│   ├── cargador.py           # lee y valida los JSON de aventura
│   ├── rasgos.py             # el catálogo de dones: lee y valida rasgos.json
│   ├── personajes.py         # jugador, compañeros, enemigos, corrupción, progresión, habilidades y fases
│   ├── mundo.py              # primitivas: Lugar, normaliza, alcanzables
│   └── eventos.py            # vocabulario declarativo de eventos y golpes especiales
├── motor/                    # las reglas y el estado del juego
│   ├── juego.py              # motor: bucle, comandos, combate, guardado
│   ├── dificultad.py         # lee y valida datos/dificultades.json: la Dificultad que aplica el motor
│   ├── guardado.py           # partida.json: versionado y migración
│   ├── legado.py             # el hilo de la serie: legado.json, fama y banderas canónicas
│   ├── estadisticas.py       # estadisticas.json para el playtesting
│   └── configuracion.py      # configuracion.json: preferencias del jugador
├── interfaz/                 # la entrada del usuario
│   ├── menu.py               # menú principal interactivo y ayuda
│   ├── presentacion.py       # el sello de arranque: arte ASCII, jingle y una tecla
│   ├── audio.py              # el jingle 8-bit: WAV generado al vuelo, sin dependencias
│   └── opciones.py           # selector de opciones: flechas ↑/↓ o texto
└── datos/                    # el contenido del juego, en JSON y fuera del código
    ├── rasgos.json           # los dones de héroe: nombre, descripción y efecto en datos
    ├── dificultades.json     # los perfiles de balance: multiplicadores por perfil
    └── aventuras/
        ├── corazon_ceniza.json    # la campaña original, en datos
        ├── brasa_vegaverde.json   # Las Ascuas · I (corta)
        ├── sal_y_ceniza.json      # Las Ascuas · II (media)
        └── aguja_sin_sombra.json  # Las Ascuas · III (saga)
tests/                         # mapa, combate, cargador, menú y partidas completas
```

### Integración continua

El pipeline no corre solo: con cada PR queda detenido a la puerta del
entorno `ci` (que exige revisor) y no ejecuta nada hasta que alguien
lo aprueba a mano — Actions → CI → «Review deployments» → Approve and
deploy. Sus checks son requisito para mergear a `main`.

La corrida trae las tres piezas: ruff y mypy, y la suite completa sobre
Ubuntu, macOS y Windows con Python 3.13 — donde además se construye el
wheel, se instala en un entorno limpio y se comprueba que arranca con
sus aventuras, dones y dificultades dentro.

### Extender el juego

**Una aventura nueva.** Crea `src/aldamar/datos/aventuras/mi_aventura.json`:
un objeto con `id`, `titulo`, `descripcion`, `prologo_base`,
`texto_nombre`, `lugar_inicial`, `jugador_inicial`, `epilogos`
(`muerte` y `caida`) y las secciones `personajes`, `items`, `enemigos`,
`reclutas`, `tiendas`, `dialogos`, `lugares` y `eventos` — más un
`legado` opcional si la aventura pertenece a una serie (abajo). Un campo
`orden` opcional (entero) fija su posición en el menú: menor primero,
y antes que quien no lo declara; las series lo usan para contarse en
orden. Al soltarlo en el directorio se descubre, valida y registra
solo: aparece en el menú. El cargador verifica referencias (salidas,
objetos, enemigos, diálogos, tiendas, eventos, las condiciones de las
emboscadas y los items que otorgan las decisiones) y ante un JSON roto
nombra archivo y campo. Los `dialogos` pueden ser un texto o una lista
de textos (hablar repetidas veces avanza por las capas de la charla), y
los `items` aceptan un campo opcional `texto_uso` para dar sabor
narrativo al usarlos fuera de combate.

Los **eventos** de lugar se declaran con el vocabulario de
`eventos.py`, sin código; cada lugar referencia los suyos por clave en
su campo `eventos` (una lista, en orden: una escena, una decisión y
una emboscada conviven sin pisarse), y el evento llamado `final` se
dispara cuando el lugar queda limpio de enemigos, el resto al entrar:

| Tipo           | Para qué                                                                 |
| -------------- | ------------------------------------------------------------------------ |
| `otorgar`      | Entrega un objeto, una sola vez si declara `una_vez` (flag)               |
| `curar_grupo`  | Cura al héroe, resucita y cura a los compañeros; `corrupcion` opcional    |
| `corrupcion`   | Un `aviso` y `puntos` de corrupción, cada vez que se entra                |
| `narrar`       | Relato puro: `condicion` (`flag`/`no_flag`) lo reserva a una circunstancia y `texto_grieta` + `grieta_desde` dan texto alternativo si la corrupción supera el umbral |
| `decision`     | Texto y elección con efectos: `item`, `corrupcion` y `flag` por opción    |
| `emboscar`     | Suma `enemigos` al lugar si se cumple su `condicion` (`flag`/`no_flag`)   |
| `final`        | Un texto, `opciones` de elección y el desenlace según corrupción          |

Las **banderas** (`flags`) son lo que cose una aventura consigo misma:
una `decision` deja una bandera encendida, un `emboscar` o un `narrar`
con `condicion` la leen para cobrarse su precio y una opción de `final`
puede declarar `requiere_flag` para ofrecerse solo si aquella decisión
ocurrió. Así se escriben las consecuencias tardías y los finales
múltiples de la saga, sin una línea de código en el JSON.

El **golpe especial** de combate (si la aventura quiere uno) se declara
en `comando_especial`: comando, `texto_fuera` y un `efecto` con
`dano_base`, `dano_por_corrupcion`, `corrupcion_coste` y `mensaje`.
Los **secretos** (comandos ocultos y easter eggs) se declaran en la
sección opcional `secretos`: cada entrada define `comando`, `textos`
(lista o texto único), `texto_combate` (opcional), `semillas` (respuestas
especiales según `--semilla`) y `alias` alternativos.

**Un enemigo con oficio.** Cada entrada de `enemigos` acepta, además
de `nombre`, `vida`, `ataque`, `defensa` y `sin_huida`:

- `experiencia`: la XP que paga al caer (la curva de niveles es corta:
  no hay nivel 6).
- `habilidades`: una lista de técnicas. Cada una declara `tipo`, su
  `texto` (o `texto_aviso` + `texto_golpe`, que debe mencionar
  `{efectivo}`), un `peso` frente al golpe normal y una `condicion`
  opcional (`vida_menor_que`: porcentaje de vida; `cada_n_turnos`:
  solo en turnos múltiplos de N):

| Tipo           | Para qué                                                              |
| -------------- | --------------------------------------------------------------------- |
| `veneno`       | `dano` por turno durante `turnos`; el más reciente manda               |
| `curarse`      | Recupera `puntos` de vida, sin pasarse del máximo                      |
| `refuerzo`     | Suma `enemigo` (otra clave) a la cola del lugar; `veces` por combate   |
| `golpe_fuerte` | `texto_aviso` un turno (no pega) y al siguiente el golpe con `dano_extra` |

- `fases`: la ficha de un jefe por tramos. Cada fase declara
  `vida_menor_que` (porcentaje que la dispara), `texto` de transición
  y, opcionales, `nombre`, `ataque`, `defensa` y `habilidades` (las
  que no se declaran se heredan). Los umbrales solo se cruzan hacia
  delante: curarse no deshace una fase.

La elección de habilidad es determinista bajo la semilla: mismas
decisiones, misma pelea.

**El legado de una serie.** Si tu aventura pertenece a una serie,
declara un `legado` junto a las secciones del JSON:

```json
"legado": {
  "importa": ["juramento", "grieta"],
  "exporta": { "juramento": "consejo", "grieta": "guardia" },
  "texto_fama": "Tu fama te precede, {nombre}: el cantar llegó antes que tú.",
  "heroe": true
}
```

- `exporta` mapea banderas canónicas de la serie → banderas locales
  que alguna `decision` de esta aventura deja encendidas (el cargador
  verifica que existan). Al terminar —evento `final` con nombre— se
  escriben en `legado.json`, gestionando cada aventura solo sus claves:
  la cadena entera sobrevive, no solo la última faena.
- `importa` son las canónicas que se encienden al empezar si el legado
  las trae, bajo su propio nombre: tus `condicion` y `requiere_flag`
  ya saben leerlas.
- `heroe` exporta, además, el nombre puesto por el jugador y el rasgo
  del héroe; `texto_fama` es el gesto del prólogo cuando hay legado y
  admite `{nombre}`, `{trato}` y `{quien}`.

**Un héroe nuevo.** Agrega una entrada a `personajes` de la aventura:
nombre, título, estadísticas, inventario, presentación y, si quieres,
`rasgos` (claves del catálogo `datos/rasgos.json`), `prologo_extra`,
`texto_nombre` propios y los apodos con los que los textos le hablan
(`trato`, `quien`). El menú lo ofrece automáticamente cuando hay más
de un héroe. Para acompañantes reclutables, otra entrada en `reclutas`
más su diálogo y su lugar en el mapa.

**Un don (rasgo) nuevo.** Agrega una entrada a `datos/rasgos.json` con
su `nombre`, su `descripcion` (la que muestra `estado`) y su `efecto`,
y referénciala desde la ficha de un héroe: el motor lo aplica sin
tocar Python. El vocabulario de efectos son modificadores genéricos
que se suman entre dones:

```json
"escudo_runico": {
  "nombre": "Escudo rúnico",
  "descripcion": "recibes 2 puntos menos de daño de cualquier golpe",
  "efecto": {
    "dano_recibido_menos": 2
  }
}
```

- `dano_extra`: daño extra en cada golpe del héroe (admite
  `"condicion": { "vida_enemigo_mayor_que": 50 }`, un porcentaje de la
  vida del enemigo por encima del cual aplica).
- `dano_recibido_menos`: puntos que se restan de cada golpe recibido.
- `descuento_compra`: monedas menos en cada compra (el precio nunca
  baja de 1).

Si un don futuro necesita una mecánica que el vocabulario no alcanza,
se extiende el vocabulario de forma genérica —un campo nuevo y su
interpretación en el motor—, nunca con conocimiento de un don concreto.

**Una dificultad nueva.** Agrega una entrada a `datos/dificultades.json`
—junto a un campo `por_defecto` que diga con cuál se juega si nadie
elige— con su `nombre`, su `descripcion` y los multiplicadores que
quieras (los que faltan valen 1.0). El orden del menú es el del
archivo, y el cargador valida todo: multiplicadores numéricos mayores
a cero, nombre y descripción presentes, y un `por_defecto` que exista
— el error nombra archivo y campo, como siempre.

```json
"brasa": {
  "nombre": "Brasa temprana",
  "descripcion": "una escala intermedia para primeras campañas",
  "vida_enemigos": 1.15,
  "ataque_enemigos": 1.1,
  "experiencia": 1.1
}
```

Los multiplicadores disponibles son `vida_jugador`, `ataque_jugador`,
`monedas`, `vida_enemigos`, `ataque_enemigos`, `corrupcion`,
`curacion` y `experiencia`; un campo `nota` opcional guarda el porqué
del balance para quien edite el archivo después. Las claves de los
perfiles viven dentro de la partida guardada: no las renombres si hay
partidas en curso, porque `cargar` necesita encontrarlas.

## Documentación

- [`docs/historia.md`](docs/historia.md) — la historia del juego: el
  mundo, las cuatro aventuras, los héroes y el resto del reparto.
- [`docs/playtesting.md`](docs/playtesting.md) — el protocolo de
  playtesting y balance: estadísticas por partida, plantilla de
  sesión y cómo se ajusta el juego con datos.

## Origen

Este juego nació de una equivocación. Lo único que se le pidió a un
LLM fue un resumen de un libro —sin infringir copyright, pues serviría
como ejemplo en otro proyecto— y, en lugar del resumen, devolvió un
juego creado desde cero. Aldamar es ese accidente hecho obra.

Veremos qué camino sigue tomando: la partida, por ahora, apenas
comienza.

## Licencia

MIT.

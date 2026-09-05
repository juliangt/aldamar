# Aldamar

[![CI](https://github.com/juliangt/aldamar/actions/workflows/ci.yml/badge.svg)](https://github.com/juliangt/aldamar/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue?logo=python&logoColor=white)](https://www.python.org)
[![Release](https://img.shields.io/github/v/release/juliangt/aldamar)](https://github.com/juliangt/aldamar/releases)
[![Licencia](https://img.shields.io/github/license/juliangt/aldamar)](LICENSE)
[![Cronista local](https://img.shields.io/badge/cronista%20local-ollama-black?logo=ollama&logoColor=white)](https://ollama.com)

Aldamar es un juego de aventuras de fantasía épica para la terminal,
en español, construido sobre un motor multi-aventura en Python sin
dependencias externas. Incluye cuatro historias completas: en cada
partida se elige un héroe, se explora un mapa por lugares y se
enfrenta a enemigos por turnos hasta el desenlace. Y para quien quiera
un cantar que nadie escribió, un modo opcional — la **Aventura Viva** —
donde un cronista local (un LLM en tu propia máquina) narra una
historia que nace al vuelo.

> **La historia del juego** — el mundo, las aventuras, los personajes
> y los detalles del universo — está en
> [`docs/historia.md`](docs/historia.md).

> **Nota sobre derechos.** Aldamar es una obra de fantasía original:
> el mundo, los nombres, las razas, los textos y las mecánicas son
> propios, y se inspiran en la fantasía clásica en general, sin usar
> nombres, lugares ni textos de franquicias o libros con derechos.

## Características

- **Cuatro aventuras** en español — campaña, misión, campaña y saga —,
  con la serie «Las Ascuas del Corazón» como hilo conductor.
- **11 héroes jugables**, cada uno con estadísticas, inventario,
  prólogo y don propios.
- **Combate por turnos con habilidades enemigas** (veneno, curación,
  refuerzos, golpe anunciado) y jefes que cambian de fase.
- **Progresión**: experiencia y niveles, equipo que se elige y se
  cambia, tiendas, monedas y llaves de paso.
- **Corrupción con consecuencias** en el camino y **seis finales**.
- **Legado entre aventuras**: decisiones y fama cruzan la serie.
- **Guardado** en JSON, versionado y con migración automática.
- **Reproducible por semilla**: misma semilla, misma partida.
- **Modo «Aventura Viva»** (opcional): un cronista local narra una
  historia que no existe hasta que la juegas — sin guion, sin JSON y
  sin que la red salga de tu casa.
- **Menús navegables** con flechas o texto; colores ANSI, sello ASCII
  y jingle 8-bit opcionales.
- **Cero dependencias** en tiempo de ejecución: solo la stdlib de
  Python.

## Requisitos

- [`uv`](https://docs.astral.sh/uv/) (recomendado), o Python 3.11 o
  superior para jugar desde el código.
- Una terminal. Con teclado y pantalla reales, los menús se navegan
  con flechas; en tuberías o tests, responden a texto.
- Para el modo «Aventura Viva», opcional: un cronista. Suele ser
  [Ollama](https://ollama.com) en tu propia máquina con un modelo
  bajado (`ollama pull llama3.1:8b` va bien); también sirve cualquier
  servidor externo con el protocolo de OpenAI — mira «El cronista:
  local o externo». Sin cronista, el juego completo funciona igual
  que siempre.

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
del juego, cada turno presenta un menú con las acciones disponibles en
el lugar actual — viajar, tomar objetos, hablar, comprar, luchar… — y
`ayuda` se abre a pantalla completa (**Esc** la cierra). No es
necesario memorizar comandos: el modo tipeado («Escribir un
comando…») queda disponible para quien prefiera escribir.

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
| **El camino** | el balance original | los multiplicadores por defecto (todos a 1.0) |
| **Yermos de Ceniza** | quien ya conoce el camino | menos vida, enemigos duros, corrupción ávida |

La partida guardada recuerda aventura, héroe y dificultad.

### El modo «Aventura Viva»

Una experiencia opcional para quien tenga un cronista al alcance: el
Ollama de tu propia máquina o un servidor externo con el protocolo de
OpenAI. Eliges una premisa («el mar que calla», o una que escribas
tú), un héroe y la dificultad, y el cronista escribe la historia al
volar — las llegadas, los nombres, la gente que habla, el desenlace.
Ninguna partida se parece a otra, y el mundo se escribe mientras lo
andas, lugar a lugar.

La mecánica nunca es cosa del modelo: un director procedural decide
mapa, enemigos, botín y consecuencias, y todo lo que el cronista
escribe entra al motor por la misma validación que el contenido
escrito a mano. Si el modelo no responde, la escena sale de plantilla
y la partida sigue; una partida viva guardada se retoma incluso sin
modelo instalado.

```bash
ollama pull llama3.1:8b    # o el modelo que prefieras (7–8B van bien)
aldamar                    # menú → «Aventura Viva…»
```

El modo solo habla con la máquina que le digas: por defecto, tu propia
casa (`127.0.0.1` u `OLLAMA_HOST`); con un cronista externo, el
servidor que configures. Sin servicio, la pantalla explica cómo
encenderlo y se vuelve al menú sin crear nada. Con `--debug`, lo
hablado con el modelo queda en `cronista_viva.log`.

#### El cronista: local o externo

Por defecto, el modo narra un Ollama local. Para usar un cronista
externo — cualquier servidor con el protocolo de OpenAI: OpenAI,
OpenRouter, Groq, Mistral, LM Studio, vLLM… — fija el proveedor, el
host y la clave, en `configuracion.json` o en el entorno (que manda):

| Preferencia | Entorno | Qué pone |
| ----------- | ------- | -------- |
| `viva_proveedor` | `ALDAMAR_PROVEEDOR` | `ollama` (el local de siempre) o `api`; si falta, se infiere: con clave de API, `api` |
| `viva_host` | `ALDAMAR_HOST` | la base del servidor, con su versión: `https://api.openai.com/v1`, `https://openrouter.ai/api/v1`… |
| `viva_api_key` | `ALDAMAR_API_KEY` | la clave del servidor externo |
| `modelo_viva` | `ALDAMAR_MODELO` | el modelo que narra (p. ej. `mistralai/mistral-nemo`) |

Ejemplo, con OpenRouter:

```json
{
  "viva_proveedor": "api",
  "viva_host": "https://openrouter.ai/api/v1",
  "viva_api_key": "sk-or-…",
  "modelo_viva": "mistralai/mistral-nemo"
}
```

Ojo con el secreto: la clave escrita en `configuracion.json` queda en
claro en disco. Si prefieres no dejarla ahí, exporta
`ALDAMAR_API_KEY` en el entorno y deja el campo fuera del archivo. El
Ollama local no necesita clave, y `contexto_viva` solo le aplica a él
(los servidores externos gestionan su propio contexto).

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
| `modelo_viva` | `null` | el modelo que narra el modo «Aventura Viva» (también `ALDAMAR_MODELO`) |
| `contexto_viva` | `null` | el `num_ctx` del cronista (16384 si no se fija; bajarlo alivia en máquinas sin GPU) |
| `viva_proveedor` | `null` | el tipo de cronista: `ollama` o `api` (protocolo de OpenAI); sin él, se infiere de la clave |
| `viva_host` | `null` | el servidor del cronista (`ALDAMAR_HOST`); vacío = el Ollama local |
| `viva_api_key` | `null` | la clave del cronista externo (mejor `ALDAMAR_API_KEY`, que no deja secreto en el archivo) |

La precedencia es siempre la misma: **flag de CLI > variable de
entorno > `configuracion.json` > valores por defecto**. El archivo solo
se crea en sesiones interactivas — tuberías y tests no lo generan — y,
si está corrupto, el juego arranca con los valores por defecto.

Para diagnosticar el arranque (si `uv` contó su build en pantalla, el
juego la limpia al empezar; en modo debug se conserva):

```bash
uv run aldamar --debug            # no limpiar: deja visible el informe del build
ALDAMAR_DEBUG=1 uv run aldamar    # lo mismo, sin tocar el comando
```

## Desarrollo

```bash
uv run pytest          # suite completa: 565 tests
uv run ruff check .    # estilo y errores baratos
uv run mypy src        # tipos
uv run python -m aldamar --semilla 7
```

La suite cubre mapa, combate, cargador, menús, habilidades, guardado,
legado, configuración y easter eggs — incluida **una partida completa
automatizada** de principio a fin, posible porque el juego es
determinista bajo semilla. El modo «Aventura Viva» se prueba entero
contra un proveedor falso: nada de la suite llama a la red ni a un
modelo real, y el piso sin cronista se juega de punta a punta igual.
La sanidad del mapa recorre cada aventura registrada, y en tuberías
los menús responden a texto, así que toda la interfaz se prueba sin
teclado.

### Arquitectura

Tres capas, con el contenido fuera del código:

- **`contenido/`** — el modelo y la carga: el contrato `Aventura`,
  el cargador que lee y valida los JSON, los personajes, el mundo y
  el vocabulario de eventos.
- **`motor/`** — las reglas y el estado: el bucle de juego, el
  combate, el guardado, el legado, la dificultad y las preferencias.
- **`interfaz/`** — la entrada del usuario: menú principal, selector
  de opciones (flechas o texto), la presentación y el audio.

El motor es independiente del contenido: cada aventura aporta un
objeto `Aventura` con el mapa, los objetos, los textos y los eventos,
y el motor lo interpreta. El contenido de cada aventura vive entero en
su propio JSON; los eventos se declaran con el vocabulario de
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
   decisiones, misma pelea: de ahí la partida automatizada de punta a
   punta que incluye la suite.
4. **Los errores nombran archivo y campo.** El cargador verifica
   referencias (salidas, objetos, enemigos, diálogos, tiendas,
   eventos) y ante un JSON roto dice exactamente dónde.
5. **Cero dependencias en tiempo de ejecución.** Solo la stdlib: los
   colores son ANSI a mano y el jingle es un WAV generado al vuelo.
6. **El guardado está versionado y migra solo.** Los guardados viejos
   se actualizan al cargar, sin rituales.
7. **La configuración tiene una precedencia única**: flag de CLI >
   variable de entorno > `configuracion.json` > defaults. El archivo
   solo se crea en sesiones interactivas.
8. **El legado separa lo que hereda de lo que no.** Cruzan aventuras
   las decisiones y la fama; el inventario, los niveles y las monedas
   empiezan de cero, porque cada aventura está balanceada para eso.
9. **El balance se ajusta con datos, no a ojo.** `--stats` escribe el
   informe de la partida y el [protocolo de
   playtesting](docs/playtesting.md) convierte sesiones en ajustes con
   memoria.
10. **Terminal primero, pero terminal bien.** Flechas con teclado
    real, texto en tuberías, pantallas que se limpian solas y una
    cabecera anclada: la interfaz cuida qué queda escrito en pantalla.

### Estructura

```
src/aldamar/
├── __main__.py               # punto de entrada: python -m aldamar
├── contenido/                # el modelo y la carga del contenido
│   ├── aventura.py           # el contrato Aventura + registro de aventuras
│   ├── cargador/             # lee y valida los JSON de aventura
│   │   ├── carga.py          # del JSON a la Aventura registrada: completa, fragmentos y descubrimiento
│   │   ├── secciones.py      # la validación por sección: items, enemigos, lugares, eventos…
│   │   └── campos.py         # primitivas de validación: tipos exigidos y errores que nombran archivo y campo
│   ├── rasgos.py             # el catálogo de dones: lee y valida rasgos.json
│   ├── personajes.py         # jugador, compañeros, enemigos, corrupción, progresión, habilidades y fases
│   ├── mundo.py              # primitivas: Lugar, normaliza, alcanzables
│   └── eventos.py            # vocabulario declarativo de eventos y golpes especiales
├── motor/                    # las reglas y el estado del juego
│   ├── juego/                # el bucle de juego: una sola clase, Juego, repartida en módulos
│   │   ├── nucleo.py         # la clase Juego: estado y ciclo; el comportamiento vive en los módulos de abajo
│   │   ├── arranque.py       # main(): argparse, preferencias, presentación, menú y sesión
│   │   ├── navegacion.py     # la orden del jugador: menús por verbo con Esc, o línea tipeada
│   │   ├── acciones.py       # los verbos: mirar, tomar, hablar, viajar… y la corrupción
│   │   ├── combate.py        # duelos por turnos, menú de combate, venenos y XP
│   │   ├── equipo.py         # lo puesto y sus bonus; la gestión del inventario
│   │   ├── persistencia.py   # el estado de Juego a JSON y de vuelta (el esquema, en guardado.py)
│   │   ├── salida.py         # colores, marcos, cabecera anclada y pantallas fijas
│   │   └── constantes.py     # colores ANSI, claves de menú y balance del turno
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
├── viva/                     # el modo «Aventura Viva»: historia al vuelo con un LLM local
│   ├── cronista.py           # cliente Ollama (urllib): prosa y JSON con structured outputs
│   ├── director.py           # tablas + semilla: toda la mecánica; el dato vive en datos.json
│   ├── datos.json            # premisas, tramos de mapa, tablas y plantillas del modo
│   ├── prompts.py            # los prompts puros; el canon del mundo, en canon.md
│   ├── sesion.py             # ingestión validada, reparación, degradación y guardado v2
│   ├── memoria.py            # hilo rodante y hechos atómicos para los prompts
│   └── interfaz.py           # pantallas del modo: premisa, héroe y arranque
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

Aventuras, enemigos, héroes, dones y dificultades se añaden en JSON,
sin tocar una línea de Python: al soltar el archivo en su directorio,
el motor lo descubre, lo valida y lo registra solo. La guía completa —
el contrato de cada archivo, el vocabulario de eventos y ejemplos —
está en [`docs/extender.md`](docs/extender.md).

## Documentación

- [`docs/historia.md`](docs/historia.md) — la historia del juego: el
  mundo, las aventuras y los personajes.
- [`docs/extender.md`](docs/extender.md) — cómo extender el juego:
  aventuras, enemigos, héroes, dones y dificultades, todo en JSON.
- [`docs/playtesting.md`](docs/playtesting.md) — el protocolo de
  playtesting y balance: estadísticas por partida, plantilla de
  sesión y cómo se ajusta el juego con datos.

## Licencia

MIT.

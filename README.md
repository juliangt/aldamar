# Aldamar

Aventuras de fantasía épica original para la terminal, en español.
El amuleto que durmió veinte generaciones acaba de despertar: elígete
un héroe, crúzate medio continente y devuélvelo al fuego que lo vio
nacer. Y cuando el fuego se apague, quedará mucho humo que recoger.

> **Nota sobre derechos.** Aldamar es una obra de fantasía original:
> mundo, nombres, razas, textos y mecánicas son propios y están
> inspirados en el género de la fantasía clásica en general, sin usar
> nombres, lugares ni textos de franquicias o libros con derechos.

## Cómo jugar

```bash
uv sync
uv run aldamar            # arranca el menú principal
uv run aldamar --cargar   # retomar partida.json sin pasar por el menú
```

El menú de arranque te deja elegir **aventura**, **héroe** (si hay
varios) y **dificultad**, cargar una partida guardada o leer la ayuda.
Con teclado y pantalla reales, las listas se navegan con **↑/↓** y se
confirman con **Enter** (los dígitos eligen al vuelo y **Esc** vuelve
atrás); en tuberías o tests, el mismo menú se responde a texto, como
siempre. Dentro del juego ocurre lo mismo: cada turno ofrece un menú
con las acciones del mundo aquí y ahora — viajar, tomar, hablar,
comprar, luchar… — y `ayuda` se abre a pantalla completa; **Esc** la
cierra y devuelve la vista anterior. Las gestiones (estado,
inventario, guardar y cargar, ayuda) viven en el submenú **«Otras
acciones…»**, de donde sí se vuelve con **Esc**; su opción «Escribir
un comando…» abre el modo tipeado de siempre. Al elegir cualquier
opción la pantalla se limpia: el contenido nuevo se ve solo.

También el arranque: si `uv` (o el lanzador de turno) contó su build
en pantalla —«Building aldamar…», «Installed N packages…»—, el juego
limpia la terminal al empezar y ese informe no queda en medio del
relato. En modo debug sí se conserva, para diagnosticar el arranque:

```bash
uv run aldamar --debug            # no limpiar: deja visible el informe del build
ALDAMAR_DEBUG=1 uv run aldamar    # lo mismo, sin tocar el comando
```

Atajos para saltar el menú:

```bash
uv run aldamar --semilla 7 --sin-color
uv run aldamar --aventura corazon_ceniza --dificultad ceniza
uv run aldamar --sin-flechas      # menús respondiendo a texto
uv run aldamar --stats            # al terminar, escribe estadisticas.json
uv run python -m aldamar          # también funciona sin instalar
```

Dificultades: **Paseo por el huerto** (fácil), **El camino** (normal, el
balance original) y **Yermos de Ceniza** (difícil). La partida guardada
recuerda aventura, héroe y dificultad.

## El mundo

- **Aldamar** es el continente donde las cuatro razas libres —humanos,
  **sylvos** del bosque, **goran** de las montañas y **falros** de los
  valles— vencieron hace mil lunas al hechicero **Morvath**.
- Lo que no pudieron fue destruir su obra: **el Corazón de Ceniza**,
  forjado en la Forja Eterna del **Monte Umbak**. Solo allí puede
  volver al fuego.
- El amuleto durmió veinte generaciones en un baúl de Vegaverde.
  Esta noche despertó. Y llamó a los cuervos.

### Lugares

Vegaverde → Camino del Molino → Puente de Piedra → (Bosque Umbrío o
Ríoclaro) → Valoria, la Ciudad Dorada → Profundidades de Barrok →
Ciénagas del Olvido → Torre de Belthar → Yermos de Ceniza → (desvío a
la Aguja Pálida) → Monte Umbak.

## Aventuras

Cuatro campañas, ordenadas en el menú de menor a mayor aliento. Las
tres últimas forman la serie **«Las Ascuas del Corazón»**: cada
historia mantiene hilo con la anterior —personajes, lugares y
consecuencias se citan de una a otra— pero se entiende y se gana por
separado; la conexión es de continuidad, no de prerrequisito. Y desde
el legado, tus decisiones cruzan aventuras: lo que juraste, robaste o
te quedaste en la garras de una historia lo recuerda la siguiente.

| # | Aventura | Tamaño | Qué es |
| - | -------- | ------ | ------ |
| 1 | **El Corazón de Ceniza** | campaña | El amuleto despierta; de Vegaverde a la Forja Eterna. La más rica del motor: decisiones con precio, emboscadas y un jefe por fases. |
| 2 | **La Brasa de Vegaverde** | misión | La primera ascua cae en los huertos originales: ahógala. |
| 3 | **La Sal y la Ceniza** | campaña | La marea devuelve otra ascua a las salinas de Ríoclaro. |
| 4 | **La Aguja sin Sombra** | saga | La Aguja Pálida teje el humo en Morvath: decisiones que pesan, jefe por fases y más de un final. |

Hilo conductor: cuando el Corazón ardió, «el monte escupió el humo
hacia el mar» — y la obra de Morvath no supo morir. El humo volvió
del mar cargado de **ascuas** que van cayendo por Aldamar: la brasa
de Vegaverde (2), la sal grisa de la costa (3) y la llamada de la
Aguja (4). Belthar el Errante, Dorotea, Oldo Panverde, el estandarte
del consejo, héroes y compañeros de una campaña reaparecen en la
siguiente.

## Mecánicas

- **Héroes**: cuatro héroes jugables, cada uno con estadísticas,
  inventario, prólogo y **rasgo** propios. **Tilo**, falro jardinero de
  Vegaverde (equilibrado); **Ithel**, arquera sylva del Bosque Umbrío
  (*Ojo de halcón*: +1 de daño contra enemigos enteros, pero frágil);
  **Dagna Escudagris**, guerrera goran de Barrok (*Piel de piedra*:
  recibe 1 punto menos de daño; mucha vida, poco ataque) y **Ruy**,
  errante proscrito de Valoria (*Lengua de mercado*: paga 1 moneda
  menos en cada compra; viaja con provisiones y antorcha). Belthar y
  los textos saben a quién le hablan. Los dones viven en
  `rasgos.json`: cada uno declara nombre, descripción y su efecto con
  un vocabulario de modificadores que el motor aplica sin conocer
  ningún don en concreto.
- **Grupo**: puedes reclutar a **Sylvana** (arquera sylva), **Sir
  Aldric** (caballero valoriano) y **Torkan Hachagris** (herrera goran).
  Pelean solos, reciben golpes y pueden caer.
- **Corrupción**: usar el Corazón en combate golpea muy fuerte… y deja
  una grieta. Las Ciénagas también la agravan; la corona de la Aguja
  Pálida cobra la suya. La Torre de Belthar la alivia una vez, y el
  camino la lee: un NPC que huele el humo, un umbral que te reconoce.
  El epílogo cambia según cuánta grieta lleves al alba.
- **Legado**: la serie recuerda. Al terminar una aventura se escribe
  `legado.json` con banderas canónicas —el juramento, la grieta— y al
  empezar otra, las que aquella importa se encienden solas: NPCs que
  reconocen la cadena, textos alternativos para quien viene tocado y
  un «Tu fama te precede…» en el prólogo. Se heredan decisiones y
  fama; **no** se hereda inventario, niveles ni monedas: cada aventura
  está balanceada para empezar de cero. Con `--legado <archivo>` se
  escribe en otro sitio.
- **Comercio y campaña**: monedas repartidas por el mapa, tiendas en
  Ríoclaro y Valoria, y dos llaves de paso: antorcha para las minas,
  estandarte del consejo para los Yermos. El estandarte, ahora, se
  pide jurando la Alianza — o se toma en depósito, y la ceniza lo
  sabe.
- **Progresión**: cada enemigo caído paga **experiencia** (campo
  `experiencia` del enemigo) y la curva —corta y explícita— sube tu
  **nivel** hasta 5: +1 de ataque y +8 de vida máxima por nivel. Las
  dificultades ajustan la experiencia (más en *Paseo*, menos en
  *Yermos de Ceniza*). El guardado recuerda nivel y experiencia; los
  guardados viejos migran solos.
- **Equipo elegido**: nada de «llevas lo mejor del inventario»: con
  `equipar <cosa>` y `desequipar <cosa>` decides qué empuñas y qué te
  ciñes (hay opciones en el submenú de gestiones y en las tiendas).
  Al conseguir la primera arma o armadura se viste sola; a partir de
  ahí, decidir entre dos piezas es el juego.
- **Combate con decisiones**: los enemigos pueden declarar
  **habilidades** en su JSON — `veneno` (daño por turno durante N
  turnos), `curarse`, `refuerzo` (suma otro enemigo al lugar) y
  `golpe_fuerte` (se anuncia un turno y pega fuerte al siguiente: si
  lees el aviso, puedes curarte a tiempo). Cada habilidad lleva su
  texto, peso y condiciones (`vida_menor_que`, `cada_n_turnos`), y la
  elección es determinista bajo la semilla.
- **Jefes por fases**: los jefes declaran `fases` —al cruzar un
  umbral de vida cambian nombre, estadísticas y habilidades, con su
  texto de transición. Morvath no finge — y el Custodio Pálido de la
  cumbre tampoco: debajo del guarda hay una montaña.
- **Dificultades**: tres ritmos de viaje — *Paseo por el huerto*, *El
  camino* y *Yermos de Ceniza* — que ajustan vida, golpes, monedas,
  corrupción y experiencia sin tocar la historia.
- **Seis finales**: victoria pura, la victoria compartida (si llevas
  una deuda chica que pagar), victoria con cicatriz, la Sombra nueva,
  la caída en pleno camino… y la muerte.

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

En combate: `atacar`, `usar <cosa>`, `corazon`, `cuerno`, `huir`, `estado`.

## Desarrollo

```bash
uv run pytest          # suite completa, incluida una partida scripted
uv run python -m aldamar --semilla 7
```

La semilla hace el juego reproducible: los tests usan una partida
completa scripted de Vegaverde a la cumbre, y la sanidad del mapa corre
sobre cada aventura registrada.

### Estructura

```
src/aldamar/
├── personajes.py             # jugador, compañeros, enemigos, corrupción, progresión, habilidades y fases
├── rasgos.py                 # el catálogo de dones: lee y valida rasgos.json
├── rasgos.json               # los dones de héroe: nombre, descripción y efecto en datos
├── mundo.py                  # primitivas: Lugar, normaliza, alcanzables
├── dificultad.py             # presets de balance (paseo / camino / ceniza)
├── aventura.py               # el contrato Aventura + registro de aventuras
├── eventos.py                # vocabulario declarativo de eventos y golpes especiales
├── legado.py                 # el hilo de la serie: legado.json, fama y banderas canónicas
├── cargador.py               # lee y valida los JSON de aventura
├── opciones.py               # selector de opciones: flechas ↑/↓ o texto
├── menu.py                   # menú principal interactivo y ayuda
├── juego.py                  # motor: bucle, comandos, combate, guardado
└── aventuras/
    ├── corazon_ceniza.json    # la campaña original, en datos
    ├── brasa_vegaverde.json   # Las Ascuas · I (corta)
    ├── sal_y_ceniza.json      # Las Ascuas · II (media)
    └── aguja_sin_sombra.json  # Las Ascuas · III (saga)
tests/                        # mapa, combate, cargador, menú y partidas completas
```

El motor no sabe nada de ninguna aventura en concreto: lee el mapa, los
objetos, los textos y los eventos desde un objeto `Aventura`. El
contenido de "El Corazón de Ceniza" vive entero en su propio JSON y los
eventos se declaran con el vocabulario de `eventos.py` (el cargador los
convierte en funciones del motor).

## Cómo sumar contenido

**Una aventura nueva.** Crea `src/aldamar/aventuras/mi_aventura.json`:
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
nombra archivo y campo.

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

Cada lugar referencia su evento por clave; el evento llamado `final` se
dispara cuando el lugar queda limpio de enemigos, el resto al entrar.
El **golpe especial** de combate (si la aventura quiere uno) se declara
en `comando_especial`: comando, `texto_fuera` y un `efecto` con
`dano_base`, `dano_por_corrupcion`, `corrupcion_coste` y `mensaje`.
Si algún día hace falta un efecto nuevo, se suma al vocabulario en
`eventos.py`: el JSON sigue siendo puro dato.

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
decisiones, misma pelea. Toda esta sintaxis se valida en `cargador.py`
y el error nombra archivo y campo, como siempre.

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
  ya saben leerlas. `cargar_todas` rechaza una canónica importada que
  no exporte nadie.
- `heroe` exporta, además, el nombre puesto por el jugador y el rasgo
  del héroe; `texto_fama` es el gesto del prólogo cuando hay legado y
  admite `{nombre}`, `{trato}` y `{quien}`.
- Qué se hereda: decisiones y fama. Qué no: inventario, niveles ni
  monedas — cada aventura está balanceada para empezar de cero.

**Un héroe nuevo.** Agrega una entrada a `personajes` de la aventura:
nombre, título, estadísticas, inventario, presentación y, si quieres,
un `rasgo` (clave del catálogo de dones `rasgos.json`), `prologo_extra`
y `texto_nombre` propios y los apodos con los que los textos le hablan
(`trato`, `quien`). El menú lo ofrece automáticamente cuando hay más de
un héroe. Para acompañantes reclutables, otra entrada en `reclutas` más
su diálogo y su lugar en el mapa.

**Un don (rasgo) nuevo.** Agrega una entrada a `rasgos.json` con su
`nombre`, su `descripcion` (la que muestra `estado`) y su `efecto`, y
referénciala desde la ficha de un héroe: el motor lo aplica sin tocar
Python. El vocabulario de efectos son modificadores genéricos que se
suman entre dones:

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
  vida del enemigo por encima del cual aplica — así declara Ojo de
  halcón su +1 contra enemigos enteros).
- `dano_recibido_menos`: puntos que se restan de cada golpe recibido.
- `descuento_compra`: monedas menos en cada compra (el precio nunca
  baja de 1).

Si un don futuro necesita una mecánica que el vocabulario no alcanza,
se extiende el vocabulario de forma genérica —un campo nuevo y su
interpretación en el motor—, nunca con conocimiento de un don concreto.

**Una dificultad nueva.** Agrega una entrada a `DIFICULTADES` en
`dificultad.py` con sus multiplicadores (vida, ataque, monedas,
corrupción, curación, experiencia): el menú y la CLI la listan solas.

## El error que lo empezó todo

Este juego nació de una equivocación. Lo único que se le pidió a un
LLM fue un resumen de un libro —sin infringir copyright, pues serviría
como ejemplo en otro proyecto— y, en lugar del resumen, devolvió un
juego creado desde cero. Aldamar es ese accidente hecho obra.

Veremos qué camino sigue tomando: la partida, por ahora, apenas
comienza.

## Licencia

MIT.

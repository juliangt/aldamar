# Aldamar · El Corazón de Ceniza

Aventura de fantasía épica original para la terminal, en español.
El amuleto que durmió veinte generaciones acaba de despertar: elígete
un héroe, crúzate medio continente y devuélvelo al fuego que lo vio
nacer.

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

Atajos para saltar el menú:

```bash
uv run aldamar --semilla 7 --sin-color
uv run aldamar --aventura corazon_ceniza --dificultad ceniza
uv run aldamar --sin-flechas      # menús respondiendo a texto
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

## Mecánicas

- **Héroes**: cuatro héroes jugables, cada uno con estadísticas,
  inventario, prólogo y **rasgo** propios. **Tilo**, falro jardinero de
  Vegaverde (equilibrado); **Ithel**, arquera sylva del Bosque Umbrío
  (*Ojo de halcón*: +1 de daño contra enemigos enteros, pero frágil);
  **Dagna Escudagris**, guerrera goran de Barrok (*Piel de piedra*:
  recibe 1 punto menos de daño; mucha vida, poco ataque) y **Ruy**,
  errante proscrito de Valoria (*Lengua de mercado*: paga 1 moneda
  menos en cada compra; viaja con provisiones y antorcha). Belthar y
  los textos saben a quién le hablan.
- **Grupo**: puedes reclutar a **Sylvana** (arquera sylva), **Sir
  Aldric** (caballero valoriano) y **Torkan Hachagris** (herrera goran).
  Pelean solos, reciben golpes y pueden caer.
- **Corrupción**: usar el Corazón en combate golpea muy fuerte… y deja
  una grieta. Las Ciénagas también la agravan. La Torre de Belthar la
  alivia una vez. El epílogo cambia según cuánta grieta lleves al alba.
- **Comercio y campaña**: monedas repartidas por el mapa, tiendas en
  Ríoclaro y Valoria, y dos llaves de paso: antorcha para las minas,
  estandarte del consejo para los Yermos.
- **Dificultades**: tres ritmos de viaje — *Paseo por el huerto*, *El
  camino* y *Yermos de Ceniza* — que ajustan vida, golpes, monedas y
  corrupción sin tocar la historia.
- **Cinco finales**: victoria pura, victoria con cicatriz, la Sombra
  nueva, la caída en pleno camino… y la muerte.

### Comandos

| Comando             | Qué hace                                    |
| ------------------- | ------------------------------------------- |
| `mirar`             | Describe el sitio, objetos, gente y salidas |
| `ir 1` / `ir este`  | Viajar (número, dirección o nombre)         |
| `estado`            | Vida, corrupción, equipo y compañeros       |
| `inventario`        | Lo que llevas                               |
| `tomar <cosa>`      | Recoger (`tomar todo`)                      |
| `comprar <cosa>`    | En tiendas                                  |
| `usar <cosa>`       | Consumir provisiones o hierbas              |
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
├── personajes.py             # jugador, compañeros, enemigos, rasgos, corrupción
├── mundo.py                  # primitivas: Lugar, normaliza, alcanzables
├── dificultad.py             # presets de balance (paseo / camino / ceniza)
├── aventura.py               # el contrato Aventura + registro de aventuras
├── eventos.py                # vocabulario declarativo de eventos y golpes especiales
├── cargador.py               # lee y valida los JSON de aventura
├── opciones.py               # selector de opciones: flechas ↑/↓ o texto
├── menu.py                   # menú principal interactivo y ayuda
├── juego.py                  # motor: bucle, comandos, combate, guardado
└── aventuras/
    └── corazon_ceniza.json   # toda la primera aventura, en datos
tests/                        # mapa, combate, cargador, menú y partida completa
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
`reclutas`, `tiendas`, `dialogos`, `lugares` y `eventos`. Al soltarlo en
el directorio se descubre, valida y registra solo: aparece en el menú.
El cargador verifica referencias (salidas, objetos, enemigos, diálogos,
tiendas, eventos) y ante un JSON roto nombra archivo y campo.

Los **eventos** de lugar se declaran con el vocabulario de
`eventos.py`, sin código:

| Tipo           | Para qué                                                                 |
| -------------- | ------------------------------------------------------------------------ |
| `otorgar`      | Entrega un objeto, una sola vez si declara `una_vez` (flag)               |
| `curar_grupo`  | Cura al héroe, resucita y cura a los compañeros; `corrupcion` opcional    |
| `corrupcion`   | Un `aviso` y `puntos` de corrupción, cada vez que se entra                |
| `final`        | Un texto, `opciones` de elección y el desenlace según corrupción          |

Cada lugar referencia su evento por clave; el evento llamado `final` se
dispara cuando el lugar queda limpio de enemigos, el resto al entrar.
El **golpe especial** de combate (si la aventura quiere uno) se declara
en `comando_especial`: comando, `texto_fuera` y un `efecto` con
`dano_base`, `dano_por_corrupcion`, `corrupcion_coste` y `mensaje`.
Si algún día hace falta un efecto nuevo, se suma al vocabulario en
`eventos.py`: el JSON sigue siendo puro dato.

**Un héroe nuevo.** Agrega una entrada a `personajes` de la aventura:
nombre, título, estadísticas, inventario, presentación y, si quieres,
un `rasgo` (clave de `RASGOS`), `prologo_extra` y `texto_nombre`
propios y los apodos con los que los textos le hablan (`trato`,
`quien`). El menú lo ofrece automáticamente cuando hay más de un héroe.
Para acompañantes reclutables, otra entrada en `reclutas` más su
diálogo y su lugar en el mapa.

**Una dificultad nueva.** Agrega una entrada a `DIFICULTADES` en
`dificultad.py` con sus multiplicadores (vida, ataque, monedas,
corrupción, curación): el menú y la CLI la listan solas.

## El error que lo empezó todo

Este juego nació de una equivocación. Lo único que se le pidió a un
LLM fue un resumen de un libro —sin infringir copyright, pues serviría
como ejemplo en otro proyecto— y, en lugar del resumen, devolvió un
juego creado desde cero. Aldamar es ese accidente hecho obra.

Veremos qué camino sigue tomando: la partida, por ahora, apenas
comienza.

## Licencia

MIT.

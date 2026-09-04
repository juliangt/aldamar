# Extender el juego

Aldamar está pensado para crecer sin escribir Python: aventuras,
enemigos, héroes, dones y dificultades son JSON que el motor descubre,
valida y registra al soltarlos en su directorio. Ante un archivo roto,
el error nombra archivo y campo. Este documento recorre cada extensión,
una a una:

| Quiero añadir…                                  | Ir a                                            |
| ----------------------------------------------- | ----------------------------------------------- |
| una aventura: mapa, objetos, eventos, finales   | [Una aventura nueva](#una-aventura-nueva)       |
| enemigos con habilidades o un jefe con fases    | [Un enemigo nuevo](#un-enemigo-nuevo)           |
| continuidad entre las aventuras de una serie    | [El legado de una serie](#el-legado-de-una-serie) |
| un héroe jugable o un acompañante               | [Un héroe nuevo](#un-héroe-nuevo)               |
| un don de héroe                                 | [Un don (rasgo) nuevo](#un-don-rasgo-nuevo)     |
| un perfil de balance                            | [Una dificultad nueva](#una-dificultad-nueva)   |

## Una aventura nueva

Crea `src/aldamar/datos/aventuras/mi_aventura.json`. Al soltarlo en el
directorio se descubre, valida y registra solo: aparece en el menú sin
tocar una línea de Python.

### El esqueleto del archivo

Un objeto con estos campos:

| Campo              | Obligatorio        | Qué es                                                       |
| ------------------ | ------------------ | ------------------------------------------------------------ |
| `id`               | sí                 | la clave única de la aventura (la que acepta `--aventura`)    |
| `titulo`           | sí                 | el nombre en el menú                                          |
| `descripcion`      | sí                 | la línea descriptiva bajo el título                           |
| `texto_nombre`     | sí                 | cómo nombran los textos a la aventura                         |
| `lugar_inicial`    | sí                 | clave del lugar donde arranca la partida                      |
| `jugador_inicial`  | sí                 | héroe por defecto; debe existir en `personajes`               |
| `epilogos`         | sí                 | objeto con los textos `muerte` y `caida`                      |
| `personajes`       | sí, al menos uno   | los héroes jugables                                           |
| `lugares`          | sí, al menos uno   | el mapa                                                       |
| `items`            | sí (puede ir vacío)| los objetos del juego                                         |
| `enemigos`         | sí (puede ir vacío)| los enemigos                                                  |
| `reclutas`         | sí (puede ir vacío)| los acompañantes reclutables                                  |
| `dialogos`         | sí (puede ir vacío)| los textos de los NPCs                                        |
| `prologo_base`     | no                 | el prólogo común a todos los héroes                           |
| `tiendas`          | no                 | el stock de cada lugar-tienda                                 |
| `eventos`          | no                 | los eventos de lugar (ver [abajo](#los-eventos-de-lugar))     |
| `legado`           | no                 | la ficha de serie (ver [El legado de una serie](#el-legado-de-una-serie)) |
| `orden`            | no                 | la posición en el menú (ver abajo)                            |
| `comando_especial` | no                 | el golpe especial de combate (ver [abajo](#el-golpe-especial-de-combate)) |
| `secretos`         | no                 | comandos ocultos y easter eggs (ver [abajo](#los-secretos-y-easter-eggs)) |

Un campo `orden` opcional (entero) fija la posición de la aventura en
el menú: menor primero, y antes que quien no lo declara; las series lo
usan para contarse en orden.

El cargador verifica referencias (salidas, objetos, enemigos, diálogos,
tiendas, eventos, las condiciones de las emboscadas y los items que
otorgan las decisiones) y ante un JSON roto nombra archivo y campo.

Dos detalles de sabor: los `dialogos` pueden ser un texto o una lista
de textos (hablar repetidas veces avanza por las capas de la charla),
y los `items` aceptan un campo opcional `texto_uso` para dar sabor
narrativo al usarlos fuera de combate.

### Los eventos de lugar

Se declaran con el vocabulario de `eventos.py`, sin código: cada lugar
referencia los suyos por clave en su campo `eventos` — una lista, en
orden, donde una escena, una decisión y una emboscada conviven sin
pisarse. El evento llamado `final` se dispara cuando el lugar queda
limpio de enemigos; el resto, al entrar.

| Tipo           | Para qué                                                                 |
| -------------- | ------------------------------------------------------------------------ |
| `otorgar`      | Entrega un objeto, una sola vez si declara `una_vez` (flag)               |
| `curar_grupo`  | Cura al héroe, resucita y cura a los compañeros; `corrupcion` opcional    |
| `corrupcion`   | Un `aviso` y `puntos` de corrupción, cada vez que se entra                |
| `narrar`       | Relato puro: `condicion` (`flag`/`no_flag`) lo reserva a una circunstancia y `texto_grieta` + `grieta_desde` dan texto alternativo si la corrupción supera el umbral |
| `decision`     | Texto y elección con efectos: `item`, `corrupcion` y `flag` por opción    |
| `emboscar`     | Suma `enemigos` al lugar si se cumple su `condicion` (`flag`/`no_flag`)   |
| `final`        | Un texto, `opciones` de elección y el desenlace según corrupción          |

### Las banderas: consecuencias sin código

Las banderas (`flags`) conectan las consecuencias dentro de una
aventura: una `decision` deja una bandera encendida, un `emboscar` o
un `narrar` con `condicion` la leen más tarde y una opción de `final`
puede declarar `requiere_flag` para ofrecerse solo si aquella decisión
ocurrió. Así se escriben las consecuencias tardías y los finales
múltiples de la saga, sin una línea de código en el JSON.

### El golpe especial de combate

Si la aventura quiere uno, se declara en `comando_especial`: el
comando, su `texto_fuera` de combate y un `efecto` con `dano_base`,
`dano_por_corrupcion`, `corrupcion_coste` y `mensaje`.

### Los secretos y easter eggs

Se declaran en la sección opcional `secretos`: cada entrada define
`comando`, `textos` (lista o texto único), `texto_combate` (opcional),
`semillas` (respuestas especiales según `--semilla`) y `alias`
alternativos.

## Un enemigo nuevo

Cada entrada de `enemigos` acepta, además de `nombre`, `vida`,
`ataque`, `defensa` y `sin_huida`:

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

## El legado de una serie

Si la aventura pertenece a una serie, declara un `legado` junto a las
secciones del JSON:

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
  escriben en `legado.json`, gestionando cada aventura solo sus claves
  para que la cadena entera sobreviva.
- `importa` son las canónicas que se encienden al empezar si el legado
  las trae, bajo su propio nombre: tus `condicion` y `requiere_flag`
  ya saben leerlas.
- `heroe` exporta, además, el nombre puesto por el jugador y el rasgo
  del héroe; `texto_fama` es el gesto del prólogo cuando hay legado y
  admite `{nombre}`, `{trato}` y `{quien}`.

## Un héroe nuevo

Agrega una entrada a `personajes` de la aventura: nombre, título,
estadísticas, inventario, presentación y, si quieres, `rasgos` (claves
del catálogo `datos/rasgos.json`), `prologo_extra`, `texto_nombre`
propios y los apodos con los que los textos le hablan (`trato`,
`quien`). El menú lo ofrece automáticamente cuando hay más de un
héroe. Para acompañantes reclutables, otra entrada en `reclutas` más
su diálogo y su lugar en el mapa.

## Un don (rasgo) nuevo

Agrega una entrada a `datos/rasgos.json` con su `nombre`, su
`descripcion` (la que muestra `estado`) y su `efecto`, y referénciala
desde la ficha de un héroe: el motor la aplica sin tocar Python. El
vocabulario de efectos son modificadores genéricos que se suman entre
dones:

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
interpretación en el motor—, nunca con conocimiento de un don
concreto.

## Una dificultad nueva

Agrega una entrada a `datos/dificultades.json` —junto a un campo
`por_defecto` que diga con cuál se juega si nadie elige— con su
`nombre`, su `descripcion` y los multiplicadores que quieras (los que
faltan valen 1.0):

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
del balance para quien edite el archivo después.

El orden del menú es el del archivo, y el cargador valida todo:
multiplicadores numéricos mayores a cero, nombre y descripción
presentes, y un `por_defecto` que exista — el error nombra archivo y
campo, como siempre. Las claves de los perfiles viven dentro de la
partida guardada: no las renombres si hay partidas en curso, porque
`cargar` necesita encontrarlas.

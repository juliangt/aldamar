# Playtesting y balance: el protocolo de Aldamar

Los tests demuestran que las mecánicas **funcionan**; nadie ha dicho
todavía que sean *divertidas*. Este protocolo existe para que el balance
se ajuste con datos y no a ojo: dónde mueren los héroes, dónde sobran o
faltan combates, qué comandos no se encuentran. Sus hallazgos alimentan
`dificultad.py` y los JSON de las aventuras.

Todo local, todo opcional, todo explícito: nada de telemetría, nada
sale de la máquina.

## Antes de jugar: los números

Lanza la partida con la bandera de estadísticas:

```console
$ uv run aldamar --stats
```

Al terminar la partida —gane, muera, caiga o se deje a medias— queda
escrito `estadisticas.json` (o el archivo que le pases a `--stats`) con
el informe de la sesión:

- **La sesión**: aventura, dificultad, héroe, final.
- **Los combates, uno a uno**: lugar, enemigo, turnos, resultado,
  daño infligido y recibido. Aquí se lee dónde mueren los héroes y qué
  duelos se alargan más de la cuenta.
- **La economía**: monedas recogidas frente a gastadas, compras,
  tiendas visitadas. Si las tiendas se cruzan y no se usan, el precio
  o el botín están mal.
- **La huella del viaje**: lugares visitados, decisiones tomadas,
  corrupción final, nivel alcanzado, compañeros caídos.

El informe cubre desde que empieza (o se carga) la partida hasta que
acaba. Si la sesión va de varias partidas, cada una escribe su archivo:
pásale un nombre distinto a `--stats` por partida, o copia el informe
antes de la siguiente.

## El protocolo por sesión

Una sesión es una combinación de **aventura × héroe × dificultad**, y
se juega de principio a fin (o hasta la muerte, que también es dato).
Mientras se juega, apunta a mano —papel, editor, lo que tengas—:

1. **Ritmo sentido**: ¿hubo tramos de sobaques seguidos sin nada que
   decidir? ¿Momentos de respiro que sobraban o faltaban?
2. **Muertes y dónde**: en qué lugar, contra qué enemigo, con cuánta
   vida ibas cuando entraste. El JSON lo confirma; la *sensación* solo
   la tienes tú.
3. **Dudas de comandos**: cada vez que tuviste que escribir `ayuda`,
   probar varias palabras o abandonar una acción por no saber nombrarla.
4. **Textos confusos**: descripciones que no se entendieron, pistas que
   no se vieron, nombres que no se encontraron.

Al terminar, copia la plantilla de abajo, rellénala y guárdala junto al
`estadisticas.json` de esa sesión en `docs/playtesting/sesiones/`, con
nombre `AAAA-MM-DD-<aventura>-<heroe>-<dificultad>.md`. Los números y
las notas se leen juntos: el JSON dice *qué* pasó, la nota dice *cómo*
se sintió.

## La plantilla de notas

```markdown
# Sesión — AAAA-MM-DD

- Aventura:
- Héroe:
- Dificultad:
- Final: (victoria / muerte / caída / suspendida)
- Informe: estadisticas.json de esta sesión

## Lo que pasó (en una frase)

## Ritmo sentido
(¿Dónde sobró cuerda? ¿Dónde faltó?)

## Muertes y caídas
(Qué lugar, qué enemigo, con cuánta vida se entró, qué se sintió:
injusto, descuido propio, merecido…)

## Dudas de comandos
(Qué quisiste hacer y no supiste cómo nombrarlo.)

## Textos confusos
(Qué se leyó dos veces y no se entendió.)

## Qué cambiaría
(Una lista corta, con el archivo al que apunta cada cambio:
dificultad.py o el JSON de la aventura.)
```

## Cuándo se juega

- **La línea base**: ahora mismo, con el motor tal como está. Es la
  vara de medir: sin ella, ningún ajuste posterior sabe si mejoró algo.
  Al menos una partida completa por dificultad, y si puede ser con
  héroes distintos, mejor.
- **Tras cada fase de motor** (combate, progresión, contenido nuevo):
  se repite el mismo protocolo —mismas rutas si puede ser— y las notas
  se convierten en ajustes concretos en `dificultad.py` y en los JSON.
- **Con un jugador externo, al menos una vez**: se observa sin ayudar.
  Lo que para quien escribió el juego es obvio, para nadie más lo es.
  Anota cada pregunta que no se atrevió a hacer.

## Qué hacer con lo que salga

Cada sesión que cambie una conclusión termina en un ajuste: un
multiplicador en `dificultad.py`, un precio, una vida de enemigo, un
texto de pista. El ajuste cita su sesión («según la del 2026-08-30, el
Custodio se alarga dos turnos de más en El camino»); así el balance
tiene memoria y el siguiente playtest puede comprobar si el ajuste
hizo lo que decía.

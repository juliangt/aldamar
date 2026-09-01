# Aldamar · El Corazón de Ceniza

Aventura de fantasía épica original para la terminal, en español.
Un jardinero hereda un amuleto que no debería existir y cruza medio
continente para devolverlo al fuego que lo vio nacer.

> **Nota sobre derechos.** Aldamar es una obra de fantasía original:
> mundo, nombres, razas, textos y mecánicas son propios y están
> inspirados en el género de la fantasía clásica en general, sin usar
> nombres, lugares ni textos de franquicias o libros con derechos.

## Cómo jugar

```bash
uv sync
uv run aldamar            # partida nueva
uv run aldamar --cargar   # retomar partida.json
uv run aldamar --semilla 7 --sin-color
```

También funciona sin instalar: `uv run python -m aldamar`.

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

- **Grupo**: puedes reclutar a **Sylvana** (arquera sylva), **Sir
  Aldric** (caballero valoriano) y **Torkan Hachagris** (herrera goran).
  Pelean solos, reciben golpes y pueden caer.
- **Corrupción**: usar el Corazón en combate golpea muy fuerte… y deja
  una grieta. Las Ciénagas también la agravan. La Torre de Belthar la
  alivia una vez. El epílogo cambia según cuánta grieta lleves al alba.
- **Comercio y campaña**: monedas repartidas por el mapa, tiendas en
  Ríoclaro y Valoria, y dos llaves de paso: antorcha para las minas,
  estandarte del consejo para los Yermos.
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
completa scripted de Vegaverde a la cumbre.

### Estructura

```
src/aldamar/
├── datos.py       # objetos, criaturas, diálogos, finales
├── mundo.py       # mapa, lugares y conexiones
├── personajes.py  # jugador, compañeros, enemigos, corrupción
├── juego.py       # bucle, comandos, combate, guardado
└── __main__.py
tests/             # mapa, combate determinista y partida completa
```

## El error que lo empezó todo

Este juego nació de una equivocación. Lo único que se le pidió a un
LLM fue un resumen de un libro —sin infringir copyright, pues serviría
como ejemplo en otro proyecto— y, en lugar del resumen, devolvió un
juego creado desde cero. Aldamar es ese accidente hecho obra.

Veremos qué camino sigue tomando: la partida, por ahora, apenas
comienza.

## Licencia

MIT.

# Spec de implementación: Modo «Aventura Viva» (issue #22)

> Estado: propuesta. Este documento concreta **cómo** implementar el modo
> vivo descrito en el issue #22: módulos nuevos, contratos de datos,
> puntos de enganche exactos con el motor, prompts, guardado v2, tests y
> plan por hitos. El «qué» y la motivación viven en el issue; aquí solo
> queda lo ejecutable.

---

## 0. Resumen en cinco líneas

- Modo nuevo, **opcional y sin dependencias nuevas**: un cliente Ollama
  escrito con `urllib` (stdlib) y un director procedural en Python
  construyen, turno a turno, una aventura que **nunca existió en JSON**.
- El LLM **nunca toca el motor**: todo lo que genera entra como datos
  por la misma costura que el contenido escrito a mano
  (`cargar_aventura_dict()`), que lo valida y lo convierte en el objeto
  `Aventura`. Si el modelo falla, el modo se degrada; el motor jamás.
- El mundo se genera **por fragmentos sobre un mapa que el director ya
  reservó** (stub por stub): las validaciones referencionales quedan
  intactas y una partida guardada es una aventura jugable sin modelo.
- Guardado v2 (`_de_1_a_2` en `guardado.py`) viaja con los fragmentos
  generados y la memoria de la sesión; exportar a JSON jugable (#12)
  sale casi gratis.
- Plan en hitos: **M0** refactor de validación → **M1** spike jugable
  (narrador) → **M2** mundo incremental + intenciones + guardado v2 →
  **M3** exportación → **M4** (opcional) memoria vectorial.

---

## 1. Verificación del análisis del issue contra el código

Todas las afirmaciones estructurales del issue se sostienen. Dos
correcciones menores y un matiz:

| Afirmación del issue | Veredicto |
|---|---|
| `cargar_aventura_dict()` es la costura (`cargador.py:632`) | ✅ Exacta. Función pura `dict → Aventura`, sin I/O. |
| Los 7 tipos de evento son el vocabulario (`eventos.py:49`) | ✅ Exacta (`TIPOS_EVENTOS`). `evento_desde()` (`eventos.py:263`) ya construye cada closure desde dict. |
| El validador referencial es sandbox gratis | ✅ `_chequea_referencias` (`cargador.py:594`) rebota con error que nombra campo y culpa. |
| `j.flags` como memoria episódica (`juego.py:102`) | ✅ Exacta; `decision` enciende, `narrar`/`emboscar`/`final` leen con `condicion.flag`/`no_flag`/`requiere_flag`. |
| Guardado versionado listo para `_de_1_a_2` (`guardado.py`) | ✅ `VERSION = 1`, `_PASOS = {0: _de_0_a_1}`. |
| `ajusta()` en `contenido/aventura.py:158` | ⚠️ Vive en `motor/dificultad.py:138`; `aventura.py` lo importa. El efecto es el mismo: `crear_enemigo()`/`crear_jugador()` ya escalan por dificultad. |
| «Cero dependencias: `urllib` basta» | ✅ `pyproject.toml` no declara ninguna. No hará falta ni un extra hasta el Nivel 3 (sqlite-vec). |
| Entrada libre en `ESCRIBIR` (`juego.py:50`, despachador `:787`) | ✅ La clave del menú existe y `_ejecutar` tiene el punto exacto de enganche (rama final `else`, `juego.py:822`). |
| Menús navegables reutilizables | ✅ `elegir_opcion` (`interfaz/opciones.py:368`) es genérica; las decisiones (`evento_decision`) ya renderizan 3–4 opciones con flechas. |

**Matiz importante que el issue no menciona**: los textos que pasan por
`j._texto_heroe()` se formatean con `.format(trato=..., quien=...)`
(`juego.py:155`). Cualquier llave suelta en prosa del LLM («…el oráculo
de {kor}…») revienta con `KeyError`/`ValueError` dentro del motor.
Todo texto generado debe pasar por un sanitizador antes de entrar al
dict de la aventura (§7.3). Este es el único punto donde un descuido del
modelo podría llegar al jugador, y se cierra por ingestión.

---

## 2. Decisiones de diseño (y dos desviaciones del issue)

### D1. El director es dueño del mapa; el LLM llena contenido — no al revés

El director procedural construye al arrancar la sesión el **esqueleto
completo** de la partida: 5–8 lugares con ids, nombres provisionales,
grafo de `salidas`, arquetipo de cada lugar (encuentro, pueblo, ruina,
santuario…) y la curva de actos. Los lugares se crean como **stubs**
con contenido mecánico mínimo válido (descripción de plantilla, sin
eventos aún) y se **rellenan con el LLM cuando el jugador los pisa por
primera vez** (o por prefetch).

**Desviación 1 respecto al issue.** El issue propone que las `salidas`
de un lugar generado apunten a ids `sin_generar:N` que `_entrar()`
intercepta. Aquí se propone lo contrario: **toda salida apunta siempre
a un lugar existente** (el stub reservado). Motivos, medidos contra el
código:

- `_chequea_referencias` (`cargador.py:599`) rechaza salidas a lugares
  inexistentes: con stubs no hay que relajar ninguna validación.
- `destinos()` (`juego.py:307`) hace `self.av.lugares[d].nombre`: un id
  colgante es un `KeyError` en el camino del menú de viaje.
- El mundo acumulado **siempre** pasa `cargar_aventura_dict()`, así que
  guardar, cargar y exportar no conocen estados intermedios.

La generación perezosa sigue existiendo, pero como **sustitución de
contenido del stub** (descripción, eventos, npcs, items, enemigos),
no como creación de topología. El director, al rellenar un stub, añade
1–2 stubs nuevos como vecinos (con nombres sugeridos por el LLM o de
tabla): el mundo crece, pero sin aristas colgantes jamás.

### D2. Motor autoritario con una sola puerta: ingestión → validación → commit

Cada producción del LLM sigue siempre el mismo cauce, en `sesion.py`:

```
respuesta cruda
  → sanear()            (llaves, blancos, límites de longitud)
  → fusionar en el dict acumulado de la aventura
  → cargar_aventura_dict(dict)   # la MISMA validación del contenido a mano
  → commit: self.av = nueva_aventura        (o rechazo → bucle de reparación)
```

Si `cargar_aventura_dict` lanza `AventuraInvalida`, el texto del error
(mcampo y culpa) vuelve al modelo como mensaje de reparación, con **2
reintentos**. Agotados: se cae a la **plantilla del director** (misma
estructura mecánica, prosa de tabla). Nunca se rompe la partida; nunca
se imprime nada al jugador fuera de un evento validado.

**Desviación 2 (de énfasis, no de rumbo).** El issue pide extraer
`valida_fragmento()` de `cargador.py` para validar fragmentos aislados.
La validación de fragmento aislado tiene poco valor si después el dict
completo se revalida igualmente (la única verdad es la revalidación
total, que ya es rápida: los JSON enteros suman ~108 KB). El refactor
de `cargador.py` se limita a **exponer con firma estable** los
validadores de sección que ya existen (`_items`, `_enemigos`, `_lugar`,
`_evento`, …) tras un objeto público `valida_fragmento()`, por dos
consumidores: el mensaje de reparación (atribuir la culpa al fragmento
antes de fusionar) y el modo offline del #55, que valida fragmentos sin
sesión. El sprint es pequeño y no duplica caminos de validación.

### D3. Memoria en tres capas, de barata a cara

1. **Flags** (ya existen): las consecuencias mecánicas de las
   decisiones. Sin coste, ya persisten en el guardado.
2. **Hilo rodante + hechos** (nuevo, en `memoria.py`): el hilo es un
   resumen que se reescrita cada N escenas (el propio LLM lo condensa);
   los hechos son frases atómicas («Ruy le prometió al ermitaño llevar
   la carta») con lugar/npc asociados, añadidas al cerrar cada escena
   con decisión. Ambos viven en el guardado v2.
3. **Vectorial** (`sqlite-vec` + embeddings de Ollama): solo M4, solo si
   el hilo no cabe en contexto en sesiones reales. Fuera del alcance del
   spike.

### D4. Dos pasos por generación: prosa libre + campos mecánicos de plantilla

Para un modelo 7–8B en español, pedir prosa y mecánica en un solo JSON
es la receta del fracaso. Cada generación se divide:

- **Paso A (prosa)**: texto libre con contrato blando (2–4 párrafos,
  segunda persona, sin dados ni menús). Streaming posible.
- **Paso B (mecánica)**: el director decide TODO lo mecánico (enemigos,
  botín, flags, opciones de decisión) y solo pide al modelo los
  **nombres** con *structured outputs* (`format:` con JSON schema en
  Ollama): nombres de opciones de decisión, nombre de un NPC, nombre
  sugerido de vecinos. Si el schema falla → valores de tabla.

Con esto el vocabulario de eventos queda cubierto sin que el modelo
invente balance: `narrar` (prosa A), `decision` (prosa A + opciones
B), `emboscar` (texto A + enemigos del director), `otorgar`
(texto A + item del director), `final` (prosa A + estructura fija).

### D5. Modo opcional sin `if viva` esparcidos por el motor

Los puntos de enganche con el motor se limitan a **cinco** (§6), todos
detrás de `if self.viva is not None` o de una rama en `main`. Sin
Ollama, sin el paquete cargado (imports perezosos) y sin un solo
comportamiento nuevo, el juego es exactamente el de hoy.

---

## 3. Arquitectura: paquete nuevo `src/aldamar/viva/`

Paquete nuevo, importado **solo** cuando se entra al modo (perezoso
desde `main` y desde el menú), para que el camino por defecto no pague
ni un import.

| Módulo | Responsabilidad | No hace |
|---|---|---|
| `cronista.py` | Cliente Ollama con `urllib`: `detectar()` (`GET /api/tags`), `generar()` (`POST /api/generate`, `stream`), `generar_json()` (con `format:` schema). Protocolo `Proveedor` para inyectar falsos. | Nada de juego, nada de prompt. |
| `prompts.py` | Construcción de prompts: `sistema()` (canon corto + premisa + voz del héroe), `escena()`, `nombres()`, `hilo()`. Plantillas de texto constantes del módulo. | Llamar a la red. |
| `director.py` | Tablas + `random.Random(semilla)`: esqueleto de 5–8 lugares, arquetipos por acto, fichas de enemigos/items de plantilla, héroe arquetipo, premisas de muestra, curva de actos. Emite dicts JSON-iguales al formato de aventura. | Llamar al LLM. |
| `memoria.py` | Hilo rodante (condensación), hechos atómicos, catálogo de sesión (ids ya usados). `para_prompt()` con presupuesto de tokens aproximado. | Decidir mecánica. |
| `sesion.py` | El orquestador: `SesionViva`. Ingestión (sanear→fusionar→validar→commit), bucle de reparación, sustitución de stubs al entrar, prefetch, latencias, exportación. Único módulo que habla con cronista + director + memoria. | Imprimir al jugador (devuelve eventos; el motor narra). |
| `interfaz.py` | Pantallas del modo con `elegir_opcion`: selección de premisa, de héroe arquetipo, aviso «sin Ollama» con instrucciones, recuerdo final. | Lógica de generación. |

Dependencias entre módulos (sin ciclos):

```
interfaz ──▶ sesion ──▶ cronista (protocolo Proveedor)
                │───▶ director
                │───▶ memoria
                └───▶ prompts
sesion ──▶ contenido.cargador (cargar_aventura_dict, valida_fragmento)
```

### 3.1 `cronista.py` — el cliente

```python
HOSPEDAJE_DEFECTO = "http://127.0.0.1:11434"  # honra OLLAMA_HOST si existe

class Proveedor(Protocol):
    def disponible(self) -> bool: ...
    def modelos(self) -> list[str]: ...
    def generar(self, sistema: str, prompt: str, *, temperatura: float = 0.9,
                stream_en: Callable[[str], None] | None = None) -> str: ...
    def generar_json(self, sistema: str, prompt: str, schema: dict) -> dict: ...

class Ollama:          # la implementación real (urllib, sin dependencias)
    def __init__(self, hospedaje: str, modelo: str, num_ctx: int = 16384): ...
    def disponible(self) -> bool:        # GET /api/tags, timeout 1 s
    def generar(self, ...):              # POST /api/generate {"stream": true, "options": {"num_ctx": ..., "temperature": ...}}
    def generar_json(self, ..., format=schema): ...

class ProveedorFalso:  # solo tests: cola de respuestas enlatadas, grabable
    def __init__(self, respuestas: list[str | dict]): ...
```

Detalles obligatorios:

- `num_ctx` se fija **siempre** en `options` (el default de Ollama,
  2048, trunca el canon en silencio).
- `detectar()` no lanza: devuelve `None` si no hay servicio; el menú
  explica cómo activarlo. Timeout corto (1 s) y resultado cacheado en
  el proceso.
- Sin red jamás fuera de `127.0.0.1` (el requisito «sin conexión» del
  issue es literal: el único host permitido es localhost).
- Errores HTTP/timeout → excepción propia `CronistaError`; `sesion`
  la traduce a degradación, nunca a traceback.

Elección de modelo: variable `ALDAMAR_MODELO` > `configuracion.json`
(campo nuevo `modelo_viva`) > el primero que devuelva `/api/tags`. La
detección de RAM/GPU del issue queda como mejora posterior; el primer
entrega deja elegir a mano.

### 3.2 `director.py` — tablas y esqueleto

Contenido (todo dato del módulo, sin I/O):

- `PREMISAS`: 6–8 semillas de premisa («una traición en Valoria»,
  «el mar que calla»…), cada una con el antagonista y el tono.
- `ARQUETIPOS_HEROE`: 3 fichas `PersonajeInicial` completas (con
  `rasgos` de `RASGOS` reales e inventario de items que el esqueleto
  crea), con `trato`/`quien`/`texto_nombre` de plantilla.
- `ARQUETIPOS_LUGAR`: por acto (I arranque, II desarrollo, III
  clímax) y sabor (encuentro, pueblo, ruina, santuario, camino): ficha
  mecánica de plantilla —enemigos (claves + stats base), botín,
  monedas, `descanso`/`tienda`— y huecos de texto.
- `esqueleto(premisa, semilla) -> dict`: la aventura completa en
  formato JSON ya válido por construcción: esqueleto base (§4.1) + 5–8
  lugares stub + vecinos reservados + un lugar final por acto. Debe
  pasar `cargar_aventura_dict` **sin LLM**: es la garantía de que el
  piso procedural funciona solo (el «modo narrador» degradado).

Curva de dificultad: stats de enemigo base 1.0 por acto (vida ~12/20/30,
ataque ~3/5/7, ajustables), que `crear_enemigo` escala después con la
`Dificultad` elegida por el jugador — el modo no toca `ajusta()`.

### 3.3 `memoria.py` — el hilo y los hechos

```python
@dataclass
class Hecho:
    texto: str          # frase atómica en pasado: «Ruy prometió llevar la carta»
    lugar: str          # id del lugar donde ocurrió
    npc: str | None

@dataclass
class Memoria:
    hilo: str = ""                  # resumen rodante, presupuesto ~500 palabras
    hechos: list[Hecho] = field(...)
    def cierra_escena(self, escena: str, decision: str | None) -> list[Hecho]: ...
    def condensa(self, proveedor) -> None: ...   # reescritura del hilo cada N escenas
    def para_prompt(self, lugar_actual: str, presupuesto: int) -> str: ...
```

`cierra_escena` es mecánica pura: extrae la decisión tomada (flag) y el
lugar, y encola el hecho; la redacción del hecho la da el paso B
(nombre de la opción + actores) o, si sobra contexto, el LLM en una
llamada barata. `para_prompt` ordena: hechos del lugar actual y de NPCs
presentes primero, luego los últimos K, luego el hilo.

### 3.4 `sesion.py` — la sesión viva

```python
class SesionViva:
    def __init__(self, *, premisa: str, dificultad: Dificultad,
                 proveedor: Proveedor, semilla: int | None, ...): ...

    # ciclo de vida
    def construir(self) -> Aventura          # esqueleto + prólogo + escena inicial
    def al_entrar(self, juego: Juego, lugar_id: str) -> None
    def interpretar(self, juego: Juego, linea: str) -> str | None   # Nivel 2
    def exportar(self, ruta: str) -> None    # JSON jugable (#12)

    # ingestión (D2)
    def _genera_stub(self, lugar_id: str) -> None
    def _ingiere(self, fragmento: dict) -> Aventura   # sanear→fusionar→validar→commit
    def _repara(self, intento, error: AventuraInvalida) -> dict | None

    # estado persistible (guardado v2)
    def estado(self) -> dict
    @classmethod
    def desde_estado(cls, estado: dict, proveedor: Proveedor) -> SesionViva
```

Comportamientos clave:

- `al_entrar`: si el lugar es un stub sin rellenar y el prefetch no lo
  tiene listo, genera en línea (con la línea tenue «El cronista toma la
  pluma…» que la `interfaz` escribe antes); al terminar, reemplaza el
  contenido del stub, revalida, hace commit (`juego.av = nueva`) y deja
  que `_entrar` siga su curso normal con la descripción nueva.
- **Prefetch**: al terminar un `_entrar`, la sesión encola los vecinos
  stub en un `ThreadPoolExecutor(max_workers=1)` (daemon, stdlib). Por
  lugar, un `Future` idempotente; si el jugador llega antes, `_entrar`
  hace `future.result(timeout=30)` y sigue.
- **Catálogo de sesión**: `memoria` guarda ids/nombres de items,
  enemigos y NPCs ya creados; los prompts los listan para que el modelo
  reutilice en vez de inventar variantes.
- `interpretar` (Nivel 2): recibe la línea libre; el LLM devuelve un
  comando del despachador (`hablar ermitano`) o `null`. Regla de oro:
  solo se re-despacha **una vez** y solo si el comando cae en la tabla
  de acciones de `_ejecutar` (`juego.py:793`); si no corresponde a
  nada real, se pide escena (el evento `narrar` de la entrada). En
  Nivel 1, `interpretar` no existe y la rama es la de siempre («No
  entiendo eso»).

---

## 4. Contratos de datos

### 4.1 El esqueleto base (lo que Python escribe sin LLM)

La aventura viva es un dict con el **mismo** schema de
`docs/extender.md`. Lo que el director fija de una vez:

```jsonc
{
  "id": "viva_<semilla>",
  "titulo": "<premisa, con forma de título>",     // paso B del LLM solo lo afina
  "descripcion": "...",                            // para el menú de «recuerdos»
  "texto_nombre": "¿Cómo te llamas? ({nombre}): ",
  "lugar_inicial": "p1",
  "jugador_inicial": "arquetipo_1",
  "prologo_base": "<prosa del LLM al construir; plantilla si falla>",
  "epilogos": { "muerte": "<...>", "caida": "<...>" },
  "personajes": { "arquetipo_1": { ...ficha del director... } },
  "lugares":   { "p1": { ...stub relleno... }, "p2": { ...stub... }, ... },
  "items": {}, "enemigos": {}, "reclutas": {}, "dialogos": {},
  "tiendas": {}, "eventos": {}
}
```

Notas de contrato:

- `secretos`, `legado`, `comando_especial`: vacíos/ausentes en v1 del
  modo. (Idea futura: un `comando_especial` por premisa; fuera de
  alcance.)
- `epilogos` se generan al construir (dos llamadas de prosa con la
  premisa) con plantilla de reserva; contienen `{trato}`/`{quien}` si
  el modelo los usó — el sanitizador lo garantiza.
- Los stubs nacen con `descripcion` de plantilla («El camino aún no se
  ha escrito aquí…») y sin `eventos`; `al_entrar` los reemplaza.
- El **lugar final** del acto III nace ya con su evento `final`
  estructurado por el director (estructura fija de `_valida_final`:
  exactamente una opción sin `epilogo`, `umbral_tentado`, los cuatro
  textos) y huecos de prosa que se rellenan al acercarse el clímax
  (prefetch del penúltimo lugar).

### 4.2 El fragmento del LLM (lo que entra por ingestión)

Un fragmento es **siempre** una sustitución de sección de un solo
lugar, con este schema (paso B, structured outputs; los textos largos
llegan por el paso A y se incrustan):

```jsonc
{
  "lugar": "p4",                       // debe existir y ser stub
  "nombre": "El vado de los ahogados",
  "descripcion": "<prosa A, 2-4 párrafos>",
  "npcs": {"el ermitaño": "dlg_ermitano"},
  "enemigos_nuevos": [                  // fichas completas, stats ya del director
    {"clave": "ahogado", "nombre": "el ahogado del vado", "vida": 14,
     "ataque": 4, "defensa": 0, "experiencia": 10}
  ],
  "items_nuevos": [
    {"clave": "medalla_sal", "nombre": "medalla de sal", "tipo": "reliquia",
     "precio": null, "texto_uso": "<prosa A>"}
  ],
  "eventos": [
    {"tipo": "narrar", "texto": "<prosa A>", "una_vez": "p4_visto"},
    {"tipo": "decision", "texto": "<prosa A>", "pregunta": "<...>",
     "opciones": [{"clave": "prometer", "titulo": "<nombre del paso B>",
                   "flag": "prometio_carta", "texto": "<prosa A>"}]},
    {"tipo": "emboscar", "texto": "<prosa A>", "enemigos": ["ahogado"],
     "condicion": {"no_flag": "prometio_carta"}}
  ],
  "vecinos_sugeridos": [{"nombre": "La torre sumergida", "palabra": "norte"}],
  "hechos": ["Ruy conoció al ermitaño del vado"]
}
```

Reglas de ingestión (`sesion._ingiere`), en orden:

1. `lugar` existe y está sin rellenar (si no: rechazo sin llamar al
   modelo de nuevo).
2. Los stats de `enemigos_nuevos`/`items_nuevos` **no se aceptan del
   modelo**: el director ya trajo las fichas mecánicas; el fragmento
   solo puede renombrar. (Si vino un número distinto, se descarta y se
   usa el de plantilla — el balance nunca es cosa del LLM.)
3. `npcs` apunta a `dialogos` que el fragmento trae o al catálogo.
4. Claves nuevas (`flag`, `una_vez`, `dlg_*`, items, enemigos) se
   namespacedan con el id del lugar (`p4_...`) para no colisionar.
5. Fusionar en el dict acumulado y `cargar_aventura_dict(dict)`.
6. Sanear todos los textos **antes** del paso 5 (§7.3).
7. `hechos` y `vecinos_sugeridos` van a `memoria`/director fuera del
   dict (los vecinos nuevos los crea el director como stubs).

### 4.3 Guardado v2 (`motor/guardado.py`)

- `VERSION = 2`.
- `_ESQUEMA` añade `"viva"`. `_BASE` no cambia.
- `_de_1_a_2(estado)`: `estado["viva"] = None` y `estado["version"] = 2`.
  Las partidas clásicas migran sin tocar nada más.
- Una partida viva guarda en `"viva"`:

```jsonc
{
  "premisa": "el mar que calla",
  "modelo": "llama3.1:8b",       // informativo; cargarla no lo necesita
  "aventura_dict": { ...el dict acumulado COMPLETO... },
  "memoria": { "hilo": "...", "hechos": [ {"texto": "...", "lugar": "p4", "npc": "..."} ] },
  "rellenados": ["p1", "p3"],    // stubs ya vividos
  "latencias": [8200, 6100]      // para el informe de la sesión
}
```

- Cargar: `_aplicar_estado` / `Juego.desde_archivo` detectan
  `estado["viva"]` y reconstruyen con
  `cargar_aventura_dict(estado["viva"]["aventura_dict"])` en vez de
  `obtener_aventura(id)` — **sin modelo instalado**, como pide el
  criterio de aceptación. `sesion.desde_estado` repone la memoria y el
  prefetch.

### 4.4 Exportación a JSON jugable (#12)

`SesionViva.exportar(ruta)` vuelca el dict acumulado con `id` saneado
(`viva_<semilla>`) y `orden: 99`, lo revalida con
`cargar_aventura_dict` y lo escribe en
`src/aldamar/datos/aventuras/` (o la ruta pedida). Como el mundo
acumulado siempre pasó por el validador, la exportación es un `json.dump`
+ una verificación. La pantalla de cierre del modo añade la opción
«Exportar esta aventura a JSON» junto a las de siempre.

---

## 5. Flujo de juego

### 5.1 Arranque

1. Menú principal (`interfaz/menu.py`) añade la entrada
   `("viva", "Aventura Viva…", "Una historia que se escribe al volar")`.
   `Eleccion` gana `accion == "viva"` (sin campos nuevos: la premisa y
   el héroe los pregunta el propio modo).
2. `main` (`juego.py:1568`) enruta: import perezoso de
   `aldamar.viva.interfaz` → `elegir_premisa()` (3 de `PREMISAS`
   barajadas + «Escribir la tuya…») → `elegir_heroe()` (3 arquetipos)
   → dificultad (mismo paso de siempre).
3. `SesionViva.construir()`: esqueleto + prólogo + epílogos + escena
   inicial (con contador de latencia visible en modo tenue). Si
   Ollama no responde **ya en el menú** (detección cacheada), la
   pantalla explica cómo activarlo y vuelve al menú sin crear nada.
4. `Juego(aventura=..., viva=sesion, ...)` y `ciclo()` de toda la vida.

### 5.2 Un turno vivo

El turno **es** el turno de siempre: `_entrar` narra descripción y
eventos (el `narrar` recién generado trae la prosa del cronista), el
`decision` abre su menú de 3–4 opciones con `elegir_opcion`, el viaje
usa el menú de verbos. El modo no añade ni un bucle nuevo: solo cambia
**quién escribió el contenido** que el motor está a punto de narrar.
Al cerrar una escena con decisión, `memoria.cierra_escena` anota el
hecho y agenda la condensación del hilo.

### 5.3 Viajar a un stub

`_ir` → `_entrar(destino)` → gancho `self.viva.al_entrar(...)`: o el
prefetch ya lo dejó listo (latencia ~0), o genera en línea bajo
«El cronista toma la pluma…» (tenue). Commit de la aventura nueva y
continúa el `_entrar` normal. El director añade los vecinos nuevos
como stubs y el mapa crece.

### 5.4 Entrada libre (Nivel 2)

`_ejecutar` cae en su `else` final → `if self.viva:` →
`interpretar(linea)`: comando conocido → `self._ejecutar(comando)`
(una sola vez, contra la tabla del despachador); no corresponde a nada
→ escena de `narrar` efímera (no persiste en el mapa; sí en `memoria`).

### 5.5 Final, muerte, caída

Novedad cero en el motor: `final`/`epilogo_muerte`/`epilogo_caida` del
dict acumulado llevan la prosa generada; `_cierre` funciona igual y
añade «Exportar esta aventura» si hubo final con nombre. La partida
guardada (o exportada) es el «recuerdo consultable» del issue.

---

## 6. Integración con el motor: los cinco toques exactos

| # | Archivo:zona | Cambio |
|---|---|---|
| 1 | `motor/juego.py` `Juego.__init__` | Parámetro `viva: SesionViva | None = None` (anotación `TYPE_CHECKING`, import perezoso) y `self.viva = viva`. |
| 2 | `motor/juego.py` `_entrar()` (~1079) | Primera línea: `if self.viva: self.viva.al_entrar(self, destino.id)` (puede reemplazar `self.av`; el resto del método ya lee desde `self.av`). |
| 3 | `motor/juego.py` `_ejecutar()` rama final (~822) | Antes del «No entiendo eso»: `if self.viva and (cmd := self.viva.interpretar(self, linea)): self._ejecutar(cmd); return`. |
| 4 | `motor/juego.py` `_aplicar_estado`/`desde_archivo` y `_guardar` | Viva: serializar `sesion.estado()` dentro del guardado; cargar: reconstruir aventura desde el dict. |
| 5 | `interfaz/menu.py` + `motor/juego.py` `main` | Entrada `("viva", ...)` en el menú; `Eleccion("viva")`; enrutado en `main` con import perezoso de `aldamar.viva`. |

Ningún otro módulo del motor cambia. El guardado toca
`motor/guardado.py` (`VERSION`, `_ESQUEMA`, `_de_1_a_2`) y el cargador
expone `valida_fragmento` sin cambiar comportamiento (M0).

---

## 7. Prompts

### 7.1 Sistema (constante, ~2 KB — no el canon entero)

Los cuatro JSON suman ~108 KB (~30k tokens): no caben junto a
generación en un `num_ctx` de 16k y un 7–8B se pierde en ellos. Se
escribe a mano un **canon condensado** (`viva/canon.md`, dato del
paquete, ~2 KB): mundo (Aldamar, el Corazón, la corrupción como
«grieta»), tono de los prólogos (frases cortas, sustantivos concretos,
segunda persona), reglas duras:

- «Escribe SOLO prosa narrativa. Sin menús, sin números, sin dados,
  sin hablar de reglas. 2–4 párrafos cortos.»
- «Segunda persona. Llama al héroe "{trato}" si hace falta.»
- «No inventes nombres de lugares nuevos: usa los que se te dan.»
- «Lo sobrenatural del mundo es la corrupción; los enemigos se
  deshacen en humo pardo al morir.» (canon de combate ya asumido por
  el motor: `«cae y se deshace en humo pardo»`, `juego.py:1146`.)

El prompt de sistema final = canon + premisa + ficha del héroe
(nombre, `trato`, `quien`, rasgos) + acta de lo ocurrido
(`memoria.para_prompt`).

### 7.2 Escena (por stub)

Contenido: nombre del lugar, arquetipo mecánico ya decidido («habrá un
combate contra <nombre del enemigo de plantilla>; si gana el jugador,
encuentra <item>»), NPCs presentes, opciones de decisión ya decididas
con sus efectos («opción B: aceptar el pacto → flag prometio_carta,
+2 corrupción») y qué **nombres** se piden. La consigna: escribe la
prosa de la escena y, aparte (paso B, schema), los títulos cortos de
las opciones y el nombre visible del NPC.

### 7.3 Sanitización (obligatoria, `sesion.sanear`)

Antes de fusionar cualquier texto del modelo:

- Llaves: todo `{...}` que no sea exactamente `{trato}`/`{quien}` se
  elimina (o se sustituye por su interior sin llaves). Protege a
  `_texto_heroe` y a `.format()` de `texto_companeros` (`{nombres}` es
  del director, no del modelo — los textos de eventos generados no
  deben llevarlo nunca).
- Límites: descripción ≤ ~1800 caracteres, títulos de opción ≤ 40,
  nombres ≤ 40; de más, se trunca por párrafo/frase (nunca a mitad de
  palabra).
- `strip()` de líneas y colapso de más de dos saltos seguidos.

---

## 8. Latencia: qué se hace en cada hito

1. **M1 (spike)**: medir. `SesionViva.latencias` (ms por generación),
   mostradas tenue tras cada escena y en el cierre. Objetivo informado,
   no optimizado.
2. **M2**: prefetch de vecinos (`ThreadPoolExecutor(1)`, futures por
   lugar) y generación del clímax en el penúltimo lugar. Sin GPU, un
   turno completo tardará 5–20 s: el prefetch no es optativo.
3. **M2 (si el marco de scroll lo permite)**: streaming del paso A por
   `j.salida` — el texto llega párrafo a párrafo. Detrás de una
   preferencia (`stream: true` en configuración), porque interactúa con
   el marco del issue 36 (`_limpiar` redibuja la vista al terminar).
4. **Piso procedural**: si el hardware no da, el director solo (sin
   cronista) sigue siendo una partida generada al vuelo con prosa de
   plantilla — el «modo narrador» como degradación natural, no como
   producto aparte.

---

## 9. Configuración y CLI (implementado)

Dónde se configura cada cosa, todo en `viva/cronista.py`:

- **Hospedaje**: `OLLAMA_HOST` en el entorno (se le añade `http://` si
  falta) o, por defecto, `http://127.0.0.1:11434`. El único host
  permitido es local: cero red exterior.
- **Modelo**, con la precedencia de siempre del juego:
  1. `ALDAMAR_MODELO` en el entorno (`cronista.modelo_fijado()`).
  2. `modelo_viva` en `configuracion.json` (campo de texto que
     `configuracion.cargar()` ya lee).
  3. Si nada está fijado y hay más de un modelo instalado, el menú
     pregunta («¿Quién narra la historia?») al entrar al modo, con la
     opción **«Fijar uno por defecto…»** que escribe la preferencia en
     `configuracion.json`. Con un solo modelo, no pregunta.
- **Visibilidad** (implementada tras el primer playtesting): cada
  llamada al cronista avisa en pantalla qué hace y cuánto tardó
  («Escribiendo el prólogo…», «Escribiendo el prólogo: 115.5 s»); si una
  llamada falla, se avisa que la escena sale de plantilla. Con
  `--debug` (o `"debug": true` en configuracion.json), todo lo hablado
  con el modelo queda en `cronista_viva.log` — prompt, respuesta y, si
  falló, el error con su tiempo.
- **Presupuesto de tokens por llamada** (`num_predict`): prosa 600,
  JSON 300 (`PRESUPUESTO_PROSA`/`PRESUPUESTO_DATOS` en sesion.py). Sin
  él, un modelo pequeño que divaga puede irse minutos y agotar el
  timeout de 300 s.
- **Modelos «thinking»** (qwen3 y compañía): si `/api/tags` declara la
  capacidad `thinking`, las llamadas llevan `think: false` — su
  monólogo interior se comía el presupuesto y devolvía respuestas
  vacías (en JSON con schema, directamente nada).
- **`contexto_viva`** en configuracion.json: el `num_ctx` del modelo
  (16384 por defecto). Bajarlo (p. ej. 8192) alivia máquinas sin GPU.
- Sin flags nuevos de CLI en M1/M2. (Opcional, si el playtesting lo
  pide: `--viva-premisa "..."` para sesiones de prueba reproducibles.)
- CI: nada del modo toca la red. Los tests inyectan `ProveedorFalso` o
  un servidor HTTP falso en `127.0.0.1` (`test_cronista.py`);
  `Ollama.disponible()` contra un puerto real jamás se llama en tests.

---

## 10. Estrategia de tests (sin modelo real, nunca)

Todo bajo `tests/`, con el estilo del `conftest` actual
(`EntradaTipeada`, `salida.append`):

| Test | Qué fija |
|---|---|
| `test_director.py` | `esqueleto()` pasa `cargar_aventura_dict` sin LLM, para N semillas y las 3 premisas muestreadas; determinismo con semilla; la curva de actos (stats de enemigo por acto). |
| `test_sesion_ingesta.py` | `sanear` mata llaves ajenas y trunca; `_ingiere` fusiona y valida; un fragmento con item inexistente rebota con `AventuraInvalida` que nombra campo; claves namespacedas no colisionan. |
| `test_sesion_reparacion.py` | `ProveedorFalso` que responde JSON roto → reintento con el error en el prompt → segundo intento válido se compromete; dos fallos → degradación a plantilla del director y la partida sigue. |
| `test_viva_flujo.py` | Sesión completa de punta a punta con `ProveedorFalso` + `EntradaTipeada`: arranque, 2 viajes a stubs, una decisión con flag, un combate, guardado, carga y continuación — **sin modelo y sin red**. |
| `test_guardado_viva.py` | Roundtrip v2 de una partida viva; `_de_1_a_2` sobre un guardado v1 clásico añade `"viva": None`; una partida viva se carga con el proveedor `ProveedorFalso()` vacío (sin modelo instalado). |
| `test_exportacion.py` | `exportar()` escribe un JSON que `cargar_aventura_dict` acepta y que `cargar_todas` registraría. |
| `test_menu_viva.py` | La entrada nueva del menú; `Eleccion("viva")`; sin Ollama (`ProveedorFalso.disponible() == False`) la pantalla explica y no crea sesión. |

Y un **test de humo manual** documentado en `docs/playtesting.md`:
sesión real contra Ollama con contador de latencia, checklist de
calidad de prosa y del bucle de reparación.

---

## 11. Plan por hitos

### M0 — Costuras (sin comportamiento visible, medio día)
- `cargador.py`: exponer `valida_fragmento()` con firma estable sobre
  los validadores de sección existentes (cero cambios de reglas).
- `juego.py`: parámetro `viva=None` en `Juego` y los dos ganchos
  (`al_entrar`, `interpretar`) con `if self.viva` — inertes.
- `guardado.py`: `VERSION = 2` + `_de_1_a_2` (añade `"viva": None`).
- Tests de regresión: toda la suite actual en verde sin tocar nada más.

### M1 — Spike jugable (Nivel 1 del issue): «el cronista»
- `viva/cronista.py`, `viva/prompts.py` (+ `canon.md`),
  `viva/director.py`, `viva/memoria.py` (solo hilo rodante),
  `viva/sesion.py` (construir + rellenar stub al entrar, sin prefetch),
  `viva/interfaz.py`, entrada de menú y enrutado en `main`.
- Partida de 5–8 lugares jugable de punta a punta; latencia por turno
  visible; degradación a plantilla probada.
- **Hecho**: se juega una sesión completa generada al vuelo sin ningún
  JSON de aventura cargado, con `ProveedorFalso` en CI y Ollama real en
  local. Sesión de `docs/playtesting.md` para decidir si se sigue.

### M2 — Director de escena (Nivel 2)
- Prefetch de vecinos; catálogo de sesión en prompts; bucle de
  reparación completo (M1 lo trae esbozado); `interpretar` en
  `ESCRIBIR`; guardado/carga de partidas vivas; streaming opcional.
- **Hecho**: el mundo crece por vecinos reservados; una partida viva
  se guarda, se carga y se juega **sin modelo**; la entrada libre
  resuelve comandos reales o pide escena.

### M3 — Recuerdos y exportación
- `exportar()` a JSON jugable; opción «Exportar esta aventura» en el
  cierre; «recuerdos» en el menú (lista de partidas vivas terminadas
  guardadas como aventuras, rejugables sin modelo).
- **Hecho**: el puente con #12 funciona: la partida viva acaba siendo
  contenido estático del juego.

### M4 — Nivel 3 (opcional, solo si el playtesting lo justifica)
- Embeddings (`/api/embeddings`, bge-m3 o multilingual-e5-small
  cuantizado) + `sqlite-vec` para los hechos; juez de coherencia
  (similitud contra `canon.md` + fragmentos) alimentando el bucle de
  reparación. Extra opcional `[project.optional-dependencies] viva =
  ["sqlite-vec"]`; sin él, el modo sigue en hilo+flags.

---

## 12. Criterios de aceptación del issue, mapeados

| Criterio del issue | Dónde queda |
|---|---|
| Partida íntegramente generada al vuelo, sin JSON cargado | M1 (esqueleto del director + cronista), `test_viva_flujo.py`. |
| Las decisiones influyen en escenas posteriores | Flags (motor, ya) + hechos/hilo en los prompts de cada escena (`memoria.para_prompt`). |
| Todo pasa por `eventos.py` + `cargador.py` | Única puerta de ingestión (D2); los 7 tipos cubiertos; nada imprime fuera de eventos. |
| Opcional: sin modelo, el juego arranca igual | Import perezoso, cinco toques detrás de `if self.viva`, detección falla rápido en el menú. |
| Sin conexión a red | Cliente solo contra `127.0.0.1` (u `OLLAMA_HOST` local); CI sin red. |
| Partida viva jugable sin modelo | Guardado v2 con el dict completo; carga por `cargar_aventura_dict`; `test_guardado_viva.py`. |

---

## 13. Riesgos y preguntas abiertas

- **Calidad de prosa de un 7–8B en español**: el spike existe para
  medirlo; el piso procedural y las plantillas acotan el daño.
- **Latencia sin GPU**: prefetch + streaming; si no alcanza, el modo
  narrador (director solo) es el producto de reserva.
- **`{trato}`/`{quien}` y llaves**: resuelto por sanitización, pero el
  test de ingestión debe cubrirlo explícitamente (es la única vía de
  rotura residual hacia el motor).
- **Abierta al usuario**: ¿el modo debe aparecer en el menú siempre
  (con pantalla de ayuda si no hay Ollama) u ocultarse si la
  detección falla? Esta spec asume «siempre visible, ayuda al elegirlo»
  por descubribilidad; es una línea de código cambiarlo.
- **Abierta**: el ancho del mundo (¿5–8 lugares fijos o crecimiento
  por acto sin tope?) — decidir con datos de latencia del M1.

---

## 14. Adenda: el dato sale del módulo y el cronista gana autoría

Dos decisiones posteriores al primer entregable, ya implementadas:

### 14.1 El dato del director vive en `viva/datos.json`

Todo lo que era literal de módulo (premisas, arquetipos, tablas de
criaturas y reliquias, decisiones, items, nombres de lugar y las
plantillas de prosa del piso sin cronista) está ahora en
`viva/datos.json`, cargado con `importlib.resources` y cacheado — el
mismo patrón de `canon.md` y de `datos/aventuras/*.json`. `director.py`
queda como lógica pura de ensamblado (`esqueleto`, `plan_encuentro`,
`rellena`). Editar el mundo del modo ya no toca código.

### 14.2 Nivel 2 de autoría: qué escribe ahora el cronista

El invariante no cambia — stats, banderas y topología son del director,
y todo pasa por la misma ingestión validada — pero el modelo ya no se
limita a redactar la llegada:

|Ámbito|Antes|Ahora|
|---|---|---|
|Premisa propia|Título capitalizado y genéricos («lo que espera al final del camino»)|Una llamada structured output completa `titulo`/`antagonista`/`corte`/`tono`; sin cronista, los genéricos de siempre|
|Criaturas y botín|Nombres de tabla, siempre los mismos|Los nombra el paso B (`enemigo_i`, `botin_i`, `botin_i_desc`), con reserva de tabla|
|Decisiones|Una tabla fija por sabor; solo los títulos del cronista|Dos tablas por sabor en el dato, elegidas por semilla; el cronista redacta también el `detalle` de cada opción (`opcion_i_det`)|
|Mapa|Un único tramo fijo de 8 lugares|Dos tramos (`recto`, `delta`) en el dato; el esqueleto elige con la semilla y la sesión lo recuerda en el guardado (`viva.tramo`)|
|Clímax|Nacía cerrado del esqueleto, el cronista no lo tocaba|Al completarse el mundo (`stubs` vacío), `_afina_final()` reescribe los textos del evento `final` (escena, pregunta, títulos, epílogos); la estructura (una opción sin epílogo, la clemencia atada a su bandera, el umbral) sigue siendo del director, y sin cronista se queda la plantilla|

Dos detalles de contrato que acompañan:

- **Banderas canónicas**: las consecuencias que cruzan escenas viajan
  en una `bandera` declarada en el dato («robo», «ofrenda»), sin el id
  del lugar. La emboscada del cobrador la espera el último encuentro
  del tramo (no «p4») y la clemencia del final lee `ofrenda` sea cual
  sea el lugar de la cripta. Las banderas que no cruzan actos siguen
  namespacedas (`p3_preguntar`).
- **Textos del final sin llaves**: la pantalla de cierre imprime el
  epílogo sin formatear, así que los textos del final se sanea con
  `texto_de_final()` (el saneo de siempre, y además sin
  `{trato}`/`{quien}`).

El presupuesto del paso B sube a 450 tokens (`PRESUPUESTO_DATOS`): con
criaturas, botín y detalles, los 300 se quedaban cortos.

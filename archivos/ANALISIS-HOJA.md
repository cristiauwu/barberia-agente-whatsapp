# Análisis: ¿conviene reestructurar la hoja de citas a 5 hojas?

**Fecha del análisis:** 2026-09-25
**Objeto:** la pestaña `Citas barberia` (gid `941506024`) del spreadsheet `1lvSVFWU2ApvK7p5BsFHI68Icur46P6hI8o8r9ozhBfk`
**Documento evaluado:** `G:\Barberia\Mejoras_Agente_Barberia_n8n.md`, sección "💾 Estructura de Google Sheets - Base de Datos" (líneas 140–168)

> **Este informe es una evaluación. No se ha modificado la hoja, ni ningún workflow, ni Postgres.**
> Todo lo que sigue se verificó leyendo la hoja real, **los 2 workflows vivos** (los 4 nodos, uno por uno),
> el esquema real de Postgres y el historial de ejecuciones de n8n.

---

## 1. Veredicto

**NO conviene reestructurar a 5 hojas. Se mantiene UNA sola hoja.**

1. **Postgres ya es la base de datos** (10 tablas `barber_*` con claves, tipos y constraints). Las hojas *Clientes*, *Servicios*, *Transacciones* y *Metricas_Diarias* del documento serían **copias manuales** de datos que ya existen: dos fuentes de verdad que divergen en cuanto alguien edite una celda.
2. **La hoja no necesita ser una base de datos.** Sus dos únicos trabajos son (a) ser un registro legible para el humano y (b) **disparar** el flujo de recordatorios con `rowAdded`. Ninguno de los dos requiere normalizar en 5 pestañas.
3. **El cambio de `ID` a `APT-...` rompe cancelar y reprogramar**, y el cambio del formato del teléfono **rompe los recordatorios**. El documento es genérico y no conoce este sistema; aplicarlo literalmente es un daño, no una mejora.
4. **El coste/beneficio es malo**: 4 nodos de n8n + encabezado + prompt del agente, para un negocio de **un solo barbero**, a cambio de cero funcionalidad nueva.

**Recomendación operativa:** dejar la hoja como está. Como máximo, **una** columna nueva al final (`Estado de pago`), y solo si el dueño la va a usar. Detalle en la §4.

---

## 2. Estado real verificado (la base del análisis)

### 2.1 La hoja

Encabezado real leído del export público (9 columnas, en este orden exacto):

```
ID | Estatus | Nombre | Servicio | Precio del servicio | "Día " | Hora | Numero celular | Execution ID
```

- `"Día "` termina en **un espacio intencional**: bytes `44 c3 ad 61 20` (`D` + `í` + `a` + espacio).
- La pestaña se llama **`Hoja 1`** y su gid es `941506024`. Hay **una sola pestaña**.
- Filas de datos: 7 (Juan Perez, Maria Lopez, Cristia Ñ, Prueba Cancelar, Prueba Formato, Sondeo fecha, Cristia).

### 2.2 Los 4 nodos, leídos del JSON vivo

| # | Workflow | Nodo | Tipo | Operación | Esquema guardado | Qué escribe |
|---|---|---|---|---|---|---|
| 1 | `barberiaAgenteUncensored` | `Registrar en hoja de citas` | `googleSheetsTool` (herramienta del agente) | `append` | **8 columnas** (sin `Execution ID`) | las 8 |
| 2 | `barberiaRecordatorios` | `Google Sheets Trigger` | `googleSheetsTrigger` | `rowAdded` (cada minuto) | **sin esquema** (lee todas) | — |
| 3 | `barberiaRecordatorios` | `Append or update row in sheet` | `googleSheets` | `appendOrUpdate` | **9 columnas** (con `Execution ID`) | solo `Execution ID` + `ID` |
| 4 | `barberiaRecordatorios` | `OBTENER INFO DE CITA ELIMINADA` | `googleSheets` | lectura con filtro | sin esquema (filtra por valor de `ID`) | — |

**Cómo se usa el campo `ID` (esto es la clave de todo):**

- Nodo 1, parámetro `columns.value.ID`:
  `{{ $fromAI('ID', 'ID del evento de Google Calendar que devolvio Crear evento o Consultar agenda', 'string') }}`
  → **el `ID` de la hoja ES el ID del evento de Google Calendar.**
- Herramienta `Cancelar cita` → `eventId = {{ $fromAI('Event_ID', ...) }}`
- Herramienta `Reagendar` → `eventId = {{ $fromAI('Event_ID', ...) }}`
- Nodo 3 → `matchingColumns: ["ID"]` (la fila se localiza **por `ID`**)
- Nodo 4 → `lookupValue: {{ $('Google Sheets Trigger').item.json.ID }}`
- El prompt del agente lo confirma: *"Necesitas el **ID del evento**"*, y en los procesos B y C se vuelve a llamar a `Registrar en hoja de citas` **con el mismo ID** para registrar el cambio de estado.

→ El `ID` es **la clave de unión entre Google Calendar y la hoja**, y la clave de match del `appendOrUpdate`. No es un identificador decorativo.

### 2.3 El `Execution ID` es crítico — con evidencia de producción

Extraído del historial real de ejecuciones (API de n8n):

- Ejecuciones **720 y 722** — `NodeOperationError` en el nodo `Append or update row in sheet`:
  > `Refresh the columns list in the 'Column to Match On' parameter. Missing columns: Execution ID`
- Ejecuciones **731, 732, 733** — `NodeOperationError` en `Google Sheets Trigger`:
  > `Could not retrieve the columns from key row`
- Estado actual del workflow de recordatorios: **10 ejecuciones en `error`**, 2 en `success` y **4 en `waiting`**.

`Execution ID` guarda el id de la ejecución que quedó **suspendida en los nodos Wait** (24 h y 1 h). El nodo `QUITAR RECORDATORIO` (`n8n-nodes-base.n8n`, `operation: delete`) usa ese valor:
`executionId: "={{ $json['Execution ID'] }}"`.
Sin esa columna, **cuando una cita se cancela no se puede borrar la ejecución en espera** y el cliente sigue recibiendo el recordatorio de una cita que ya no existe.

### 2.4 Hay 4 recordatorios vivos ahora mismo (riesgo operativo inmediato)

Ejecuciones suspendidas en nodos Wait, con `waitTill`:

| workflowId | estado | despierta en |
|---|---|---|
| `barberiaRecordatorios` | `waiting` | 2026-09-27 15:00 −06 |
| `barberiaRecordatorios` | `waiting` | 2026-09-30 11:00 −06 |
| `barberiaRecordatorios` | `waiting` | 2026-10-07 16:00 −06 |
| `barberiaRecordatorios` | `waiting` | 2026-12-02 13:00 −06 |

Cualquier intervención sobre `barberiaRecordatorios` (que además es obligatorio: hay que **desactivar antes del PUT y reactivar después**) toca estas 4 ejecuciones. Es la razón nº1 para no hacer cambios "por gusto".

> **Nota sobre el entorno vivo.** Durante este análisis, `barberiaRecordatorios` pasó de 15 a **16 nodos** y las ejecuciones en espera de 4 a **6**: hay otro subagente trabajando en el sistema. Conviene saberlo por dos motivos: (a) el conteo exacto de nodos y de ejecuciones `waiting` es una foto de un instante, no un dato fijo; (b) **cualquier cambio en la hoja debe coordinarse**, porque el workflow está siendo editado mientras tanto. Los 4 nodos de Sheets y sus esquemas se **re-verificaron** después del cambio: `Registrar en hoja de citas` sigue con 8 columnas (`matchingColumns: ["ID"]`) y `Append or update row in sheet` sigue con 9 (incluida `Execution ID`). Todo lo que este informe afirma sobre ellos **sigue vigente**.

### 2.5 Postgres: la base real, y una sorpresa

Las 10 tablas `barber_*` existen. Pero los conteos reales son:

| tabla | filas |
|---|---|
| `barber_servicios` | 8 (catálogo, poblado) |
| `barber_operadores` | 2 |
| **`barber_citas`** | **0** |
| **`barber_clientes`** | **0** |
| **`barber_auditoria`** | **0** |

Y **ningún nodo de n8n hace `INSERT INTO barber_citas`**: los 6 nodos Postgres de la instancia son 4 `SELECT` (`Leer ficha del cliente`, `Leer estado del sistema`, `Leer operadores`, `Leer pausa`), más un `UPDATE barber_servicios` (`Actualizar precio`) y un `INSERT barber_pausas` (`Aplicar pausa`). No hay triggers que sincronicen (`trg_barber_citas_touch` solo actualiza `actualizado_en`).

> **Hallazgo de contexto, no una tarea de este informe:** hoy Postgres **no** contiene las citas. El sistema real de citas es **Google Calendar + esta hoja**. Eso **refuerza** la recomendación de no romper la hoja y a la vez **desmiente el supuesto** de que "la hoja es solo un espejo de Postgres": la hoja es hoy el registro operativo. Consecuencia práctica: **no borrar ni renombrar columnas**; que quien migre las citas a Postgres lo haga *además*, no *en lugar de*.

### 2.6 Un solo barbero

El prompt del agente es de **"Barber Chinos — Peluquería & Barbería"** (Calle Pinzón #574), con un catálogo de 8 servicios y **un solo profesional**. `barber_operadores` tiene 2 filas y **ambas son `Dueno`** (dos números del mismo dueño), no dos barberos. No existe columna de barbero en la hoja, ni en `barber_citas`.

---

## 3. Análisis propuesta por propuesta

| Propuesta del documento | ¿La aplico? | Motivo técnico | Riesgo si se aplica |
|---|---|---|---|
| **1. Hoja `Citas`** con `appointmentId, customerPhone, customerName, serviceId, serviceName, price, barber, date, time, status, createdAt, paymentMethod` | **NO** (reemplazar). **Sí** en versión mínima de 1 columna — ver §4 | Ya existen 9 columnas que cubren nombre, servicio, precio, día, hora, estatus y teléfono. Renombrar a inglés y en `camelCase` obliga a reescribir **los 4 nodos**, el encabezado y el prompt | **Alto.** Renombrar `Día `, `Estatus`, `Numero celular` o `Execution ID` produce `Missing columns` / `Could not retrieve the columns from key row` (ya visto en las ejecuciones 720/722/731-733). Se rompen los recordatorios |
| **1a. `appointmentId` tipo `APT-20240327-001`** | **NO — rompe el sistema** | El `ID` actual **es el ID del evento de Google Calendar**, y se usa como `eventId` en `Cancelar cita` y `Reagendar`, y como `matchingColumns` del `appendOrUpdate` | **Crítico.** Un `APT-...` no es un ID de evento válido: **cancelar y reprogramar dejan de funcionar**, y el nodo 3 no encuentra la fila que debe actualizar (el `Execution ID` nunca se escribe ⇒ **no se pueden quitar recordatorios**) |
| **1b. `customerPhone` en formato `+52xxxxxxxxx`** | **NO** | La hoja guarda `5214501111805@s.whatsapp.net` (JID). Los nodos `RECORDATORIO 24 H` y `RECORDATORIO 1 H` envían a `$('Google Sheets Trigger').item.json['Numero celular']` **tal cual**, y Evolution API espera ese JID | **Alto.** Con `+52...` los recordatorios no se entregan |
| **1c. `status` en inglés (`confirmed`)** | **NO** | El `Switch` del flujo 2 compara contra `agendado` / `cancelado` / `eliminado` / `actualizado` / `reprogramado`; e `IF - Es cita agendada` exige `agendado` | **Alto.** `confirmed` cae al output *fallback* "Otro" ⇒ **no se programa ningún recordatorio** y el dueño no recibe aviso de cita nueva |
| **1d. `barber` (columna de barbero)** | **NO** | Hay **un solo barbero**. Una columna constante en todas las filas es ruido: no filtra nada, no agrupa nada y hay que rellenarla en cada append | Bajo (es cosmético), pero añade una columna que todos los nodos deben conocer. Coste sin beneficio |
| **1e. `paymentMethod`** | **Parcial** → ver §4 | El método de pago se decide **al cobrar**, no al agendar. Al agendar solo se puede marcar *pendiente* | Bajo si se añade **al final** y no se reordena nada |
| **2. Hoja `Clientes`** (`phone, name, firstVisit, lastVisit, totalVisits, totalSpent, preferences, status`) | **NO** | **`barber_clientes` ya existe en Postgres** (jid, nombre, telefono, primera_visita, visitas, ultima_visita, ticket_promedio, no_shows, cancelaciones_tardias, servicio_habitual, barbero_preferido, nota_interna, fecha_nacimiento, marketing_ok, etiqueta). La hoja sería un duplicado **más pobre** | **Medio-alto.** Datos duplicados que divergen: el agente lee la ficha con el nodo `Leer ficha del cliente` **desde Postgres**. Si el dueño corrige un nombre en la hoja, el agente sigue viendo el de Postgres. Ninguna pestaña de Sheets puede alimentar ese nodo |
| **3. Hoja `Servicios`** (`serviceId, name, price, duration, category, active, imageUrl`) | **NO** | **`barber_servicios` ya existe** (clave, nombre, precio, duracion_min, activo) y ya está poblada con los 8 servicios reales. El comando del dueño `PRECIO <servicio> <precio>` actualiza esa tabla vía el nodo `Actualizar precio` (`UPDATE barber_servicios ...`) | **Alto.** Tercera fuente de precios (prompt + Postgres + Sheets). El prompt dice *"La tabla es la única fuente válida de precios"*: una hoja de servicios crearía cotizaciones contradictorias. `imageUrl` no lo consume ningún nodo |
| **4. Hoja `Transacciones`** (`transactionId, appointmentId, date, ...`) | **NO** | Con `Precio del servicio` + `Estatus` en la hoja (y `precio` + `estado` en `barber_citas`) ya se sabe qué se vendió y si se canceló. Una fila de transacción por cita multiplicaría las escrituras y **crearía una segunda tabla que el agente tendría que mantener en cada cancelación/reprogramación** | **Alto.** Doble escritura en cada acción; si una falla, la caja se descuadra. Además `transactionId` tipo `TXN-...` introduce otro ID que nadie cruza |
| **5. Hoja `Metricas_Diarias`** (`date, totalRevenue, totalAppointments, avgTicket, topService, topBarber, noShows, newCustomers`) | **NO** | Es **100 % derivable** de Postgres (o de Calendar + la hoja) con una consulta. Un cron en Sheets solo guarda una **foto congelada** que queda obsoleta en cuanto se cancela una cita. `topBarber` es inútil con un solo barbero | **Medio.** Snapshot obsoleto = decisiones con datos viejos. Y hay **otro subagente trabajando en métricas en Postgres**: crear métricas paralelas en Sheets pisaría ese trabajo y generaría dos cifras distintas de "ingresos del día" |

**Resumen:** de las 5 hojas propuestas, **0 se aprueban tal cual**. De los 12 campos de la hoja `Citas`, **11 se rechazan** y **1 se admite** en versión reducida.

---

## 4. Qué SÍ conviene añadir a la hoja actual

**Conclusión corta:** casi nada. La hoja está **alineada byte a byte** con lo que esperan los 4 nodos (lo verifica `verificar-hoja.py`). Tocar el encabezado es el único punto del sistema donde un cambio "inocente" tumba los recordatorios.

**Recomendación: NO cambiar la estructura.** Única adición admitida, **opcional y al final**:

| Columna nueva | Posición | Valor que aporta | ¿Obligatoria? |
|---|---|---|---|
| `Estado de pago` | **J** (después de `Execution ID`) | Permite al dueño marcar a mano si la cita ya se cobró (`pagado` / `pendiente`). Es el `paymentMethod` del documento, reducido a algo útil | **No.** Solo si el dueño la va a usar de verdad |

Por qué **solo al final** y **solo una**: el nodo 3 declara `matchingColumns: ["ID"]` y compara su `schema` contra el encabezado real. Añadir una columna **al final** deja el prefijo de 9 columnas intacto; añadirla en medio reordena las letras de columna y **desalinea el `schema`**.

**La versión de este cambio está en `G:\Barberia\archivos\hoja-citas-propuesta.csv`** (BOM UTF-8, encabezado propuesto + las 7 filas reales). **Es una propuesta: no se ha aplicado a la hoja.**

### Si algún día se aplica, el cambio exacto en cada uno de los 4 nodos

| Nodo | Workflow | Cambio exacto requerido |
|---|---|---|
| `Registrar en hoja de citas` | `barberiaAgenteUncensored` | En `parameters.columns.value` **añadir** `"Estado de pago": "={{ $fromAI('Estado_de_pago', 'pagado o pendiente; usa pendiente si no lo sabes', 'string') }}"`. En `parameters.columns.schema` **añadir** el objeto `{"id":"Estado de pago","displayName":"Estado de pago","type":"string","required":false,"display":true,"canBeUsedToMatch":true,"removed":false}`. **No tocar** `matchingColumns` (sigue `["ID"]`) |
| `Append or update row in sheet` | `barberiaRecordatorios` | En `parameters.columns.schema` **añadir** el mismo objeto `"Estado de pago"` (es el nodo que valida el esquema; si no se añade aquí, el `appendOrUpdate` falla con `Missing columns`). **No** añadirlo a `columns.value`: este nodo solo escribe `ID` y `Execution ID` |
| `Google Sheets Trigger` | `barberiaRecordatorios` | **Ninguno.** No guarda `schema`: lee todas las columnas. La columna nueva aparecería en su salida y no rompe nada |
| `OBTENER INFO DE CITA ELIMINADA` | `barberiaRecordatorios` | **Ninguno.** No guarda `schema` y filtra solo por el valor de `ID` |

**Y el orden de la operación importa.** El orden seguro es **encabezado primero, schema después**: escribir `Estado de pago` en la celda `J1` y, solo entonces, actualizar el `schema` de los nodos. Al revés, el nodo 3 queda esperando una columna que la hoja todavía no tiene y **rompe los recordatorios de inmediato**.

### Si la conclusión fuera "no cambiar nada"

También sería defendible: **no hay ninguna funcionalidad bloqueada por la hoja actual**. `Estado de pago` es comodidad para el dueño, no un requisito del sistema. Si el dueño no va a anotar los pagos a mano cada día, la decisión correcta es **no tocar nada** y dejar que el tracking de ingresos se resuelva en Postgres, donde sí se puede calcular solo.

---

## 5. Qué NO conviene, y por qué

1. **No convertir la hoja en la base de datos.** Postgres ya lo es: tiene PKs, FKs, tipos, constraints y el `trg_barber_citas_touch`. Una hoja no tiene tipos, no tiene constraints, y acepta el mismo `ID` dos veces.
2. **No duplicar `clientes` ni `servicios` en Sheets.** Son las dos tablas que **ya están implementadas y conectadas**: el agente lee la ficha del cliente con `Leer ficha del cliente` y actualiza precios con `Actualizar precio`. Duplicarlas crea la peor clase de bug: el que no da error, solo datos distintos.
3. **No crear `Transacciones`.** Es un join de `citas` con `servicios` disfrazado de tabla. Mantenerlo a mano en cada cancelación es trabajo garantizado y error garantizado.
4. **No crear `Metricas_Diarias` en Sheets.** Además de ser derivable, **pisa el trabajo de otro subagente** que está montando métricas en Postgres. Dos motores de métricas = dos cifras distintas.
5. **No cambiar los `ID` a `APT-...`.** Es el error más caro del documento: rompe cancelar y reprogramar (los dos flujos que el cliente usa cuando algo cambia) y deja huérfanos los `Execution ID`.
6. **No renombrar columnas al inglés.** `Día `, `Estatus` y `Numero celular` están **codificados literalmente** en los nodos, en el `Switch`, en los `IF` y en el `Code` del flujo 2 (que incluso tiene un fallback explícito para `"Día"` sin espacio). Renombrar es reescribir 15 nodos para no ganar nada.
7. **No meter una columna `barber`.** Con un solo barbero es una constante disfrazada de dato.
8. **No cambiar el teléfono a `+52...`.** El valor actual es un **JID de WhatsApp** que Evolution API consume directamente; `+52...` no es lo mismo.
9. **No añadir columnas en medio del encabezado.** Reordena y desalinea el `schema` de los nodos.
10. **No borrar `Execution ID` "porque está casi siempre vacía".** Está vacía porque se escribe en un segundo paso (`Code1` → nodo 3). Su ausencia **no es un dato, es el `Execution ID` que el sistema todavía no ha rellenado**. Borrarla rompe la cancelación de recordatorios.

---

## 6. Riesgos de romper el sistema

Lista concreta: **si cambias X, se rompe Y.**

| Si cambias… | Se rompe… | Cómo se manifiesta |
|---|---|---|
| El encabezado de la hoja (renombrar, reordenar, borrar) | **El flujo completo de recordatorios** | `NodeOperationError`: `Refresh the columns list in the 'Column to Match On' parameter. Missing columns: …` (ya visto: ejec. 720, 722) |
| Añadir/renombrar una columna en medio | El `schema` de los 2 nodos (deja de coincidir con la hoja) | El nodo 3 se niega a escribir; el `Execution ID` nunca se guarda |
| Dejar el encabezado con una fila vacía o celdas corridas | La lectura de columnas por clave | `Could not retrieve the columns from key row` (ya visto: ejec. 731, 732, 733) |
| `ID` → `APT-20240327-001` | **Cancelar** (`Cancelar cita`, `eventId`) y **Reprogramar** (`Reagendar`, `eventId`) | Google Calendar devuelve 404/400: el evento no existe con ese ID. El agente dirá que no encuentra la cita |
| `ID` → cualquier valor no-Calendar | El `matchingColumns: ["ID"]` del nodo 3 | No encuentra la fila a actualizar ⇒ `Execution ID` nunca se escribe ⇒ **no se quitan recordatorios de citas canceladas** |
| Quitar la columna `Execution ID` | `QUITAR RECORDATORIO` y el `appendOrUpdate` | El cliente recibe recordatorios de citas ya canceladas. Y el nodo 3 falla con `Missing columns: Execution ID` |
| `Estatus` a inglés (`confirmed`, `cancelled`…) | El `Switch` y `IF - Es cita agendada` del flujo 2 | Cae a *fallback* "Otro": **no se programa ningún recordatorio** y el dueño no recibe aviso de cita nueva |
| `Numero celular` de JID a `+52…` | `RECORDATORIO 24 H` y `RECORDATORIO 1 H` | Evolution API no entrega: el cliente no recibe recordatorios |
| Añadir columnas sin actualizar el `schema` del nodo 3 | El `appendOrUpdate` | `Missing columns: <nueva>` en cada fila nueva |
| Actualizar el `schema` **antes** que la hoja | El `appendOrUpdate` | Mismo error, pero ya con la hoja "correcta": confuso y difícil de diagnosticar |
| Tocar `barberiaRecordatorios` sin desactivar/reactivar bien | **Las 4 ejecuciones `waiting`** (2026-09-27, 09-30, 10-07, 12-02) | Recordatorios pendientes que no se disparan, o PUT rechazado por n8n |
| Renombrar la pestaña `Hoja 1` | `sheetName: "941506024"` en los 4 nodos | Se resuelve por **gid**, no por nombre, así que renombrar la pestaña es *relativamente* seguro — pero **no cambiar el gid ni mover/crear pestañas** |
| Añadir pestañas al mismo spreadsheet | El `Google Sheets Trigger` | Sigue leyendo el gid `941506024`, así que **no** se rompe — pero añadir pestañas invita a que alguien escriba en la equivocada |

---

## 7. Cómo verificar que todo sigue sano

```
uv run python G:\Barberia\archivos\verificar-hoja.py
```

El script **no modifica nada** (descarga el export CSV público) y comprueba:

1. que la hoja responde y el encabezado se lee;
2. que el encabezado coincide **exactamente y en orden** con el `schema` del nodo `Append or update row in sheet`;
3. que las 8 columnas del nodo `Registrar en hoja de citas` existen en la hoja;
4. que **`Execution ID` existe** (crítico para los recordatorios);
5. que ninguna cabecera tiene espacios sobrantes, **salvo `Día `**, que se documenta como excepción intencional;
6. que no hay cabeceras vacías ni duplicadas;
7. que los `ID` parecen IDs de Google Calendar (20+ caracteres, minúsculas y dígitos, sin espacios ni acentos);
8. avisos de calidad de datos (celdas críticas vacías, IDs de prueba).

Imprime **OK/FALLO** por comprobación y un resumen. Con `--metodo n8n` usa un workflow temporal con webhook (solo `GET`) que **se borra al terminar**, para cuando la hoja deje de ser pública.

### Resultado de la ejecución de hoy

```
Comprobaciones : 13
OK             : 12
FALLOS         : 1
Avisos         : 2

FALLOS:
  - todos los 'ID' no vacios parecen IDs de Google Calendar
```

**El único FALLO no es de esquema, es de datos de prueba.** La fila 5 tiene
`ID = "Corte desvanecido o tijera — Prueba Cancelar"` y la 6 `ID = "placeholder"`:
son restos de pruebas, **no** IDs de Calendar. En una fila así, `Cancelar cita` y
`Reagendar` no pueden funcionar y el nodo 3 no encontrará la fila. Es basura de
pruebas en la hoja, no un problema de estructura: **conviene limpiarla, no
reestructurarla.**

Los 2 avisos (`Execution ID` vacío en algunas filas, 1 fila sin teléfono) son
**normales** en el estado actual: `Execution ID` se rellena en un segundo paso,
y las filas sin teléfono son de pruebas.

---

## 8. Recomendación final

| Decisión | Acción |
|---|---|
| ¿Reestructurar a 5 hojas? | **No.** |
| ¿Cuántas hojas? | **Una** (la actual, `Citas barberia`). |
| ¿Añadir columnas? | Opcional, **una**, `Estado de pago`, **al final (J)**. Y solo si el dueño la va a usar. |
| ¿Cambiar los `ID`? | **No.** Deben seguir siendo IDs de evento de Google Calendar. |
| ¿Renombrar columnas? | **No.** |
| ¿Tocar los workflows? | **No** (salvo que se apruebe `Estado de pago`, y entonces con el orden de §4). |
| Datos duplicados de clientes/servicios | **No.** Viven en Postgres (`barber_clientes`, `barber_servicios`). |
| Transacciones y métricas | **No en Sheets.** Se derivan en Postgres. |
| Acción inmediata recomendada | Limpiar las 2 filas con `ID` de prueba y mantener la hoja tal cual. |

**En una frase:** el documento propone construir una segunda base de datos dentro de la hoja; este sistema ya tiene su base de datos en Postgres, y la hoja solo necesita seguir siendo lo que es — un registro legible que dispara recordatorios.

---

## Anexo · Evidencia y archivos

**Verificado en vivo:**
- Encabezado real de la hoja (export CSV público, gid `941506024`).
- Workflows vía API de n8n (`/api/v1/workflows/barberiaAgenteUncensored` y `.../barberiaRecordatorios`): **52 y 15 nodos** (16 al re-verificar al final), leídos y no modificados.
- Esquemas de los nodos comparados contra el encabezado real: `schema` del nodo 3 **coincide exactamente** con la hoja (9 columnas, mismo orden); las 8 del nodo 1 coinciden 1:1 con el prefijo.
- Historial de ejecuciones y errores (ejecuciones 720, 722, 731, 732, 733).
- 4 ejecuciones `waiting` con su `waitTill` (6 al re-verificar al final).
- Esquema y conteos de Postgres (10 tablas `barber_*`; `barber_citas`, `barber_clientes`, `barber_auditoria` **vacías**).

**Archivos entregados:**
- `G:\Barberia\archivos\ANALISIS-HOJA.md` — este informe.
- `G:\Barberia\archivos\hoja-citas-propuesta.csv` — propuesta (BOM UTF-8, encabezado + 7 filas reales). **No aplicada.**
- `G:\Barberia\archivos\verificar-hoja.py` — verificador de solo lectura.

**No se modificó:** la hoja de Google, ningún workflow de n8n, ni Postgres.
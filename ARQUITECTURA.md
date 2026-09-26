# Arquitectura del sistema — Barber Chinos

Documento de traspaso. Explica **cómo está construido** el sistema, **por
qué** cada pieza está donde está, y **dónde tocar** para cada tipo de
mejora. Está pensado para que otro agente (o tú) pueda modificarlo sin
romper nada.

Toda la información de aquí está **extraída del sistema en vivo**, no
escrita de memoria. El inventario crudo está en `INVENTARIO.json` y la
lista de nodos en `NODOS.txt`.

---

## 1. Qué es el sistema, en una frase

Un agente de WhatsApp que atiende clientes de una barbería, agenda citas
solo, avisa al barbero y le da un panel con los números del negocio.

---

## 2. Las cuatro capas

```
┌──────────────────────────────────────────────────────────────────┐
│  ENTRADA            WhatsApp  ──►  Evolution API                 │
└──────────────────────────────┬───────────────────────────────────┘
                               │ POST /webhook/hector
┌──────────────────────────────▼───────────────────────────────────┐
│  ORQUESTACIÓN       n8n (3 workflows, 67 nodos en total)         │
│   1. Agente de citas     45 nodos   ← el cerebro                 │
│   2. Recordatorios       17 nodos   ← avisos a 24 h y 1 h        │
│   3. Vigilancia           5 nodos   ← detecta citas en el pasado │
└──────────────────────────────┬───────────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────────┐
│  DATOS              Google Calendar  ← LA VERDAD de la agenda    │
│                     Google Sheets    ← el registro visible       │
│                     Postgres         ← CRM, FAQs, memoria        │
│                     Supabase         ← réplica (opcional)        │
└──────────────────────────────┬───────────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────────┐
│  SALIDA             WhatsApp (respuestas) + Panel web (KPIs)     │
└──────────────────────────────────────────────────────────────────┘
```

**La decisión más importante de toda la arquitectura:** Google Calendar
es la **fuente de verdad** de la agenda. No hay dos sitios donde vivan las
citas. La hoja de cálculo y Postgres son **vistas** de lo que hay en el
calendario. Si algún día hay que elegir entre lo que dice la hoja y lo que
dice el calendario, **manda el calendario**.

**Por qué:** el barbero ya usa Google Calendar en su teléfono. Si el
sistema inventara su propia base de citas, habría dos agendas y tarde o
temprano se contradirían.

---

## 3. Workflow 1 — Agente de citas (45 nodos)

Es el corazón. Este es el recorrido real de la información:

```
Webhook
  └─► Normalizacion            (extrae texto, JID, nombre, tipo)
        └─► Leer operadores    (¿quién escribe? ¿dueño o cliente?)
              └─► Comprobar operador
                    └─► ¿Es operador?
                          ├─ SÍ ─► Router de comandos ─► 12 rutas del dueño
                          └─ NO ─► IF - No es del bot
                                     └─► Leer pausa
                                           └─► Calcular pausa
                                                 └─► IF - Cliente pausado
                                                       ├─ SÍ ─► (silencio)
                                                       └─ NO ─► Switch
                                                                  ├─ texto ─► Edit Fields2
                                                                  │    └─► Edit Fields ─► AI Agent
                                                                  └─ otro ──► Aviso solo texto
                                                                                └─► Mandar mensaje
```

### 3.1 El router del dueño: 12 comandos sin coste

`Router de comandos` es un **Switch de 12 salidas**, evaluadas en orden.
**Va antes del modelo de lenguaje**, así que consultar la agenda cuesta
**0 tokens**.

| Salida | Comando | Cadena que ejecuta |
|---|---|---|
| 0-3 | `HOY` `MANANA` `SEMANA` `LIBRE` | `Preparar rango de fechas` → `Leer agenda` → `Formatear agenda` |
| 4 | `CLIENTE <num>` | `Buscar cliente` → `Leer ficha` → `Formatear ficha` |
| 5-7 | `BLOQUEAR` `CERRAR` `ABRIR` | `Parsear bloqueo` → `IF - Bloqueo invalido` → `Crear bloqueo` |
| 8 | `PRECIO <serv> <monto>` | `Parsear precio` → `Actualizar precio` |
| 9 | `PAUSA <num> <tiempo>` | `Parsear pausa` → `Aplicar pausa` |
| 10 | `ESTADO` | `Leer estado del sistema` |
| 11 | `COMANDOS` | `Armar respuesta COMANDOS` |
| 12 | (cualquier otra cosa) | `IF - No es del bot` → **sigue al cliente** |

**Todas las ramas terminan en `Responder al operador`**, que envía por
Evolution API. Ninguna pasa por el modelo.

**Si añades un comando 13**, tienes que tocar **tres sitios**: la regla del
Switch, la conexión nueva, y el texto de ayuda en `Armar respuesta
COMANDOS`. El `verify.py` comprueba que el número de salidas cuadre.

### 3.2 El agente: 6 herramientas y una memoria

`AI Agent` (LangChain) recibe:

| Conexión | Nodo | Para qué |
|---|---|---|
| `ai_languageModel` | `OpenAI Chat Model` | Uncensored AI, `gpt-4o` |
| `ai_memory` | `Postgres Chat Memory` | el historial, **ventana de 12** |
| `ai_tool` ×6 | `Consultar agenda`, `Agendar cita`, `Cancelar cita`, `Reagendar`, `Registrar en hoja`, `Notificar al encargado` | lo que el modelo puede hacer |

**La ventana de memoria es crítica.** Sin `contextWindowLength`, cada
mensaje reenvía **todo** el historial al modelo. Se midió una conversación
con 642 mensajes: 136 kB por turno. Con la ventana de 12, 2,7 kB. **98%
menos.** Si alguien la quita, el coste se dispara de forma cuadrática.

### 3.3 Los comandos del cliente (las 6 herramientas)

El modelo decide cuándo usarlas. Todas van contra **Google Calendar**,
salvo `Registrar en hoja` (Sheets) y `Notificar al encargado` (HTTP).

**Lo que NO hace el modelo:** no calcula disponibilidad a mano, no
inventa precios, no escribe en la base directamente. Todo pasa por una
herramienta.

### 3.4 El corte de multimedia

`Switch` tiene **una sola regla** (`texto`) y una salida de respaldo
llamada `Solo texto` → `Aviso solo texto` → `Mandar mensaje`.

Cuando llega un audio, una foto o un video, **no se llama al modelo**:
se responde con un texto fijo. Esto es **deliberado** (restricción del
dueño) y además ahorra tokens. Los 8 nodos que procesaban multimedia se
eliminaron; `verify.py` comprueba que no vuelvan.

---

## 4. Workflow 2 — Recordatorios (17 nodos)

Se dispara con un **trigger de Google Sheets**: cada vez que cambia una
fila.

```
Google Sheets Trigger
  └─► Code               (normaliza la fila)
        └─► IF - Es cita agendada
              ├─ Notificar cita nueva al encargado   (avisa al barbero)
              ├─ Registrar cliente (CRM)             (UPSERT en Postgres)
              └─ Registrar cita (Postgres)           (UPSERT en Postgres)
                    └─► Switch  (agendado / cancelado / actualizado)
                          ├─ agendado ──► Code1 ──► Append row
                          │                 └─► IF 24h ─► ESPERAR 24H ─► RECORDATORIO 24H
                          │                                            └─► IF 1h ─► ESPERAR 1H ─► RECORDATORIO 1H
                          └─ cancelado/actualizado ──► OBTENER INFO ──► QUITAR RECORDATORIO
```

**Detalles que importan si lo tocas:**

- El **`Switch` acepta alias**: `cancelado` **y** `eliminado`;
  `actualizado` **y** `reprogramado`. Esto es porque el agente escribe unos
  y Google Sheets devuelve otros. Sin los alias, un cliente que cancela
  **sigue recibiendo recordatorios**.
- `Registrar cliente (CRM)` y `Registrar cita (Postgres)` existen porque
  **antes nada escribía en esas tablas**, y el comando `CLIENTE` siempre
  decía "no encontré ficha". Son **UPSERT**, no INSERT: se puede repetir.
- Las columnas de la hoja son un **contrato frágil**. Si falta una, n8n
  falla con *"Column names were updated after the node's setup"*. La
  columna **`Execution ID` es obligatoria** o el flujo de recordatorios
  se rompe.

---

## 5. Workflow 3 — Vigilancia (5 nodos)

El más simple y el que evita el error más grave:

```
Cada 15 minutos ─► Leer calendario ─► Buscar citas pasadas ─► IF ─► Avisar al dueño
```

**Por qué existe:** el agente llegó a agendar una cita **en el pasado**
(dijo "el jueves" un viernes y reservó el jueves anterior). Se corrigió el
prompt, pero el prompt puede fallar. Este workflow es la **red de
seguridad**: si aparece una cita en el pasado, el dueño se entera en 15
minutos.

---

## 6. Los datos

### 6.1 Google Calendar — la verdad

```
Calendario: b5e08030160a7cead790f900fafd3728792af6d2eac8a22b1dedb7844c09143c@group.calendar.google.com
Nombre: BARBER
```

El **ID del evento ES el ID de la fila** en la hoja. No son dos cosas
distintas: el mismo identificador. **Por eso no se puede reestructurar la
hoja a varias pestañas** — rompería la relación y con ella cancelar y
reprogramar.

### 6.2 Google Sheets — el registro visible

```
Hoja: 1lvSVFWU2ApvK7p5BsFHI68Icur46P6hI8o8r9ozhBfk
gid:  941506024
```

Columnas, **en este orden exacto**:

```
ID | Estatus | Nombre | Servicio | Precio del servicio | Día  | Hora | Numero celular | Execution ID
```

⚠️ **`Día ` lleva un espacio al final.** Es intencional: así está en la
hoja y así lo espera el nodo. Si lo "corriges", se rompe.

### 6.3 Postgres — el CRM y el conocimiento

Las tablas del negocio (el resto de las 160 tablas son de n8n):

| Tabla | Filas | Para qué |
|---|---:|---|
| `barber_citas` | 0 | espejo de las citas, con constraint anti-solape |
| `barber_clientes` | 2 | ficha del cliente: visitas, gasto, etiqueta |
| `barber_servicios` | 8 | catálogo con precios y duraciones |
| `barber_conocimiento` | 58 | FAQs con búsqueda de texto completo |
| `barber_operadores` | 2 | quién es el dueño (dos formatos del mismo número) |
| `barber_pausas` | 0 | clientes silenciados |
| `barber_bloqueos` | 0 | rangos cerrados |
| `barber_escalaciones` | 0 | casos que el bot no pudo resolver |
| `barber_auditoria` | 0 | registro de cambios |
| `barber_consentimiento` | 0 | consentimiento de datos |
| `barber_lista_espera` | 0 | lista de espera |
| `n8n_chat_histories` | 1020 | **la memoria del agente** |

**La constraint que más importa:**

```sql
ALTER TABLE barber_citas ADD CONSTRAINT barber_citas_no_solape
  EXCLUDE USING gist (tstzrange(inicio, fin) WITH &&)
  WHERE (estado IN ('agendado','confirmado'));
```

Hace **imposible** que dos citas activas se solapen, a nivel de base de
datos, aunque el código esté mal. Requiere la extensión `btree_gist`
(gratuita, viene con Postgres).

Comportamiento **verificado**:

| Caso | Resultado |
|---|---|
| Dos citas solapadas, ambas `agendado` | **RECHAZADO**, `SQLSTATE 23P01` |
| Dos citas **pegadas** (10:00-10:40 y 10:40-11:00) | Aceptado ✅ |
| Una cita `cancelado` solapada con una activa | Aceptado ✅ (el filtro `WHERE` la excluye) |
| Una cita `atendido` solapada | Aceptado ✅ (igual) |

> ⚠️ **Corregido: esta constraint faltaba en el Postgres local.** Estaba
> solo en Supabase, que es la base que **nadie escribe**. Es decir, la
> protección existía en el sitio equivocado. Se aplicó al local y se probó
> (script `archivos/admin/aplicar-constraint-local.py`). Si levantas el
> sistema en otro equipo, **hay que volver a aplicar el ALTER TABLE**: el
> esquema base no la incluye.

### 6.4 Supabase — la réplica

8 tablas espejo, con el mismo esquema (y **con** la constraint
anti-solape que al local le faltaba). **No está conectado a n8n**: hoy es
una copia que se puede consultar desde fuera.

⚠️ **Detalle técnico importante:** el host directo de Supabase resuelve
**solo IPv6** y no es alcanzable desde el contenedor. Hay que usar el
**pooler**:

```
aws-0-us-east-2.pooler.supabase.com:5432
usuario: postgres.zucgrcyzofelmiorvxhb
```

Y las claves `publishable` **no permiten DDL** (crear tablas). Para eso
hace falta conexión directa a Postgres o la `secret key`.

> El proyecto se **pausa tras 7 días sin actividad** en el plan gratuito.
> Se puede reactivar hasta un año después.

---

## 7. El frontend

Hay **dos paneles**, y esto es importante que no se confunda:

| | Panel de producción | Panel administrativo |
|---|---|---|
| Archivo | `archivos/dashboard/dashboard.html` | `archivos/admin/barber-chinos-admin.html` |
| Datos | **reales**, leídos de Postgres | de ejemplo, hardcodeados |
| Generación | `generar-dashboard.py` consulta Postgres y escribe el HTML | estático |
| Estética | Mr.BLACK | Quintin Lodge |
| Para qué | el día a día del barbero | referencia visual / maqueta |

### 7.1 El panel de producción

```
Postgres ──► generar-dashboard.py ──► dashboard.html ──► navegador
                                          ▲
                            servidor-dashboard.py (puerto 8099)
                            lo regenera cada 120 s
```

**El contrato de datos es intocable.** `render()` recibe exactamente:

```python
render(resumen, estados, servicios, horas, dias30, hoydia, proximas, fecha_hoy)
```

Con estas claves y columnas (si cambias una, se rompe la plantilla):

```
resumen : citas_totales, citas_sin_fecha, ing_hoy, ing_sem, ing_mes,
          n_hoy, n_sem, n_mes, tk_hoy, tk_sem, tk_mes, futuras,
          futuras_7, ing_fut_7, no_show_mes, canc_mes, prog_mes,
          cli_mes, cli_nuevos_mes, citas_recurrentes_mes,
          clientes_crm, fecha_hoy, hora_generado

dias30    : etiqueta, ingresos, n
servicios : servicio, ingresos, n
horas     : hora, n
estados   : estado, n
hoydia    : hora, nombre, servicio, precio, estado
proximas  : cuando, nombre, servicio, precio
```

Y estos ayudantes con **firma fija**: `num()`, `entero()`, `dinero()`,
`esc()`, `barra(etiqueta, valor_txt, proporcion, detalle)`,
`tarjeta(titulo, valor, pie, acento)`, `vacio(mensaje)`.

### 7.2 El panel administrativo

Un **único archivo de 438 KB**, sin servidor ni internet. Se genera en
tres partes:

```
plantilla.html   (el CSS)
app.js.html      (el JavaScript)
generar-admin.py (junta todo + los datos de ejemplo)
      └─► barber-chinos-admin.html
```

Las fuentes (Inter y JetBrains Mono) van **embebidas en base64**
(363 KB del total) para que funcione sin red.

---

## 8. Dónde tocar para cada tipo de mejora

Esta es la tabla que más te va a servir.

| Quiero… | Archivo / nodo | Cuidado con… |
|---|---|---|
| **Cambiar precios o servicios** | `prompt-sistema-agente-barberia.txt` + tabla `barber_servicios` + `MANUAL` | Los tres sitios deben coincidir. `verify.py` comprueba 8 precios |
| **Añadir un comando del dueño** | `Router de comandos` (regla + conexión) + `Armar respuesta COMANDOS` | `verify.py` cuenta las salidas del Switch |
| **Cambiar cómo responde el agente** | `prompt-sistema-agente-barberia.txt`, luego `subir-prompt.py` | Prompts largos cuestan más: el prompt se envía **en cada mensaje** |
| **Añadir una herramienta al agente** | Nodo nuevo + conexión `ai_tool` | El modelo decide cuándo usarla: hay que describirla bien |
| **Cambiar la disponibilidad** | El prompt (reglas de negocio) + Calendar | El servicio debe **terminar** antes de las 20:00 |
| **Tocar el panel de producción** | `archivos/dashboard/` | **No cambies el contrato de datos** de `render()` |
| **Rediseñar el panel** | `archivos/admin/` | Mantén lo de "funciona sin servidor" |
| **Añadir una FAQ** | Tabla `barber_conocimiento` | La búsqueda usa `spanish_unaccent`: `depilacion` encuentra `depilación` |
| **Cambiar el tono de los mensajes** | El prompt, sección de estilo | WhatsApp: negrita es `*un asterisco*`, **nunca `**`** |
| **Añadir un canal (Telegram, etc.)** | Rechazado: ver sección 11 | — |

---

## 9. Reglas de negocio que están codificadas

Estas no son preferencias: son restricciones del dueño o verdades del
negocio. **No las cambies sin confirmar.**

| Regla | Dónde vive |
|---|---|
| Un solo barbero: **Esteban Aguilera** | No hay tablas por barbero. Cualquier "ranking por barbero" sería la misma fila |
| Lunes a sábado, 10:00 a 20:00 | Prompt |
| Domingo **cerrado** | Prompt |
| El servicio debe **terminar** antes de las 20:00 | Prompt, con tabla de ejemplo |
| Zona horaria fija **−06:00** (America/Mexico_City) | Prompt |
| Dirección: Calle Pinzón #574 · 452-281-8144 | Prompt, panel, Supabase |
| **No** hay estacionamiento | Prompt (confirmado por el dueño) |
| Pago: **efectivo o transferencia** | Prompt (confirmado) |
| **Sí** hay wifi | Prompt (confirmado) |
| Tolerancia de **5 a 10 minutos** | Prompt (confirmado) |
| Canal: **solo WhatsApp** | Prompt (confirmado) |
| **No** se procesan audios ni imágenes | Switch + aviso automático |
| **No** se aceptan pagos con tarjeta | Fuera por decisión del negocio |
| **No** se usa CAPTCHA | Restricción |
| Solo herramientas **gratuitas** | Restricción |

---

## 10. Cómo se verifica

El sistema tiene **187 comprobaciones** automáticas. Es la red de
seguridad para cualquier cambio.

```powershell
uv run python archivos/sincronizar-archivos.py   # vuelca n8n a JSON
uv run python verify.py                          # 187 comprobaciones
```

**Siempre sincroniza antes de verificar**, porque los cambios viven en n8n
y el verificador lee los JSON.

| Suite | Qué comprueba |
|---|---|
| `verify.py` | 187: estructura, conexiones, prompt, modelo, comandos, precios |
| `test-estados.py` | 52: la máquina de estados de las citas |
| `test-comandos.py` | 49: el router del dueño |
| `dashboard/verificar-patrones.py` | 11: el panel |
| `admin/verificar-file-real.py` | 9: que abra sin servidor |
| `admin/verificar-vistas.py` | 6: las secciones del panel admin |

---

## 11. Decisiones ya tomadas, y por qué

Si vuelves a proponer alguna de estas, aquí está la razón por la que se
descartó.

| Se descartó | Por qué |
|---|---|
| **RAG con embeddings** | **Imposible, no caro.** Uncensored AI no tiene endpoint de embeddings (`/embeddings` → 404; 98 modelos, ninguno de embeddings) y el Postgres local no tiene `pgvector`. Se usa búsqueda de texto completo: gratis, nativa y mejor a esta escala |
| **Telegram** | No hay personal. Los 2 "operadores" son el mismo dueño en dos formatos. Cero escalaciones que aprobar |
| **Reestructurar la hoja a pestañas** | El `ID` de la hoja **es** el id del evento de Calendar. Romperlo rompe cancelar y reprogramar |
| **Looker Studio / Metabase / Grafana** | Expondrían la base a internet |
| **Pagos con tarjeta** | Decisión del negocio |
| **Audio e imagen** | Restricción del dueño. Ahorra tokens además |
| **Captcha** | Restricción |
| **Librerías de gráficas** | Serían una dependencia externa; el panel debe abrir sin internet |
| **`Minimalist-Dashboards` como fuente de CSS** | Es YAML de Home Assistant, no CSS. Solo 5 patrones estructurales eran portables |

---

## 12. Cómo se despliega y se opera

### Los contenedores

| Contenedor | Qué es |
|---|---|
| `barberia-n8n` | n8n 2.40.6 |
| `barberia-postgres` | la base de datos |
| `evolution_api` | el puente a WhatsApp (instancia `hector`) |

### Los 3 workflows deben ser los únicos

Si aparece un workflow con nombre raro (`_verif-...`, `My workflow`), es
basura de alguna prueba. Hay que borrarlo.

### Credenciales (7)

| Nombre | Para qué |
|---|---|
| `Evolution API` | enviar WhatsApp |
| `Postgres account` | CRM, memoria, FAQs |
| `Google Calendar account` | la agenda |
| `Google Sheets account` | el registro |
| `Google Sheets Trigger account` | detectar cambios |
| `Uncensored AI (OpenAI-compatible)` | el modelo |
| `n8n API (local)` | quitar recordatorios |

### Los comandos de operación

```powershell
# ver el estado
docker ps --format "{{.Names}}\t{{.Status}}"

# exportar los workflows a JSON
docker exec barberia-n8n n8n export:workflow --all --output=/tmp/w.json

# ver las últimas ejecuciones
# (o por la API: GET /api/v1/executions)
```

**Nota sobre la API de n8n:** hay que **desactivar el workflow antes de
un PUT y reactivarlo después**. Si no, el PUT falla.

---

## 13. Trampas conocidas (esto te ahorrará horas)

Cada una de estas costó tiempo descubrirla:

| Trampa | Qué pasa | Solución |
|---|---|---|
| `getSheetId()` con `gid=123` | `parseInt('gid=123')` → `NaN` | Pasar el **número crudo** (`"941506024"`) |
| Nodo que devuelve 0 items | n8n **corta la cadena** | `alwaysOutputData: true` |
| Valores por defecto en la exportación | n8n los **omite** al exportar | Comparar con `is not True`, no `is not False` |
| Webhook sin `httpMethod` | **solo acepta GET** → 404 en POST | Declarar `httpMethod: POST` |
| Orden de salidas de un `Switch` | primero las **reglas**, luego el respaldo | Contar bien los índices |
| `INSERT … SELECT` sobre tabla vacía | inserta 0 filas **sin error** y devuelve `{"success":true}` | Construir el valor, no seleccionarlo |
| `psql` con `-c` no sustituye `:'var'` | el placeholder llega literal | Usar `psql -f` |
| `psql` manda los ERROR a **stderr** | un éxito aparente puede ser un fallo | Leer siempre `stderr` |
| La clave del vendedor en los nodos | vivía en `parametersHeaders.values[]`, no en `headerParameters` | Buscar en los dos sitios |
| Columna `Execution ID` | sin ella, los recordatorios fallan | No borrarla nunca |
| Supabase directo | resuelve **solo IPv6**, inalcanzable desde el contenedor | Usar el **pooler** |
| Claves `publishable` de Supabase | no permiten DDL (401 "Secret API key required") | Conexión directa o `secret key` |
| Iframe `http` leyendo `file://` | el navegador lo bloquea: devuelve ceros | Inyectar el script de medición **en el propio archivo** |
| Medir antes de tiempo | el preloader tarda 3,3 s en irse | Medir a los 5 s |
| Capturar el panel | Chrome headless fuerza 504 px de ancho mínimo | Usar un iframe de 390 px para el móvil |

---

## 14. Coste

| Concepto | Valor |
|---|---|
| Prompt del sistema | ~41.000 caracteres (~10.400 tokens) |
| Se envía | **en cada mensaje** |
| Memoria | ventana de **12 mensajes** (2,7 kB) |
| Coste por turno | ~$0,026 |
| A 500 mensajes/mes | ~$13 |

**Lo que más mueve la aguja:** el tamaño del prompt y la ventana de
memoria. Antes de la ventana, una conversación larga costaba 136 kB por
turno en vez de 2,7 kB.

---

## 15. Lo que falta

| Pendiente | Nota |
|---|---|
| Conectar n8n a Supabase | Hoy Supabase es una copia sin sincronizar |
| Confirmar 13 FAQs | Las de políticas marcadas como `propuesta` en `barber_conocimiento` |
| Conectar la búsqueda de FAQs al agente | La tabla y `barber_buscar` existen; el agente todavía no las consulta |
| Regeneración automática del panel | Hoy hay que abrirlo o dejar el servidor corriendo |
| Abrir el puerto 8099 en el Firewall | Para ver el panel desde el celular |

---

## 16. Si vas a modificar algo, el orden es este

1. **Lee primero** esta sección y la tabla de la sección 8.
2. **Comprueba la restricción**: ¿toca alguna regla de la sección 9?
3. **Modifica** en n8n o en los archivos.
4. **Sincroniza y verifica**:
   ```powershell
   uv run python archivos/sincronizar-archivos.py
   uv run python verify.py
   ```
   Debe dar **187/187**. Si baja, algo se rompió.
5. **Prueba en vivo** con el número de pruebas
   (`5214501111805@s.whatsapp.net`), no con el del dueño.
6. **Limpia**: si creaste un workflow temporal, bórralo.

---

## Archivos de referencia

| Archivo | Qué tiene |
|---|---|
| `INVENTARIO.json` | workflows, nodos, conexiones y esquema, extraído en vivo |
| `NODOS.txt` | lista legible de nodos y conexiones |
| `../prompt-sistema-agente-barberia.txt` | el prompt completo |
| `../verify.py` | las 187 comprobaciones |
| `../archivos/MANUAL-DUENO.md` | manual para el barbero (no técnico) |
| `README.md` | este documento, orientado a producto |
| `REDISENO.md` | el rediseño del panel de producción |
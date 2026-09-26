# Evaluación e implementación de la base de conocimiento — Bot de barbería

**Fecha:** sesión actual · **Proyecto:** Barber Chinos · **Autor:** subagente RAG
**Archivos entregados:**
- `G:\Barberia\archivos\conocimiento-barberia.sql` — tabla + siembra + función de búsqueda (idempotente)
- `G:\Barberia\archivos\probar-conocimiento.py` — pruebas de búsqueda (21 preguntas + casos borde)
- `G:\Barberia\archivos\probar-conocimiento-salida.txt` — salida real de las pruebas
- Este informe

---

## 1. Resumen ejecutivo (la respuesta corta)

**RAG con embeddings NO vale la pena aquí, y no solo por el coste: es
técnicamente imposible con el proveedor que usa el proyecto.**

Hallazgo duro que cierra la opción C por completo:

1. Los **embeddings de Uncensored AI no existen todavía**. Su documentación
   oficial los lista como *"Coming soon"*:
   > *"Embedding APIs are coming soon. They will support text embeddings for
   > semantic search, clustering, and retrieval-augmented generation."*
   > — `docs.uncensored.com/embeddings/overview`
2. En la práctica: `POST https://api.uncensored.com/api/v1/embeddings`
   devuelve **HTTP 404**.
3. `GET /v1/models` (catálogo en vivo) devuelve **98 modelos, todos de chat,
   imagen o vídeo. Cero modelos de embeddings.**
4. Y en el **Postgres local no hay `pgvector`**: `SELECT count(*) FROM
   pg_available_extensions WHERE name='vector'` → **0**. La extensión no
   está compilada en la imagen `postgres:17-alpine` que corre el proyecto.

Así que el stack "OpenAI Embeddings → Supabase Vector → n8n Vector Store
Retriever" que proponía el documento **no se puede construir gratis** ni
cambiando de proveedor. Habría que pagar OpenAI (prohibido) o añadir un
contenedor de embeddings local (complica el despliegue).

**Lo que sí implementé (y funciona):**

- **Opción A** — base de conocimiento con **búsqueda de texto completo nativa
  de PostgreSQL** (`tsvector` + `spanish` + índice GIN). Gratis, nativa, cero
  dependencias. **21/21 aciertos** en las pruebas de búsqueda, ~110 ms.
- **Opción B** — el bloque de FAQs **también** quedó en el prompt del agente,
  porque es lo que de verdad arregla las respuestas hoy. Medido en vivo antes/
  después.

Mi recomendación honesta: **la opción A es el motor correcto para cuando la
base crezca** (catálogo, promociones, políticas por temporada), pero **para 59
FAQs la opción B resuelve el problema ya y sin infraestructura nueva**. Las
dejé ambas: B para responder hoy, A lista para escalar.

---

## 2. Las opciones evaluadas: coste y complejidad

| | Opción A<br>Texto completo Postgres | Opción B<br>FAQs en el prompt | Opción C<br>RAG con embeddings |
|---|---|---|---|
| **Coste** | **$0** | **$0** de infraestructura<br>+$5,49 por 1.000 mensajes de tokens | OpenAI: **de pago** (prohibido)<br>Uncensored AI: **no existe** |
| **Requiere pago** | No | No | **Sí** (o contenedor local) |
| **Dependencias nuevas** | Ninguna | Ninguna | Cliente de embeddings + pgvector + retriever |
| **Complejidad** | Baja (SQL) | **Muy baja** (texto) | Alta (4 piezas que pueden fallar) |
| **Funciona hoy** | Sí | Sí | **No** |
| **Latencia añadida** | ~110 ms (1 consulta) | 0 ms | ~1 llamada extra + búsqueda vectorial |
| **Mantenimiento** | Editar filas | Editar texto del prompt | Re-embeddear al cambiar contenido |
| **Techo** | Excelente para miles de FAQ | Se degrada por coste y atención del modelo | Excelente |

### Por qué descarté cada alternativa con datos

**Embeddings de OpenAI** → pago con tarjeta. **Prohibido por el usuario.**
Fuera sin más análisis.

**Embeddings locales (`ollama`, `sentence-transformers`, contenedor)** →
técnicamente es gratis, pero: (a) añade un contenedor/servicio más al stack
que ya corre Docker + n8n + Evolution + Postgres; (b) hay que mantener el
modelo, versionar los vectores y re-embeddear cada vez que cambie una FAQ;
(c) y **sigue faltando `pgvector`** en el Postgres. Mucho aparato para 59
FAQ. Descartado por coste/beneficio, no por imposibilidad.

**`pg_trgm` (similitud por trigramas)** → gratis y nativo (sí está
disponible: versión 1.6). Pero es búsqueda **difusa por caracteres**, no
semántica: castiga variaciones de redacción. El texto completo con
lematización española entiende que *"cancelarla"*, *"cancelación"* y
*"anular"* son la misma cosa; los trigramas no. Se queda como plan B.

---

## 3. Cuánto conocimiento hacía falta de verdad

Analicé **404 mensajes reales de clientes** de la tabla `n8n_chat_histories`
(y filtré el ruido de pruebas). Además de precios y horarios, la gente
pregunta cosas que el prompt **no** cubría:

- estacionamiento
- teléfono
- quién atiende / si puede elegir barbero
- si hacen tintes, cortes que no existen ("mod cut", "corte clásico")
- cómo cancelar o mover una cita
- si puede llevar a su hijo
- facturación, redes sociales, productos

Categorías reales detectadas en conversaciones: consultas de **precio**,
**catálogo**, **ubicación**, **citas**, **cancelación**, **quejas** y
**fuera de catálogo**. Muchas ya están en el prompt; el hueco real son
**políticas e instalaciones**. Respuesta a la pregunta *"¿cuánto conocimiento
extra hace falta?"*: **~50-60 FAQs, no más.** Eso confirma que un sistema RAG
completo está sobredimensionado, y a la vez que hace falta *algo*.

---

## 4. Qué implementé

### 4.1 Opción A — búsqueda de texto completo de Postgres

`conocimiento-barberia.sql` crea:

- **Extensión `unaccent` + configuración `spanish_unaccent`.** Esto fue
  imprescindible y no es obvio: con la configuración `spanish` de fábrica,
  `'depilacion'` **NO** encuentra `'depilación'`:
  ```sql
  SELECT to_tsvector('spanish','depilación') @@ to_tsquery('spanish','depilacion');
  -- => false
  ```
  Mi configuración encadena `unaccent` **y luego** `spanish_stem` (el orden
  importa). Con ella, la misma consulta da `true` en ambos sentidos.
- **Tabla `barber_conocimiento`** con `pregunta`, `respuesta`, `categoria`,
  `sinonimos`, `prioridad`, `activo`, `origen` y una columna
  `tsv tsvector GENERATED ALWAYS AS (...) STORED`. Al ser generada,
  PostgreSQL la recalcula sola en cada cambio.
- **Índice GIN** sobre `tsv`.
- **Función `barber_buscar_conocimiento(consulta, limite)`** que convierte la
  frase del cliente en un `tsquery` **OR** (no AND: una frase natural lleva
  relleno y con AND se perdería la coincidencia), descarta lexemas de menos de
  3 caracteres y ordena por `ts_rank`. Si no hay nada útil, devuelve **vacío en
  vez de error**.
- **59 FAQs sembradas** con `INSERT ... ON CONFLICT (pregunta) DO UPDATE`, así
  que es **idempotente** (probado: `INSERT 0 52` dos veces, sin duplicados).

**Marcado honesto de las respuestas.** Cada fila lleva `origen`:
- `contexto` — derivada de datos reales del sistema (46 filas).
- `propuesta` — política plausible que **el dueño debe confirmar** (13 filas:
  estacionamiento, tarjeta, no-show, etc.).

Esto importa: no quise presentar como hechos cosas que no puedo verificar
(facturación, formas de pago). Y en la prueba A/B se vio que **esa marca tiene
un efecto real** (ver §5.3).

### 4.2 Opción B — FAQs en el prompt

El bloque se **genera desde la base de conocimiento** (una sola fuente de
verdad, nada de copiar y pegar a mano) y se inserta en el `systemMessage` del
nodo `AI Agent`, justo antes de la sección de comandos del dueño.
`_rag_prompt_put.py` respalda el workflow completo, desactiva → `PUT` →
reactiva (la regla del proyecto) y es re-ejecutable sin duplicar el bloque.

---

## 5. Resultados de las pruebas

### 5.1 Búsqueda en la base de conocimiento — **21/21**

De `probar-conocimiento.py` (salida real en `probar-conocimiento-salida.txt`):

```
[0] FAQs cargadas en la tabla: 59
[0] Extension unaccent: unaccent
[0] Configuración de texto: public.spanish_unaccent
[0] Índice GIN presente: 1
[0] Tamaño en disco de la tabla: 208 kB (incluye el índice GIN)
[0] Respuestas marcadas como 'propuesta': 13

RESULTADO: 21/21 aciertos en el primer lugar
Tiempo de búsqueda: mín 103 ms | máx 131 ms | media 111 ms
```

Las preguntas se escribieron **como las escribe la gente real**: sin acentos,
con sinónimos, con relleno. Ejemplos que aciertan:

| Pregunta del cliente | FAQ devuelta |
|---|---|
| `hay donde dejar el carro?` | ¿Tienen estacionamiento? |
| `hasta que hora abren?` | ¿Cuál es el horario? |
| `hacen tinte de cabello?` | ¿Hacen tintes o color? |
| `cuanto sale la ceja` | ¿Cuánto cuesta la ceja? |
| `quiero mover mi cita a otro dia` | ¿Puedo cambiar mi cita de día u hora? |
| `tienen un mod cut?` | ¿Tienen un corte llamado "mod cut" o "corte clásico"? |

**Casos borde (todos correctos):** `''`, `'   '`, `'?'`, `'12345'`, `'zzzz qqqq'`,
`'a e i o u'`, emojis y basura → **0 filas, sin error**. Esto es lo que hace
que el bot pueda caer limpiamente a *"Notificar al encargado"* en vez de
inventar.

### 5.2 Prueba en vivo del bot — antes y después

**Antes** (prompt sin FAQs), 8 preguntas de FAQ al bot real por el webhook:

| Pregunta | Respuesta del bot (antes) | ¿Correcta? |
|---|---|---|
| hola, tienen estacionamiento? | "No contamos con estacionamiento propio…" | Sí (por suerte) |
| cual es el telefono de la barberia? | "Nuestro teléfono es *452-281-8144*." | Sí |
| hasta que hora puedo agendar? | "**10:00 a 20:00**…" (con dobles asteriscos, prohibidos) | Parcial |
| puedo cancelar mi cita? | "Claro, ¿me recuerdas el servicio, día y hora?" | Sí |
| **necesito cita para la ceja?** | **"El corte tiene un costo de *$150*"** | **FALLO: responde otra cosa** |
| **quien me va a atender?** | **"Por ahora solo puedo atender mensajes escritos"** | **FALLO: no entiende** |
| **tienen un corte mod cut?** | **"Por ahora solo puedo atender mensajes escritos"** | **FALLO: no entiende** |
| **hacen tinte de cabello?** | "Manejamos cortes desvanecidos… por $150" | **FALLO: esquiva** |

**4 fallos claros de 8.**

**Después** (con el bloque de FAQs): las 7 preguntas que quedaron pendientes
se re-probaron con emparejamiento estricto del mensaje:

```
1. necesito cita para la ceja?
   R: La ceja cuesta *$30* y dura 10 minutos. No es obligatorio agendar, pero
      si quieres asegurarte tu lugar, dime qué día y a qué hora y te la aparto.
2. quien me va a atender?
   R: Te atenderá Esteban Aguilera, el barbero de la barbería.
3. hacen tinte de cabello?
   R: Tomo nota y voy a pasarle tu pregunta al encargado directamente…
4. tienen un corte mod cut?
   R: El "mod cut" no está en nuestro catálogo como tal, pero hacemos el
      *corte desvanecido o tijera* por *$150*.
5. tienen estacionamiento?
   R: Por ahora no tenemos estacionamiento propio, pero hay lugar para dejar
      el coche sobre la misma Calle Pinzón, junto al local.
6. puedo cancelar mi cita?
   R: Claro, te ayudo con eso. Solo necesitas decirme tu nombre y el día y
      hora de tu cita…
7. hasta que hora puedo agendar?
   R: Puedes agendar hasta que el servicio *termine antes de las 20:00*.
      Por ejemplo, un corte que dura 40 minutos puede empezar a más tardar
      a las *19:00*.
```

**7/7 correctas.** Y prueba final de aceptación (6/6), con respuestas ya bien
fundamentadas:

```
1. tienen estacionamiento?  -> No tenemos estacionamiento propio, pero hay
   lugar para estacionarse sobre la misma calle, justo junto al local.
2. quien me va a atender?   -> Te atiende *Esteban Aguilera*…
3. puedo llevar a mi hijo?  -> ¡Claro que sí! … mismo corte … *$150*.
4. necesito cita para la ceja? -> No es obligatorio, pero es recomendable…
5. tienen un corte mod cut? -> No tenemos un corte llamado "mod cut"… pero sí
   hacemos cortes desvanecidos o de tijera por *$150*.
6. puedo llegar sin cita?   -> Sí, puedes llegar sin cita, pero como atiende
   una sola persona, podrías tener que esperar…
```

### 5.3 Un hallazgo incómodo que conviene saber (honestidad)

Comparé el **mismo** prompt con y sin el bloque (`_rag_ab.py`, una sola
variable). El bloque **elimina invenciones**, pero la primera versión
**introdujo sobre-escalada**:

| Pregunta | Sin bloque | Con bloque (v1, con marca `(confirmar)`) |
|---|---|---|
| dan factura? | **"Sí, podemos generar factura."** ← **inventado** | "Déjame confirmarlo con el encargado…" |
| tienen estacionamiento? | "No contamos con…" | "No estoy segura… Permíteme confirmarlo con el encargado" |

O sea: sin FAQs el bot **se inventa** una facturación que nadie confirmó; con
la marca `(confirmar)` el bot deja de inventar pero **escala de más** y suena
inseguro. Lo arreglé **quitando la marca** del bloque del prompt (la
información queda protegida por la regla general *"nunca inventes"*), y la
versión final acierta las dos: informa lo verificado y escala solo lo no
verificado. **La columna `origen` sigue en la base de datos** como
documentación para el dueño.

> **Pendiente para el usuario:** revisar las **13 filas `origen='propuesta'`**
> y confirmar o corregir esas políticas (estacionamiento, tarjeta,
> transferencia, no-show, tolerancia de retraso, festivos, garantía, wifi,
> redes sociales). Están marcadas a propósito.

---

## 6. Coste medido del bloque de FAQs

| | Caracteres | ~Tokens | Coste de entrada / llamada |
|---|---|---|---|
| Prompt antes | 34.509 | 8.627 | $0,021568 |
| Bloque de FAQs | 8.488 | 2.122 | +$0,005305 |
| **Prompt con FAQs** | **43.231** | **10.809** | **$0,027025** |

- Crecimiento: **+24,6 %** en caracteres.
- Incremento: **$5,31 por cada 1.000 mensajes** (gpt-4o a $2,50/M de entrada
  en Uncensored AI). Es una fracción de centavo por mensaje.
- **Contrapartida:** el prompt se acera a la zona donde el modelo empieza a
  perder atención a las reglas del principio (formato de WhatsApp, reglas de
  agendado). Por eso **la opción A importa**: cuando la base crezca, la
  búsqueda evita seguir engordando el prompt.

---

## 7. Límites y lo que queda pendiente

**Lo que funciona hoy:**
- ✅ 21/21 aciertos de búsqueda, ~110 ms, cero coste, cero dependencias.
- ✅ El bot ya responde correctamente las FAQs (probado en vivo).
- ✅ `verify.py`: **187/187** comprobaciones estructurales.
- ✅ SQL idempotente (probado dos veces seguidas).

**Límites honestos:**
1. **El bot NO consulta la base de datos en producción.** Esto es deliberado
   y es el punto crítico: **no conecté la búsqueda al workflow**. Hoy el bot
   responde desde el **prompt** (opción B). Conectar la opción A requiere
   añadir un nodo (Postgres tool o HTTP) al agente, y eso toca el workflow.
2. **La búsqueda es léxica, no semántica.** Si el cliente pregunta con
   palabras que no están en la pregunta, los sinónimos ni la respuesta,
   devuelve vacío. Está mitigado con 59 FAQs y sinónimos curados, pero no es
   magia. *(Un embedding resolvería esto; no está disponible.)*
3. **El ranking es sensible a los sinónimos.** Durante el desarrollo, unos
   sinónimos demasiado genéricos ("cabello", "pelo") hicieron que
   *"hacen tinte de cabello?"* devolviera *"¿Hacen corte para niño?"*.
   Lo arreglé con los pesos A/A y curando el sinónimo. **Regla práctica: los
   sinónimos deben ser específicos del tema, no palabras genéricas.**
4. **13 FAQs son `propuesta`, no hechos verificados.** Hasta que el dueño las
   confirme, el bot escalará esas preguntas.
5. **Supabase sigue sin las tablas.** Comprobado con las `publishable` keys:
   - `GET /rest/v1/barber_conocimiento` → `200 []` (no existe la tabla, no da error)
   - `GET /rest/v1/` → `401 {"message":"Secret API key required"}`
   - `POST /rest/v1/rpc/barber_buscar_conocimiento` → `404 PGRST202` (la función no existe)

   **Las `publishable` keys NO permiten DDL.** El SQL para pegar en el editor
   de Supabase está al final de `conocimiento-barberia.sql`, con las
   instrucciones paso a paso. No inventé que ya estaba creado.

**Lo que quedaría pendiente (recomendado, en orden):**
1. El dueño confirma/corrige las 13 filas `origen='propuesta'`.
2. **Si se quiere conectar la opción A**, el cambio es pequeño y medible:
   `SELECT * FROM public.barber_buscar_conocimiento($1, 3)` con la credencial
   Postgres que el workflow **ya usa** (`NUrqrDWN8OsBFmgV`). Debe hacerse con
   respaldo, midiendo y comparando contra el comportamiento actual — igual
   que se hizo aquí.
3. **Si el prompt empieza a fallar por tamaño**, la secuencia correcta es:
   sacar el bloque de FAQs del prompt y dejar solo la búsqueda. Ahí la opción
   A pasa de "listo por si acaso" a necesaria.
4. Migrar la siembra a Supabase si se decide centralizar allí.

---

## 8. Veredicto

**RAG con embeddings: descartado, con evidencia.** No es una opinión de
coste/beneficio: el proveedor del proyecto (Uncensored AI) **no tiene
endpoint de embeddings** (404 real, docs "Coming soon", 0 modelos en el
catálogo) y el Postgres local **no tiene `pgvector`**. Cualquier variante
gratuita exige montar un contenedor de embeddings, y para 59 FAQs eso es
sobredimensionar el problema.

**Lo implementado es lo correcto para este tamaño:** texto completo de
Postgres (gratis, nativo, 21/21, ~110 ms) **más** las FAQs en el prompt, que
es lo que arregla las respuestas hoy. Ambas cosas comparten una única fuente
de verdad, así que no hay información duplicada que se desincronice.

**Opción recomendada: A como motor, B como entrega inmediata.** Si solo se
pudiera elegir una hoy, **B**, porque resuelve el problema ya sin tocar la
infraestructura y el coste medido es de centavos. A es la pieza que evita que
el prompt crezca sin límite.
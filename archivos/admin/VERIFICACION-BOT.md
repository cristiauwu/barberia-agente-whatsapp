# VERIFICACIÓN DEL AGENTE DE WHATSAPP — "Barber Chinos"

**Fecha:** viernes 25 de septiembre de 2026 · **Zona:** America/Mexico_City (UTC−06:00)
**Workflow auditado:** `Barberia - Agente de citas (Uncensored AI)` — id `barberiaAgenteUncensored` — **47 nodos** (el enunciado decía 45; el workflow tiene 47)
**Versión vigente durante las pruebas:** `ce1d5933-8575-4606-8837-4c9645da783a`, guardada el **2026-09-25T21:40:40.868Z** (= 15:40 hora local), nombre de versión *"Definir texto fijo de respaldo"*
**Modelo:** nodo `OpenAI Chat Model` con `model.value = "gpt-4o"`, credencial de Uncensored AI.

Todo lo que aparece aquí se **ejecutó y se leyó** de las ejecuciones reales de n8n (API `/executions`), de Postgres y de Google. **No se modificó ningún workflow ni el prompt** del agente.

**Nota sobre la memoria del bot (importante para interpretar los resultados).** El workflow usa el nodo `Postgres Chat Memory` con `sessionKey = {{ $body.data.key.remoteJid }}` y ventana de 12 mensajes, persistido en la tabla `n8n_chat_histories` de `barberia-postgres`. El JID de pruebas `5214501111805@s.whatsapp.net` tenía **660 mensajes previos** de otras campañas de prueba. Para poder medir el caso **B9 (primer mensaje)** se respaldó esa memoria y se vació. Al terminar se **restauró íntegra** (660 filas, ids 1–1100). El CRM `barber_clientes` también se restauró a su valor original (`Cliente Prueba`). Efecto colateral en los resultados: los casos **C11a** (basura `?`) sufrieron el sesgo de memoria descrito en su fila.

---

# ⛔ FALLOS ENCONTRADOS

## FALLO 1 — El bot INVENTA el día de la semana al listar las citas de un cliente

**Gravedad: alta.** El cliente recibe fechas con el día equivocado.

**Evidencia REAL** — ejecución **1139**, **tráfico real** (no una prueba mía): la dueña `5214521206246@s.whatsapp.net` ("Cristia Ñ") escribió `ver mis citas` el **2026-09-25 16:40:33−06**, **una hora después** de la última versión guardada (21:40:40 UTC = 15:40 local), es decir con la versión vigente.

Texto literal enviado por el bot (respuesta cruda, `\n` como salto real):

```
Cristia, estas son tus citas programadas actualmente:

1. *Corte de cabello dama* — $250
   Hoy, 25 de septiembre, a las 4:00 p.m.

2. *Corte desvanecido o tijera* — $150
   Miércoles 27 de septiembre, a las 3:00 p.m.

3. *Corte desvanecido o tijera* — $150
   Jueves 28 de septiembre, a las 2:20 p.m.

4. *Mascarilla* — $50
   Jueves 8 de octubre, a las 4:00 p.m.

5. *Corte desvanecido o tijera* — $150
   Jueves 1 de octubre, a las 4:00 p.m.

6. *Ceja* — $30
   Lunes 5 de octubre, a las 11:00 a.m.

7. *Peinado* — $300
   Martes 6 de octubre, a las 5:00 p.m.

¿Hay algo más en lo que te pueda ayudar? 😊
```

Contraste con los `start.dateTime` que la herramienta `Consultar agenda` devolvió **en esa misma ejecución**:

| # | El bot dijo | `dateTime` real de la agenda | Día real (verificado con `datetime`) | ¿Acierta? |
|---|---|---|---|---|
| 1 | Hoy, 25 de septiembre | `2026-09-25T16:00:00-06:00` | viernes 25 | ✅ |
| 2 | **Miércoles 27 de septiembre** | `2026-09-27T15:00:00-06:00` | **domingo 27** | ❌ |
| 3 | **Jueves 28 de septiembre** | `2026-09-28T14:20:00-06:00` | **lunes 28** | ❌ |
| 4 | Jueves 8 de octubre | `2026-10-08T16:00:00-06:00` | jueves 8 | ✅ |
| 5 | Jueves 1 de octubre | `2026-10-01T16:00:00-06:00` | jueves 1 | ✅ |
| 6 | Lunes 5 de octubre | `2026-10-05T11:00:00-06:00` | lunes 5 | ✅ |
| 7 | Martes 6 de octubre | `2026-10-06T17:00:00-06:00` | martes 6 | ✅ |

Cálculo real ejecutado con Python:

```
2026-09-25 -> viernes
2026-09-26 -> sábado
2026-09-27 -> domingo     <-- el bot dijo "miércoles"
2026-09-28 -> lunes       <-- el bot dijo "jueves"
2026-09-29 -> martes
2026-10-01 -> jueves
2026-10-05 -> lunes
2026-10-06 -> martes
2026-10-08 -> jueves
```

**2 de 7 días de la semana están mal.**

**Causa probable:** el prompt exige que el día de la semana se lea del ISO que devuelve la herramienta (`Agendar cita` → `start.dateTime`) y prohíbe calcularlo "de memoria". Pero **no existe ninguna herramienta que traduzca ISO → nombre del día**: el cálculo queda 100 % a criterio del modelo. En la ruta de *listar citas* (que no es "agendar") el modelo recibe varios `dateTime` y deriva el nombre del día por su cuenta, con el desplazamiento que se ve arriba.

**Intermitencia (dato clave):** al reproducirlo en vivo con la misma versión (exec 1183, `ver mis citas` con 2 citas) la respuesta **sí** fue correcta (`Sábado 26 de septiembre` y `Lunes 5 de octubre`). El fallo es **intermitente**, no sistemático, lo que lo hace más peligroso porque pasa desapercibido.

---

## FALLO 2 — Respuesta de 24 líneas y con sangría (rompe el tope de formato)

**Gravedad: media.** Mismo origen que el FALLO 1: ejecución **1139**.

- **24 líneas** — el prompt impone un máximo duro de **10** ("Máximo 10 líneas por mensaje. Si te pasas, recorta").
- **Sangría de 3 espacios** al inicio de las líneas de detalle (`   Hoy, 25 de septiembre…`), prohibida explícitamente ("Tampoco pongas sangría al inicio del renglón… Cada línea empieza pegada al margen").
- Asteriscos simples ✅ · sin espacios finales ✅ · 1 emoji ✅.

**Causa probable:** el prompt blindó el formato de dos plantillas concretas (**el menú del primer mensaje** y **la confirmación de cita**), pero **no** definió plantilla ni tope para "listar mis citas". El modelo cae en una lista numerada con líneas de detalle indentadas y se pasa del límite.

---

## FALLO 3 (histórico — YA CORREGIDO antes de esta verificación) — El agente enviaba mensajes VACÍOS y la ejecución terminaba en `error`

**Requisito 17.** En las últimas 50 ejecuciones del agente hay **5 en estado `error`**, todas por el mismo motivo:

| Exec | Cuándo (local) | Entrada del cliente | Salida del `AI Agent` | Error literal |
|---|---|---|---|---|
| 1089 | 2026-09-25 15:43:48 | ` Hola` (de `…1415196`) | `""` (vacío) | `Bad request` / `Bad Request` |
| 1091 | 2026-09-25 15:44:31 | ` Hola` (de `…1415196`) | `""` | ídem |
| 1094 | 2026-09-25 16:10:20 | ` Hola` (de `…1253750`) | `""` | ídem |
| 1106 | 2026-09-25 18:42:53 | ` hola` (del dueño) | `""` | ídem |
| 1109 | 2026-09-25 18:48:09 | ` qeu servicios hay` (del dueño) | `""` | ídem |

Error literal extraído de la ejecución:

```
error.msg  = "Bad request - please check your parameters"
error.node = "Mandar mensaje"
error.desc = "Bad Request"
request.body = {"number": "5214521415196@s.whatsapp.net", "text": "", "delay": 1000}
```

El modelo devolvía texto vacío, `Mandar mensaje` lo enviaba igual, y Evolution API contestaba **400 Bad Request** (no admite mensaje sin texto). **El cliente no recibía nada.** En esas 5 ejecuciones el nodo `IF - Respuesta no vacia` **no se ejecutó** (el flujo era anterior al blindaje; el grafo actual sí lo intercala).

**Corroboración documental** — historial de versiones del workflow:

```
2026-09-25T21:40:40.871Z  "Definir texto fijo de respaldo"
2026-09-25T21:39:50.034Z  "Responder cuando agente no devuelve texto"
                          → "Añade respuesta neutral en rama false del IF;
                             mantiene rama true, avisos multimedia y las seis
                             herramientas del agente sin cambios."
2026-09-25T20:06:41.145Z  (sin nombre)
```

**Verificación de que el fix FUNCIONA (hecha en esta auditoría):** sobre las **47 ejecuciones posteriores** al fix:

```
ejecuciones post-fix examinadas: 47
usaron respaldo 'Respuesta sin texto': 6
envios con texto vacio: 0     <-- ninguna ejecución en error
```

Las 6 veces que el modelo devolvió vacío (entradas `Hola`, `Hollq`, `Cita`, `Cits`, `Menu`) el respaldo envió el texto fijo:

```
No pude entenderte bien esta vez. ¿Me escribes de nuevo qué necesitas?
```

**Conclusión:** fallo real (5 clientes/dueño sin respuesta), **ya resuelto** en la versión vigente. Se documenta por exigirlo el requisito 17.

---

## FALLO 4 (histórico, fuera del agente) — 10 ejecuciones en `error` en `Barberia - Recordatorios de cita`

**Gravedad: media.** No es el agente de WhatsApp, pero entra en el barrido del requisito 17.

| Exec | Cuándo (local) | Causa literal |
|---|---|---|
| 733, 732, 731 | sin `startedAt` | `Could not retrieve the columns from key row` |
| 722 | 2026-09-25 06:32:00 | `Column names were updated after the node's setup` → `Missing columns: Execution ID` (nodo *Append or update row in sheet*) |
| 720 | 2026-09-25 06:29:49 | ídem `Missing columns: Execution ID` |
| 703, 687, 680 | 06:21 / 06:07 / 06:06 | `Forbidden - perhaps check your credentials?` → `The caller does not have permission` (hoja `17iqMobaQBz29tZ5hP5Q9ejzSJUfkov8lkjB245vpoZY`) |
| 611, 596 | 2026-09-24 23:35 / 23:18 | ídem `Forbidden` |

El último error (06:32) es **anterior** al `updatedAt` del workflow (**2026-09-25 07:33:45−06**) y desde entonces no hay errores nuevos: el resto son `success` (5), `waiting` (8, estado normal de un recordatorio esperando su hora) y `canceled` (1, exec 779). Se reporta como **histórico ya corregido**, no vigente.

---

## OBSERVACIÓN (no es fallo de los casos pedidos) — dos emojis en el menú

En 5 respuestas (execs **1100, 1129, 1132, 1164, 1169**) el menú sale con **dos** emojis (`💈` en el encabezado y `😊` al cierre), y el prompt dice *"Máximo uno por mensaje… Dos emojis en un mensaje de datos… ya es demasiado: **elige uno**"*.

Ejemplo literal (exec 1169, entrada `cuales son los servicios y precios`):

```
¡Hola! Estos son nuestros servicios 💈
- Corte: $150 caballero, $250 dama
- Barba: $100
- Ceja: $30
- Mascarilla: $50
- Planchado express: $150
- Peinado: $300
- Depilación: precio según la zona

¿Cuál te aparto? 😊
```

Desviación del prompt, pero **no** incumple los puntos 7, 8, 9 ni 10 encargados (asteriscos simples, cabe en 10 líneas/213 caracteres, están los 8 servicios, sin espacios finales).

---

# A. HORARIOS

Pruebas enviadas por `POST http://localhost:5678/webhook/hector` con JID `5214501111805@s.whatsapp.net` (creado como `Cliente Prueba`), `pushName` "Prueba Verif".

| # | Caso | Mensaje enviado | Respuesta REAL del bot (cita textual) | Exec | Veredicto |
|---|---|---|---|---|---|
| A1 | Horario de apertura | `¿A qué hora abren?` | `Abrimos de *lunes a sábado de 10:00 a 20:00*. El domingo estamos cerrados. ¿Te aparto una cita? 😊` | 1150 | **OK** |
| A2 | Horario de cierre | `¿Y hasta qué hora están abiertos?` | `Estamos abiertos hasta las *8:00 p.m.* de lunes a sábado. Si necesitas una cita, dime la hora y lo reviso al momento. 😊` | 1151 | **OK** |
| A3 | Cita fuera de horario (07:00) | `quiero un corte mañana a las 7 de la mañana` | `Abrimos hasta las *10:00 a.m.*, así que no podemos atenderte a las *7:00 a.m.*. ¿Te parece bien a las *10:00 a.m.* o prefieres otra hora? 😊` | 1152 | **OK** — rechazó |
| A4 | Termina después de cerrar (peinado 19:30 + 45 min = 20:15) | `quiero un peinado mañana a las 19:30` | `Un peinado tiene una duración de 45 minutos, por lo que si empezamos a las *7:30 p.m.* terminaríamos a las *8:15 p.m.* Sin embargo, cerramos a las *8:00 p.m.*, así que sería necesario iniciar a más tardar a las *7:15 p.m.* para que alcance a terminar antes del cierre.` ⏎ (blanco) ⏎ `¿Te parece bien agendar a las *7:15 p.m.* o eliges otra hora? 😊` | 1153 | **OK** — rechazó y ofreció 19:15 |
| A5 | Domingo | `quiero un corte el domingo a las 12` | `El domingo estamos cerrados, pero te puedo agendar el corte el lunes a las *12:00 p.m.* o en otro horario que prefieras. ¿Te parece? 😊` | 1155 | **OK** — no agendó |
| A6 | Fecha en el pasado | `quiero un corte ayer a las 4` | `No puedo agendar citas en el pasado. Si necesitas un corte, dime un día y horario que sea a partir de hoy, y lo reviso al momento. 😊` | 1156 | **OK** — no se creó ningún evento |
| A7 | "el jueves" (hoy es **viernes 25**) | `quiero un corte el jueves a las 4 de la tarde` | `El jueves a las *4:00 p.m.* ya está ocupado. Puedo agendar tu corte a las *4:40 p.m.* o a las *3:20 p.m.*. ¿Cuál prefieres? 😊` | 1157 | **OK** |

**A7 — comprobación de que usó el jueves CORRECTO (no el pasado).** Argumentos reales de la llamada a `Consultar agenda` en la ejecución 1157:

```
"After":  "2026-10-01T00:00:00-06:00"
"Before": "2026-10-01T23:59:59-06:00"
evento devuelto → "start.dateTime": "2026-10-01T16:00:00-06:00"
                  summary "Corte desvanecido o tijera — Cristia"
```

`2026-10-01` es **jueves** (verificado con `datetime`), y es **posterior** a hoy (viernes 25). El jueves 24 (ayer) **nunca se consultó**. El bot interpretó "el jueves" como **el próximo jueves**. ✅

---

# B. MENSAJES Y FORMATO

Método: además de revisar las respuestas de los 18 envíos en vivo, se pasó un validador automático a **83 respuestas reales** del agente (últimas 90 ejecuciones) buscando `**`, espacios/tabuladores finales de línea, sangría inicial, >10 líneas, >620 caracteres, marcos de texto (`╔ ╗ ╚ ╝ ┏ ┓ ┗ ┛ ━ ─ ═`) y número de emojis.

| # | Caso | Método | Resultado REAL | Veredicto |
|---|---|---|---|---|
| B7 | Negrita WhatsApp: `*un asterisco*`, nunca `**dos**` | 83 respuestas escaneadas + 18 en vivo | **`**` aparece 0 veces** en las 101 respuestas. Los únicos `**` del sistema están dentro del `systemMessage` (notación interna para el modelo), nunca en la salida al cliente | **OK** |
| B8 | Ninguna respuesta > ~12 líneas | 83 + 18 respuestas | 17 de 18 en vivo cumplen (la mayor: A4, 3 líneas / 333 car.). **1 incumple: exec 1139 con 24 líneas** | **FALLO** (FALLO 2) |
| B9 | Menú con los 8 servicios en el PRIMER mensaje de un cliente nuevo | `hola` con la memoria del JID vaciada | `¡Hola! Estos son nuestros servicios 💈` ⏎ `- Corte: $150 caballero, $250 dama` ⏎ `- Barba: $100` ⏎ `- Ceja: $30` ⏎ `- Mascarilla: $50` ⏎ `- Planchado express: $150` ⏎ `- Peinado: $300` ⏎ `- Depilación: precio según la zona` ⏎ (blanco) ⏎ `¿Cuál te aparto?` | **OK** — 10 líneas, 211 caracteres, los 8 servicios, **palabra por palabra** el menú aprobado del prompt |
| B10 | Sin espacios finales de línea | 101 respuestas escaneadas | **0 líneas** terminan con espacio o tabulador en toda la muestra. Sí apareció **sangría inicial** en exec 1139 (regla distinta, también prohibida) | **OK** para espacios finales; la sangría se reporta en FALLO 2 |

**Detalle de las 6 anomalías que detectó el escáner** (de 83 respuestas):

| Exec | Qué detectó | Nota |
|---|---|---|
| 1169 | 2 emojis | menú + ` 😊` → Observación |
| 1164 | 2 emojis | ídem |
| 1132 | 2 emojis | `Te ayudo a apartar tu cita en Barber Chinos 💈. ¿Te interesa el corte de dama que mencionaste o algún otro servicio? 😊` |
| 1129 | 2 emojis | menú + ` 😊` |
| 1100 | 2 emojis | menú + ` 😊` |
| **1139** | **sangría + 24 líneas** | ver FALLO 1 / FALLO 2 |

---

# C. ERRORES Y CASOS RAROS

| # | Caso | Mensaje enviado | Respuesta REAL del bot (cita textual) | Exec | Veredicto |
|---|---|---|---|---|---|
| C11a | Basura `?` | `?` | `No te entendí bien. ¿Me confirmas si alguna de las opciones que te di te funciona?` ⏎ `- Jueves a las *3:20 p.m.*` ⏎ `- Jueves a las *4:40 p.m.*` ⏎ (blanco) ⏎ `¿O prefieres otro horario? 😊` | 1158 | **OK** (responde; ver nota de memoria) |
| C11b | Basura `asdfgh` | `asdfgh` | `No te entendí bien. ¿Me puedes decir qué servicio necesitas y para qué día u hora? 😊` | 1159 | **OK** |
| C11c | Basura `12345` | `12345` | `No estoy seguro de qué necesitas. ¿Podrías decirme qué servicio te gustaría agendar y para qué día u hora? 😊` | 1160 | **OK** |
| C12 | Mensaje muy largo | 1 366 caracteres, luego una 2ª prueba de **2 115 caracteres** | Ambas: `¡Hola! Estos son nuestros servicios 💈` + menú completo (10 líneas) | 1164, 1187 | **OK** — ninguna ejecución falló ni truncó |
| C13 | Emojis solos | `😀😀😀` | `No te entendí bien. ¿Qué servicio te gustaría apartar y para cuándo? 😊` | 1161 | **OK** |
| C14 | Petición imposible: tinte | `quiero un tinte de cabello` | `Por ahora, no contamos con servicio de tintes en nuestra barbería. Sin embargo, ofrecemos cortes, arreglo de barba, peinado, planchado y otros servicios. ¿Te interesa alguno? 😊` | 1162 | **OK** — no inventó el servicio |
| C15 | Precio de corte de niño | `¿cuánto cuesta el corte de niño?` | `El corte para niño tiene el mismo precio que el corte desvanecido o tijera, que es de *$150*. ¿Te gustaría agendar uno? 😊` | 1163 | **OK** — $150 real del catálogo (`barber_servicios.corte = 150`) |
| C16 | Doble reserva a la misma hora | 1) `quiero un corte mañana a la 1 de la tarde` → 2) **segundo cliente** pide lo mismo (memoria borrada) | 1ª: `Listo, tu cita quedó apartada:` ⏎ (blanco) ⏎ `*Corte desvanecido* — *$150*` ⏎ `Sábado 26 de septiembre, *1:00 p.m.*` ⏎ `Calle Pinzón #574` ⏎ (blanco) ⏎ `Te esperamos ✅` — 2ª: `Mañana a la 1:00 p.m. ya está ocupado. ¿Te sirve a las *12:00 p.m.* o a las *1:40 p.m.*?` | 1170, 1174 | **OK** — detectó ocupado y **NO duplicó** |
| C17 | Ejecuciones en `error`/`crashed` en las últimas 50 | Barrido por API de los 3 workflows | Agente: 45 `success` + **5 `error`** (FALLO 3). Recordatorios: 5 `success`, 8 `waiting`, 1 `canceled`, **10 `error`** (FALLO 4). Vigilancia: 40 `success`, 0 errores | — | **FALLO** (históricos, ya corregidos) |

**Detalle de C16 (verificación de que NO hubo doble reserva).** Evento creado por la 1ª petición:

```
id:          mvhhjisn6bk4efd7fnqlm0ghls
summary:     "Corte desvanecido o tijera — Doble Reserva"
start:       2026-09-26T13:00:00-06:00
end:         2026-09-26T13:40:00-06:00
description: "Doble Reserva, corte desvanecido o tijera, $150, WhatsApp: 5214501111805"
```

Tras la 2ª petición, el calendario del 26 de septiembre contenía **exactamente el mismo evento y ningún otro**. La ejecución 1174 sí llamó `Consultar agenda`, recibió el evento ocupado de 13:00 y **no** llamó `Agendar cita` (sus nodos de herramientas son solo `Consultar agenda`). Además la 1ª reserva registró correctamente la fila en la hoja (`ID`, `Estatus: agendado`, `Nombre: Doble Reserva`, `Precio: 150`, `Día: 2026-09-26`, `Hora: 13:00:00`).

**Nota sobre C11a (memoria).** El `?` se envió justo después del caso A7 (que dejó pendientes las opciones "jueves 3:20 / 4:40"), y el bot respondió **retomando esa conversación** en lugar de dar la pregunta genérica "¿qué servicio quieres?". Es coherente con la memoria de sesión de 12 mensajes, no un fallo: el bot no se quedó callado ni reventó. Los casos C11b y C11c, ya sin ese contexto, dieron la respuesta genérica esperada.

---

# D. NO DEBE HABER

Búsqueda previa en el `systemMessage` vigente (41 048 caracteres): `"no-show"` → **0**, `"no show"` → **0**, `"noshow"` → **0**. `"factura"` aparece 2 veces, pero solo en la FAQ que dice *"Déjame preguntarle al encargado y te confirmo en un momento"* (no promete facturación).

| # | Caso | Mensaje enviado | Respuesta REAL del bot (cita textual) | Exec | Veredicto |
|---|---|---|---|---|---|
| D18 | No mencionar "no-show" | `¿qué pasa si no llego?` | `Si no llegas a tiempo, te esperamos de *5 a 10 minutos*. Si crees que te vas a tardar más, avísame por aquí para coordinar mejor. 😊` | 1165 | **OK** — nunca dice "no-show" |
| D19 | No decir que escuchó audio / vio foto | `te mandé un audio y una foto, ¿los escuchaste?` | `Por ahora solo puedo atender mensajes escritos. ¿Me escribes lo que necesitas? 😊` | 1166 | **OK** |
| D20 | No prometer facturación | `¿me pueden facturar la cita?` | `Voy a confirmar esto con el encargado y te aviso en un momento. 😊 ¿Te puedo ayudar con algo más mientras tanto?` | 1167 | **OK** — no promete factura; escala al encargado |

**Prueba adicional D19 (nodo multimedia).** Se envió un `messages.upsert` con `messageType: "audioMessage"`. Ejecución **1177**, `success`: el flujo tomó la rama *fallback* del `Switch` → nodo **`Aviso solo texto`** (el agente **no** se ejecutó) y envió literalmente:

```
Por ahora solo puedo atender mensajes escritos. ¿Me escribes lo que necesitas? 🙏
```

El nodo multimedia es **determinista**, no depende del modelo: es imposible que el bot afirme haber oído un audio.

---

# CASOS QUE NO SE PUDIERON PROBAR

| Caso | Motivo |
|---|---|
| Reprogramar y cancelar citas (no pedidos explícitamente, pero relacionados con C16) | Fuera del alcance fijado por el enunciado. Solo se auditó su configuración de nodos (sin `onError`, con `retryOnFail: true`, `maxTries: 3`). |
| Estado `crashed` | En las últimas 50 ejecuciones del agente, y en los otros dos workflows, **no existe ninguna** ejecución `crashed`; solo `success`, `error`, `waiting` y `canceled`. No hay nada que reportar. |
| Mensajes de audio/imagen entrantes con payload real de WhatsApp | Se simuló con el `messageType`/`message` de Evolution (`audioMessage`), suficiente para probar el enrutamiento del `Switch`. No se dispone de un audio real subido a Evolution, y el sistema no lo procesa en ningún caso. |

---

# LIMPIEZA REALIZADA

Se verificó el estado **antes y después** con la API de n8n, Postgres y Google Calendar.

| Artefacto | Acción | Verificación posterior |
|---|---|---|
| Evento `mvhhjisn6bk4efd7fnqlm0ghls` ("Corte desvanecido o tijera — Doble Reserva", 26-sep 13:00) | **Borrado** del calendario BARBER | El calendario pasó de 16 a **15 eventos**; el id ya no aparece |
| Fila 8 de la hoja `Citas barbería` (ID `mvhhjisn6bk4efd7fnqlm0ghls`) | **Borrada** de "Hoja 1" | La hoja pasó de **7 a 6 filas**; las 6 restantes son las originales (Juan Perez, Maria Lopez, Cristia Ñ ×3, Cristia) |
| Memoria del JID `5214501111805@s.whatsapp.net` | Respaldada, vaciada para B9, y **restaurada** al terminar | Vuelve a tener **660 filas**, ids **1–1100** (idéntico al respaldo). Las 662 filas de mis pruebas se eliminaron |
| CRM `barber_clientes` | Mi prueba renombró al cliente a "Doble Reserva"; **restaurado** | Vuelve a `Cliente Prueba`, `visitas 5`, `servicio_habitual "Corte desvanecido o tijera"`, `etiqueta frecuente` |
| Workflows temporales que creé para leer el calendario y la hoja | **Eliminados** | La lista de workflows contiene solo los 7 originales (`barberiaVigilancia`, `barberiaAgenteUncensored`, `barberiaRecordatorios` activos + 4 TEMP/W2 preexistentes de otra campaña) |
| `barber_escalaciones`, `barber_pausas`, `barber_bloqueos` | No se tocaron | **0 / 0 / 0** filas, igual que al inicio |

**Ninguna modificación a workflows ni al prompt del agente.** Solo se hicieron llamadas de lectura/ejecución. La memoria de sesión del bot se manipuló únicamente en el JID de pruebas y quedó restaurada.

---

# RESUMEN

| Sección | Casos probados | OK | FALLO |
|---|---|---|---|
| A. Horarios | 7 | 7 | 0 |
| B. Mensajes y formato | 4 | 3 | 1 (B8, por la exec 1139) |
| C. Errores y casos raros | 9 | 8 | 1 (C17: solo hallazgos **históricos**) |
| D. No debe haber | 4 (3 en vivo + 1 de audio) | 4 | 0 |
| **Total** | **24** | **22** | **2** (1 vigente + 1 histórico) |

**Fallo vigente:** el bot inventa el día de la semana al listar las citas de un cliente (FALLO 1, exec 1139: dijo "miércoles 27" por **domingo 27** y "jueves 28" por **lunes 28**), y con esa misma respuesta rompe el tope de formato (FALLO 2: 24 líneas con sangría).
**Fallo histórico ya corregido:** mensajes vacíos que terminaban en `error` y dejaban al cliente sin respuesta (FALLO 3, 5 ejecuciones) — el respaldo posterior funciona (0 envíos vacíos en 47 ejecuciones).
**Observación menor:** doble emoji en el menú (5 respuestas), sin incumplir los puntos 7–10 verificados.

**Lo que funciona bien:** horarios y cierre (A1–A4), domingo y fechas pasadas (A5–A6), cálculo del "próximo jueves" (A7), formato WhatsApp sin `**` ni espacios finales (B7, B10), menú exacto de 8 servicios (B9), mensajes basura / emojis / 2 115 caracteres (C11–C13), no inventar servicios ni precios (C14, C15), y detección de doble reserva sin duplicar (C16).
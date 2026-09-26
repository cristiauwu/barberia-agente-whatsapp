# VERIFICACIÓN DE FECHAS Y HORARIOS — Agente de WhatsApp "Barber Chinos"

**Fecha de la verificación:** 25–26 de septiembre de 2026
(`NOW` del sistema: viernes 25/09/2026, ~18:30–19:00 h America/Mexico_City)
**Workflow verificado:** `barberiaAgenteUncensored`
**Nodo auditado:** `Que dia es` (`@n8n/n8n-nodes-langchain.toolCode`, v1.3)
**Método:** extracción del `jsCode` real por la API de n8n + ejecución en el
**runtime real de n8n** + diálogos en vivo contra el webhook + barrido de las
últimas 60 ejecuciones.

> **Aviso de concurrencia.** Durante esta sesión otros agentes editaron el
> workflow: pasó de **48 a 56 nodos** y el prompt cambió (FAQ de pagos,
> tolerancia, wifi, factura, redes). El `jsCode` del nodo `Que dia es` es
> **byte a byte idéntico** al que se extrajo y probó
> (sha256 `51d7472a2041d1ce`, 2 971 caracteres). Esos cambios son ajenos a
> esta verificación.

---

# FALLOS

**13 fallos en la herramienta + 4 fallos en el uso en vivo.** El más grave es
el primero: **es la misma clase de error que se creía corregida** (el bot
nombra mal el día de la semana), solo que por otra entrada.

## FALLO 1 — CRÍTICO — La herramienta resta un día a las fechas `AAAA-MM-DD`

**Es exactamente el fallo original: nombra mal el día de la semana.**

| | |
|---|---|
| Entrada | `2026-09-27` (fecha suelta, sin hora) |
| Salida real | `sabado 26 de septiembre de 2026 (2026-09-26)` |
| Verdad (Python `datetime`) | **2026-09-27 = domingo** |
| Veredicto | **MAL** |

También falla con ISO **sin offset** en horas de madrugada (00:30–05:59),
la franja que en México cae antes de las 06:00 UTC:

| Entrada | Salida real | Verdad |
|---|---|---|
| `2026-09-27T00:30:00` | sabado 26 de septiembre (2026-09-26) | domingo 27 |
| `2026-09-27T01:00:00` | sabado 26 (2026-09-26) | domingo 27 |
| `2026-09-27T05:59:00` | sabado 26 (2026-09-26) | domingo 27 |
| `2026-09-28T02:00:00` | domingo 27 (2026-09-27) | lunes 28 |

**Causa (probada, no supuesta).** Sonda directa sobre el motor de fechas:

```
entrada "2026-09-27" -> isoUTC       "2026-09-27T00:00:00.000Z"
                        isoEnMexico  "2026-09-26"
```

`new Date('2026-09-27')` lo interpreta **el motor de V8** como **medianoche
UTC** (así lo manda el estándar ECMAScript para `Date.parse` de fechas sin
hora). El código después reconvierte ese instante a `America/Mexico_City`
(UTC−6), con lo que retrocede a `2026-09-26T18:00` y devuelve el **día
anterior**. El `Intl.DateTimeFormat` con `timeZone` hace bien su trabajo; el
problema es el instante que recibe. Lo mismo pasa con cualquier ISO sin offset
cuya hora UTC caiga en el día anterior en México.

**Riesgo.** El prompt le ordena al modelo dos cosas que producen justo esta
entrada: *"escribe solo la fecha numérica"* y *"pásale la fecha tal como viene
de Google Calendar"*. Si el modelo pasa `2026-09-27` en vez de
`2026-09-27T15:00:00-06:00`, la herramienta devuelve el día previo y el
cliente llega un día antes.

**Alcance real de lo probado.** **No observé esta entrada en vivo**: en los 4
casos en vivo el modelo pasó texto en español. El fallo está **probado a nivel
de herramienta**, no observado en conversación real. Lo digo tal cual.

## FALLO 2 — GRAVE — El formato `dd/mm/aaaa` se malinterpreta (VISTO EN VIVO)

**Este sí se observó en conversación real, con el agente en producción.**

| Caso | Lo que escribió el cliente | Lo que devolvió la herramienta | Lo que dijo el agente |
|---|---|---|---|
| x1 (exec 1319) | `¿qué día de la semana cae el 27/12/2026?` | `domingo 27 de septiembre de 2026 (2026-09-27)` | "El **27 de diciembre** de 2026 cae en **domingo**" |
| x2 (exec 1320) | `¿qué día cae el 05/01/2027?` | `viernes 30 de abril de 2027 (2027-04-30)` | "El **5 de enero** de 2027 cae en **martes**" |

Evidencia literal del `runData` (entrada y salida de la herramienta):

```json
// exec 1319
"inputOverride": {"ai_tool": [[{"json": {"query": "27/12/2026"}}]]}
"response":      "domingo 27 de septiembre de 2026 (2026-09-27)"

// exec 1320
"inputOverride": {"ai_tool": [[{"json": {"query": "05/01/2027"}}]]}
"response":      "viernes 30 de abril de 2027 (2027-04-30)"
```

**El día que dijo el agente acertó por casualidad** (27/12/2026 sí es domingo;
5/01/2027 sí es martes), porque el modelo **ignoró el resultado de la
herramienta** y calculó por su cuenta. La **salida de la herramienta es basura
en ambos casos**: devolvió el 27 de septiembre en vez del 27 de diciembre, y el
30 de abril de 2027 en vez del 5 de enero de 2027.

**Causa (probada).** `new Date('27/12/2026')` **es inválido** en V8 (sondeo:
`INVALID`), así que cae al respaldo por expresión regular, que toma el `27`
como día, **descarta el mes 12** y usa el **mes en curso** (septiembre).
`new Date('05/01/2027')` **sí es válido**: V8 lo lee como formato
estadounidense `mm/dd/aaaa` → 1 de mayo de 2027, y al reconvertir a México
retrocede al 30 de abril.

## FALLO 3 — GRAVE — Entradas basura devuelven un día inventado, no un error

| Entrada | Salida real | Esperado |
|---|---|---|
| `32/13/2026` | `viernes 2 de octubre de 2026 (2026-10-02)` | Error legible |
| `2026-13-01` (mes 13) | `domingo 20 de septiembre de 2026 (2026-09-20)` | Error legible |
| `9999-99-99` | `martes 8 de diciembre de 2026 (2026-12-08)` | Error legible |
| `2026` (solo el año) | `miercoles 31 de diciembre de 2025 (2025-12-31)` | Error legible |
| `20260927` (número) | `miercoles 20 de septiembre de 2609 (2609-09-20)` | Error legible |
| `27 septiembre` (sin año) | `miercoles 26 de septiembre de 2001 (2001-09-26)` | Error legible |

**Causa.** El respaldo por expresión regular
`(\d{1,2})\s*(?:de\s+)?([a-záéíóú]+)?\s*(?:de\s+)?(\d{4})?`
acepta **cualquier** corrida de 1–2 dígitos como día y **cualquier** corrida de
4 dígitos como año, **sin validar rango**. Después `Date.UTC()` **desborda en
silencio** los valores fuera de rango en lugar de fallar. En `20260927` el
regex toma `20` como día y `2609` como año → "año 2609".

Las entradas **sí previstas como basura** (`''`, `null`, `undefined`, `'   '`,
`'hola'`) sí devuelven error correctamente: 5 de 10.

## FALLO 4 — El día se sigue inventando cuando el modelo no llama la herramienta

**Hallazgo del historial, no de laboratorio. Prueba de que el arreglo no está
garantizado.** La ejecución **1198** (26/09/2026 00:06 UTC) es **posterior** a
la instalación de `Que dia es` (versión creada 00:02:56) y **volvió a fallar
igual que antes**:

```
Entrada: " mis citas"
Herramienta 'Que dia es': NO se ejecutó
Herramientas usadas: ['Consultar agenda']
Respuesta (literal, 27 líneas):
  "Estas son tus citas programadas actualmente, Cristia:

   1. *Corte de cabello dama* — $250
      Hoy, **25 de septiembre**, a las *4:00 p.m.*

   2. *Corte desvanecido o tijera* — $150
      **Miércoles 27 de septiembre**, a las *3:00 p.m.*

   3. *Corte desvanecido o tijera* — $150
      **Jueves 28 de septiembre**, a las *2:20 p.m.*
   ...
   6. *Ceja* — $30
      **Lunes 2 de octubre**, a las *11:00 a.m.*
   ..."
```

Comprobación contra el calendario real:

| Dijo | Fecha real | Verdad | Veredicto |
|---|---|---|---|
| "Miércoles 27 de septiembre" | 2026-09-27 | **domingo** | **MAL** |
| "Jueves 28 de septiembre" | 2026-09-28 | **lunes** | **MAL** |
| "Lunes 2 de octubre" | 2026-10-02 | **viernes** | **MAL** |

La ejecución **1139** (25/09/2026 22:40 UTC) repite dos de esos errores
("Miércoles 27", "Jueves 28").

**Causa probable.** El arreglo es **de prompt, no de código**: el prompt dice
"llama a `Que dia es`" pero nada lo obliga. Para listar 8 citas el modelo tomó
el atajo de calcular los 8 días "de memoria" y volvió a equivocarse en 3. De
las 60 ejecuciones analizadas, la herramienta se ejecutó en **1 sola (1,7 %)**:
el modelo **casi nunca la usa**.

## FALLO 5 — El límite de 10 líneas también se rompe (posterior al arreglo)

La ejecución **1198**: **27 líneas / 743 caracteres** (tope: 10 líneas /
600 caracteres) y **8 líneas con sangría de 3 espacios**. La ejecución
**1139**: **24 líneas / 606 caracteres** y **7 líneas con sangría**. Ambas son
posteriores a la instalación de la herramienta. El prompt lo prohíbe
expresamente y aun así ocurre cuando el modelo lista muchas citas.

---

# 1. HERRAMIENTA `Que dia es` — prueba exhaustiva

**Cómo se probó.** Se extrajo el `jsCode` real del nodo vía
`GET /api/v1/workflows/barberiaAgenteUncensored`. Se ejecutó **dentro del
runtime de Code de n8n** (workflow temporal con un nodo Code, borrado después)
y **cada resultado se comparó contra `datetime` de Python** como referencia.

**Hallazgo de entorno relevante:** el runtime de Code de n8n corre con
**TZ = UTC** (`offset 0`), mientras que `docker exec barberia-n8n node` corre
con **TZ = America/Mexico_City** (`offset 360`). El mismo código da resultados
**distintos** en cada uno. Prueba previa con `docker exec node`: 52/61
(85,2 %). Prueba definitiva en el runtime real de n8n:
**65 casos, 52 aciertos, 13 fallos = 80,0 %**. La cifra válida es esta última.

## Resumen por grupo

| Grupo | Aciertos |
|---|---|
| 1. Los 7 días de la semana | **7/7** |
| 2. Frontera de zona horaria (19:00 México) | **9/9** |
| 3. Frontera de medianoche | **5/5** |
| 4. Cambio de mes | **6/6** |
| 5. Cambio de año | **4/4** |
| 6. 29 de febrero de 2028 | **4/4** |
| 7. ISO con offset y sin offset | 5/10 |
| 8. Texto en español | 7/10 |
| 9. Entradas basura | 5/10 |
| **TOTAL** | **52/65 = 80,0 %** |

## Los 65 casos

| # | Entrada | Salida real de la herramienta | Esperado (Python) | Veredicto |
|---|---|---|---|---|
| 1a | `2026-09-28T12:00:00-06:00` | lunes 28 de septiembre de 2026 | lunes 28/09 | OK |
| 1b | `2026-09-29T12:00:00-06:00` | martes 29 de septiembre de 2026 | martes 29/09 | OK |
| 1c | `2026-09-30T12:00:00-06:00` | miercoles 30 de septiembre de 2026 | miércoles 30/09 | OK |
| 1d | `2026-10-01T12:00:00-06:00` | jueves 1 de octubre de 2026 | jueves 01/10 | OK |
| 1e | `2026-10-02T12:00:00-06:00` | viernes 2 de octubre de 2026 | viernes 02/10 | OK |
| 1f | `2026-10-03T12:00:00-06:00` | sabado 3 de octubre de 2026 | sábado 03/10 | OK |
| 1g | `2026-09-27T12:00:00-06:00` | domingo 27 de septiembre de 2026 | domingo 27/09 | OK |
| 2a | `2026-09-28T19:00:00-06:00` | lunes 28 de septiembre de 2026 | lunes 28/09 | OK |
| 2b | `2026-09-29T01:00:00Z` | lunes 28 de septiembre de 2026 | lunes 28/09 | OK |
| 2c | `2026-09-29T01:00:00+00:00` | lunes 28 de septiembre de 2026 | lunes 28/09 | OK |
| 2d | `2026-09-29T01:00:00.000Z` | lunes 28 de septiembre de 2026 | lunes 28/09 | OK |
| 2e | `2026-09-28T18:59:00-06:00` | lunes 28 de septiembre de 2026 | lunes 28/09 | OK |
| 2f | `2026-09-28T20:00:00-06:00` | lunes 28 de septiembre de 2026 | lunes 28/09 | OK |
| 2g | `2026-09-28T06:00:00Z` | lunes 28 de septiembre de 2026 | lunes 28/09 | OK |
| 2h | `2026-09-27T19:00:00-06:00` | domingo 27 de septiembre de 2026 | domingo 27/09 | OK |
| 2i | `2026-09-28T01:00:00Z` | domingo 27 de septiembre de 2026 | domingo 27/09 | OK |
| 3a | `2026-09-28T00:00:00-06:00` | lunes 28 de septiembre de 2026 | lunes 28/09 | OK |
| 3b | `2026-09-28T23:59:00-06:00` | lunes 28 de septiembre de 2026 | lunes 28/09 | OK |
| 3c | `2026-09-29T05:59:00Z` | lunes 28 de septiembre de 2026 | lunes 28/09 | OK |
| 3d | `2026-09-29T06:00:00Z` | martes 29 de septiembre de 2026 | martes 29/09 | OK |
| 3e | `2026-09-29T05:59:59Z` | lunes 28 de septiembre de 2026 | lunes 28/09 | OK |
| 4a | `2026-08-31T10:00:00-06:00` | lunes 31 de agosto de 2026 | lunes 31/08 | OK |
| 4b | `2026-09-01T10:00:00-06:00` | martes 1 de septiembre de 2026 | martes 01/09 | OK |
| 4c | `2026-08-31T23:59:00-06:00` | lunes 31 de agosto de 2026 | lunes 31/08 | OK |
| 4d | `2026-09-01T06:00:00Z` | martes 1 de septiembre de 2026 | martes 01/09 | OK |
| 4e | `2026-09-30T23:00:00-06:00` | miercoles 30 de septiembre de 2026 | miércoles 30/09 | OK |
| 4f | `2026-10-01T05:00:00Z` | miercoles 30 de septiembre de 2026 | miércoles 30/09 | OK |
| 5a | `2026-12-31T22:00:00-06:00` | jueves 31 de diciembre de 2026 | jueves 31/12/26 | OK |
| 5b | `2027-01-01T04:00:00Z` | jueves 31 de diciembre de 2026 | jueves 31/12/26 | OK |
| 5c | `2027-01-01T00:30:00-06:00` | viernes 1 de enero de 2027 | viernes 01/01/27 | OK |
| 5d | `2026-12-31T23:59:00-06:00` | jueves 31 de diciembre de 2026 | jueves 31/12/26 | OK |
| 6a | `2028-02-29T12:00:00-06:00` | martes 29 de febrero de 2028 | martes 29/02/28 | OK |
| 6b | `2028-02-29T18:00:00Z` | martes 29 de febrero de 2028 | martes 29/02/28 | OK |
| 6c | `2028-02-28T23:00:00-06:00` | lunes 28 de febrero de 2028 | lunes 28/02/28 | OK |
| 6d | `2028-03-01T02:00:00-06:00` | miercoles 1 de marzo de 2028 | miércoles 01/03/28 | OK |
| 7a | `2026-09-27T15:00:00-06:00` | domingo 27 de septiembre de 2026 | domingo 27/09 | OK |
| 7b | `2026-09-27T15:00:00` (sin offset) | domingo 27 de septiembre de 2026 | domingo 27/09 | OK |
| 7c | `2026-09-27T23:00:00` (sin offset) | domingo 27 de septiembre de 2026 | domingo 27/09 | OK |
| 7d | `2026-09-27T00:30:00` (sin offset) | sabado 26 de septiembre de 2026 | domingo 27/09 | **MAL** |
| 7e | `2026-09-27T15:00:00.000-06:00` | domingo 27 de septiembre de 2026 | domingo 27/09 | OK |
| 7f | `2026-09-27` (solo fecha) | sabado 26 de septiembre de 2026 | domingo 27/09 | **MAL** |
| 7g | `2026-09-27T05:59:00` (sin offset) | sabado 26 de septiembre de 2026 | domingo 27/09 | **MAL** |
| 7h | `2026-09-27T06:00:00` (sin offset) | domingo 27 de septiembre de 2026 | domingo 27/09 | OK |
| 7i | `2026-09-27T01:00:00` (sin offset) | sabado 26 de septiembre de 2026 | domingo 27/09 | **MAL** |
| 7j | `2026-09-28T02:00:00` (sin offset) | domingo 27 de septiembre de 2026 | lunes 28/09 | **MAL** |
| 8a | `27 de septiembre de 2026` | domingo 27 de septiembre de 2026 | domingo 27/09 | OK |
| 8b | `27 septiembre` (sin año) | miercoles 26 de septiembre de 2001 | Error legible | **MAL** |
| 8c | `27/09/2026` | domingo 27 de septiembre de 2026 | domingo 27/09 | OK |
| 8d | `27 de septiembre` | domingo 27 de septiembre de 2026 | domingo 27/09 | OK |
| 8e | `domingo 27 de septiembre de 2026` | domingo 27 de septiembre de 2026 | domingo 27/09 | OK |
| 8f | `27 de sep de 2026` | domingo 27 de septiembre de 2026 | domingo 27/09 | OK |
| 8g | `septiembre 27 de 2026` | domingo 27 de septiembre de 2026 | domingo 27/09 | OK |
| 8h | `27/12/2026` (dd/mm) | domingo 27 de septiembre de 2026 | domingo 27/12 | **MAL** |
| 8i | `05/01/2027` (dd/mm) | viernes 30 de abril de 2027 | martes 05/01/27 | **MAL** |
| 8j | `1 de octubre de 2026` | jueves 1 de octubre de 2026 | jueves 01/10 | OK |
| 9a | `''` | Error: no me diste ninguna fecha… | Error | OK |
| 9b | `hola` | Error: no pude entender "hola"… | Error | OK |
| 9c | `32/13/2026` | viernes 2 de octubre de 2026 (2026-10-02) | Error | **MAL** |
| 9d | `null` | Error: no me diste ninguna fecha… | Error | OK |
| 9e | `undefined` | Error: no me diste ninguna fecha… | Error | OK |
| 9f | `'   '` | Error: no me diste ninguna fecha… | Error | OK |
| 9g | `2026-13-01` | domingo 20 de septiembre de 2026 | Error | **MAL** |
| 9h | `9999-99-99` | martes 8 de diciembre de 2026 | Error | **MAL** |
| 9i | `2026` | miercoles 31 de diciembre de 2025 | Error | **MAL** |
| 9j | `20260927` (número) | miercoles 20 de septiembre de 2609 | Error | **MAL** |

**Conclusión de la sección.** La herramienta **sí corrige el fallo original**:
el cálculo con ISO completo, con y sin offset en horas "de oficina", con
frontera de zona horaria, medianoche, cambio de mes, cambio de año y 29 de
febrero es **correcto en los 43 casos de esos grupos (100 %)**. **Pero tiene
13 agujeros**, y dos de ellos (7f fecha suelta, 8h/8i dd/mm) **reproducen el
mismo síntoma**: un día de la semana equivocado que suena plausible.

---

# 2. USO CONVERSACIONAL — diálogos reales en vivo

Todos los diálogos se enviaron al webhook `POST /webhook/hector` como el
cliente de pruebas `5214501111805@s.whatsapp.net`, esperando 45–60 s. Se
verificó en el `runData` si se ejecutó `Que dia es` y se comparó cada día
nombrado contra Python. **Hoy = viernes 25/09/2026** (confirmado con Python).

| Caso | Entrada | Respuesta literal del bot | ¿Usó `Que dia es`? | Verdad (Python) | Veredicto |
|---|---|---|---|---|---|
| c1 (1241) | `¿Qué día cae el 27 de septiembre de 2026?` | "El *27 de septiembre de 2026* cae en *domingo*. 😊 Recuerda que los domingos estamos cerrados…" | **SÍ** → `domingo 27 de septiembre de 2026 (2026-09-27)` | domingo | **OK** |
| c2 (1264) | `¿Qué día es el 1 de octubre de 2026?` | "El 1 de octubre de 2026 cae en jueves. 😊" | **SÍ** → `jueves 1 de octubre de 2026` | jueves | **OK** |
| c3 (1269) | `Quiero un corte el viernes a las 4` | "Listo, tu cita quedó apartada: *Corte desvanecido* — *$150* / **Viernes 25 de septiembre**, *4:00 p.m.* / Calle Pinzón #574" | NO | El día dicho es correcto (25/09 = viernes) | **MAL** (ver abajo) |
| c4 (1277) | `¿Qué día de la semana es mañana?` | "Mañana es *sábado, 26 de septiembre de 2026*. 😊" | **SÍ** → `sabado 26 de septiembre de 2026` | sábado 26/09 | **OK** |
| c5 (1281) | `Agéndame un corte el 30 de septiembre a las 3` | "Listo… *Miércoles 30 de septiembre*, *3:00 p.m.*" | NO | miércoles 30/09 | **OK** (día y `dateTime` correctos) |
| c6 (1283) | `muéstrame mis próximas citas` | "Estas son tus próximas citas: - *Corte desvanecido* — $150, *25/09 a las 4:00 p.m.* - *Corte desvanecido* — $150, *30/09 a las 3:00 p.m.*" | NO | — | **OK** (usó fecha numérica, 6 líneas) |
| x1 (1319) | `¿qué día de la semana cae el 27/12/2026?` | "El 27 de diciembre de 2026 cae en *domingo*. 😊" | **SÍ** → herramienta devolvió **2026-09-27** (mal) | 27/12/2026 = domingo | **MAL de la herramienta** (el bot acertó por su cuenta) |
| x2 (1320) | `¿qué día cae el 05/01/2027?` | "El 5 de enero de 2027 cae en martes. 😊" | **SÍ** → herramienta devolvió **2027-04-30** (mal) | 5/01/2027 = martes | **MAL de la herramienta** (el bot acertó por su cuenta) |

## Detalle de c3 — se agendó una cita en el PASADO

```
Entrada : "Quiero un corte el viernes a las 4"   (enviado a las 18:36 h CDMX)
Agendar cita -> start.dateTime = "2026-09-25T16:00:00-06:00"
                end.dateTime   = "2026-09-25T16:20:00-06:00"
                summary        = "Corte — Cliente Prueba"
Registrar en hoja -> Día: 2026-09-25, Hora: 16:00:00
Respuesta: "Listo, tu cita quedó apartada: … Viernes 25 de septiembre, 4:00 p.m."
```

El "viernes" era **hoy 25/09**, y la cita se puso a las **16:00**, es decir
**2,5 horas en el pasado** respecto al momento del mensaje (18:36). El día
nombrado es correcto, pero **el agente agendó en el pasado sin rechistar**.
El prompt dice expresamente *"antes de agendar, compara la fecha calculada con
HOY. Si la fecha es anterior a hoy, está mal"* y *"prohíbo agendar una cita en
el pasado"*. La regla se aplica contra el **día**, no contra la **hora**.

**Veredicto de la sección 2: 6 de 8 diálogos correctos (75 %).** La herramienta
se usó **4 veces de 8 (50 %)** en vivo — muy por encima del 1,7 % del historial
(porque las preguntas eran explícitamente "¿qué día…?", que es el disparador
obvio), pero **el modelo sigue sin usarla cuando lista citas**.

---

# 3. HORARIOS DEL NEGOCIO

| Caso | Entrada | Respuesta literal del bot | ¿Creó evento? | Veredicto |
|---|---|---|---|---|
| h1 (1284) | `Quiero un corte el lunes 28 de septiembre a las 19:30` | "Un corte a las *19:30* el lunes 28 de septiembre terminaría a las *20:10*, y cerramos a las *20:00*. El horario más tarde que sí cabe es *19:00*. ¿Te sirve a esa hora o prefieres otro día? 😊" | **NO** | **OK** — rechaza bien y calcula 19:30+40 min = 20:10 |
| h2 (1285) | `Quiero un corte el lunes 28 de septiembre a las 20:00` | "El negocio cierra a las 20:00, así que no podemos agendar a esa hora porque no habría tiempo de terminar el servicio. ¿Te parece bien agendar el corte a las *19:00*…?" | **NO** | **OK** — rechaza |
| h3 (1286) | `Quiero un corte el lunes 28 de septiembre a las 9:00` | "Abrimos a las *10:00*, así que no podemos agendar a las *9:00*. ¿Te parece bien agendar el corte a las *10:00*…?" | **NO** | **OK** — rechaza (abren 10:00) |
| h4 (1290) | `Quiero un corte el domingo 27 de septiembre a las 12:00` | "El domingo estamos cerrados. ¿Te parece bien agendar tu corte el *lunes 28 de septiembre* a las *12:00 p.m.*? 😊" | **NO** | **OK** — dice cerrado y ofrece el lunes |
| h5 (1295) | `Quiero un corte el jueves 24 de septiembre a las 4` | "Esa fecha ya pasó. ¿Te parece bien si agendamos tu corte para mañana, **viernes 26 de septiembre**, a las *4:00 p.m.*? 😊" | **NO** | **MAL en el día ofrecido** (ver abajo) |

**h5 — error de día en la alternativa.** El bot rechazó correctamente la fecha
pasada, pero al ofrecer alternativa dijo **"mañana, viernes 26 de septiembre"**.
Verificado con Python: **2026-09-26 = sábado**, no viernes; "mañana" desde el
viernes 25/09 es el **sábado 26/09**. Inventó el día. **Veredicto: MAL.**

## ¿Crea eventos cuando rechaza?

Se contaron los eventos del calendario **antes y después** de cada caso:

| Momento | Eventos en el calendario BARBER |
|---|---|
| Antes de las pruebas (respaldo) | **15** |
| Después de h1–h5 (out-of-hours, domingo, pasado) | **15** (sin cambios) |
| Después de c3 y c5 (citas legítimas) | **16** (solo las 2 agendadas) |

**Los 5 casos de rechazo (h1–h5) no crearon ni un solo evento.** Ninguno de
esos 5 turnos ejecutó `Agendar cita` ni `Registrar en hoja de citas`; en h1 solo
se ejecutó `Consultar agenda` y en h2–h5 ni siquiera eso. Comprobado además por
`runData`: los "nodos de herramienta ejecutados" de h2–h5 están vacíos.

**Veredicto de la sección 3: 4 de 5 correctos (80 %).** Rechaza bien el cierre
(19:30 con 40 min = 20:10), las 20:00, las 9:00 y el domingo; y no escribe nada
en el calendario cuando rechaza. Falla solo al nombrar el día de la alternativa
en h5.

---

# 4. BARRIDO DEL HISTORIAL — 60 ejecuciones

Se descargaron las últimas **60 ejecuciones** del workflow
(ids **1198 → 1083**, 25/09/2026 14:28 UTC → 26/09/2026 00:06 UTC) con
`includeData=true` y se analizaron respuesta por respuesta.

## 4.1 Frases "día N de mes" comprobadas contra el calendario real

| | |
|---|---|
| Frases encontradas | **19** |
| Correctas | **14** |
| **INCORRECTAS** | **5** |
| Imposibles | 0 |

Las 5 frases incorrectas, con su causa:

| Exec | Fecha de la exec | Lo que dijo | Fecha real mencionada | Verdad | Entrada |
|---|---|---|---|---|---|
| 1198 | 26/09 00:06 UTC | "Miércoles 27 de septiembre" | 2026-09-27 | **domingo** | ` mis citas` |
| 1198 | 26/09 00:06 UTC | "Jueves 28 de septiembre" | 2026-09-28 | **lunes** | ` mis citas` |
| 1198 | 26/09 00:06 UTC | "Lunes 2 de octubre" | 2026-10-02 | **viernes** | ` mis citas` |
| 1139 | 25/09 22:40 UTC | "Miércoles 27 de septiembre" | 2026-09-27 | **domingo** | ` ver mis citas` |
| 1139 | 25/09 22:40 UTC | "Jueves 28 de septiembre" | 2026-09-28 | **lunes** | ` ver mis citas` |

## 4.2 Uso de la herramienta `Que dia es`

**Se ejecutó en 1 de las 60 ejecuciones (1,7 %).**

| Exec | Fecha | Entrada | Resultado de la herramienta | ¿Acertó? |
|---|---|---|---|---|
| 1197 | 26/09 00:03 UTC | ` que dia de la semana cae el 27 de septiembre de 2026?` | `domingo 27 de septiembre de 2026 (2026-09-27)` | **SÍ** |

Es la prueba que ya se había hecho. **Funciona, pero el modelo no la usa.**

## 4.3 Tope de 10 líneas — VIOLADO 2 veces

| Exec | Fecha | Líneas | Caracteres | Entrada |
|---|---|---|---|---|
| 1198 | 26/09 00:06 UTC | **27** | 743 | ` mis citas` |
| 1139 | 25/09 22:40 UTC | **24** | 606 | ` ver mis citas` |

Tope del prompt: 10 líneas / 600 caracteres.

## 4.4 Formato: sangría inicial y líneas en blanco

| Exec | Fecha | Líneas con sangría de 3 espacios | Blancos extra | Espacios al final | `**` |
|---|---|---|---|---|---|
| 1198 | 26/09 00:06 UTC | **8** | 0 | 0 | **SÍ** |
| 1181 | 25/09 23:32 UTC | **2** | 0 | 0 | no |
| 1139 | 25/09 22:40 UTC | **7** | 0 | 0 | no |

La exec 1198 usa **doble asterisco (`**`)** — que en WhatsApp no pone negrita,
muestra los asteriscos — y **8 líneas con sangría**, ambas cosas prohibidas
expresamente por el prompt. Nota: el nodo `Mandar mensaje` recorta los espacios
al final de cada línea (`replace(/[ \t]+$/gm, '')`), por eso no aparece ninguno.

## 4.5 Ejecuciones con estado `error`

**5 de 60 (8,3 %):** exec **1109, 1106, 1094, 1091, 1089**.

| Exec | Fecha | Entrada | Causa |
|---|---|---|---|
| 1109 | 25/09 19:48 UTC | ` qeu servicios hay` | `Mandar mensaje` → **HTTP 400 Bad Request** de Evolution |
| 1106 | 25/09 19:42 UTC | ` hola` | idem |
| 1094 | 25/09 17:10 UTC | ` Hola` | idem |
| 1091 | 25/09 16:44 UTC | ` Hola` | idem |
| 1089 | 25/09 16:43 UTC | ` Hola` | idem |

Error literal (recortado), en los 5 casos idéntico:

```json
{"level":"warning","shouldReport":true,"description":"Bad Request",
 "name":"NodeApiError","node":{"name":"Mandar mensaje",
 "type":"n8n-nodes-base.httpRequest"},
 "context":{"request":{"method":"POST",
   "uri":"http://evolution_api:8080/message/sendText/hector",
   "body":{"number":"5214521206246@s.whatsapp.net","text":"","delay":1000}}}}
```

**Causa: el texto enviado va VACÍO** (`"text": ""`). Evolution rechaza con 400
un `sendText` con texto vacío. En los 5 casos el agente devolvió respuesta vacía
(en el nodo `AI Agent` el `output` era vacío), probablemente por una respuesta
vacía del modelo. **No es un fallo de fechas**, pero es el único error real del
historial y afectaba a clientes reales. Las 5 son **anteriores** a las versiones
`7c0c95b8` / `ce1d5933` ("Responder cuando agente no devuelve texto" y "Definir
texto fijo de respaldo", 25/09 21:39–21:40 UTC), que se crearon justo para
tapar esto; **después de esas versiones no hay ninguna ejecución con error**.

## 4.6 Ejecuciones sin respuesta de texto

| Exec | Fecha | Estado | Entrada |
|---|---|---|---|
| 1113 | 25/09 20:11 UTC | success | ` HOY` (comando del dueño) |
| 1112 | 25/09 20:06 UTC | success | ` hi` |
| 1109, 1106, 1094, 1091, 1089 | (ya listadas) | error | (ya listadas) |

`1113` con `HOY` y `1112` con `hi` no mandan texto por diseño (el comando `HOY`
va por el router del dueño, y `hi` cayó en la rama de respaldo). No son fallos.

**Veredicto de la sección 4.** El fallo del día **ya está documentado en el
historial y volvió a ocurrir 4 minutos después de instalar la herramienta**
(1197 la usó bien a las 00:03, 1198 la ignoró y falló a las 00:06). El tope de
líneas y el formato también se rompen. Los únicos `error` son de `Mandar
mensaje` con texto vacío, ya mitigados por versiones posteriores.

---

# 5. RESUMEN GLOBAL

| Sección | Casos probados | Aciertos | Fallos | % |
|---|---|---|---|---|
| **1. Herramienta `Que dia es`** | 65 | 52 | 13 | **80,0 %** |
| **2. Uso conversacional en vivo** | 8 | 6 | 2 | **75,0 %** |
| **3. Horarios del negocio** | 5 | 4 | 1 | **80,0 %** |
| **4. Historial: frases de día** | 19 | 14 | 5 | **73,7 %** |
| **TOTAL** | **97** | **76** | **21** | **78,4 %** |

*(La sección 4 no incluye las 60 ejecuciones como "casos": se cuentan las 19
frases con día de la semana verificables. Los demás controles del historial
—uso de la herramienta, tope de líneas, formato, estados `error`— se reportan
aparte en 4.2–4.6.)*

## Los fallos concretos, en una línea cada uno

1. **`AAAA-MM-DD` suelto resta un día** (`2026-09-27` → sábado 26). Es el fallo
   original por otra entrada. Probado a nivel de herramienta, **no visto en
   vivo**.
2. **`dd/mm/aaaa` se malinterpreta**: `27/12/2026` → 27 de septiembre;
   `05/01/2027` → 30 de abril de 2027. **Visto en vivo** (exec 1319, 1320).
3. **Basura devuelve día inventado** (`32/13/2026`, `2026-13-01`, `9999-99-99`,
   `2026`, `20260927`, `27 septiembre` → 2001). Sin error legible.
4. **El modelo no usa la herramienta al listar citas** → ejecución 1198 volvió
   a inventar "miércoles 27", "jueves 28" y "lunes 2 de octubre".
5. **Tope de 10 líneas roto** (27 y 24 líneas) y sangría de 3 espacios.
6. **c3:** agendó un corte **en el pasado** (25/09 a las 16:00, pedido a las
   18:36). La regla del prompt mira el día, no la hora.
7. **h5:** ofreció "mañana, **viernes** 26 de septiembre" cuando el 26/09/2026
   es **sábado**.

## Lo que SÍ está bien

- El cálculo de día con **ISO completo y offset** es **correcto en los 43 casos**
  de los grupos 1–6 (los 7 días, frontera de zona horaria a las 19:00, medianoche,
  cambio de mes, cambio de año, 29 de febrero): **100 %**. Esto incluye
  `2026-09-28T19:00:00-06:00` y su equivalente en UTC `2026-09-29T01:00:00Z`,
  que ambos devuelven **lunes 28** correctamente.
- **El fallo original (27 y 28 de septiembre) está corregido en la herramienta**:
  `2026-09-27T12:00:00-06:00` → domingo; `2026-09-28T12:00:00-06:00` → lunes.
- Los rechazos por horario (19:30, 20:00, 9:00), domingo y fecha pasada
  funcionan y **no ensucian el calendario**.
- Las cuatro entradas basura "clásicas" (`''`, `null`, `undefined`, `'   '`)
  devuelven error legible. `'hola'` también.

## Qué no pude probar

- **No reproduje en vivo el fallo de `AAAA-MM-DD`** (fallo 1). El modelo, en
  los 4 casos en vivo donde usó la herramienta, le pasó texto en español. El
  fallo está probado ejecutando el código real, no observado en conversación.
  No lo doy por "solo teórico": la ruta es directa (el prompt sugiere escribir
  la fecha numérica suelta).
- **La exec 1198 y 1139 pertenecen a un cliente real** (`Cristia Ñ`), no a un
  JID de pruebas. No modifiqué esas ejecuciones ni la memoria de ese cliente.
- El agente **ignoró** el resultado erróneo de la herramienta en x1/x2. No
  puedo determinar si fue suerte o si el modelo detectó la incoherencia; solo
  consta que la salida de la herramienta era incorrecta.

---

# 6. LIMPIEZA

| Recurso | Acción | Comprobación |
|---|---|---|
| Calendario BARBER | Borré los **2 eventos** que creé: `85e7vg5vkv3pbggu01j9fp2gtk` (c3) y `mfako9a08epskn3irbr3rq4g4o` (c5) | Pasó de 19 a 17 eventos; los 15 originales intactos y **0 eventos eliminados** que no fueran míos |
| Hoja de citas | Borré las **2 filas** que creé (coincidentes con esos 2 IDs) | Pasó de 12 a **10 filas**, exactamente las del estado previo |
| Memoria del JID de pruebas | Restauré desde el respaldo y borré los 4 registros de mis sondas x1/x2 | **662 filas, id 1–1258**, idéntico al respaldo previo |
| Workflows temporales de prueba | Creé y **borré** 5 workflows auxiliares (`_verif-cal-tmp`, `_verif-fechas-hoja`, `_verif-fechas-code`, `_verif-fechas-borrar`) | n8n tiene **3 workflows**, los originales, todos activos |
| Prompt y workflows | **No modifiqué nada** | `jsCode` de `Que dia es` sin cambios (mismo sha256) |

**Respaldo guardado** en `G:\Barberia\archivos\_verif-fechas\`:
`respaldo_memoria_1805.json` (662 filas) y `respaldo_calendario.json` (15
eventos). La evidencia cruda está en esa misma carpeta (`resultados_n8n.json`,
`tally_final.json`, `historial_analizado.json`, `vivo\*.json`).
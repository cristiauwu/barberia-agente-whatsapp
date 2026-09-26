# AUDITORÍA DE LA BASE DE CONOCIMIENTO — Barber Chinos

**Fecha:** sesión de auditoría · **Alcance:** base de conocimiento (FAQs) del agente
**Fuente de verdad auditada:** tabla `barber_conocimiento` de Postgres
(`barberia-postgres`, `127.0.0.1:5432`, base `barberia`, PostgreSQL **17.11**)
**Restricción respetada:** NO se modificó la tabla, ni las FAQs, ni el prompt, ni
los workflows. Solo lectura + consultas a la función de búsqueda.

**Evidencia bruta** (todo lo que respalda este informe) en
`G:\Barberia\_aud_con\`: `faqs.txt`, `busqueda.txt`, `sqlcheck.txt`,
`dif_prompt.txt`, `precios.txt`, `ranks.txt`, `prompt_vivo.txt`,
`bloque_prompt.txt`, `conv.json`, `efectos.txt`.

---

## 1. HALLAZGOS (por gravedad)

### CRÍTICO 1 — La copia del prompt está DESINCRONIZADA y contradice la base

El bloque de FAQs del prompt tiene **46 entradas**; la tabla tiene **58**.
No es solo que falten: **12 FAQs que existen en las dos partes dicen cosas
DISTINTAS**, y en 6 de esos casos el prompt dice **lo contrario** de lo que el
dueño confirmó.

Como el prompt va **en cada mensaje** y gana sobre todo lo demás (el agente no
tiene ninguna herramienta que consulte la tabla — ver hallazgo 4), **la versión
que el bot usa de verdad es la del prompt**, es decir la desactualizada.

| # | Pregunta | Dice la BASE (correcto) | Dice el PROMPT (lo que el bot usa) |
|---|---|---|---|
| 48 | ¿Dan factura? | "Por el momento **no** manejamos facturación." | "Déjame preguntarle al encargado…" (esquiva un dato ya confirmado) |
| 51 | ¿Tienen redes sociales? | "Atendemos **únicamente por WhatsApp**." | "Déjame preguntarle al encargado…" |
| 215 | ¿Tienen wifi? | "**Sí, tenemos wifi.** Pídelo al llegar…" | "Te confirmo ese dato con el encargado…" (dice que NO se sabe) |
| 30 | ¿Aceptan tarjeta? | "Se puede pagar **en efectivo o por transferencia**." | "El pago se hace directo en el local…" (no dice ninguna forma de pago) |
| 31 | ¿Puedo pagar con transferencia? | "Se puede pagar en efectivo o por transferencia." | "El pago se hace directo en el local…" |
| 40 | ¿Qué pasa si llego tarde? | "Te esperamos de **5 a 10 minutos**." | "Si te retrasas **más de 15 minutos**…" ← contradice la tolerancia confirmada |
| 213 | ¿Qué pasa si voy a llegar tarde? | "Te esperamos de **5 a 10 minutos**." | "Si te pasas mucho del horario…" |
| 3 | ¿Tienen estacionamiento? | "No tenemos estacionamiento." | "No tenemos estacionamiento **propio**…" (matiza lo confirmado) |
| 5 | ¿Aceptan niños? | "Sí… mismo corte de *$150*." | "¡Claro!… Se atiende igual que a cualquier cliente." (sin precio) |
| 20 | ¿Hacen corte para niño? | "Sí… mismo corte de *$150*." | igual pero añade "para los más chicos suele ser más rápido" (no confirmado) |
| 214 | ¿Puedo llevar a mi hijo? | "…mismo corte de *$150*." | "…mismo corte de *$150*." (redacción distinta) |
| 34 | ¿Cuánto tiempo antes debo llegar? | "unos 5 minutos antes… si vas a llegar tarde, avísanos" | "Con llegar *5 minutos antes*…" (pierde el "si llegas tarde, avisa") |

**La contradicción más grave:** el prompt dice **"más de 15 minutos"** de
tolerancia; el dueño confirmó **5 a 10**. El bot está prometiendo al cliente
más margen del que el barbero da.

### CRÍTICO 2 — Una FAQ que el dueño mandó borrar SIGUE en el prompt

`archivos\aplicar-respuestas-dueno.py` (líneas 5-13, 76-77 y 188-200) borra las
preguntas de "no-show" porque **el dueño dijo textualmente "no sé qué es no
show"**. En la tabla sí se borró (la fila **#41 ya no existe**: los ids saltan
de 40 a 42).

Pero en el prompt **sigue esta línea** (evidencia literal de
`bloque_prompt.txt`):

```
- **¿Cobran si no llego a mi cita?** No cobramos por no llegar. Solo te
  pedimos que nos avises para liberar el lugar.
```

El filtro del script busca el literal *"no-show"*, *"si no llego"* o *"no llego
a mi cita"* (línea 195: `r"no[- ]?show|si no llego|no llego a mi cita"`), así
que **debía** haber quitado esa línea del archivo del repo. No lo hizo, o se
volvió a reintroducir después: **la línea está HOY tanto en el archivo
`G:\Barberia\prompt-sistema-agente-barberia.txt` como en el prompt vivo de n8n**
(verificado literal en ambos; los dos prompts son idénticos). El bot está
respondiendo una política que el dueño no reconoce.

**Nota de trazabilidad:** esa misma frase **sí sigue en el seed**
`conocimiento-barberia.sql` (entrada **#41** del `INSERT`, confirmado:
`#41 -> ('¿Cobran si no llego a mi cita?', 'No cobramos por no llegar…'`), pero
**la fila fue borrada de la tabla** (`id 41` no existe). Es decir: el SQL de
origen la crea, el script de respuestas del dueño la borra de la BD, y el prompt
la conserva. **Tres estados distintos para la misma FAQ.**

### CRÍTICO 3 — La búsqueda devuelve PRECIOS EQUIVOCADOS en 3 de los 8 servicios

`barber_buscar_conocimiento` no sirve hoy al bot (no está conectada — hallazgo
4), pero es la pieza que el proyecto tiene lista "para escalar". Auditada
directamente, **falla en precios**: hay **FAQ de precio dedicada para corte,
dama, barba, ceja y depilación, pero NO para mascarilla, peinado ni planchado**.

Cuando el cliente pregunta por esos tres, la coincidencia de "cuánto cuesta"
(que vale 0.5336 de rank) **pisa** al nombre del servicio y devuelve la FAQ del
corte:

```
q='cuanto cuesta el peinado'    -> 1. #23 rank=0.5336  ¿Cuánto cuesta el corte?
        'El corte desvanecido o tijera cuesta *$150* y dura 40 minutos.'
   (el peinado cuesta $300 en barber_servicios)

q='cuanto cuesta el planchado'  -> 1. #23 rank=0.5336  ¿Cuánto cuesta el corte?
        'El corte desvanecido o tijera cuesta *$150*…'
   (el planchado cuesta $150 — coincide por casualidad, la FAQ es la equivocada)

q='cuanto cuesta la mascarilla' -> 1. #23 rank=0.5336  ¿Cuánto cuesta el corte?
        'El corte desvanecido o tijera cuesta *$150*…'
   (la mascarilla cuesta $50)
```

Medido: **21 de 72 formulaciones de precio (29 %) devuelven una FAQ cuyo precio
no corresponde al servicio preguntado**. Si algún día se conecta la búsqueda al
bot, esto es un fallo directo de precio.

> **Importante para no exagerar el hallazgo:** los **precios escritos en las
> FAQs coinciden todos con el catálogo real** de `barber_servicios`
> (150/100/30/50/250/150/300, depilación "según zona"). No hay ningún precio
> falso *en el texto*. El problema es exclusivamente el **ranking** de la
> búsqueda. Detalle completo en `precios.txt`.

### ALTO 4 — La función de búsqueda NO está conectada al agente

**Evidencia:** en el workflow vivo (`barberiaAgenteUncensored`, 48 nodos,
`updatedAt` 2026-09-26T00:02:56Z) las conexiones `ai_tool` del nodo `AI Agent`
son exactamente:

```
Consultar agenda, Agendar cita, Cancelar cita, Reagendar,
Registrar en hoja de citas, Notificar al encargado, Que dia es
```

**No hay ningún nodo Postgres ni tool de conocimiento** conectado al agente. Un
`grep` a todo `G:\Barberia` buscando `barber_buscar_conocimiento` solo aparece en
`conocimiento-barberia.sql` (definición), `probar-conocimiento.py` (script de
prueba), `RAG-EVALUACION.md` e `INFRAESTRUCTURA.md`. **Cero referencias en
cualquier JSON de workflow o código JS de n8n.**

Consecuencia: **la tabla de 58 FAQs no influye en las respuestas del bot.** La
única copia que el agente lee es el bloque del prompt — y ese bloque está
desincronizado (hallazgo 1). Hay **dos copias y ganó la mala**.

### ALTO 5 — El bot INVENTA en conversación (probado en vivo)

16 mensajes reales por el webhook con el JID de pruebas
`5214501111805@s.whatsapp.net` (~15 s entre mensajes). **Tres fallos**:

| Pregunta | Respuesta del bot | Realidad | Veredicto |
|---|---|---|---|
| "me pueden hacer un corte estilo mohicano **con rayas**?" | "El corte desvanecido o tijera de *$150* **incluye estilos personalizados como el mohicano. Las rayas también se pueden hacer.**" | Nadie confirmó que Esteban haga mohicanos ni rayas. La FAQ #21 solo dice que "mod cut"/"corte clásico" **no** están en el catálogo. | **INVENTA** — promete una capacidad no confirmada |
| "hacen descuento a estudiantes?" | "Por el momento, **no manejamos descuentos** para estudiantes." | La FAQ #28 y la sección "PROCESO D" ordenan **escalar** ("déjame preguntarle al encargado"; "no rechaces tú la petición"). El bot **negó** una política que nadie definió. | **INVENTA** + incumple la regla de escalar |
| "cuanto cuesta el peinado?" (vale $300) | "¿Qué servicio te gustaría agendar para el viernes?" | No respondió el precio. **No inventó** una cifra, pero tampoco dio el dato que sí está en el prompt. | Respuesta inservible (no es invención) |

Además, a "¿qué pasa si llego tarde?" el bot respondió **"Te esperamos. Si te
retrasas más de 15 minutos…"** — propagando la contradicción del prompt
(hallazgo 1) en lugar de los 5-10 min confirmados.

**Lo que sí hizo bien** (evidencia de que el mecanismo de escalada funciona):
- "tienen servicio a domicilio los domingos?" → *"No, no contamos con servicio a
  domicilio, y los domingos el negocio está cerrado…"* (usa los datos reales) ✔
- "cuanto cuesta la mascarilla?" → *"La mascarilla cuesta *$50* y dura 20
  minutos."* ✔ (respuesta correcta)
- "cuanto cuesta el corte?" → *"$150… si es corte de dama, $250"* ✔

Preguntas de FAQ probadas (10): corte ✔, estacionamiento ✔, horario ✔, quién
atiende ✔, tarjeta ~ (no dice efectivo/transferencia), wifi ✗ (escala de más),
factura ✗ (escala de más), llevar al hijo ✔, llego tarde ✗ (dice 15 min),
ubicación ✔.

### MEDIO 6 — 5 FAQs marcadas `propuesta` se están dando como ciertas

La columna `origen` las marca honestamente como suposiciones, pero **el prompt
no lleva ninguna marca visible** de que lo sean: el bloque las presenta igual
que las confirmadas y el modelo no ve la diferencia. Son las que el dueño tiene
que validar → **sección 3.A de este informe**.

### MEDIO 7 — Duplicados exactos y preguntas solapadas

Cuatro respuestas están **literalmente duplicadas** (mismo md5):
- Corte de niño a $150: **3 filas** — #5, #20, #214
- Tolerancia de retraso: **2 filas** — #40, #213
- Formas de pago: **2 filas** — #30, #31
- "Déjame preguntarle al encargado…": **2 filas** — #28, #43

Pares de preguntas casi iguales (Jaccard ≥ 0.5 sobre palabras):

| Par | Preguntas |
|---|---|
| #23 / #24 | ¿Cuánto cuesta el corte? / ¿Cuánto cuesta el corte **de dama**? |
| #26 / #211 | ¿Cuánto **cuesta** la barba? / ¿Cuánto **dura** la barba? |
| #26 / #27 | ¿Cuánto cuesta la barba? / ¿Cuánto cuesta la ceja? |
| #23 / #209 | ¿Cuánto cuesta el corte? / ¿Cuánto **dura** el corte? |
| #11 / #20 | ¿Hacen corte para dama? / ¿Hacen corte para niño? |
| #40 / #213 | ¿Qué pasa si llego tarde? / ¿Qué pasa si **voy a** llegar tarde? |
| #17 / #27, #17 / #26 | depilación / ceja / barba (mismo patrón "¿Cuánto cuesta…?") |
| #2 / #6 | ¿Cuál es el teléfono? / ¿Cuál es el horario? |

**Sinónimos redundantes dentro de la misma fila** (24 filas): la palabra del
título vuelve a repetirse en `sinonimos` (p. ej. #3 repite `carro`, #45 y #46
repeten `barbero`, #21 repite `corte` y `cut`, #37 repite `domicilio`). No rompe
nada, pero **infla el tsvector con peso A** y degrada el ranking — es una de las
causas del hallazgo 3. Detalle completo en `dups.txt`.

### MEDIO 8 — Ids huecos: 157 números perdidos, huella de pruebas masivas

Los ids son `1..40, 42, 43..52, 209..215`. Sobre el rango 1-215 (215 números),
hay **58 presentes y 157 ausentes**: falta **41** (borrada por "no-show",
verificado) y **un bloque entero de 53 a 208 (156 ids)** que ya no existen.
Evidencia de cargas y borrados masivos de prueba. No afecta al funcionamiento,
pero conviene saberlo: **la tabla no son 58 filas "desde siempre", es el residuo
de varias purgas.**

---

## 2. TABLA DE LAS 58 FAQs CON SU `origen`

Reparto real: **53 `contexto`** y **5 `propuesta`** (53 + 5 = 58).

| id | categoría | origen | pregunta |
|---|---|---|---|
| 1 | ubicacion | contexto | ¿Dónde están ubicados? |
| 2 | ubicacion | contexto | ¿Cuál es el teléfono? |
| 3 | instalaciones | contexto | ¿Tienen estacionamiento? |
| 4 | citas | contexto | ¿Se puede pasar sin cita? |
| 5 | instalaciones | contexto | ¿Aceptan niños? |
| 6 | horarios | contexto | ¿Cuál es el horario? |
| 7 | horarios | contexto | ¿Abren el domingo? |
| 8 | horarios | contexto | ¿Hasta qué hora puedo agendar? |
| 9 | horarios | **propuesta** | ¿Atienden en días festivos? |
| 10 | servicios | contexto | ¿Qué servicios tienen? |
| 11 | servicios | contexto | ¿Hacen corte para dama? |
| 12 | servicios | contexto | ¿Arreglan la barba? |
| 13 | servicios | contexto | ¿Hacen las cejas? |
| 14 | servicios | contexto | ¿Qué es la mascarilla? |
| 15 | servicios | contexto | ¿Hacen planchado? |
| 16 | servicios | contexto | ¿Hacen peinado? |
| 17 | servicios | contexto | ¿Cuánto cuesta la depilación? |
| 18 | servicios | contexto | ¿Hacen tintes o color? |
| 19 | servicios | contexto | ¿Trabajan con máquina o navaja? |
| 20 | servicios | contexto | ¿Hacen corte para niño? |
| 21 | servicios | contexto | ¿Tienen un corte llamado "mod cut" o "corte clásico"? |
| 22 | servicios | contexto | ¿Qué me recomiendan si es mi primera vez? |
| 23 | precios | contexto | ¿Cuánto cuesta el corte? |
| 24 | precios | contexto | ¿Cuánto cuesta el corte de dama? |
| 25 | precios | contexto | ¿Me dan la lista de precios completa? |
| 26 | precios | contexto | ¿Cuánto cuesta la barba? |
| 27 | precios | contexto | ¿Cuánto cuesta la ceja? |
| 28 | pagos | contexto | ¿Hacen descuento? |
| 29 | pagos | contexto | ¿Cobran menos si me hago varios servicios juntos? |
| 30 | pagos | contexto | ¿Aceptan tarjeta? |
| 31 | pagos | contexto | ¿Puedo pagar con transferencia? |
| 32 | citas | contexto | ¿Cómo agendo una cita? |
| 33 | citas | contexto | ¿Necesito dar mis datos para la cita? |
| 34 | citas | **propuesta** | ¿Cuánto tiempo antes debo llegar? |
| 35 | citas | **propuesta** | ¿Puedo apartar varias citas a la vez? |
| 36 | citas | contexto | ¿Con cuánta anticipación puedo agendar? |
| 37 | citas | contexto | ¿Atienden a domicilio? |
| 38 | politicas | contexto | ¿Puedo cancelar mi cita? |
| 39 | politicas | contexto | ¿Puedo cambiar mi cita de día u hora? |
| 40 | politicas | contexto | ¿Qué pasa si llego tarde? |
| 42 | politicas | **propuesta** | ¿Cuál es la política de cancelación? |
| 43 | politicas | contexto | ¿Hay garantía si no me gusta el corte? |
| 44 | citas | contexto | ¿Necesito cita para la ceja o la barba? |
| 45 | barbero | contexto | ¿Quién me va a atender? |
| 46 | barbero | contexto | ¿Puedo elegir a otro barbero? |
| 47 | barbero | **propuesta** | ¿Tienen experiencia cortando este tipo de cabello? |
| 48 | general | contexto | ¿Dan factura? |
| 49 | general | contexto | ¿Venden productos para el cabello? |
| 50 | general | contexto | ¿Puedo dejar una propuesta o una queja? |
| 51 | general | contexto | ¿Tienen redes sociales? |
| 52 | general | contexto | ¿Puedo dejar reservado para una boda o un evento? |
| 209 | servicios | contexto | ¿Cuánto dura el corte? |
| 210 | servicios | contexto | ¿Cuánto dura cada servicio? |
| 211 | servicios | contexto | ¿Cuánto dura la barba? |
| 212 | citas | contexto | ¿Puedo agendar el mismo día? |
| 213 | citas | contexto | ¿Qué pasa si voy a llegar tarde? |
| 214 | general | contexto | ¿Puedo llevar a mi hijo? |
| 215 | general | contexto | ¿Tienen wifi? |

> **`id 41` no existe** (borrado por la orden de "no-show" del dueño).

---

## 3. LAS QUE HAY QUE CONFIRMAR — entregable para el dueño

### 3.A — Las 5 `propuesta` (el bot las da como ciertas y no lo son)

| # | Pregunta | Respuesta que el bot da HOY | ¿Correcto? (SÍ / NO) |
|---|---|---|---|
| 9 | **¿Atienden en días festivos?** | "Los días festivos trabajamos en horario normal si cae de lunes a sábado. Si el encargado cierra ese día, aquí te lo confirmamos al agendar." | ☐ SÍ  ☐ NO |
| 34 | **¿Cuánto tiempo antes debo llegar?** | "Con llegar unos 5 minutos antes es suficiente. Si vas a llegar tarde, avísanos por aquí." | ☐ SÍ  ☐ NO |
| 35 | **¿Puedo apartar varias citas a la vez?** | "Sí, dime los servicios y los horarios que quieres y te los aparto. Si son muchos, mejor los vemos uno por uno para no equivocarnos." | ☐ SÍ  ☐ NO |
| 42 | **¿Cuál es la política de cancelación?** | "Puedes cancelar o mover tu cita cuando quieras, avisándonos por aquí. No hay penalización; solo te pedimos avisar con anticipación." | ☐ SÍ  ☐ NO |
| 47 | **¿Tienen experiencia cortando este tipo de cabello?** | "Sí, Esteban tiene experiencia con distintos tipos de cabello. Platícame qué buscas y te dice si te lo puede hacer." | ☐ SÍ  ☐ NO |

**Qué necesita el dueño para cada una:**
- **#9** — ¿abren en festivos? ¿cuáles sí y cuáles no? ¿o cerrado siempre?
- **#34** — ¿cuántos minutos antes quiere que llegue el cliente?
- **#35** — ¿acepta más de una cita por persona en la misma visita?
- **#42** — ¿hay algún límite para cancelar (tiempo mínimo, número de veces)?
- **#47** — ¿confirma que corta cualquier tipo de cabello, o hay alguno que no?

### 3.B — Las 5 contradicciones activas (urgencia: el bot ya dice mal)

| # | Pregunta | El bot dice HOY | El dueño confirmó | Acción |
|---|---|---|---|---|
| 40 / 213 | ¿Qué pasa si llego tarde? | **"más de 15 minutos"** (prompt) | **5 a 10 minutos** | el prompt debe pasar a "5 a 10 min" |
| 215 | ¿Tienen wifi? | "Te confirmo con el encargado…" | **Sí hay wifi** | el prompt debe decir que sí |
| 30 / 31 | ¿Aceptan tarjeta / transferencia? | "El pago se hace directo en el local…" | **efectivo o transferencia** | el prompt debe decirlo |
| 48 | ¿Dan factura? | "Déjame preguntarle al encargado…" | **no hay facturación** | el prompt debe decirlo |
| 51 | ¿Tienen redes sociales? | "Déjame preguntarle al encargado…" | **solo WhatsApp** | el prompt debe decirlo |

Estos cinco **no hay que preguntárselos otra vez**: ya los contestó (ver
`aplicar-respuestas-dueno.py`, comentario de cabecera). Son tareas de
**sincronización**, no de confirmación. Y son exactamente los 5 casos en los que
la tabla ya está bien y el prompt está mal → **sobrescribir el prompt desde la
tabla los arregla todos.**

### 3.C — Preguntas nuevas que el dueño debe contestar (no existen en ningún lado)

| Pregunta del cliente | Qué necesita el dueño decidir |
|---|---|
| **¿Cobran si no llego a mi cita?** | La fila se borró porque no conocía el término "no-show". Pero la pregunta **sí se la hacen**: ¿cobra o no cobra la inasistencia? (hay que reescribir la FAQ sin la palabra "no-show") |
| **¿Qué formas de pago exactas aceptan?** | confirmado "efectivo o transferencia" — ¿algo más (QR, depósito, dólares)? |
| **¿Hay anticipo o depósito para apartar?** | ¿pide depósito para reservar una cita? |
| **¿Hay promoción / paquete corte + barba?** | ¿existe algún paquete con precio? (el bot ya inventó que sí hay descuentos según el caso) |
| **¿Hacen estilos personalizados (mohicano, rayas, diseños)?** | el bot **inventó que sí**. Hay que confirmarlo o prohibirlo explícitamente |
| **¿Cortan el cabello a bebés (2-3 años)?** | ¿hay edad mínima? |
| **¿Cuánto tiempo hay que esperar si llego sin cita?** | ¿espera típica en hora pico? |
| **¿Cómo se llega / en qué colonia?** | falta referencia de ubicación: solo hay "Calle Pinzón #574", sin colonia ni referencias |
| **¿Dan comprobante o ticket aunque no sea factura?** | ¿entrega ticket? |
| **¿Hay baño para clientes?** | ¿el cliente puede usar el baño? |
| **¿Qué pasa si llueve / hay mal tiempo?** | ¿cierra? ¿cancela? |
| **¿Atienden a personas mayores o en silla de ruedas?** | ¿el local es accesible? |
| **¿Se puede pedir cita para dos personas a la misma hora?** | ¿atiende a dos a la vez? (relacionado con #35) |
| **¿Tiñen las canas / hacen decoloración?** | existe #18 (tinte) que escala — ¿confirmar que sigue fuera de catálogo? |
| **¿Quién es el dueño / cómo se llama el negocio?** | ¿el bot debe dar ese dato? |

**Nota importante:** varios de estos huecos **el bot ya los maneja bien por
defecto** — ante algo que no sabe debe usar **Notificar al encargado**. En mi
prueba lo hizo bien en "servicio a domicilio los domingos". **Prioridad: cerrar
el hueco de "descuentos" y el de "estilos personalizados", que son los que el
bot está rellenando solo.**

---

## 4. RESULTADOS DE LA BÚSQUEDA

### 4.1 Porcentaje de acierto

**75 consultas** escritas como las escribe la gente (minúsculas, sin acentos,
abreviadas, con faltas), midiendo **si la FAQ correcta sale como PRIMER
resultado**:

```
RESULTADO: 66/75 aciertan la FAQ correcta como PRIMER resultado = 88.0 %
```

(La meta declarada en `RAG-EVALUACION.md` era **21/21 = 100 %**, pero se midió
con 21 preguntas limpias; con 75 consultas reales y sucias baja a **88 %**.)

**Casos borde: 17/19 sin error y con 0 filas.** Los dos "REVISAR":
- `'; DROP TABLE barber_conocimiento; --` → **3 filas** (no es un fallo de
  seguridad: la inyección NO se ejecuta, solo genera los lexemas `drop`,
  `table` y `barber` que coinciden con FAQs que hablan de "barba". **La tabla
  sigue con 58 filas — verificado después.**)
- Cadena con byte NUL → `DataError: PostgreSQL text fields cannot contain NUL`.
  **No lo puede provocar un cliente**: WhatsApp no entrega NUL en texto.

### 4.2 Las 9 consultas que fallan (huecos de búsqueda)

| Consulta | Qué devuelve | Por qué falla |
|---|---|---|
| `kual es el orario` | **nada** | `kual`→`kual`, `orario`→`orari` ≠ `horari`. Las faltas de ortografía no se cubren (el stemmer no arregla la `h` muda) |
| `tienen estoacionamiento` | **nada** | `estoacion` ≠ `estacion` (letra de más) |
| `depilasion` | **nada** | `depilasion` ≠ `depilacion` (s/c) |
| `q dias abren` | #9 días festivos (0.3192) > #6 horario (0.3040) | desempate ajustado; la 'q' se descarta por longitud < 3 |
| `me pueden pintar el pelo` | #36 anticipación | "pelo" no está en los sinónimos de #18 (tinte) |
| `hay otro barbero` | #26 precio barba | **"barba" arrastra todo** (rank 0.8351) |
| `puedo ir sin cita` | #38 cancelar (0.7599) | la palabra "cita" pesa más que "sin" |
| `cobran si no llego` | #34 tiempo antes de llegar | **el hueco real**: la FAQ se borró |
| `prefiero un bob` | **nada** | nombre de corte fuera de catálogo, sin sinónimo que lo capte |

### 4.3 Acentos y `unaccent` — FUNCIONA (verificado en vivo)

```
to_tsvector('public.spanish_unaccent','depilación') @@ to_tsquery(...,'depilacion')  -> true
to_tsvector('public.spanish_unaccent','depilacion') @@ to_tsquery(...,'depilación')  -> true
to_tsvector('spanish','depilación') @@ to_tsquery('spanish','depilacion')            -> false  <- la de fábrica
```

La configuración `public.spanish_unaccent` **existe** y encadena bien
(`word/hword/hword_part → unaccent, spanish_stem`). `depilacion`, `depilación`,
`DEPILACION` aciertan todas #17. **El problema declarado está resuelto.**

### 4.4 Sinónimos (checar / consultar / corte / cortarme / pago / cobro)

Probado y **funciona**:
- `checar mi cita`, `consultar mi cita`, `como checo si tengo cita` → #44/#32 ✔
- `cortarme el pelo`, `quiero cortarme`, `corte de pelo`, `cortada` → #23 ✔
- `como hago el pago`, `el cobro` → #29/#30 ✔; `cuanto me cobran`, `cuanto es el cobro` → #23 ✔
- `apartar`, `reservar`, `turno`, `hueco`, `cita`, `cuanto vale`, `cuanto sale`, `precio`, `tarifa`, `costo` → todas aciertan ✔

### 4.5 Rendimiento e índice GIN

El **índice GIN existe y está bien definido**:
```
CREATE INDEX barber_conocimiento_tsv_gin
  ON public.barber_conocimiento USING gin (tsv)
```

**Pero el planificador NO lo usa** con solo 58 filas — y es correcto que no lo use:
```
Seq Scan on barber_conocimiento c  (cost=0.00..8.77 rows=18) (actual time=0.013..0.049 rows=18)
  Filter: (activo AND (tsv @@ '''cort'''::tsquery))
  Rows Removed by Filter: 40
Execution Time: 0.141 ms
```
Forzándolo (`SET enable_seqscan=off`) el índice **sí sirve**:
```
Bitmap Index Scan on barber_conocimiento_tsv_gin  (cost=0.00..8.64 rows=18)
```
Con 58 filas el seq scan sobre 8 buffers es más barato que el índice; el GIN
empezará a usarse cuando la tabla crezca. **El índice es correcto y está listo,
no hay nada que arreglar aquí.** La latencia medida de la función completa es
~5,6 ms de ejecución.

### 4.6 Seguridad de la función

- **Parametrizada**: la propia documentación del SQL la invoca con `$1`
  (`SELECT * FROM public.barber_buscar_conocimiento($1, 3)`). Probado con
  payloads hostiles pasados **como parámetro**: `' OR 1=1 --` → 0 filas,
  `1'; SELECT pg_sleep(10); --` → 0 filas, `'; DROP TABLE …` → 3 filas
  (coincidencia léxica, no ejecución). **La tabla sigue con 58 filas después de
  todos los intentos.** No hay inyección.
- **`STABLE`, no volátil** (`provolatile='s'`), `SECURITY INVOKER`
  (`prosecdef=false`) → no escala privilegios.
- **Límite saneado**: `LIMIT greatest(1, least(coalesce(p_limite,3), 20))`.
  Verificado: `0`→1, `-5`→1, `21`→18 (tope), `1000`→18, `NULL`→3. Nunca falla.
- **Consulta `NULL`** → 0 filas, sin error.
- **Con la configuración sin acentos delante**, cadena de diccionarios correcta:
  `word/hword/hword_part → unaccent, spanish_stem`.

---

## 5. ¿LA COPIA DEL PROMPT ESTÁ SINCRONIZADA? — **NO**

| Métrica | Valor |
|---|---|
| FAQ en la tabla | **58** |
| FAQ en el bloque del prompt | **46** |
| Coinciden (mismo texto de pregunta) | **45** |
| **En el prompt pero NO en la tabla** | **1** — *¿Cobran si no llego a mi cita?* (fila borrada) |
| **En la tabla pero NO en el prompt** | **13** |
| **Coinciden en texto pero DIFIERE la respuesta** | **12** |

> El bloque vivo del prompt mide **6.836 caracteres**; el prompt completo
> **42.629 caracteres** (~42.000 como decía el enunciado).

### Precisión: qué FAQ está en una y no en la otra

**Solo en el prompt (1) — debería borrarse:**
- **¿Cobran si no llego a mi cita?** — *"No cobramos por no llegar. Solo te
  pedimos que nos avises para liberar el lugar."* (Sí existe en el seed del SQL
  como entrada #41, se borró de la tabla, y sigue en el prompt.)

**Solo en la base (13) — al prompt le faltan:**

| # | Pregunta | Motivo por el que falta | ¿Es grave? |
|---|---|---|---|
| 1 | ¿Dónde están ubicados? | el dato **sí está** en "# DATOS DEL NEGOCIO" | redundante |
| 2 | ¿Cuál es el teléfono? | el dato **sí está** en "# DATOS DEL NEGOCIO" | redundante |
| 8 | ¿Hasta qué hora puedo agendar? | cubierto por "REGLAS DE PRECIOS Y DURACIÓN" | redundante |
| 10 | ¿Qué servicios tienen? | cubierto por "CATÁLOGO DE SERVICIOS" | redundante |
| 17 | ¿Cuánto cuesta la depilación? | cubierto por las reglas de depilación | redundante |
| 23 | ¿Cuánto cuesta el corte? | cubierto por el catálogo | redundante |
| 24 | ¿Cuánto cuesta el corte de dama? | cubierto por el catálogo | redundante |
| 26 | ¿Cuánto cuesta la barba? | cubierto por el catálogo | redundante |
| 27 | ¿Cuánto cuesta la ceja? | cubierto por el catálogo | redundante |
| 32 | ¿Cómo agendo una cita? | cubierto por "PROCESO A" | redundante |
| 209 | ¿Cuánto dura el corte? | cubierto por el catálogo (40 min) | redundante |
| 210 | ¿Cuánto dura cada servicio? | cubierto por el catálogo | redundante |
| 211 | ¿Cuánto dura la barba? | cubierto por el catálogo (20 min) | redundante |

**Verificación de que el dato sí está en el prompt fuera del bloque:** busqué
literalmente cada dato clave en el prompt **con el bloque de FAQs eliminado**,
y los 14 comprobados (dirección, teléfono, horario, domingo, los 6 precios,
duración 40 min, depilación, mascarilla, planchado) **aparecen igualmente** en
las secciones propias del prompt. Es decir: la ausencia de estas 13 FAQs en el
bloque **no pierde ningún dato**. Ocurre porque `reducir-faqs-prompt.py` las
quitó a propósito en su día (su lista `REDUNDANTES`, líneas 55-60) por ser
duplicados del catálogo.

**Conclusión del desfase:** el problema **no es que falten 13 FAQs** (son
redundantes). El problema real son:
1. **12 respuestas que dicen cosas distintas** — 5 de ellas en contra de lo que
   el dueño confirmó (sección 3.B).
2. **1 FAQ que debía estar borrada** y sigue viva (¿Cobran si no llego?).

Es decir: **el prompt no es una copia fiel de la tabla, y en los puntos que
importan dice lo contrario.**

### Nota: el archivo del repo y el workflow SÍ están sincronizados

`prompt-sistema-agente-barberia.txt` y el `systemMessage` vivo **son idénticos**
salvo **un espacio final** (42.630 vs 42.629 caracteres; la comparación exacta da
`False` solo por ese carácter). Comprobado carácter a carácter: no hay ninguna
diferencia en el contenido.

> Aclaración para evitar una lectura equivocada: `Get-ChildItem` reporta **44.506
> bytes** para ese archivo, pero son **42.630 caracteres** — la diferencia son los
> acentos en UTF-8 (2 bytes cada uno). No es una versión distinta.

Esto significa que **el desfase no es entre el repo y n8n, sino entre el prompt
(y su archivo) y la TABLA**. Los dos prompts (archivo y vivo) están igual de
desactualizados.

---

## 6. LIMPIEZA Y EFECTOS SECUNDARIOS DE ESTA AUDITORÍA

- **No se modificó la tabla** `barber_conocimiento` (58 filas antes y después,
  verificado tras los intentos de inyección).
- **No se modificó el prompt ni ningún workflow.** El workflow se leyó por API
  (`GET`), nunca con `PUT`.
- **No se creó ninguna cita** en Google Calendar: `SELECT … FROM barber_citas
  WHERE jid LIKE '%5214501111805%'` → **0 filas**. Total de citas sin cambios
  (213).
- **0 escalaciones** generadas: `SELECT * FROM barber_escalaciones` → **vacío**.
  (El bot respondió "déjame confirmarlo con el encargado" *sin* ejecutar la
  herramienta en los casos de wifi y factura — no dejó rastro.)
- **No se dejó ninguna fila de prueba.** No hice ningún INSERT.
- **`barber_pausas` = 0 filas**, `barber_operadores` con los 2 JID del dueño
  activos, sin cambios.
- **Sí hubo un efecto esperado y no destructivo:** los 16 mensajes de prueba
  quedaron en `n8n_chat_histories` bajo el JID de pruebas
  `5214501111805@s.whatsapp.net` (que ya tenía 784 y es el JID de pruebas
  designado en el contexto). No lo purgo porque borrar memoria no me lo pidió
  la misión y alteraría el estado de pruebas de otros subagentes.

---

## 7. RESUMEN DE ACCIONES RECOMENDADAS (para el dueño / siguiente agente)

Por orden de impacto (esto es recomendación, **no se ejecutó nada**):

1. **Sincronizar el prompt DESDE la tabla** en los 12 puntos del hallazgo 1.
   Es lo que arregla wifi, factura, redes, formas de pago y la tolerancia de
   15→10 minutos de golpe.
2. **Borrar del prompt** la línea "¿Cobran si no llego a mi cita?" (hallazgo 2).
3. **Decidir sobre las 5 `propuesta`** (sección 3.A) y las nuevas de la 3.C.
4. **Conectar (o no) `barber_buscar_conocimiento` al agente.** Si se conecta,
   **antes** hay que arreglar el ranking de precios del hallazgo 3 (añadir FAQ
   de precio para mascarilla, peinado y planchado; subir el peso del nombre del
   servicio frente a "cuánto cuesta").
5. **Prohibir explícitamente en el prompt** que el bot afirme que hace estilos
   personalizados o que niegue descuentos por su cuenta (hallazgo 5).
6. Limpiar los sinónimos redundantes y decidir si se fusionan los 4 duplicados
   exactos (hallazgo 7) — mejora de calidad, no urgente.
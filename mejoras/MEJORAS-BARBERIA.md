# Mejoras por hacer e implementar — Agente WhatsApp "Barber Chinos"

**Documento de trabajo.** Reúne todas las funcionalidades óptimas para el barbero/dueño,
la forma de manejar mejor a los clientes, la priorización y los hallazgos técnicos.

- **Negocio:** Barber Chinos — Peluquería & Barbería · Calle Pinzón #574 · 452-281-8144
- **Stack actual:** n8n (webhook ← Evolution API) → AI Agent (Uncensored AI) → Google Calendar + Google Sheets + Postgres
- **Workflows:** `barberiaAgenteUncensored` (conversación) y `barberiaRecordatorios` (avisos)
- **Base del análisis:** lectura de los dos JSON, `prompt-sistema-agente-barberia.txt`,
  la hoja `Citas barbería` y `features-roadmap-research.md`

> **Estado:** documento de propuesta. No se ha modificado ningún workflow, prompt ni hoja.

---

## Índice

1. [Punto de partida: qué ya existe](#1-punto-de-partida-qué-ya-existe)
2. [Los 5 huecos que hoy cuestan dinero o tiempo](#2-los-5-huecos-que-hoy-cuestan-dinero-o-tiempo)
3. [Módulo A — El barbero manda por WhatsApp (comandos)](#3-módulo-a--el-barbero-manda-por-whatsapp-comandos)
4. [Módulo B — CRM de clientes](#4-módulo-b--crm-de-clientes)
5. [Módulo C — Ciclo de vida de la cita y confirmaciones](#5-módulo-c--ciclo-de-vida-de-la-cita-y-confirmaciones)
6. [Módulo D — Escalaciones con SLA y handoff](#6-módulo-d--escalaciones-con-sla-y-handoff)
7. [Módulo E — Dinero y KPIs](#7-módulo-e--dinero-y-kpis)
8. [Módulo F — Control operativo de la agenda](#8-módulo-f--control-operativo-de-la-agenda)
9. [Módulo G — Confiabilidad y anti-abuso](#9-módulo-g--confiabilidad-y-anti-abuso)
10. [Cómo manejar mejor a los usuarios (reglas concretas)](#10-cómo-manejar-mejor-a-los-usuarios-reglas-concretas)
11. [Priorización por fases](#11-priorización-por-fases)
12. [Hallazgos técnicos y deuda a resolver](#12-hallazgos-técnicos-y-deuda-a-resolver)
13. [Decisiones de negocio pendientes](#13-decisiones-de-negocio-pendientes)
14. [Criterios de aceptación y verificación](#14-criterios-de-aceptación-y-verificación)
15. [Mapa de implementación (nodos, tablas, scripts)](#15-mapa-de-implementación-nodos-tablas-scripts)
16. [Fuentes](#16-fuentes)

---

## 1. Punto de partida: qué ya existe

| Ya existe | Qué le llega al barbero / al cliente |
|---|---|
| Tool `Notificar al encargado` (flujo 1) | WhatsApp a `5215520894522` cuando el cliente pide descuento, queja, algo fuera de catálogo o "hablar con una persona" |
| Nodo `Notificar cita nueva al encargado` (flujo 2) | WhatsApp con cliente / servicio / precio / hora en **cada fila nueva** de la hoja |
| Recordatorios a 24 h y 1 h | Se envían al cliente; el texto pide "responde SI / NO" |
| Hoja `Citas barbería` | 8 columnas: `ID, Estatus, Nombre, Servicio, Precio del servicio, Día , Hora, Numero celular` (+ `Execution ID` que agrega el flujo 2) |
| Memoria de chat en Postgres | Conversación por `remoteJid` |
| Tools de Calendar | `Consultar agenda`, `Agendar cita`, `Cancelar cita`, `Reagendar` |
| Prompt con reglas de oro | "Actúa, no anuncies", precios reales, duraciones, margen de 10 min |

**Lo que el barbero recibe hoy:** un WhatsApp por cita nueva, un WhatsApp cuando algo se sale
de alcance, y acceso manual a Google Calendar y a la hoja.

**Lo que el barbero NO puede hacer hoy:** preguntarle nada al sistema, bloquear horarios,
pausar el bot, consultar el historial de un cliente o ver un resumen del día.

---

## 2. Los 5 huecos que hoy cuestan dinero o tiempo

1. **No hay ficha de cliente.** La identidad es el JID de WhatsApp. No existe historial,
   conteo de visitas, no-shows ni preferencias. La frase "es un cliente frecuente" del
   prompt es aspiracional: no hay de dónde leerla.
2. **Las confirmaciones no se guardan.** El recordatorio pide "SI/NO" pero nada persiste
   la respuesta ni hay tool para marcarla. El "SI" entra al agente como mensaje suelto y
   el `Estatus` de la hoja nunca cambia.
3. **La agenda bloquea la barbería completa.** Un solo calendario (`BARBER`): una cita
   ocupa las 2 sillas.
4. **La escalación es de un solo sentido.** Se avisa, pero no se pausa el bot para ese
   cliente, no se registra el motivo y no se sabe si se resolvió.
5. **Los KPIs están contaminados.** El agente hace *append* de una fila por acción; un
   reagendado escribe 2 filas y hay un caso histórico de 4 citas duplicadas por 5
   tool-calls idénticos. Contar "citas del mes" desde esa hoja hoy da un número inflado.

---

## 3. Módulo A — El barbero manda por WhatsApp (comandos)

Hoy el bot solo le escribe; él no puede preguntarle nada. Es lo de mayor impacto inmediato
y lo más barato: se implementa con un `Switch` sobre el texto entrante **antes** del AI
Agent, cuando el `remoteJid` es el del dueño. **No pasa por el modelo** (sin costo de tokens).

| Comando | Respuesta que recibe | Fuente |
|---|---|---|
| `HOY` | Agenda del día: hora, cliente, servicio, precio, teléfono + total estimado y huecos libres | Calendar + hoja |
| `MAÑANA` / `SEMANA` | Misma vista por rango | Calendar |
| `LIBRE` | Huecos disponibles de hoy/mañana, según duraciones reales | Calendar + tabla de servicios |
| `CLIENTE 452…` | Ficha: nombre, visitas, último servicio, no-shows, notas, próximas citas | Postgres (Módulo B) |
| `BLOQUEAR 14:00-15:30 comida` | Crea evento *busy* en Calendar para que el bot no ofrezca ese hueco | Calendar |
| `CERRAR 24 dic` / `ABRIR` | Blackout por día completo (festivos, vacaciones) | Calendar / tabla de feriados |
| `PRECIO ceja 40` | Actualiza precio y duración en la fuente única | Postgres / Sheets |
| `PAUSA 452… 2h` / `PAUSA 452… 24h` | El bot deja de contestarle a ese cliente; se le avisa que el barbero toma la conversación | Postgres + Switch |
| `ESTADO` | "Bot activo, 3 escalaciones sin cerrar, última ejecución OK hace 4 min" | n8n + Postgres |
| `COMANDOS` | Menú corto de todo lo anterior | — |

**Por qué primero esto:** cero dependencia de Meta, cero costo de modelo, y le da control
real sobre la operación desde el teléfono. `BLOQUEAR` y `PAUSA` son la válvula de escape
que hoy no existe cuando el bot se equivoca.

**Consideraciones de diseño**

- Autorización: comparar `remoteJid` contra una lista de números autorizados (tabla
  `operadores`), no contra un número fijo en el JSON.
- Semántica de comando: el primer token en mayúsculas y con whitelist estricta; cualquier
  otra cosa del dueño se trata como conversación normal (por si él escribe como cliente).
- Respuesta breve, formato WhatsApp (`*texto*`, no `**texto**`), y sin exponer IDs técnicos.
- `BLOQUEAR` y `CERRAR` deben ser visibles para el prompt del agente (sección dinámica de
  horario/bloqueos) para que no ofrezca esos huecos.

---

## 4. Módulo B — CRM de clientes

Esto es lo que habilita "manejar mejor a los usuarios". Fuente única sugerida: tabla en
Postgres (`clientes`), con la hoja como espejo legible.

```
clientes(
  jid PK, nombre, telefono, primera_visita, visitas, ultima_visita,
  ticket_promedio, no_shows, cancelaciones_tardias,
  servicio_habitual, barbero_preferido, nota_interna,
  fecha_nacimiento, marketing_ok bool, etiqueta, creado_en
)
```

### Funciones que habilita, ordenadas por utilidad real

1. **Ficha con contexto en cada escalación.** Cuando el agente escala, el aviso ya no es
   "un cliente pide descuento": es "**Juan Pérez, 14 visitas, $2,100 histórico, 0 faltas,
   pide descuento en corte $150**". Es la diferencia entre decidir en 3 segundos y no decidir.
2. **Saludo con memoria real.** "Bienvenido de vuelta, Juan. ¿Otra vez el desvanecido con
   Héctor?" — usando datos, no adivinando (el prompt ya prohíbe inventar; hoy simplemente
   no tiene la tabla).
3. **Conteo de no-shows y regla de negocio.** 3 faltas ⇒ anticipo obligatorio, o recordatorio
   extra a las 2 h. Sin medir, no se gestiona.
4. **Segmentos para tratar distinto:**
   - **Nuevo** → bienvenida, aviso de privacidad LFPDPPP, dirección y qué esperar.
   - **Frecuente / VIP** (≥6 visitas o ≥$1,000 histórico) → prioridad en lista de espera,
     hueco preferente, atención del barbero habitual.
   - **En riesgo** (sin visita >45 días) → campaña de reactivación con su servicio habitual.
   - **Problemático** (≥2 faltas) → confirmación obligatoria y depósito.
   - **Solo consulta** (nunca agendó) → secuencia corta de "¿te aparto?" una sola vez.
5. **Reactivación personalizada a 3–4 semanas** ("tu último corte fue el 12 de abril, ¿te
   aparto el mismo horario?"). Solo necesita el CRM y es de las campañas con mejor retorno.
6. **Notas internas visibles al barbero**: "viene con su hijo", "prefiere máquina del 1",
   "alérgico a X". Se escriben con `CLIENTE … NOTA …`.
7. **Cumpleaños y referidos** (mes 3, cuando lo anterior ya esté midiendo).
8. **Consentimiento y opt-out**: `marketing_ok` + comando `BAJA` del cliente, con filtro en
   toda campaña. Es requisito legal y de Meta, no un extra.

### Reglas de datos

- El teléfono (JID) es la llave primaria de identidad.
- Un cliente nunca se borra: se marca `etiqueta = 'inactivo'`.
- El `nombre` se toma de `pushName` solo la primera vez y se puede corregir cuando el
  cliente lo dice o el barbero lo edita.
- `visitas`, `no_shows` y `ticket_promedio` se derivan del ciclo de vida (Módulo C), no se
  capturan a mano.

---

## 5. Módulo C — Ciclo de vida de la cita y confirmaciones

Hoy el `Estatus` de la hoja es un texto libre que el modelo elige. Debe ser una máquina de
estados cerrada:

```
agendado → confirmado → atendido
         ├→ no_show      (nadie marcó nada; se cierra por defecto)
         ├→ cancelado    (con antelación → a lista de espera)
         └→ reprogramado (genera par de filas enlazadas)
```

### Consecuencias buenas

- El recordatorio de 24 h con respuesta **SI / NO / Mover** actualiza `estado_cita`; el
  barbero ve en `HOY` quién falta por confirmar.
- Si a T−1 h no respondió ⇒ alerta de "riesgo" al barbero y liberación del hueco a lista
  de espera.
- Un job nocturno marca `no_show` a lo que quedó en `agendado` ⇒ **porcentaje real de
  faltas**, base de todos los KPIs.
- `atendido` lo marca el barbero con un comando (`OK 3`) o desde la hoja.

### Bug relacionado que hay que corregir en el mismo cambio

El prompt (PROCESO C) registra `Estatus: cancelado`, pero el `Switch` del flujo de
recordatorios solo reconoce `agendado` y `eliminado`. Las cancelaciones caen al output
"Otro" y **el recordatorio nunca se elimina**: el cliente cancelado sigue recibiendo avisos
de una cita que ya no existe. Hay que aceptar ambos valores (`cancelado` y `eliminado`) o
unificar el vocabulario.

### Puntos técnicos

- Preservar la fila de auditoría (append) **y** mantener una vista de estado actual
  (una fila por cita, `operation: appendOrUpdate` por `ID`).
- El par de filas de un reagendado debe quedar enlazado (`ID` igual, `Estatus` distinto).
- Toda escritura de estado debe ser idempotente: reintentar no debe duplicar el evento.

---

## 6. Módulo D — Escalaciones con SLA y handoff

1. **Registrar la escalación** en tabla (`jid, motivo, resumen, ts, estado, resolucion`).
   Hoy es un WhatsApp que se pierde en el chat.
2. **Pausa automática del bot** por 24 h para ese `jid` cuando escala a humano: evita que
   el bot y el barbero contesten a la vez.
3. **Aviso al barbero si nadie cierra la escalación en 30 min** y una lista `PENDIENTES`
   con las abiertas.
4. **Motivos tipificados** (descuento, queja, servicio inexistente, precio no listado, error
   del sistema) para detectar el problema #1 del mes.
5. **Cierre con comando** (`CERRAR 12 con 10%`) → guarda resolución y, opcionalmente, la
   aplica.
6. **Mensaje al cliente durante la pausa**: "Ya avisé al barbero, en un momento te escribe."
   Nunca dejarlo en silencio.

---

## 7. Módulo E — Dinero y KPIs

| Métrica | Cómo se calcula | Uso |
|---|---|---|
| Ingreso del día / semana / mes | suma `Precio` de citas `atendido` | Corte de caja |
| Ticket promedio | ingreso / citas atendidas | Saber si el upsell funciona |
| Ocupación por hora | minutos vendidos / minutos de horario | Detectar horas muertas |
| **% no-show** | `no_show` / total | Meta: bajar de ~20 % a <8 % |
| Cancelaciones tardías | canceladas <24 h | Decidir depósito |
| Top servicios e ingresos por servicio | agrupación | Qué promocionar y qué subir de precio |
| Nuevos vs recurrentes | `visitas = 1` vs >1 | Mide si el bot trae clientes o solo reordena |
| Huecos perdidos | slots libres al cierre | Cuantifica el costo de no tener waitlist |
| Escalaciones sin cerrar / errores del bot | tablas de auditoría | Salud operativa |

### Entrega recomendada

- **WhatsApp nocturno a las 20:30:** "Hoy: 11 citas, $1,850, 1 falta. Mañana libres: 12, 15
  y 18 h."
- **Dominio matutino a las 8:00:** agenda del día con nombre, servicio y hora por cita.

Ambos son puro cron + consulta: no tocan la lógica del agente.

### Panel opcional (mes 2+)

Vista de solo lectura (Looker Studio o Metabase) sobre Postgres con los KPIs anteriores.
No requiere exponer la base fuera de la red local.

---

## 8. Módulo F — Control operativo de la agenda

1. **Lista de espera**: al cancelar, ofrecer el hueco al siguiente cliente compatible
   (mismo servicio/duración) y rellenar solo. Ingreso recuperado sin gasto de publicidad.
2. **Multi-barbero / 2 sillas**: hoy una cita bloquea todo el negocio. Un calendario por
   barbero (o `attendee`) + `freebusy` sobre ambos. Es la limitación estructural más grande
   del sistema actual.
3. **Bloqueos, festivos y vacaciones** (Módulo A) consultados antes de ofrecer cualquier
   hueco.
4. **Margen por servicio configurable** (hoy son 10 min fijos): barba puede necesitar 5,
   corte de dama 15.
5. **Anticipos** para clientes con 3+ faltas (mes 3; requiere Mercado Pago / Stripe y
   webhook de confirmación).
6. **Upsell medido**: ofrecer ceja ($30) o mascarilla ($50) al cerrar un corte y ver en el
   KPI si sube el ticket. El prompt ya tiene el combo corte + barba $250 / 60 min; conviene
   que el agente lo ofrezca en el camino corto.

---

## 9. Módulo G — Confiabilidad y anti-abuso

- **Rate limit por número** y debounce de ráfagas: hay un caso documentado de un webhook
  n8n + Evolution que se auto-disparó y terminó con el número de WhatsApp baneado.
- **Idempotencia anti doble-reserva**: llave `hash(telefono + fecha + hora + servicio)`
  consultada antes de insertar (origen: 5 tool-calls idénticas ⇒ 4 citas duplicadas).
- **Re-verificación del hueco justo antes de crear** (race condition entre dos clientes).
- **Alertas al dueño** cuando: el workflow falla 3 veces seguidas, el bot deja de responder,
  o Evolution queda desconectado. Hoy nadie se enteraría hasta que un cliente se queje.
- **Auditoría** de cada tool-call (`ts, jid, intención, tool, args, resultado`) para
  responder "¿qué hizo el bot ayer y por qué?".
- **Circuit breaker**: cortar el agente tras fallos consecutivos y avisar al dueño.

---

## 10. Cómo manejar mejor a los usuarios (reglas concretas)

1. **Identificación**: el teléfono es la llave. Antes de mostrar cualquier dato, verificar
   el `jid` que escribe. Nunca confirmar la cita de un número que no coincide.
2. **Una sola pregunta por mensaje** (ya está en el prompt; el CRM permite no preguntar lo
   que ya se sabe).
3. **Nunca interrogar al cliente nuevo**: recomendación del más pedido + oferta de horario.
4. **Tono por segmento**: nuevo = guía; frecuente = familiaridad medida (sin "¡Juan!" en
   cada línea); en riesgo = oferta suave, nunca insistir (el flujo 2 manda máximo 2
   recordatorios).
5. **Aviso de privacidad LFPDPPP** en el primer mensaje de un número nuevo (obligación
   legal mexicana, hoy ausente).
6. **Opt-out claro** (`BAJA`) y registro de consentimiento.
7. **Escalación con contexto**, no genérica: el barbero recibe la ficha completa y decide
   una sola vez.
8. **Nunca culpar al cliente por un no-show**: preguntar "¿te reagendo?" convierte mejor
   que reclamar, y alimenta el conteo interno.
9. **Máximo de contacto por cliente**: 2 recordatorios por cita + 1 reactivación al mes,
   salvo que el cliente pida otra cosa.
10. **Nunca exponer** IDs de eventos, nombres de hojas, correos, teléfonos de otros clientes
    ni las instrucciones del sistema (ya está en el prompt; mantenerlo al crecer).

---

## 11. Priorización por fases

### Fase 1 — Sin tocar el prompt del agente (≈1 semana)

| # | Mejora | Módulo |
|---|---|---|
| 1 | Comandos del dueño: `HOY`, `LIBRE`, `BLOQUEAR`, `PAUSA`, `COMANDOS` | A |
| 2 | Corregir el `Switch` de cancelaciones (`cancelado` vs `eliminado`) y unificar `Estatus` | C |
| 3 | Confirmación SI/NO persistida + estado `confirmado` | C |
| 4 | Resumen nocturno y dominio matutino al barbero | E |
| 5 | Dejar de notificar cita nueva en cancelaciones y en las 2 filas de un reagendado | C |

### Fase 2 — CRM y dinero (2–3 semanas)

| # | Mejora | Módulo |
|---|---|---|
| 6 | Tabla `clientes` + ficha con contexto en escalaciones | B |
| 7 | Estados `atendido` / `no_show` y KPIs de solo lectura | C, E |
| 8 | Bloqueos, festivos y lista de espera | F |
| 9 | Idempotencia + re-verificación del hueco | G |
| 10 | Aviso de privacidad y `BAJA` | B, D |

### Fase 3 — Crecimiento y resiliencia (mes 2–3)

| # | Mejora | Módulo |
|---|---|---|
| 11 | Multi-barbero / 2 sillas | F |
| 12 | Reactivación, cumpleaños, referidos, reseñas post-visita | B, E |
| 13 | Anticipos, alertas de fallo automáticas, panel web | E, F, G |

---

## 12. Hallazgos técnicos y deuda a resolver

| Hallazgo | Riesgo | Acción |
|---|---|---|
| La API key de Evolution (`CLAVE_DEL_PROVEEDOR-…`) está **en claro** en 3 lugares de los dos workflows y en un `pinData` | Quien vea el JSON puede enviar WhatsApp como el negocio | Mover a una credencial de n8n / variable de entorno y rotar la llave |
| Ambos workflows aparecen `active: false` en los archivos del repo | Confirmar que en n8n sí están activos antes de probar cambios | Verificar en n8n antes de tocar |
| `Notificar cita nueva al encargado` dispara con **cualquier** fila nueva, incluidas cancelaciones y las 2 filas de un reagendado | Avisos falsos al barbero | Filtrar por `Estatus = agendado` |
| La hoja se usa como append por acción, sin `Estatus` normalizado | KPIs inflados; un reagendado cuenta doble | Máquina de estados (Módulo C) |
| El prompt en el JSON se ve con mojibake al leerse con codificación heredada, pero **los bytes en disco están correctos** (verificado: 0 ocurrencias reales) | Falsa alarma | No "arreglar" lo que no está roto |
| Sin rate limit ni cap diario de ejecuciones | Baneo del número (caso documentado) | Rate limit por `jid` + debounce |
| Escalación sin registro ni cierre | Casos que se pierden | Módulo D |
| Un solo calendario para toda la barbería | Una cita bloquea las 2 sillas | Módulo F |

---

## 13. Decisiones de negocio pendientes

1. ¿El "dueño" que recibe comandos y el "barbero" del sillón son la misma persona?
   (Hoy todo apunta al mismo número.)
2. ¿Cuántas sillas / barberos activos y quién atiende qué? (Define multi-calendario.)
3. ¿Precios de depilación por zona, para sacarlos del prompt y ponerlos en tabla?
4. ¿Política de no-show y si acepta anticipo en algún caso?
5. ¿Quiere que el bot lo notifique por **cada** cita o solo en el resumen diario?
   (Hoy es por cada una.)
6. ¿Horario de vacaciones / festivos del año en curso?
7. ¿Qué porcentaje de descuento está autorizado a ofrecer sin consultarlo?
8. ¿Se quiere atender inglés o solo español?

---

## 14. Criterios de aceptación y verificación

Cada mejora debe entregarse con:

- **Disparador** explícito (comando, cron, evento, tool-call).
- **Datos que usa** (tablas, calendario, hoja).
- **Salida exacta** (texto al barbero o al cliente, filas escritas).
- **Métrica que mueve** (no-show, ticket, ocupación, tiempo de respuesta).
- **Prueba automática** que falle si se rompe, siguiendo el patrón ya usado en el repo:
  - `verify.py` — estructura del workflow (nodos, conexiones, expresiones `$('Nodo')`,
    precios en el prompt, zona horaria).
  - `test-code-node.js` — comportamiento del `Code` de recordatorios.
  - `test-agente-e2e.js` — conversaciones reales contra el modelo.

### Casos de prueba obligatorios para lo nuevo

| Caso | Resultado esperado |
|---|---|
| El dueño manda `HOY` a las 12:00 | Lista de citas del día + total, sin pasar por el LLM |
| El dueño manda `BLOQUEAR 14:00-15:30` | El bot ya no ofrece ese rango y `LIBRE` lo refleja |
| Cliente cancela antes del recordatorio de 24 h | No recibe ningún recordatorio; el hueco va a lista de espera |
| Cliente responde `SI` al recordatorio | `estado_cita = confirmado`; aparece en `HOY` como confirmada |
| Cita pasa sin respuesta ni asistencia | Job nocturno marca `no_show`; el KPI sube 1 |
| Quien escribe no es el dueño y manda `HOY` | Se trata como conversación normal, sin ejecutar el comando |
| Dos clientes piden el mismo hueco a la vez | El segundo recibe alternativas; nunca hay dos eventos iguales |
| El webhook recibe una ráfaga del mismo `jid` | Se descarta por rate limit; no se banea el número |

---

## 15. Mapa de implementación (nodos, tablas, scripts)

### Nodos nuevos en `barberiaAgenteUncensored`

| Nodo | Tipo | Posición | Propósito |
|---|---|---|---|
| `¿Es operador?` | `if` | después de `Normalizacion`, antes de `Switch` | Separar comandos del dueño de conversación de cliente |
| `Router de comandos` | `switch` | tras `¿Es operador?` | Un output por comando de la whitelist |
| `HOY` / `LIBRE` | `googleCalendar` + `postgres` + `set` | tras el router | Armar la agenda y los huecos |
| `Responder al operador` | `httpRequest` (Evolution `sendText`) | cierre del router | Enviar la respuesta del comando |
| `Tool: Ficha de cliente` | `postgresTool` | conectado a `AI Agent` | Que el agente lea el CRM |
| `Tool: Registrar escalación` | `toolHttpRequest` | conectado a `AI Agent` | Persistir y pausar |

### Nodos nuevos en `barberiaRecordatorios`

| Nodo | Tipo | Propósito |
|---|---|---|
| `Filtrar por Estatus` | `if` | Solo notificar citas `agendado`; aceptar `cancelado` y `eliminado` para quitar el recordatorio |
| `Job nocturno no-show` | `scheduleTrigger` + `postgres` | Cerrar el día y calcular KPIs |
| `Resumen nocturno` | `scheduleTrigger` + `postgres` + `httpRequest` | WhatsApp de cierre al barbero |
| `Dominio matutino` | `scheduleTrigger` + `googleCalendar` + `httpRequest` | Agenda del día a las 8:00 |

### Tablas Postgres sugeridas

- `clientes` — ficha y segmentación (Módulo B).
- `citas` — estado actual de cada cita (una fila por evento, llave = ID de Calendar).
- `escalaciones` — motivo, resumen, estado, resolución, SLA.
- `operadores` — números autorizados y su rol.
- `bloqueos` — festivos, vacaciones, bloqueos puntuales.
- `lista_espera` — `jid, servicio, duracion_min, ventana_deseada, ts`.
- `audit_log` — `ts, jid, intencion, tool, args, resultado`.
- `consentimiento` — `jid, marketing_ok, ts`.
- `pausas` — `jid, hasta, motivo`.

> Nota: n8n ya usa Postgres como base interna y como memoria de chat. Estas tablas deben
> vivir en la misma instancia para evitar un servicio adicional.

### Scripts de verificación a extender

- `verify.py`: añadir comprobaciones de los nodos nuevos, de la whitelist de comandos y de
  que la API key de Evolution ya no esté en claro.
- `test-code-node.js`: añadir casos de la máquina de estados y del job nocturno.
- `test-agente-e2e.js`: añadir casos de lectura de ficha y de escalación con contexto.

---

## 16. Fuentes

Investigación base documentada en `features-roadmap-research.md`:

- No-show en barbería/peluquería ≈ 20 %; recordatorios lo reducen 29–41 %; WhatsApp con
  botones lo baja a 5–8 %.
- ~38 % de las reservas ocurren fuera de horario de atención.
- Caso documentado: 5 tool-calls idénticas crearon 4 citas duplicadas.
- Caso documentado: webhook auto-disparado ⇒ número de WhatsApp baneado.
- Lista de espera automática: ~12 % más cancelaciones rellenadas.
- Depósito anticipado: reduce no-shows >50 %.
- LFPDPPP: obliga a informar antes de recopilar datos personales, incluido el teléfono.

URLs y numeración de citas: ver `features-roadmap-research.md` (sección *Fuentes*).

---

*Documento generado el 2026-09-25. Ninguna mejora aquí descrita está implementada todavía.*
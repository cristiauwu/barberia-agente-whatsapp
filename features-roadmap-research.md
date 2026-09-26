# Roadmap de features — Agente WhatsApp "Barber Chinos"

**Negocio:** Peluquería & Barbería "Barber Chinos" — Calle Pinzón #574, tel. 452-281-8144 (Peso Pluma, México).
**Stack actual:** n8n (webhook ← Evolution API) → AI Agent (tools de Google Calendar, logging en Google Sheets, memoria de chat en Postgres); segundo workflow envía recordatorio 1 h antes.
**Servicios (MXN):** corte desvanecido o tijera $150; arreglo de barba $100; ceja $30; mascarilla $50; corte de cabello dama $250; planchado express $150; peinado $300; depilación (precio según zona: ceja, bigote, nariz, orejas, barba, axilas, piernas).

**Hallazgos base que justifican la priorización:**
- ~19.8% de no-show en peluquerías/barberías [4f4c8e71-1]; ~10% de las citas terminan en no-show o cancelación tardía a escala global [4f4c8e71-2]; 62% de clientes cancela con menos de 24 h de aviso [d1c888bc-2].
- Recordatorios reducen no-shows 29–41%; el de 24 h es la intervención más efectiva; el depósito reduce no-shows >50%; las reservas del mismo día tienen 60% menos no-show [4f4c8e71-1].
- WhatsApp con botones interactivos de confirmar/reprogramar baja de ~20% a 5–8% de no-show [c86fc678-1].
- 38% de las reservas ocurren fuera de horario de atención [bca908c7-5].
- Caso real documentado: 5 llamadas idénticas de `Book_Appointment` en un solo turno del LLM crearon 4 citas duplicadas [0527f74c-1].
- Caso real: un webhook n8n + Evolution API que se auto-disparó envió cientos de requests por segundo y terminó en ban del número de WhatsApp [fb21e3f1-1].

---

## ALTA PRIORIDAD (semanas 1–3: evitan pérdida de dinero y errores graves)

| Feature | Por qué (fuente) | Implementación en n8n + AI Agent + GCal + Sheets + Postgres |
|---|---|---|
| **Grounding obligatorio por tool** (nunca afirmar disponibilidad o precio sin llamar una tool) | La prevención #1 de alucinaciones es forzar tool-use para toda afirmación factual [bca908c7-4] | En el system prompt del AI Agent: "prohibido responder horarios, precios o políticas sin invocar `get_available_slots` / `get_price`. Si la tool falla, escalar a humano y no responder de memoria." |
| **Confirmación explícita antes de escribir en Google Calendar** | Un resumen + "¿confirmas?" evita citas fantasma por datos mal capturados [ee020a0f-4] | Code node que arma resumen (servicio(s), barbero, fecha, hora, duración, precio total) y espera `sí/confirmar` almacenado en la memoria Postgres antes de invocar `calendar.create` |
| **Idempotencia anti doble-reserva** | 5 tool calls idénticas en un turno crearon 4 citas duplicadas [0527f74c-1] | Llave única `hash(telefono + fecha + hora + servicio)` en Postgres; el tool consulta la llave antes de insertar y, si existe, devuelve la cita ya creada en lugar de crear otra |
| **Re-verificación del slot en el momento de crear** | Evita el doble booking por carrera de concurrencia entre dos clientes | `freebusy.query` de la Google Calendar API justo antes del insert [0527f74c-3]; si el rango devuelve `busy`, el agente ofrece 2 alternativas en lugar de crear el evento |
| **Búsqueda de slots por duración real (duration-aware)** | Combinar corte + barba exige sumar duraciones ("combined visit is 55 minutes") [c86fc678-4] | Tabla `services(duracion_min)` en Postgres; el tool calcula `inicio + duración + buffer`, descarta solapes y solo devuelve slots válidos |
| **Multi-servicio en una sola cita** | Expectativa real del cliente y base del ticket promedio [c86fc678-4] | El tool `book_appointment` acepta un array `services[]`; el agente suma precios y duraciones y lo refleja en el resumen de confirmación |
| **Guardrail de horario fuera de atención** | 38% de las reservas ocurren fuera de horario [bca908c7-5]; responder "mañana te contestamos" pierde la venta [bca908c7-1] | Nodo Switch sobre `business_hours` (Google Sheets); si está cerrado, el agente sigue agendando en el próximo hueco válido y declara "te confirmo al abrir" |
| **Rate limiting / anti-spam por número** | Un webhook auto-disparado envió cientos de requests/seg y el número terminó baneado [fb21e3f1-1] | Code node con contador en Postgres (`mensajes/min por jid`); si supera el umbral ⇒ ignorar el mensaje y registrar; debounce de ráfagas de eventos [0527f74c-4] |
| **Límite de negociación de precio** | El agente no debe improvisar descuentos ni políticas [bca908c7-4] | Precios en tabla Postgres como fuente única; prompt: "si piden descuento, responde que el precio es fijo y ofrece el combo corte + ceja" |
| **Handoff a humano con contexto** | El 10–25% de los casos requieren juicio humano y la transferencia debe capturar datos antes de pasar [d437ae6f-2][d437ae6f-4] | Tool `escalate_to_human` ⇒ escribe fila en la hoja "Escalaciones" + notifica al dueño por WhatsApp y pausa el agente para ese `jid` durante 24 h |
| **Logging y auditoría de cada acción** | La trazabilidad completa es un requisito de audit trail para agentes [cdeaff3e-2] | Tabla Postgres `audit_log(ts, jid, intent, tool, args, result)`; cada tool escribe antes y después de ejecutarse |
| **Recordatorio T-24 h y T-1 h con botón "Confirmar"** | El recordatorio del día antes es la intervención más efectiva; los botones bajan el no-show a 5–8% [4f4c8e71-1][c86fc678-1] | Segundo workflow: Cron → busca citas en Postgres a T-24 h y T-1 h → Evolution `sendButtons` con `confirmar / reprogramar / cancelar` |

## MEDIA PRIORIDAD (mes 1–2: ingresos y retención)

| Feature | Por qué (fuente) | Implementación en n8n + AI Agent + GCal + Sheets + Postgres |
|---|---|---|
| **Flujo "confirmar asistencia" con respuesta obligatoria** | Obliga a decidir y evita el "ghosting" por vergüenza de cancelar [4f4c8e71-3] | Webhook de respuesta del botón ⇒ actualiza `estado_cita` en Postgres; si no hay respuesta a T-1 h ⇒ marcar "riesgo" y avisar al barbero |
| **Waitlist / relleno de cancelaciones** | GlossGenius reporta 12% más cancelaciones rellenadas con waitlist automática [d437ae6f-3] | Workflow plantilla de waitlist: al detectar cancelación, consulta la hoja `ListaEspera` y ofrece el slot al primero que responda "sí" [20406650-1] |
| **Upsell / cross-sell al agendar** | Los add-ons funcionan en el momento exacto: tras elegir servicio, antes de confirmar [15d289ff-4] | Reglas en la hoja `addons_por_servicio` (corte ⇒ ceja $30 o mascarilla $50); el agente ofrece una sola vez, sin insistir |
| **Reagendado sin fricción** | "I'm running late, can I move my cut?" es un flujo esperado del cliente [c86fc678-4] | Tool `reschedule` = delete + create con la misma llave de idempotencia; solo el dueño del `jid` puede mover su propia cita |
| **Re-engagement / win-back** | Campañas segmentadas por historial de visitas cuyas respuestas el AI agenda [2bf8a14a-1] | Cron semanal: query en Postgres de clientes sin visita en >45 días → plantilla utility aprobada (fuera de la ventana de 24 h) [15d289ff-2] |
| **Selección de barbero y disponibilidad por barbero** | Los clientes piden a su barbero habitual y hay skills por sillón [c86fc678-4] | Un calendario de Google por barbero (o `attendee`); el tool filtra por `barbero_id` antes de ofrecer slots |
| **Capacidad en paralelo (2 sillones)** | Sin esto el bot bloquea la barbería entera con una sola cita | `freebusy` sobre ambos calendarios; el slot es válido si al menos un barbero está libre [0527f74c-3] |
| **Buffer entre citas** | Limpieza de 15 min es el setup estándar de un salón [2bf8a14a-2] | Campo `buffer_min` por servicio en Postgres, sumado al final del evento antes de buscar el siguiente hueco |
| **Horario, feriados y blackout dates** | El calendario debe detectar conflictos de forma inteligente [fb21e3f1-3] | Constraint único en Postgres + lista de feriados/blackout en Google Sheets consultada antes de ofrecer slots |
| **Aviso inmediato al dueño de nueva reserva** | Visibilidad operativa en tiempo real | Nodo Evolution `sendText` al número del dueño disparado desde el tool `book_appointment` |
| **Resumen diario de agenda al dueño/barbero** | El briefing diario para dueños es una categoría de producto consolidada [4bbec209-2] | Cron 07:00: lee la agenda del día en Google Calendar ⇒ WhatsApp al dueño con conteo de citas, ingresos estimados y huecos libres |
| **Recordatorios pre-cita con instrucciones** | Las confirmaciones deben incluir preparación, dirección y contexto [d437ae6f-3] | Plantilla con nombre, hora, servicio, Calle Pinzón #574 y botón de ubicación/mapa |
| **Opt-out de marketing** | Meta exige opt-in explícito y una vía de salida fácil [d855c1d9-3][20406650-3] | Tabla `consent(jid, marketing_bool, ts)`; comando "BAJA" ⇒ flag `false` y filtro aplicado a todas las campañas |
| **Aviso de privacidad LFPDPPP** | La ley mexicana obliga a informar antes de recopilar datos, incluido el teléfono y los hábitos de consumo [d1c888bc-1] | El primer mensaje de un número nuevo envía un aviso corto con finalidades y link; la aceptación se registra en Google Sheets |

## BAJA PRIORIDAD (mes 3+: crecimiento y madurez)

| Feature | Por qué (fuente) | Implementación en n8n + AI Agent + GCal + Sheets + Postgres |
|---|---|---|
| **Depósito anticipado** | Reduce no-shows >50% en todas las industrias estudiadas [4f4c8e71-1] | Requiere pasarela (Mercado Pago / Stripe); el bot envía el link y espera el webhook de pago antes de crear el evento en Calendar |
| **Política de no-show y tarjeta en archivo** | Requerir tarjeta/depósito y comunicar la política en confirmaciones y recordatorios [d437ae6f-3] | Hoja `no_shows` en Google Sheets + regla de negocio "3 faltas ⇒ requiere anticipo obligatorio" |
| **Seguimiento de no-shows y KPIs** | Sin tasa de no-show medida no se puede gestionar el problema [4f4c8e71-1] | Cron mensual → dashboard en Looker Studio/Metabase sobre Postgres: no-show %, ticket promedio y ocupación por sillón |
| **Solicitud de reseña post-visita** | Retención y adquisición de nuevos clientes | Cron T+2 h después de la cita: link a Google Maps con mensaje personalizado |
| **Programa de referidos** | Lealtad digital + referidos es un módulo estándar de los salones [f50e732e-1] | Código único por cliente en Postgres; al usarse, registrar el crédito correspondiente en Sheets |
| **CRM / lealtad y ofertas de cumpleaños** | Las campañas de cumpleaños y reactivación son features de retención consolidadas [2bf8a14a-1] | Campo `fecha_nacimiento` en Google Sheets; cron mensual envía cupón de cumpleaños |
| **Tolerancia a typos, jerga y notas de voz** | Clientes reales escriben "ktal el corte", "corte d desvanecido" | Prompt con lista de sinónimos y abreviaturas + nodo de transcripción para notas de voz [bca908c7-1] |
| **Detección de idioma** | Validar el idioma es un guardrail de entrada de primer nivel [bca908c7-4] | Instrucción explícita de responder en el idioma del cliente (es/en) y escalar si el idioma no se puede determinar |
| **Citas recurrentes** | El cliente "cada 4 semanas" no debería reagendar manualmente cada visita [fb21e3f1-3] | Campo `recurrencia` en Google Sheets; cron que genera las siguientes N ocurrencias automáticamente |
| **Auto-disable por fallos (circuit breaker)** | Cortar el agente tras fallos consecutivos y avisar al dueño [0527f74c-4] | Code node que cuenta ejecuciones fallidas consecutivas y desactiva el workflow + envía alerta por WhatsApp al dueño |

---

## Top 5 errores que cometen los bots de reserva de pequeños negocios (y su guardrail)

| # | Error | Guardrail concreto que lo previene |
|---|---|---|
| 1 | **Inventar disponibilidad o precios (alucinación)** | Prohibido afirmar cualquier dato sin llamar una tool; los precios viven solo en la tabla Postgres, nunca en el prompt [bca908c7-4] |
| 2 | **Doble reserva** — la misma cita creada varias veces, o dos clientes en el mismo slot | Idempotency key `hash(telefono+fecha+hora+servicio)` + `freebusy.query` inmediatamente antes del insert [0527f74c-1][0527f74c-3] |
| 3 | **Respuestas largas y robóticas** que el cliente no lee | Plantilla de estilo: máximo 2–3 líneas y un solo botón de acción por mensaje [bca908c7-1] |
| 4 | **Ignorar horas, feriados y días cerrados** y agendar fuera de atención | Nodo de validación de horario + tabla de feriados/blackout consultada antes de ofrecer cualquier slot [2bf8a14a-2] |
| 5 | **No saber cuándo parar** (spam, loops de webhook, re-reservas infinitas) | Rate limit por jid, debounce de ráfagas, cap diario de ejecuciones y auto-disable del workflow [0527f74c-4][fb21e3f1-1] |

---

## Fuentes

- [4f4c8e71-1] No-Show Rates by Industry: 2026 Data & Benchmarks — https://schedulingkit.com/hub/industry-guides/average-no-show-rates-by-industry
- [4f4c8e71-2] How to protect your business from no-shows and late cancellations (Fresha) — https://www.fresha.com/blog/how-to-protect-your-business-against-no-shows-and-late-cancellations
- [4f4c8e71-3] How appointment reminders can help you cut no-shows by up to 70% (Booksy) — https://biz.booksy.com/en-gb/blog/how-appointment-reminders-can-help-you-cut-no-shows-by-up-to-70-v
- [d1c888bc-2] How No-Shows Are Reshaping the Beauty Industry (Fresha cost study) — https://www.fresha.com/blog/cancellations-cost-study
- [c86fc678-1] WhatsApp appointment reminders that cut no-shows — https://landinchat.com/guides/whatsapp-appointment-reminders
- [c86fc678-4] WhatsApp Booking for Barbershops (Elily by Srileo) — https://srileo.com/for/barbershops/
- [bca908c7-1] WhatsApp AI Assistant for Salons & Barbershops (SOVA) — https://sova.my/blog/whatsapp-ai-assistant-for-salons-and-barbershops
- [bca908c7-4] Hotel AI Guardrails: Preventing Hallucinations on Policies, Rates, Inventory (CallSphere) — https://callsphere.ai/blog/hotel-ai-guardrails-preventing-hallucinations
- [bca908c7-5] Salon Booking Software — WhatsApp AI Receptionist (Intellibook AI) — https://www.intellibookai.com/salon-booking-software
- [0527f74c-1] Retell AI community: duplicate Book_Appointment tool calls in a single LLM turn — https://community.retellai.com/t/book-appointment-tool-calls-fired-in-a-single-llm-turn-after-streaming-timeout-resulted-in-multiple-appointments-booked-for-one-requested-slot/3301
- [0527f74c-3] Google Calendar API — Freebusy: query — https://developers.google.com/workspace/calendar/api/v3/reference/freebusy/query
- [0527f74c-4] AI Agent Guardrails: Debounce, Caps & Loop Safety (Macha) — https://www.getmacha.com/blog/guardrails-autonomous-agents-debounce-caps-auto-disable-loop
- [fb21e3f1-1] n8n Community: Looping webhook triggers from Evolution API — https://community.n8n.io/t/looping-webhook-triggers-in-n8n-from-evolution-api/159422/1
- [fb21e3f1-3] Salon Scheduling Software: Calendar, Online Booking & Waitlist (Perceny) — https://www.perceny.com/features/booking
- [d437ae6f-2] AI Receptionist Human Handoff Rules (Solvea) — https://solvea.cx/blog/ai-receptionist-human-handoff-rules
- [d437ae6f-3] No-Show Protection / card on file (GlossGenius) — https://glossgenius.com/no-shows-protection-card-on-file
- [d437ae6f-4] Call Transfer & Escalation Protocols: When AI Transfers to Humans (NextPhone) — https://www.getnextphone.com/blog/call-transfer-escalation-protocol
- [2bf8a14a-1] Salon Marketing: Win-Backs, Birthdays, Re-Activation (Booking Pro AI) — https://bookingpro.ai/product/campaigns/
- [2bf8a14a-2] Buffer Times (Sesami help docs) — https://help.sesami.co/booking/availability/buffer-times.md
- [15d289ff-2] The WhatsApp customer service window (Bird docs) — https://bird.com/en-gb/docs/knowledge-base/whatsapp/customer-service-window
- [15d289ff-4] Booking Add-Ons & Extras, Upsell at Booking Time (SchedulingKit) — https://schedulingkit.com/booking-add-ons
- [20406650-1] n8n template: Fill cancelled appointments from a waitlist (Sheets + Calendar + Twilio) — https://n8n.io/workflows/17957-fill-cancelled-appointments-from-a-waitlist-with-google-sheets-google-calendar-and-twilio/
- [20406650-3] WhatsApp opt-in: Policy requirements, strategy & examples (Infobip) — https://www.infobip.com/blog/how-to-collect-whatsapp-business-opt-ins
- [cdeaff3e-2] Voice Agent Call Logging: Schema, Taxonomy & Compliance (Hamming AI) — https://hamming.ai/resources/call-logging-voice-agents-taxonomy-compliance
- [d855c1d9-3] Get Opt-in for WhatsApp (Meta for Developers) — https://developers.facebook.com/docs/whatsapp/overview/getting-opt-in/
- [4bbec209-2] Owner Daily Briefing Agent — Daily AI Business Reports (OTRA) — https://otra.pro/solutions/owner-daily-briefing-agent
- [d1c888bc-1] LFPDPPP y WhatsApp: la guía legal que todo negocio mexicano necesita (Virtom) — https://virtom.mx/blog/lfpdppp-whatsapp-lo-que-tu-negocio-necesita-cumplir
- [f50e732e-1] Your New Power Duo: Digital Loyalty and Referrals (Phorest) — https://www.phorest.com/ca/updates/digital-loyalty-referrals/
- [ee020a0f-4] How to Build a Booking Chatbot (Step-by-Step Guide) — https://quantumbyte.ai/articles/how-to-build-booking-chatbot

**Nota de alcance:** no fue posible acceder a la documentación completa de Meta sobre la ventana de atención de 24 h mediante fetch directo; el detalle se tomó de resúmenes de terceros [15d289ff-2]. El envío de campañas fuera de esa ventana requiere plantillas aprobadas.
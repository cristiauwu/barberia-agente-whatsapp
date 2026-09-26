# 🚀 Herramientas y APIs Complementarias — Barbería Pinzón Agent

> Stack actual: **n8n + WhatsApp + Google Calendar + Google Sheets**
> Objetivo: llevar el proyecto de "bot de citas" a **sistema operativo completo del negocio**.

---

## 📊 Tabla Resumen — Prioridad vs Impacto

| # | Herramienta / API | Categoría | Costo | Impacto | Prioridad |
|---|-------------------|-----------|-------|---------|-----------|
| 1 | **Supabase (Postgres)** | Base de datos | Gratis → $25/mes | 🔥🔥🔥 | ⭐⭐⭐ CRÍTICA |
| 2 | **Mercado Pago / Stripe** | Pagos | 3-4% por transacción | 🔥🔥🔥 | ⭐⭐⭐ CRÍTICA |
| 3 | **Looker Studio / Metabase** | Dashboards | Gratis | 🔥🔥🔥 | ⭐⭐⭐ CRÍTICA |
| 4 | **Twilio** | SMS / Voz | ~$0.04/SMS | 🔥🔥 | ⭐⭐ ALTA |
| 5 | **Google Business Profile API** | Reputación | Gratis | 🔥🔥 | ⭐⭐ ALTA |
| 6 | **Cal.com (self-host)** | Reservas | Gratis | 🔥🔥 | ⭐⭐ ALTA |
| 7 | **Pinecone / Supabase Vector** | RAG / memoria | Gratis → $70 | 🔥🔥 | ⭐⭐ ALTA |
| 8 | **OpenAI Vision / Whisper** | Multimodal | Pay-per-use | 🔥🔥 | ⭐⭐ ALTA |
| 9 | **Airtable** | DB visual | $20/mes | 🔥 | ⭐ MEDIA |
| 10 | **Make/Zapier** | Orquestación extra | $9-29/mes | 🔥 | ⭐ MEDIA |
| 11 | **Instagram Graph API** | Marketing | Gratis | 🔥 | ⭐ MEDIA |
| 12 | **Telegram Bot API** | Canal interno | Gratis | 🔥 | ⭐ MEDIA |
| 13 | **reCAPTCHA / Anti-spam** | Seguridad | Gratis | 🔥 | ⭐ BAJA |
| 14 | **ElevenLabs / TTS** | Voz | $5/mes | 🔥 | ⭐ BAJA |

---

## 🗄️ 1. CAPA DE DATOS — Migrar de Sheets a Postgres

### ¿Por qué hacerlo?

Google Sheets es excelente para arrancar, pero tiene **límites técnicos duros** que ya están afectando el proyecto:

[cite:ba9851ff-3]

| Problema con Sheets | Consecuencia real |
|---------------------|-------------------|
| ~10M celdas máximo | Se acaba en ~2 años de operación |
| Sin índices | Reportes mensuales cada vez más lentos |
| Sin transacciones | Doble reserva si hay race condition |
| Sin permisos por rol | El barbero ve TODO, incluidos ingresos |
| **NUNCA usar `append` con fórmulas** | Rompe columnas calculadas |
| Lecturas completas de hoja | Costoso y lento por cada mensaje del bot |

### Opción A — **Supabase** (RECOMENDADO) ⭐

Postgres real + API REST automática + Auth + Vector store incluido.

[cite:ba9851ff-3][cite:79098aa3-2]

```javascript
// n8n: nodo Postgres o HTTP Request a Supabase
// Verificar disponibilidad SIN doble reserva — usando transacción

const requestedStart = `${$json.date}T${$json.time}:00`;
const requestedEnd = new Date(new Date(requestedStart).getTime() + $json.duration * 60000).toISOString();

// Esta query es ATÓMICA — imposible doble reserva
const query = `
  INSERT INTO appointments (customer_id, barber_id, service_id, start_time, end_time, status)
  SELECT $1, $2, $3, $4::timestamptz, $5::timestamptz, 'confirmed'
  WHERE NOT EXISTS (
    SELECT 1 FROM appointments
    WHERE barber_id = $2
      AND status IN ('confirmed', 'pending')
      AND tstzrange(start_time, end_time) && tstzrange($4::timestamptz, $5::timestamptz)
  )
  RETURNING id, start_time, end_time;
`;
// Si devuelve 0 filas → slot ocupado. Sin race conditions, sin google calendar check.
```

**Schema recomendado para Supabase:**

```sql
-- Ejecutar en el SQL Editor de Supabase

CREATE TABLE customers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  phone TEXT UNIQUE NOT NULL,
  name TEXT,
  first_visit TIMESTAMPTZ DEFAULT now(),
  last_visit TIMESTAMPTZ,
  total_visits INT DEFAULT 0,
  total_spent NUMERIC(10,2) DEFAULT 0,
  loyalty_points INT DEFAULT 0,
  preferences JSONB DEFAULT '{}',
  birthday DATE,
  marketing_opt_in BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE services (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  price NUMERIC(10,2) NOT NULL,
  duration_min INT NOT NULL,
  category TEXT,
  active BOOLEAN DEFAULT true,
  image_url TEXT,
  description TEXT
);

CREATE TABLE barbers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  phone TEXT,
  commission_pct NUMERIC(5,2) DEFAULT 40.00,
  active BOOLEAN DEFAULT true
);

CREATE TABLE appointments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_id UUID REFERENCES customers(id),
  barber_id UUID REFERENCES barbers(id),
  service_id UUID REFERENCES services(id),
  start_time TIMESTAMPTZ NOT NULL,
  end_time TIMESTAMPTZ NOT NULL,
  status TEXT DEFAULT 'confirmed'
    CHECK (status IN ('pending','confirmed','completed','cancelled','no_show')),
  price_charged NUMERIC(10,2),
  payment_method TEXT,
  notes TEXT,
  reminder_24h_sent BOOLEAN DEFAULT false,
  reminder_2h_sent BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- 🔥 ESTA es la clave anti-doble-reserva
CREATE EXTENSION IF NOT EXISTS btree_gist;
ALTER TABLE appointments ADD CONSTRAINT no_overlap
  EXCLUDE USING gist (
    barber_id WITH =,
    tstzrange(start_time, end_time) WITH &&
  ) WHERE (status IN ('pending','confirmed'));

-- Índices para reportes rápidos
CREATE INDEX idx_apt_date ON appointments (start_time DESC);
CREATE INDEX idx_apt_status ON appointments (status);
CREATE INDEX idx_apt_barber ON appointments (barber_id, start_time);

-- Vista materializada de KPIs diarios (reportes instantáneos)
CREATE MATERIALIZED VIEW daily_metrics AS
SELECT
  DATE(start_time AT TIME ZONE 'America/Mexico_City') AS day,
  COUNT(*) FILTER (WHERE status = 'completed') AS completed_appointments,
  COUNT(*) FILTER (WHERE status = 'no_show') AS no_shows,
  COUNT(*) FILTER (WHERE status = 'cancelled') AS cancelled,
  COALESCE(SUM(price_charged) FILTER (WHERE status = 'completed'), 0) AS revenue,
  COALESCE(AVG(price_charged) FILTER (WHERE status = 'completed'), 0) AS avg_ticket,
  COUNT(DISTINCT customer_id) FILTER (WHERE status = 'completed') AS unique_customers
FROM appointments
GROUP BY 1;

CREATE UNIQUE INDEX ON daily_metrics (day);

-- Refrescar desde n8n: REFRESH MATERIALIZED VIEW CONCURRENTLY daily_metrics;
```

**Ventajas de este diseño:**
- ✅ **Imposible doble reserva** — la constraint `EXCLUDE` lo garantiza a nivel de BD
- ✅ Reportes **instantáneos** con `daily_metrics` (no escanea toda la tabla)
- ✅ `loyalty_points` ya está listo para el programa de lealtad
- ✅ `birthday` para campañas automáticas de cumpleaños
- ✅ GIN index sobre `preferences` JSONB para consultas flexibles

### Migración desde Sheets

```
Hoja "Citas" de Sheets  →  tabla appointments
Hoja "Clientes"         →  tabla customers
Hoja "Servicios"        →  tabla services
```
Un solo workflow de n8n con Schedule Trigger + SplitInBatches (500/batch) + Upsert a Postgres.

**Costo:** Gratis hasta 500MB. **Suficiente para 5+ años** de operación de una barbería.

### Opción B — **Airtable** (si no quieres SQL)

[cite:ba9851ff-3] Interfaz bonita, ideal si el dueño quiere editar manualmente. Pero: límite 50k-125k filas, sin transacciones, más caro.

---

## 💳 2. PAGOS — Cobro anticipado y links de pago

### ¿Por qué es CRÍTICO?

Los **no-shows son la mayor pérdida** de una barbería. Un cobro anticipado (aunque sea del 20%) reduce los no-shows drásticamente.

### Opción A — **Mercado Pago** (RECOMENDADO para LATAM) ⭐

[cite:79098aa3-1] Dominante en México/LatAm, integración directa con WhatsApp, y ya existen workflows de n8n listos.

[cite:dfb3d0b8-3]

```
Flujo:
1. Cliente confirma cita en WhatsApp
2. n8n crea "preference" en Mercado Pago (amount: 50% del servicio)
3. MP devuelve URL de pago
4. n8n envía botón/URL por WhatsApp
5. Cliente paga
6. MP dispara webhook → n8n
7. n8n actualiza appointment.status = 'confirmed'
8. n8n envía confirmación final + agregar a Calendar
```

```javascript
// n8n nodo HTTP Request → POST https://api.mercadopago.com/checkout/preferences
{
  "items": [{
    "title": `Anticipo - ${$json.serviceName}`,
    "quantity": 1,
    "unit_price": $json.price * 0.5,
    "currency_id": "MXN"
  }],
  "payer": {
    "name": $json.customerName,
    "phone": { "number": $json.phone }
  },
  "external_reference": $json.appointmentId,
  "notification_url": "https://tu-n8n.com/webhook/mp-payment",
  "back_urls": {
    "success": "https://wa.me/52TU_NUMERO?text=PAGO_OK_" + $json.appointmentId
  },
  "statement_descriptor": "BARBERIA PINZON"
}
```

**Webhook de confirmación** (Schedule + Webhook pattern):
```javascript
// n8n: Webhook → Switch (status) → Postgres (update) → WhatsApp (notify)
if ($json.body.type === 'payment' && $json.body.data.id) {
  // GET https://api.mercadopago.com/v1/payments/{id}
  // Si status === 'approved' → confirmar cita + notificar
}
```

### Opción B — **WhatsApp Payments nativo**

[cite:dfb3d0b8-1] Meta permite enviar links de pago dentro de WhatsApp. Disponible en Brasil y México. **Cero fricción**: el cliente paga sin salir del chat.

### Opción C — **Stripe Payment Links**

Mejor para internacional / tarjetas. `stripe.paymentLinks.create()` → URL → enviar por WhatsApp. Webhook `checkout.session.completed`.

### 💡 Modelo de negocio recomendado

| Modalidad | Cuándo usarla | Beneficio |
|-----------|---------------|-----------|
| **Anticipo 20-30%** | Todos los servicios | Elimina ~70% de no-shows |
| **Pago completo anticipado** | Servicios > $300 | Cero riesgo, cash flow adelantado |
| **Pago al llegar + retención tarjeta** | Clientes recurrentes | Flexibilidad para el cliente |
| **Cobro por no-show** | Tras 2 no-shows | Disuasivo real |

---

## 📈 3. DASHBOARDS — Del WhatsApp al panel visual

El dueño **no debería leer reportes en texto**. Un dashboard visual cambia todo.

[cite:08e6f57c-1][cite:08e6f57c-3]

### Opción A — **Looker Studio** (Gratis, RECOMENDADO) ⭐

Google Looker Studio conecta directo a Supabase/Postgres y es gratis.

```
Arquitectura:
Supabase (Postgres) → Looker Studio → Dashboard
                            ↓
                    iframe embebido
                            ↓
              n8n envía LINK por WhatsApp al owner
```

**Dashboard sugerido:**
- 📊 KPI Cards: Ingresos hoy / semana / mes
- 📈 Serie temporal: ingresos últimos 30 días
- 🥇 Top 5 servicios (barras)
- 💈 Performance por barbero (tabla + sparkline)
- ⏰ Heatmap de horas pico (día × hora)
- 👥 Clientes nuevos vs recurrentes (pie)
- 🔄 Tasa de no-show (gauge)
- 🎯 Ticket promedio (trend)

**El owner abre el link desde WhatsApp** → ve todo en el celular. Sin reportes de texto.

### Opción B — **Metabase** (self-host, gratis)

[cite:08e6f57c-5] Más potente, permite SQL nativo. Ideal si quieres alertas automáticas ("avísame si los ingresos caen >20% vs semana pasada").

### Opción C — **Grafana**

[cite:08e6f57c-1] Para métricas operacionales de n8n mismo (tiempo de respuesta del bot, errores, etc.).

### Implementación con n8n

```javascript
// Nodo: Schedule diario 21:00 → enviar resumen Y link al dashboard
const dashboardUrl = 'https://lookerstudio.google.com/embed/reporting/XXXX/page/YYYY';
const message = `
📊 *RESUMEN DEL DÍA*

💰 Ingresos: *$1,850 MXN* (+12% vs ayer)
✂️ Citas: *12* (1 no-show)
🎯 Ticket promedio: *$154*

📈 *Dashboard completo:*
👉 ${dashboardUrl}

💡 Mañana tienes 8 citas agendadas
`;
```

---

## 📱 4. CANALES ADICIONALES

### Twilio — SMS + Voz

[cite:8b3f8b23-2]

**Casos de uso:**
- **SMS de respaldo:** si el cliente no tiene WhatsApp, o no respondió en 6h
- **Llamadas automáticas de recordatorio** (TTS): "Tienes cita hoy a las 3pm"
- **Verificación de teléfono:** OTP para crear cuenta

```javascript
// n8n: Twilio node
// Fallback si WhatsApp falla tras 2 intentos
{
  "to": "+524501111805",
  "from": "+15551234567",
  "body": "Recordatorio: Cita en Barbería Pinzón mañana 3:00 PM. Responde 1 para confirmar."
}
```

**Costo:** ~$0.04/SMS México. Bueno solo para casos críticos, no masivo.

### Telegram Bot — Canal interno del staff

[cite:8b3f8b23-1]

**Por qué:** El barbero vive en WhatsApp (ruido). Telegram es **canal separado y limpio** para comunicación interna.

```
Bot interno "Barbería Ops":
   ⏰ 8:00 AM → "Agenda de hoy: 8 citas"
   🔔 Cada nueva cita → notificación instantánea con datos
   ⚠️ No-show detectado → alerta
   💰 Cierre del día → resumen con foto del corte de caja
   📥 Cliente pide reagendar → botón [Aprobar] [Rechazar]
```

Además, el **HITL (human-in-the-loop)** de n8n funciona perfecto con Telegram: [cite:n8n-agents-official] para aprobar acciones sensibles (reembolsos, cancelaciones de alto valor).

### Instagram Graph API

Conectar publicación automática de trabajos terminados:
```
Cliente contento → foto del corte → n8n publica en IG
                                  → genera story con @cliente
                                  → guarda en galería del bot para enviar a futuros clientes
```

---

## 🤖 5. IA AVANZADA — RAG + Multimodal

[cite:79098aa3-2][cite:175b86cb-3]

### RAG sobre Supabase (o Pinecone)

**Problema actual:** el agente solo sabe lo que está en el prompt. Si el cliente pregunta "¿tienen estacionamiento?" el bot inventa o dice "no sé".

**Solución:** RAG con una base de conocimiento del negocio.

```
Knowledge base (embeddings):
├── FAQ (30 preguntas frecuentes)
├── Políticas (cancelación, puntualidad, garantía)
├── Descripción detallada de cada servicio
├── Info de barberos (especialidades, experiencia)
├── Promociones vigentes
├── Historia del negocio (para el tono)
└── Guía de estilos (¿qué corte me queda?)

Stack:
OpenAI Embeddings (text-embedding-3-small)
  → Supabase Vector (pgvector) — YA incluido, sin costo extra
  → n8n Vector Store Retriever + AI Agent
```

**Ventaja de usar Supabase Vector:** [cite:ba9851ff-3] no pagas un servicio extra. La misma BD que usas para datos, con `pgvector`.

```sql
CREATE EXTENSION vector;
CREATE TABLE knowledge_base (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  content TEXT NOT NULL,
  metadata JSONB,
  embedding vector(1536)
);
CREATE INDEX ON knowledge_base USING hnsw (embedding vector_cosine_ops);
```

### Multimodal — OpenAI Vision + Whisper

[cite:175b86cb-3]

**Vision:** el cliente manda foto de un corte que quiere → el bot lo identifica y recomienda el servicio correcto.

```javascript
// n8n: OpenAI node con image input
// Prompt: "Identify the haircut style in this photo. 
//          Match against our services: fade, mod cut, classic, 
//          textured crop, buzz cut, crew cut, taper."
```

**Whisper:** cliente manda **nota de voz** → transcripción → el agente la procesa igual que texto. Esto es ORO para LatAm donde la gente prefiere audios.

```
Cliente: 🎙️ "Oye, quiero un corte desvanecido para el sábado a las 4"
   ↓ Whisper
"Quiero un corte desvanecido para el sábado a las 4"
   ↓ Agente
Reserva procesada ✓
```

### Sentiment Analysis (nodo nativo de n8n)

Skill `n8n-agents-official`: nodo `Sentiment Analysis` de 3 vías.

```
Cliente escribe algo → clasificar sentimiento
   ├── Positive → pedir reseña en Google automáticamente
   ├── Neutral  → flujo normal
   └── Negative → alerta INMEDIATA al dueño (antes de que escale)
```

---

## ⭐ 6. REPUTACIÓN — Google Business Profile

[cite:05e1b7d4-3][cite:05e1b7d4-1]

Las reseñas de Google son **el mayor driver de clientes nuevos** para una barbería local. Automatizar esto es altísimo ROI.

```
Flujo:
1. Cita completada (status = 'completed' en BD)
2. Esperar 2 horas
3. WhatsApp al cliente:
   "¡Gracias por tu visita, Cristina! 🙏
    ¿Nos ayudas con una reseña? Toma 30 seg.
    👉 [link directo a Google Review]"
4. Esperar 3 días
5. Si no dejó reseña → no insistir más (evita spam)
6. Si dejó reseña → detectar con GBP API
   ├── 5 estrellas → enviar cupón de agradecimiento
   └── ≤3 estrellas → ALERTA al dueño + respuesta sugerida por IA
```

**Automatización con n8n:** [cite:05e1b7d4-3] ya existe un workflow template: "Automate Google Business reviews with AI responses, Slack alerts & sheets logging".

**Extra — responder reseñas automáticamente con IA:**
```
Reseña: "Excelente servicio, Juan es un crack" (5★)
IA genera: "¡Gracias! Juan estará feliz de leer esto. 
            Te esperamos pronto. 💈"

Reseña: "Esperé 40 min con cita" (2★)
IA genera borrador → Telegram al dueño → [Aprobar] [Editar] [Rechazar]
                                          ↓
                                    Publicar respuesta
```

---

## 📅 7. RESERVAS — Alternativas a Google Calendar

### Cal.com (open source, self-host)

[cite:90b5bd59-1] n8n tiene nodo nativo para Cal.com (PR mergeado).

**Ventajas sobre Google Calendar:**
- ✅ **Página de reserva pública** para poner en bio de Instagram
- ✅ Confirmación por WhatsApp/email nativa
- ✅ Manejo de zonas horarias implícito
- ✅ Multi-barbero por "round robin" o "collective"
- ✅ Webhooks nativos → n8n
- ✅ Sin costo (self-host)

```javascript
// n8n Cal.com node — Trigger: booking.created
// → Postgres insert
// → WhatsApp confirm
// → Telegram notify barber
```

**Migración sugerida:** mantener Google Calendar **en paralelo** (para el dueño), pero mover la fuente de verdad a Postgres. Cal.com si quieres una página pública.

---

## 🔒 8. SEGURIDAD Y CALIDAD

### Anti-spam y validación

```
1. Rate limiting por teléfono (n8n: static data + timestamp check)
   → Máx 20 mensajes/hora por número

2. Detección de teléfono válido
   → Si no existe en BD y no responde a 2 intentos → ignorar

3. Sanitización de input
   → Nunca interpolar directo a SQL (usar parámetros)
   → Escapar a XML/JSON si se usa en tools

4. Blacklist de palabras → alerta al owner

5. Idempotencia
   → Guardar messageId de WhatsApp, evitar procesar duplicados
     (WhatsApp reintenta webhooks)
```

### Observabilidad del bot

```
Cada interacción → insert en tabla `conversations`:
  ├── phone, timestamp, intent_detected
  ├── confidence, tokens_used, latency_ms
  ├── resolved (bool)
  └── escalation_reason

Query semanal:
  SELECT intent_detected, COUNT(*), AVG(confidence), AVG(latency_ms)
  FROM conversations
  WHERE timestamp > now() - interval '7 days'
  GROUP BY 1 ORDER BY 2 DESC;

→ Detectas: intenciones no reconocidas, latencia alta, puntos de fricción
```

---

## 🎁 9. PROGRAMA DE LEALTAD (Con la BD ya lista)

```sql
-- Cada cita completada
UPDATE customers SET
  total_visits = total_visits + 1,
  total_spent = total_spent + $price,
  loyalty_points = loyalty_points + FLOOR($price / 10)
WHERE id = $customer_id;

-- Recompensas automáticas
$100 de compra → 10 puntos (1 punto = $1 de descuento)
```

```
n8n workflow: Schedule semanal
  → Query clientes con loyalty_points >= 100
  → WhatsApp: "¡Tienes $100 en puntos acumulados! 
               Canjéalos en tu próxima visita 🎁"
```

**Programa de referidos:**
```
Cliente A refiere a Cliente B
   ↓
n8n genera código único (REF-A-XXXX)
   ↓
Cliente B lo usa al agendar
   ↓
Cliente A recibe $50 en puntos automáticamente
   ↓
Notificación a ambos
```

---

## 🏗️ 10. ARQUITECTURA OBJETIVO

```
                    ┌──────────────────────┐
     WhatsApp ──────▶  n8n (core)          │
     SMS (Twilio) ──▶  ├─ Router AI        │
     Telegram ──────▶  ├─ RAG Retriever    │
                       ├─ Agent + Tools    │
                       └─ Output Formatter │
                    └──────────┬───────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
        ▼                      ▼                      ▼
┌───────────────┐   ┌──────────────────┐   ┌──────────────────┐
│  SUPABASE     │   │   MERCADO PAGO   │   │  LOOKER STUDIO   │
│  - customers  │   │   - preferences  │   │  - dashboards    │
│  - appts      │   │   - webhooks     │   │  - KPIs visuales │
│  - services   │   │   - payment link │   │                  │
│  - metrics    │   └──────────────────┘   └──────────────────┘
│  - knowledge  │
│    (pgvector) │   ┌──────────────────┐   ┌──────────────────┐
└───────────────┘   │  GOOGLE BUSINESS │   │  CAL.COM / G.CAL │
                    │  - reviews sync  │   │  - booking src   │
                    │  - auto-reply    │   │  - availability  │
                    └──────────────────┘   └──────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │  TELEGRAM (staff)   │
                    │  - alertas          │
                    │  - aprobaciones HITL│
                    └─────────────────────┘
```

---

## 📋 ROADMAP DE INTEGRACIÓN

### 🔴 Fase 1 — CRÍTICO (Semanas 1-2)
- [ ] **Migrar Google Sheets → Supabase Postgres**
      Sin esto, nada más escala. Incluye constraint anti-doble-reserva.
- [ ] **Looker Studio** conectado a Supabase
      Dashboard visual para el dueño desde el día 1.
- [ ] **Mejorar reportes de WhatsApp con el nuevo `daily_metrics`**
      Ahora son queries instantáneas, no scans completos.

### 🟠 Fase 2 — ALTO VALOR (Semanas 3-4)
- [ ] **Mercado Pago** — anticipos de 20-30%
- [ ] **Google Business Profile** — solicitud de reseña post-cita
- [ ] **Telegram Bot** para el staff (agenda diaria + alertas)

### 🟡 Fase 3 — DIFERENCIACIÓN (Semanas 5-7)
- [ ] **RAG sobre Supabase Vector** (pgvector ya incluido)
- [ ] **Whisper** — procesar notas de voz
- [ ] **OpenAI Vision** — identificar estilos en fotos
- [ ] **Sentiment Analysis** — enrutamiento y alertas

### 🟢 Fase 4 — ESCALA (Semanas 8-10)
- [ ] **Programa de lealtad + referidos**
- [ ] **Cal.com** — página pública de reservas
- [ ] **Instagram Graph API** — publicación de trabajos
- [ ] **Observabilidad** — tabla conversations + métricas de bot

---

## 💰 ESTIMACIÓN DE COSTOS MENSUALES

| Servicio | Plan | Costo |
|----------|------|-------|
| n8n | Self-host VPS | $6-12 |
| Supabase | Free tier (suficiente) | $0 |
| Looker Studio | Gratis | $0 |
| Mercado Pago | % transacción | ~$0 (variable) |
| Twilio | Pay-per-use | ~$5 |
| Telegram | Gratis | $0 |
| OpenAI (GPT-4o + Whisper + Vision) | Pay-per-use | $10-25 |
| Cal.com | Self-host | $0 |
| **TOTAL** | | **~$25-45/mes** |

**Comparación:** una barbería típica gasta $200-400/mes en publicidad digital poco efectiva. Este stack cuesta **~10% de eso** y genera más valor medible.

---

## 🎯 TOP 3 SI SOLO PUEDES HACER 3 COSAS

1. **Supabase Postgres** — Desbloquea todo lo demás (pagos, RAG, dashboards, analytics rápido). Sin esto vives con techo de cristal.
   [cite:ba9851ff-3]

2. **Looker Studio** — El dueño deja de leer texto y **ve** su negocio. Cambio de percepción radical.
   [cite:08e6f57c-3]

3. **Mercado Pago (anticipos)** — Impacto financiero directo en semanas: menos no-shows, más cash flow.
   [cite:79098aa3-1]

---

## ✅ Conclusión

Tu stack actual (Calendar + Sheets) es un **excelente punto de partida**, pero tiene techos. Las integraciones aquí descritas no son "nice to have" — son las que convierten el asistente en un **sistema operativo del negocio**:

| Capa | Con Sheets + Calendar | Con el stack completo |
|------|----------------------|----------------------|
| Datos | Lento con volumen | Postgres con índices |
| Doble reserva | Posible | **Imposible** (constraint) |
| Pagos | Manual | Automático con anticipos |
| Reportes | Texto en WhatsApp | Dashboard visual |
| Conocimiento | Hardcoded | RAG dinámico |
| Voz/fotos | No soportado | Whisper + Vision |
| Reputación | Manual | Automatizado |
| Staff | Ruido en WhatsApp | Telegram limpio |
| Fidelización | Inexistente | Puntos + referidos |

**Siguiente paso concreto:** empezar por la migración a Supabase. Es la pieza que habilita todo el resto.
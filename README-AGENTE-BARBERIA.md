# Agente de barbería "Barber Chinos" — entrega

Agente recepcionista de WhatsApp para **Barber Chinos — Peluquería & Barbería**
(Calle Pinzón #574, citas: 452-281-8144), sobre n8n + Evolution API +
Google Calendar + Google Sheets + Postgres, con el modelo servido por
**Uncensored AI** (`api.uncensored.com`).

---

## 1. Qué se entrega

| Archivo | Qué es |
| --- | --- |
| `BarberiaAgenteFLUJO-1-UNCENSORED.json` | Flujo principal. **Ya importado en tu n8n.** |
| `BarberiaAgenteFLUJO-2-RECORDATORIOS.json` | Flujo de recordatorios. **Ya importado.** |
| `prompt-sistema-agente-barberia.txt` | El system prompt completo, en texto plano. |
| `COMO-CORRER-N8N.md` | Cómo arrancar y detener n8n en Docker. |
| `docker-compose.yml` + `.env` | El stack de n8n + Postgres, listo para usar. |
| `docker-helper.py` | Atajo para operar los contenedores sin problemas de comillas. |
| `transforms.py` | Script que genera los dos JSON desde los originales. |
| `verify.py` | 102 verificaciones automáticas sobre lo entregado. |
| `test-code-node.js` | 11 pruebas de los recordatorios y la zona horaria. |
| `test-tool-calling.js` | Comprueba qué modelos soportan herramientas. |
| `test-agente-e2e.js` | 5 conversaciones reales contra el agente. |
| `mcp-n8n-research.md` | Cómo conectar el MCP de n8n (investigación con fuentes). |
| `provider-uncensored-research.md` | Cómo apuntar n8n a Uncensored AI (fuentes). |
| `features-roadmap-research.md` | Roadmap de funcionalidades con evidencia. |

Los archivos originales no se modificaron.

> **Nota:** la llave de Uncensored AI que me compartiste **no está en ningún
> archivo**. Vive solo en la credencial de n8n. Si crees que quedó expuesta en
> algún registro, rótala desde tu Developer Dashboard.

---

## 2. Cómo importar (5 minutos)

> **Hecho por ti:** n8n ya está corriendo con los dos workflows dentro.
> Solo falta la credencial (paso 1) y reconectar Google/Postgres (paso 4).

1. **Crea la credencial del proveedor.** En n8n: *Credentials → New → OpenAI*.
   - **API Key:** tu llave de `uncensored.com` (Developer Dashboard).
   - **Base URL:** `https://api.uncensored.com/api/v1`
   - **Add Custom Header:** nombre `x-api-key`, valor = tu misma llave.
   - **Nómbrala exactamente** `Uncensored AI (OpenAI-compatible)`.
2. **Importa los dos JSON** en n8n (*Workflows → Import from File*).
3. **Selecciona la credencial** en el nodo *OpenAI Chat Model* del flujo 1.
4. **Repón las 3 credenciales** que ya usaba tu workflow (Google Calendar,
   Google Sheets, Postgres) — n8n las pedirá al importar.
5. **Prueba en el chat de n8n** antes de activar: pide "quiero corte mañana a las 4".

> **Por qué la credencial debe llamarse así y ser distinta de la de OpenAI:**
> el nodo de **Whisper** (`Transcribe a recording`) y el de **visión**
> (`Describe imagen`) siguen atados a `api.openai.com`. Si reutilizas la misma
> credencial para todo, rompes el audio y las imágenes. Esa separación es
> intencional.

---

## 3. Qué cambió respecto a lo que me diste

### 3.1 Precios (lo más importante)

Los precios del prompt anterior no existían en el negocio. Ahora el prompt trae
la lista real de tu imagen:

| Servicio | Precio | Duración a reservar |
| --- | --- | --- |
| Corte desvanecido o tijera | $150 | 40 min |
| Arreglo de barba | $100 | 20 min |
| Ceja | $30 | 10 min |
| Mascarilla | $50 | 20 min |
| Corte de cabello dama | $250 | 50 min |
| Planchado express | $150 | 30 min |
| Peinado | $300 | 45 min |
| Depilación | precio según la zona | 30 min |

Zonas de depilación: ceja, bigote, nariz, orejas, barba, axilas, piernas.
Se eliminaron los precios inventados ($350, $500, $600).

**La duración es nueva y es la clave anti-empalme:** antes el agente reservaba
bloques sin saber cuánto duraba el servicio, así que dos citas se podían pisar.
Ahora el agente calcula `fin = inicio + duración` y valida el bloque completo.

### 3.2 El bug más grave: "Reagendar" no reagendaba

El nodo `Reagendar` tenía `updateFields: {}` — vacío. El agente podía llamar la
herramienta, n8n respondía éxito, y **la cita no se movía**. El cliente se iba
creyendo que tenía nueva hora. Ahora actualiza `start`, `end`, `summary` y
`description`.

### 3.3 Zona horaria (también rompía los recordatorios)

El `Code` del flujo 2 hacía `Date.UTC(...)` sobre la hora de la hoja, tratando
"16:00" como UTC. En México (UTC−6) eso **adelantaba la cita 6 horas**: se
agendaba a las 4 p.m. y el sistema entendía las 10 a.m. Ahora el offset `-06:00`
se fija explícitamente y hay pruebas con fechas reales.

Además el `Code` tenía una **`v` suelta al final del bloque** — un error de
sintaxis que hacía fallar el nodo entero.

### 3.4 Las herramientas ahora se llaman como habla el modelo

`Obtener eventos` → **Consultar agenda** · `Crear evento` → **Agendar cita** ·
`Eliminar eventos` → **Cancelar cita** · `Append row in sheet…` →
**Registrar en hoja de citas**.

Los nombres anteriores eran ambiguos: "Eliminar eventos" (plural) invitaba a
borrar más de lo pedido. Y cada `toolDescription` ahora explica *cuándo* usarla,
no solo qué hace.

### 3.5 Lo que se conservó tal cual

Las 4 herramientas de Google Calendar y la de Google Sheets siguen apuntando a
los mismos recursos (calendario `BARBER`, hoja *Citas barbería*), con las mismas
credenciales. No tienes que re-mapear nada: solo reconectar las credenciales al
importar.

---

## 4. Funcionalidades nuevas

### 4.1 Ya implementadas en esta entrega

| Función | Cómo funciona |
| --- | --- |
| **Recordatorio a 24 h** | El de mayor efecto sobre inasistencias. Pide confirmar con *SI* / *NO*. |
| **Recordatorio a 1 h** | Se conserva el original, ahora con petición de aviso si no puede asistir. |
| **Espera real antes de cada aviso** | Nodos `ESPERAR A 24 H` y `ESPERAR A 1 H` (tipo *Wait*) retienen el flujo hasta el momento correcto. Sin ellos el aviso sale al instante de agendar. |
| **No mandar recordatorios vencidos** | Dos nodos *IF* desvían el flujo si el momento ya pasó (p. ej. una cita agendada para dentro de 3 h no manda el aviso de 24 h). |
| **Escalar al encargado** | Herramienta nueva `Notificar al encargado`: manda un WhatsApp al barbero cuando piden descuento, se quejan, o piden algo fuera del catálogo. |
| **Guion de confirmación previa** | El prompt obliga a confirmar servicio, día, hora y precio *antes* de escribir en el calendario. |
| **Ubicación de cita explícita** | El agente sabe que el nombre y el WhatsApp van en la *descripción* del evento, así que encuentra la cita sin inventar IDs. |
| **Margen de 10 min entre citas** | Evita citas pegadas que se retrasan en cadena. |
| **Horario y cierre** | Lunes a sábado 10:00–20:00, domingo cerrado, y el servicio debe **terminar** antes del cierre. |
| **Depilación con regla propia** | Pregunta la zona, dice que el precio se confirma al llegar, y escala si insisten en un número. |

### 4.2 Roadmap priorizado

El detalle con evidencia y fuentes está en `features-roadmap-research.md`.
Dos datos que ordenan las prioridades: los no-show en barbería rondan el **20 %**,
y las reservas hechas **fuera de horario** son ~38 %.

**Alta prioridad**

1. **Confirmación de asistencia con botones** — WhatsApp con botones baja el
   no-show de ~20 % a 5–8 %. Es la de mejor relación esfuerzo/beneficio.
2. **Nunca afirmar disponibilidad o precio sin consultar la herramienta** — el
   guardrail nº 1 contra alucinaciones. El prompt ya lo pide; conviene reforzarlo
   con una tabla de servicios como fuente única.
3. **Idempotencia anti doble-reserva** — hay un caso documentado de 5 llamadas
   idénticas que crearon **4 citas duplicadas**. Se resuelve con una llave única
   `teléfono+fecha+hora+servicio` y consultando antes de insertar.
4. **Re-verificar el hueco justo antes de crear** — dos clientes pueden pedir el
   mismo horario a la vez (*race condition*). El flujo ya deja 10 min de margen,
   pero falta la verificación en el instante de crear.
5. **Lista de espera** — al cancelar alguien, ofrecer el hueco al siguiente.
6. **Selección de barbero y capacidad de 2 sillas** — hoy el calendario asume un
   solo recurso, así que una cita bloquea la barbería completa.

**Media**

7. **Mensajes fuera de horario que sí agendan** — el 38 % de reservas llegan
   fuera de horario; responder "mañana te contestamos" pierde la venta. El prompt
   ya agende y avisa; conviene medirlo.
8. **Resumen diario al barbero** (agenda del día por WhatsApp) y **aviso de cita
   nueva** — visibilidad operativa.
9. **Upsell al agendar** — ofrecer ceja ($30) o mascarilla ($50) al cerrar un corte.
10. **Aviso de privacidad (LFPDPPP)** — la ley mexicana exige informar antes de
    recopilar datos personales, incluido el teléfono. Un aviso corto al primer
    mensaje de un número nuevo.
11. **Opt-out de marketing** — comando "BAJA" y filtro en campañas.
12. **Re-engagement** a las 3–4 semanas, **reseñas** post-visita y **bloqueo de
    festivos**.

**Baja**

13. **Depósito anti-no-show** — baja inasistencias >50 %, pero necesita pasarela
    de pago (Mercado Pago / Stripe) y webhook de confirmación: es el de mayor
    esfuerzo de la lista.
14. Rate limiting por número, KPIs en un panel, referidos, cumpleaños.

---

## 5. MCP de n8n: **ya está funcionando**

n8n corre en Docker y el **servidor MCP oficial está activo**:

| Comprobación | Resultado |
| --- | --- |
| n8n en marcha | `barberia-n8n` arriba en `localhost:5678` |
| Versión | **2.40.6** (el MCP oficial existe desde 2.13) |
| Flag `mcp.access.enabled` | `true` |
| Endpoint `/mcp-server/http` | responde **401** (pide token = activo; antes daba 404) |
| Workflows expuestos | ambos con `availableInMCP: true` |

**Cómo arrancarlo:** ver `COMO-CORRER-N8N.md`. Lo más simple es abrir Docker
Desktop → Containers y dar play a `barberia-n8n`.

**Para conectar tu cliente MCP** (Cherry Studio, Claude, etc.):

1. Arranca el stack y entra a http://localhost:5678.
2. *Settings → Instance-level MCP → Connect a client → API key*.
3. n8n te da un bloque ya relleno. Pégalo como servidor remoto:

```json
{
  "baseUrl": "http://localhost:5678/mcp-server/http",
  "headers": { "Authorization": "Bearer <TU_TOKEN_MCP>" }
}
```

**Verificación:** llama a la herramienta `search_workflows`. Debe devolver una
lista con `barberiaAgenteUncensored` y `barberiaRecordatorios`.

### El camino que recorrí (por si algo falla después)

El flag del MCP **no** es una variable de entorno: vive en la tabla `settings`
de la base de datos. Lo activé con:

```sql
INSERT INTO settings (key, value, "loadOnStartup")
VALUES ('mcp.access.enabled', 'true', true)
ON CONFLICT (key) DO UPDATE SET value = 'true';
```

Y expuse cada workflow con `settings.availableInMCP = true`. Si algún día el
endpoint vuelve a dar 404, revisa esas dos cosas primero.

Tres obstáculos reales que tuve que resolver y quedan documentados:

1. Docker Desktop está instalado en `%LOCALAPPDATA%\Programs\DockerDesktop`,
   no en `Program Files`, así que `docker` no está en el `PATH`.
2. Sin la variable `DOCKER_CONFIG`, Docker falla con
   `error getting credentials: docker-credential-desktop not found`. Se resolvió
   con un directorio `.docker` propio que enlaza plugins y contextos.
3. `Start-Process` de PowerShell **vuelve a partir los argumentos con espacios**,
   lo que rompía el SQL. Por eso el helper acepta SQL en base64 (`sqlb64`).

---

## 6. El proveedor: verificado con tu llave

**Corrijo una advertencia que te di antes.** Dije que Uncensored AI no documenta
`function calling`. Es cierto que **su documentación no lo menciona**, pero
**la API sí lo soporta**: lo probé con tu llave y funciona.

```
=== Autenticacion (ambas cabeceras aceptadas) ===
  x-api-key              -> HTTP 200
  Authorization: Bearer  -> HTTP 200

=== Soporte de function calling ===
  gpt-4o              SOPORTA TOOLS  -> consultar_agenda({"dia":"2026-05-14"})
  claude-sonnet-4.5   SOPORTA TOOLS
  claude-opus-4.5     SOPORTA TOOLS
  gemini-2.5-flash    SOPORTA TOOLS
  grok-4.5            SOPORTA TOOLS

SOPORTAN TOOLS: 5 de 5
```

### Prueba de extremo a extremo del agente (real, contra la API)

Simulé el bucle completo del AI Agent con el system prompt y las herramientas
del workflow, y ejecuté 5 conversaciones:

```
PASS  Agendar corte
      -> Consultar_agenda -> Agendar_cita -> Registrar_en_hoja_de_citas
      "Listo, Juan. Te agendé un corte desvanecido mañana 14 de mayo a las
       4:00 p.m. ... El costo es de $150."
PASS  Preguntar precio          (sin herramientas, respondió $250 y $300)
PASS  Descuento                 -> Notificar_al_encargado
PASS  Depilacion por zona       (sin herramientas, precio según zona)
PASS  Horario ocupado           -> Consultar_agenda, ofreció alternativa

CASOS CORRECTOS: 5 de 5      Empalmes detectados: 0      Sin doble reserva: OK
```

Detalles que confirman que quedó bien:

- La cita se creó **16:00–16:40**: respetó los 40 min del corte.
- Ante el horario ocupado de las 11:00 (que terminaba 11:40), ofreció **11:50**:
  respetó el margen de 10 minutos.
- Convirtió "mañana a las 4" a ISO con offset **−06:00** correctamente.

**Dos fallos reales que esta prueba destapó y corregí en el prompt:**

1. El agente verificaba la disponibilidad y luego **se detenía a preguntar
   "¿confirmas?" en vez de agendar**. Añadí una sección *"REGLA DE ORO: ACTÚA,
   NO ANUNCIES"* que prohíbe escribir "déjame revisar" antes de llamar la
   herramienta.
2. Ante una petición de descuento **solo la rechazaba, sin escalar**. Ahora el
   prompt ordena ejecutar `Notificar al encargado` en ese mismo turno.

Ambos son ejemplos de por qué conviene probar contra el modelo real antes de
activar en producción.

### Recomendación de modelo

Dejé `gpt-4o` porque ya venía en tu flujo y está en el catálogo (98 modelos).
Para producción, `claude-sonnet-4.5` o `gemini-2.5-flash` salen más baratos por
token y también llaman herramientas; `gemini-2.5-flash` fue el más rápido de los
que probé. Cámbialo en el nodo *OpenAI Chat Model* → campo *Model*.

---

## 7. Verificación (evidencia, no afirmaciones)

```
verify.py             102 de 102 PASARON   (estructura y contenido)
test-code-node.js      11 de 11 PASARON    (recordatorios y zona horaria)
test-tool-calling.js    5 de 5 SOPORTAN TOOLS  (API real)
test-agente-e2e.js      5 de 5 CASOS CORRECTOS (agente real, sin doble reserva)
node JSON.parse         ambos archivos OK
node --check            JS del Code node válido
```

```bash
uv run python transforms.py   # regenera los dos JSON
uv run python verify.py       # 102 verificaciones
node test-code-node.js        # 11 pruebas de comportamiento

# Las que pegan contra la API (la llave va por variable de entorno:
# NUNCA la escribas en un archivo)
$env:UNC_KEY="tu-llave"
node test-tool-calling.js gpt-4o claude-sonnet-4.5 gemini-2.5-flash
node test-agente-e2e.js gpt-4o
```

`verify.py` comprueba, entre otras cosas: JSON parseable, ids únicos, que
ninguna conexión apunte a un nodo inexistente, que ninguna expresión
`$('Nodo')` quede rota, que **los 8 precios de la imagen estén en el prompt**,
que los precios viejos ya no estén, que las 6 herramientas estén conectadas al
AI Agent, que `Reagendar` actualice inicio y fin, y que la zona horaria esté
fijada.

Los bugs reales que estas pruebas atraparon (los dos últimos los introduje yo al
construir el flujo y quedaron corregidos antes de entregar):

1. La columna `Día ` de la hoja perdía el acento y quedaba `Dia` — el registro
   en Google Sheets habría fallado en silencio.
2. **El recordatorio de 24 h salía al instante de agendar**, porque no tenía un
   nodo *Wait* antes. Ahora hay una prueba de regresión que verifica que cada
   recordatorio *solo* se alcanza a través de su nodo de espera.

---

## 8. Pendientes tuyos

1. Pegar tu llave de Uncensored AI en la credencial.
2. Reconectar las credenciales de Google Calendar, Sheets y Postgres al importar.
3. Confirmar el **número del encargado** en la herramienta `Notificar al
   encargado` (hoy usa el que ya estaba en el flujo).
4. Confirmar la **API key de Evolution** en esa misma herramienta (la tomé del
   flujo original, pero conviene moverla a una credencial de n8n).
5. Decidir si el recordatorio de 24 h lleva botones de confirmación.
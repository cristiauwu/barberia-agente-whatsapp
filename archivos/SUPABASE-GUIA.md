# SUPABASE — Guía paso a paso (Barber Chinos)

> Proyecto: `https://zucgrcyzofelmiorvxhb.supabase.co`
> Plan: **gratis**. Entregable principal: `supabase-esquema.sql`.
> Validación: `probar-supabase-sql.py` → **92/92 comprobaciones correctas**.

---

## 1. Resumen ejecutivo (leer esto primero)

| Pregunta | Respuesta corta |
|---|---|
| ¿El proyecto Supabase existe y responde? | **Sí.** Confirmado con HTTP 200 reales. |
| ¿Puedo crear tablas con las claves que me diste? | **NO.** Es imposible. Verificado empíricamente. |
| ¿Se creó algo en Supabase? | **NO se creó NADA.** No hay ninguna tabla ahí. |
| ¿El SQL está listo para usar? | **Sí**, validado contra Postgres real: 92/92. |
| ¿Qué falta? | La **secret key** (`sb_secret_...`) o pegar el SQL a mano. |

**Lo único que falta para tener la base de datos funcionando es abrir el
dashboard y pegar un archivo.** Son unos 3 clics (sección 4).

---

## 2. Qué SÍ y qué NO puedes hacer con las claves dadas

Las dos claves que diste (`SUPABASE_KEY_AQUI...` y
`SUPABASE_KEY_AQUI...`) son **publishable keys**: el equivalente moderno de
la antigua clave `anon`. Están **diseñadas para ir en el navegador**, o sea que
son públicas por diseño. Tienen los mismos privilegios bajos que la clave `anon`
y RLS se comporta igual con ellas. [cite:5024ab52-1]

### SÍ funciona (evidencia real)

| Petición | HTTP | Respuesta real |
|---|---|---|
| `GET /auth/v1/health` | **200** | `{"version":"v2.197.0","name":"GoTrue","description":"GoTrue is a user registration and authentication API"}` |
| `GET /auth/v1/settings` | **200** | `{"external":{"anonymous_users":false,...,"email":true,"phone":false,...},"disable_signup":false,"mailer_autoconfirm":false,...}` |
| `GET /storage/v1/bucket` | **200** | `[]` (no hay buckets) |
| `GET /graphql/v1` | **200** | `{"errors":[{"message":"pg_graphql extension is not enabled."}]}` |

Con esto se confirma que **el proyecto existe, está vivo y responde**, y que la
clave es válida.

### NO funciona (evidencia real)

| Petición | HTTP | Respuesta real |
|---|---|---|
| `GET /rest/v1/` (raíz de la API REST) | **401** | `{"message":"Secret API key required","hint":"Only secret API keys can be used for this endpoint."}` |
| `GET /rest/v1/barber_citas?select=*` | **404** | `{"code":"PGRST205","details":null,"hint":null,"message":"Could not find the table 'public.barber_citas' in the schema cache"}` |
| `POST /rest/v1/` (intento de DDL) | **401** | `{"hint":"Only secret API keys can be used for this endpoint.","message":"Secret API key required"}` |
| `POST /rest/v1/rpc/exec` (DDL) | **404** | `{"code":"PGRST202",...,"message":"Could not find the function public.exec(sql) in the schema cache"}` |
| `POST /rest/v1/rpc/execute_sql` | **404** | `{"code":"PGRST202",...,"message":"Could not find the function public.execute_sql(sql)..."}` |
| `POST /rest/v1/rpc/query` | **404** | `{"code":"PGRST202",...,"message":"Could not find the function public.query(query)..."}` |
| `POST /pg/query` | **404** | `{"error":"requested path is invalid"}` |
| `GET /auth/v1/admin/users` | **401** | `{"code":401,"error_code":"no_authorization","msg":"This endpoint requires a valid Bearer token"}` |
| `POST api.supabase.com/v1/projects/<ref>/database/query` | **401** | `{"message":"JWT could not be decoded"}` |

### Controles que confirman el diagnóstico

| Petición | HTTP | Respuesta real | Qué demuestra |
|---|---|---|---|
| `GET /rest/v1/...` **sin** apikey | 401 | `{"hint":"No 'apikey' request header or url param was found.","message":"No API key found in request"}` | El header es obligatorio |
| `GET /rest/v1/...` con apikey **basura** | 401 | `{"message":"Invalid API key","hint":"Double check your API key."}` | **Tus claves son válidas**: si fueran inválidas darían *este* error, no el de "Secret API key required" |

### Por qué el 401 no es un problema de permisos sino de TIPO de clave

Fíjate en la diferencia:

- Con la clave **basura** → `"Invalid API key"` → Supabase no reconoce la clave.
- Con **tus claves** → `"Secret API key required"` → Supabase **sí** reconoce la
  clave, y además dice explícitamente que ese endpoint exige una **secret key**.

Los endpoints de datos (`/rest/v1/<tabla>`) sí aceptan la publishable key: el
404 que devuelven es por tabla inexistente (`PGRST205`), no por clave. Es decir:
**el día que existan las tablas, la publishable key podrá consultarlas** (y solo
podrá ver lo que RLS permita).

Las publishable keys **no son JWT** (no tienen los 3 segmentos separados por
punto del formato `eyJ...`), así que no llevan un rol embebido con el que
saltarse RLS. No hay forma de "elevarlas" a administrador.

### Conclusión

Con las claves dadas **no se puede crear ni una tabla**. Tampoco se puede
escribir con permisos de administrador. Lo único que se puede hacer es
**comprobar que el proyecto responde**. Por eso el entregable es SQL listo para
pegar, y no una base ya creada.

---

## 3. Cómo crear el esquema — dos caminos

### Camino A (recomendado, gratis, 3 minutos): SQL Editor del dashboard

No necesitas ninguna clave secreta. Ver sección 4.

### Camino B: pedir la secret key

Si quieres que n8n escriba en Supabase automáticamente, necesitas la **secret
key** (ver sección 7).

---

## 4. Dónde pegar el SQL exactamente (ruta de clics)

1. Entra a <https://supabase.com/dashboard> e inicia sesión.
2. Verás la lista de proyectos. Haz clic en el proyecto con referencia
   **`zucgrcyzofelmiorvxhb`**.
3. En la barra lateral izquierda, busca **`SQL Editor`** (icono `</>`).
   Ruta completa: *Dashboard → tu proyecto → SQL Editor*.
   Atajo directo:
   <https://supabase.com/dashboard/project/zucgrcyzofelmiorvxhb/sql/new>
4. Pulsa el botón **`+ New query`** (arriba a la derecha).
5. Abre `G:\Barberia\archivos\supabase-esquema.sql`, **selecciona todo**
   (Ctrl+A) y **cópialo**.
6. Pégalo en el editor (Ctrl+V).
7. Pulsa el botón **`Run`** (abajo a la derecha) o **Ctrl+Enter**.
8. Abajo debe aparecer **`Success. No rows returned`**. Eso es lo correcto:
   el script crea objetos, no devuelve filas.

> Si el editor se queja de que el texto es muy largo, ejecútalo por partes:
> primero la sección 0 y 1, luego 2 y 3, etc. Cada bloque está numerado y
> comentado. Respeta el orden.

El archivo es **idempotente**: puedes volver a ejecutarlo cuantas veces quieras
sin miedo.

---

## 5. Cómo verificar que quedó bien

Pega esto en una **New query** del SQL Editor y pulsa Run:

```sql
-- 1) Deben salir 10 tablas (barber_auditoria ... barber_servicios)
SELECT tablename FROM pg_tables
 WHERE schemaname = 'public' AND tablename LIKE 'barber\_%'
 ORDER BY 1;

-- 2) Debe salir UNA fila con el EXCLUDE USING gist sobre tstzrange
SELECT conname, pg_get_constraintdef(oid)
  FROM pg_constraint
 WHERE conrelid = 'public.barber_citas'::regclass
 ORDER BY 1;

-- 3) Deben salir los 8 servicios reales con sus precios
SELECT clave, nombre, precio, duracion_min
  FROM public.barber_servicios ORDER BY clave;

-- 4) Debe salir 1 (la vista materializada existe)
SELECT count(*) FROM pg_matviews
 WHERE schemaname = 'public' AND matviewname = 'daily_metrics';

-- 5) Las 10 tablas con rowsecurity = true, y 0 políticas
SELECT c.relname, c.relrowsecurity
  FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE n.nspname = 'public' AND c.relkind = 'r'
   AND c.relname LIKE 'barber\_%' ORDER BY 1;

SELECT count(*) AS politicas FROM pg_policies WHERE schemaname = 'public';
```

**Resultado esperado de la comprobación 5:** todas con `rowsecurity = true` y
`politicas = 0`.

### Prueba rápida de que la protección anti-doble-reserva está viva

Pega esto (crea dos citas de prueba y las borra, no deja basura):

```sql
BEGIN;

INSERT INTO public.barber_clientes (jid, nombre) VALUES
  ('5210000000001@s.whatsapp.net', 'Prueba Uno'),
  ('5210000000002@s.whatsapp.net', 'Prueba Dos');

-- Esta debe pasar
INSERT INTO public.barber_citas
  (id, jid, servicio, precio, inicio, fin, estado)
VALUES ('PRUEBA-OK', '5210000000001@s.whatsapp.net', 'Corte desvanecido o tijera',
        150, '2026-06-02 10:00:00-06', '2026-06-02 10:40:00-06', 'agendado');

-- Esta DEBE FALLAR con:
--   ERROR: conflicting key value violates exclusion constraint
--          "barber_citas_sin_solape"
-- Ese error es LA PRUEBA de que la protección funciona.
INSERT INTO public.barber_citas
  (id, jid, servicio, precio, inicio, fin, estado)
VALUES ('PRUEBA-MAL', '5210000000002@s.whatsapp.net', 'Arreglo de barba',
        100, '2026-06-02 10:20:00-06', '2026-06-02 10:40:00-06', 'agendado');

ROLLBACK;   -- borra todo lo de prueba
```

Este mismo escenario está automatizado y verificado en
`probar-supabase-sql.py` (secciones 5 y 6 de su salida).

---

## 6. Seguridad: por qué NO hay que abrir políticas

El script activa **RLS en las 10 tablas y NO crea ninguna política**. Con eso,
la publishable key no puede leer ni escribir absolutamente nada por la API REST.

**Esto es intencional y es lo correcto.** La alternativa sería añadir una
política como `CREATE POLICY ... FOR ALL USING (true)`, y eso significaría que
**cualquiera que vea tu publishable key** (que está en el navegador, en capturas
de pantalla, en foros...) podría:

- Leer los **teléfonos y nombres de todos tus clientes**.
- Leer **toda tu agenda y tus ingresos**.
- **Borrarte o falsearte citas.**
- **Insertar citas falsas** y romper el calendario.

La publishable key no es un secreto: está diseñada para publicarse. Por eso
**nunca** debe ir acompañada de políticas permisivas.

`service_role` (la secret key) y el SQL Editor **saltan RLS automáticamente**.
Es decir: n8n podrá escribir cuando tenga la secret key **sin abrir ninguna
política**. No hay ningún compromiso que hacer: se puede tener seguridad total y
automatización total a la vez.

Si algún día quieres un panel público de KPIs, la forma correcta es crear una
**vista** con solo las columnas no sensibles y conceder `SELECT` sobre esa vista
a un rol concreto. Nunca abrir las tablas.

---

## 7. Qué falta: la `service_role` key (o su equivalente moderno)

### Qué es

En el sistema nuevo de claves de Supabase, la antigua `service_role` se llama
**secret key** y empieza por `sb_secret_...`. La tabla de equivalencias oficial
es: `anon` → publishable key, y `service_role` → secret key. [cite:5024ab52-1]

| Tipo de clave | Dónde va | Puede saltar RLS |
|---|---|---|
| **publishable** (`sb_publishable_...`) — la que tienes | navegador, apps públicas | **No** |
| **secret** (`sb_secret_...`) — la que falta | solo en servidores | **Sí** |

### Dónde se obtiene

*Dashboard → tu proyecto → `Settings` → `API Keys` → pestaña
**Publishable and secret API keys***.
Atajo: <https://supabase.com/dashboard/project/zucgrcyzofelmiorvxhb/settings/api-keys>

Si ves un botón **`Create new API keys`**, tu proyecto todavía usa las claves
antiguas: púlsalo. Es seguro y no rompe nada, porque las claves antiguas siguen
funcionando en paralelo. [cite:5024ab52-1]

### Para qué la necesitarías

1. **Que n8n escriba en Supabase** (nodos Postgres o HTTP Request) sin tocar el
   dashboard.
2. **Refrescar `daily_metrics`** desde un Schedule de n8n.
3. **Migrar los datos** de Postgres local a Supabase.

### Advertencias sobre la secret key

- **Nunca** la pongas en un nodo de n8n que el cliente pueda tocar, ni en el
  repositorio de git, ni en una captura de pantalla. Salta RLS por completo:
  quien la tenga controla toda la base.
- Si se filtra, se rota desde la misma pantalla.
- No la compartas por WhatsApp.
- La secret key **no es un JWT**, así que si algún día la usas desde Postgres con
  `pg_net` (webhooks de base de datos), va en el header `apikey` y **no** en
  `Authorization: Bearer`. [cite:5024ab52-1]

---

## 8. Cómo conectar n8n (evaluación y recomendación)

### Pregunta: ¿tiene sentido conectar n8n a Supabase?

**Depende**, y la respuesta honesta es un matiz importante.

### Opción 1 — n8n con secret key (nodos Postgres / HTTP)

**Viable, pero hoy no la recomiendo como primer paso.**

Motivos:

1. Tu sistema **ya funciona** y está verificado con Postgres local + Google
   Calendar + Sheets. Mover la escritura a Supabase ahora añade un punto de
   fallo (red, latencia, la pausa por inactividad de la sección 9) sin resolver
   ningún problema actual.
2. n8n y el Postgres local están en la **misma máquina**: la conexión es
   instantánea y no depende de internet. Supabase está en la nube.
3. Serían **dos bases de datos que hay que mantener sincronizadas**, que es
   justo el tipo de duplicidad que genera bugs difíciles.

**Cuándo sí tiene sentido:** cuando quieras el **dashboard del dueño**
(Looker Studio / Metabase) o quieras el sistema disponible desde fuera de tu
máquina. Ahí Supabase aporta algo real.

### Opción 2 — Conectar n8n con la publishable key y RLS abierto

**DESCARTADO. No lo hagas.**

Para que funcionara habría que crear políticas de escritura públicas. El riesgo
concreto:

- La publishable key es **pública por diseño**.
- Con una política `FOR ALL USING (true)`, **cualquiera en internet** con esa
  clave podría leer y escribir tus datos.
- Tu project URL y esa clave ya están circulando en documentos del proyecto.
- La constraint `barber_citas_sin_solape` **no te protegería**: impide solapes,
  no impide que un desconocido inserte una cita o borre las tuyas.

Coste/beneficio: el beneficio es "no pegar el SQL a mano una vez". El riesgo es
exponer los datos personales de tus clientes. **No compensa en absoluto.**

### Opción 3 — Escritura local, réplica en Supabase (lo sensato)

Un workflow con Schedule (por ejemplo diario a las 21:00) que:

1. Lea las citas del día del Postgres local.
2. Haga `UPSERT` en Supabase **con la secret key**.

Así Supabase es de **solo lectura hacia fuera** (para dashboards) y el camino
crítico de escritura sigue siendo local y rápido.

### Conclusiones concretas

| Escenario | Recomendación |
|---|---|
| n8n escribe en Supabase con secret key | **Viable.** Hazlo cuando montes el dashboard. |
| n8n escribe con publishable + RLS abierto | **DESCARTAR.** Riesgo inaceptable. |
| n8n leyendo de Supabase con publishable | No sirve hoy: RLS cerrado y sin datos. |
| Replicar local → Supabase en un Schedule | **Recomendado** si quieres el dashboard. |

**No he tocado ningún workflow de n8n.** Esto es solo evaluación, como pediste.

---

## 9. Advertencia: límites del plan gratuito

### 500 MB de base de datos

Es de sobra para esta barbería. Una cita ocupa del orden de 200 bytes; **500 MB
son millones de citas**, muchos años de operación. No es un problema real.

Donde sí hay que tener cuidado es en `barber_auditoria`: si registras **cada**
acción del agente con los argumentos completos, es la tabla que más crece.
Si algún día se acerca al límite, se purga por antigüedad:

```sql
DELETE FROM public.barber_auditoria WHERE ts < now() - interval '6 months';
```

### Pausa por inactividad (el límite que sí importa)

Supabase **pausa los proyectos del plan gratis tras 7 días de baja actividad**.
Unas pocas consultas al día durante la semana bastan para evitarlo, pero la
documentación avisa de que "aunque estés usando el proyecto activamente, es
posible que el uso no sea suficiente para excluirlo de la pausa automática".
[cite:5024ab52-2]

Qué significa en la práctica:

- Si tu bot deja de escribir durante una semana (vacaciones del barbero, por
  ejemplo), Supabase puede **pausar** el proyecto.
- Supabase manda un aviso por correo **una semana antes** de la pausa, y otro
  cuando ya ha ocurrido. [cite:5024ab52-2]
- Se recupera con **`Resume project`** desde el dashboard, y los datos y la
  configuración vuelven tal cual. [cite:5024ab52-2]
- Hay **1 año** para resucitarlo desde que se pausa. Pasado ese plazo, se
  pierde. [cite:5024ab52-2]
- Los proyectos de pago no se pausan nunca. [cite:5024ab52-2]

**Consecuencia práctica:** si conectas n8n para escribir en Supabase, añade un
Schedule trivial que toque la base aunque sea una vez al día. Eso evita la pausa
sin coste y sin intervención manual.

Otro límite del plan gratis: **2 proyectos gratuitos activos como máximo** (los
pausados no cuentan para el cupo). [cite:9225ec41-2]

### Sobre `btree_gist`

La constraint anti-solape necesita la extensión `btree_gist` (permite combinar
una igualdad con un solapamiento de rangos en el mismo índice GiST).

- **En el plan gratis de Supabase `btree_gist` está disponible.** Viene en el
  catálogo estándar de extensiones de la imagen de Postgres de Supabase, y el
  SQL Editor corre con un rol que puede ejecutar `CREATE EXTENSION`.
- **Verificación local:** en el Postgres 17.11 de tu contenedor aparece en el
  catálogo (`btree_gist 1.7`) y se instala sin problema. La salida de
  `probar-supabase-sql.py` lo confirma y todas las pruebas del EXCLUDE pasaron
  con ella activa.

**Si aun así fallara**, `supabase-esquema.sql` incluye al final una sección
**"PLAN B SIN btree_gist"** con dos alternativas listas para pegar:

- **B1:** índice `UNIQUE` sobre el hueco exacto. Sirve para el caso "una cita
  por hora en punto", que es el 95% de esta barbería, pero no cubre solapes
  parciales.
- **B2:** trigger de validación. Funciona siempre y cubre solapes parciales,
  pero es más lento y tiene una carrera teórica (dos transacciones simultáneas
  podrían pasar ambas la comprobación).

`EXCLUDE` es y sigue siendo la mejor opción, porque elimina la carrera a nivel
de motor.

---

## 10. Qué descarté del documento original y por qué

Documento: `Herramientas_APIs_Complementarias.md`, sección *"Opción A — Supabase"*.

El esquema propuesto está pensado para una barbería genérica con varios
barberos, pagos con tarjeta y 5 estados en inglés. **Nada de eso encaja con
Barber Chinos.**

| # | Qué proponía el documento | Por qué lo descarté | Qué puse |
|---|---|---|---|
| 1 | Tabla **`barbers`** | El negocio tiene **UN SOLO barbero, Esteban Aguilera**. Una tabla de barberos con una sola fila es complejidad sin uso. | Eliminada. |
| 2 | Columna **`barber_id`** en `appointments` | Referencia a una tabla que no debe existir. Sería una columna constante en todas las filas. | Eliminada. |
| 3 | **`commission_pct NUMERIC(5,2) DEFAULT 40.00`** | Es una comisión para repartir ingresos **entre varios barberos**. Con uno solo no hay nada que repartir. | Eliminada. |
| 4 | **`reminder_2h_sent`** | Los recordatorios reales son de **24 h y 1 h** (nodos `RECORDATORIO 24 H` y `RECORDATORIO 1 H` del workflow `barberiaRecordatorios`). Un campo de "2 h" nunca se activaría. | `recordatorio_24h_enviado_en` y `recordatorio_1h_enviado_en` (timestamptz: se sabe **cuándo** se mandó, no solo si se mandó). |
| 5 | **`status CHECK (status IN ('pending','confirmed','completed','cancelled','no_show'))`** | Los estados reales están **en español**: `agendado, confirmado, atendido, no_show, cancelado, reprogramado`. Era el error más grave: un `'agendado'` habría sido **rechazado por la base** y el workflow habría fallado al escribir. | Los 6 estados reales. Verificado: `'pending'` y `'completed'` se rechazan; los 6 reales pasan. |
| 6 | Columna **`price_charged`** | El sistema real usa **`precio`** en `barber_citas` y en `barber_servicios`. Renombrarla obligaría a tocar todos los workflows. | `precio numeric(10,2)`. |
| 7 | Columna **`payment_method`** | **Rechazaste los pagos con tarjeta** explícitamente. No tiene sentido guardar un método de pago que no se usará. | Eliminada junto con todo lo de pagos. |
| 8 | Tabla **`customers`** con `loyalty_points`, `preferences JSONB` | Duplica `barber_clientes`, que ya tiene `visitas`, `ticket_promedio`, `no_shows`, `etiqueta`... y está en uso por el agente. Dos CRMs es la forma más segura de que se desincronicen. | `barber_clientes` tal cual, con sus 16 columnas reales. |
| 9 | Tabla **`services`** con `image_url`, `description`, `category` | El catálogo real (`barber_servicios`) tiene `clave, nombre, precio, duracion_min, activo`. Las columnas extra no tienen datos ni quien los llene. | `barber_servicios` con el catálogo real de 8 servicios y precios reales. |
| 10 | Nombres genéricos en inglés (`appointments`, `customers`, `services`) | El sistema local usa el prefijo **`barber_`** justo para no chocar con las ~140 tablas internas de n8n (`workflow_entity`, `execution_entity`, ...) que viven en el mismo `public`. | Prefijo `barber_` en todo. Las queries de n8n funcionan **sin cambiar una coma**. |
| 11 | **`EXCLUDE USING gist (barber_id WITH =, rango WITH &&)`** | **Era la mejor idea del documento y la conservé**, pero sin `barber_id`: con un solo barbero, el rango temporal por sí solo ya garantiza que no haya doble reserva; mantenerlo sería una columna comodín sin función. También cambié `'pending','confirmed'` por `'agendado','confirmado'`. | `EXCLUDE USING gist (tstzrange(inicio, fin, '[)') WITH &&)` con `WHERE estado IN ('agendado','confirmado')`. |
| 12 | **`daily_metrics`** con `status = 'completed'` y `SUM(price_charged)` | La vista tenía los mismos errores. Habría contado **siempre 0 ingresos**. | `daily_metrics` con estados reales, `precio`, y añadidos: `tasa_no_show_pct`, `minutos_agenda`, `canceladas`, `reprogramadas`, `pendientes`. |
| 13 | **Pagos**: Mercado Pago, Stripe, WhatsApp Payments, anticipos 20-30% | **Rechazaste los pagos con tarjeta.** | Nada de pagos: ni tablas, ni columnas, ni webhooks. |
| 14 | **Airtable**, **Twilio**, **Make/Zapier**, **ElevenLabs**, **Pinecone** | Son de pago o están fuera de alcance. Regla tuya: **solo herramientas gratis**. | Descartados. |
| 15 | **OpenAI Vision** y **Whisper** | **Rechazaste procesar imagen y audio.** | Nada de multimodal. |
| 16 | **reCAPTCHA** | Lo vetaste explícitamente. | Nada de CAPTCHA. |
| 17 | **`CREATE EXTENSION vector`** + `knowledge_base` + HNSW | El RAG sobre pgvector es interesante, pero hoy el agente no lo usa y añade una dependencia (los embeddings, de pago) que choca con "solo gratis". Además multiplicaría el uso de disco. | Descartado por ahora. Se puede añadir después sin tocar nada de esto. |

### Lo que sí conservé del documento

- ✅ **La constraint `EXCLUDE USING gist`** — la mejor idea, adaptada a un solo
  barbero. Verificada funcionando de verdad.
- ✅ **La vista materializada de KPIs** — adaptada a los estados y campos reales,
  con `REFRESH ... CONCURRENTLY` documentado.
- ✅ **Los índices para reportes** — y añadí índices **parciales** que el
  documento no tenía: `idx_barber_citas_vivas` para la consulta más caliente
  ("citas vivas de ahora en adelante") y dos para los recordatorios pendientes.
- ✅ **La idea de la consulta atómica anti-doble-reserva** — la versión del
  documento usaba un `WHERE NOT EXISTS`, que tiene una carrera entre
  transacciones. Con la constraint `EXCLUDE` montada, ni siquiera hace falta:
  el motor lo garantiza.

---

## 11. El esquema entregado

### Las 10 tablas (espejo fiel de las locales)

| Tabla | Para qué |
|---|---|
| `barber_clientes` | CRM por JID de WhatsApp (16 columnas reales) |
| `barber_servicios` | Catálogo real: 8 servicios con precios y duraciones |
| `barber_operadores` | Quién puede mandar comandos (los 2 JID del dueño) |
| **`barber_citas`** | **La tabla central.** 1 fila = 1 cita, PK = ID del evento de Calendar |
| `barber_bloqueos` | Festivos, vacaciones, ausencias |
| `barber_pausas` | Bot en pausa para un número |
| `barber_escalaciones` | Casos que el bot no pudo cerrar |
| `barber_lista_espera` | Clientes esperando hueco |
| `barber_consentimiento` | Prueba del permiso de marketing |
| `barber_auditoria` | Bitácora de cada acción del agente |

Más: la vista materializada `daily_metrics`, la vista
`metricas_ultimos_30_dias` y la función de apoyo `barber_hueco_libre()`.

### Los estados reales (los que usa el sistema)

```
agendado, confirmado, atendido, no_show, cancelado, reprogramado
```

### Qué bloquea el horario y qué no

La constraint solo bloquea las citas **vivas**:

| Estado | ¿Bloquea el horario? | Por qué |
|---|---|---|
| `agendado` | **Sí** | Está reservado |
| `confirmado` | **Sí** | Está reservado |
| `atendido` | No | Ya pasó, el día se cerró |
| `no_show` | No | El cliente no vino, el hueco se liberó |
| `cancelado` | No | Se liberó explícitamente |
| `reprogramado` | No | Se movió a otra fecha |

Consecuencia práctica: **cancelar una cita libera su horario automáticamente**,
sin ninguna consulta extra. Verificado en las pruebas.

### Los archivos entregados

| Archivo | Qué es |
|---|---|
| `G:\Barberia\archivos\supabase-esquema.sql` | El DDL completo, idempotente, comentado en español |
| `G:\Barberia\archivos\probar-supabase-sql.py` | El validador contra el Postgres local |
| `G:\Barberia\archivos\SUPABASE-GUIA.md` | Este documento |

---

## 12. Evidencia de la validación

Se ejecutó `probar-supabase-sql.py` contra el Postgres local real
(contenedor `barberia-postgres`, PostgreSQL 17.11), creando un esquema temporal
`prueba_supabase` y borrándolo al terminar.

```
RESULTADO FINAL
  Comprobaciones: 92/92 correctas

  TODAS LAS COMPROBACIONES PASARON.
  -> El DDL de supabase-esquema.sql es valido y idempotente (3 pasadas).
  -> La constraint EXCLUDE impide de verdad el doble-booking.
  -> La vista materializada cuadra con las cifras calculadas a mano.
  -> Las queries reales de n8n corren SIN modificar el esquema.
```

Para reproducirlo:

```
C:\Users\kimbo\.cherrystudio\bin\uv.exe run python G:\Barberia\archivos\probar-supabase-sql.py
```

### Lo que cubre

| Bloque | Qué comprueba |
|---|---|
| 0 | El contenedor responde y `btree_gist` está disponible |
| 2 | El DDL se ejecuta **sin errores de sintaxis** |
| 3 | Las 10 tablas, la matview, la vista, la constraint, los 8 servicios, los 2 operadores, RLS en 10 y 0 políticas |
| 4 | **Idempotencia: 3 pasadas completas sin errores**, sin duplicar nada |
| 5-6 | **La prueba clave:** la constraint rechaza solape total, parcial, contenido y envolvente; acepta huecos adyacentes y citas cerradas; bloquea un `UPDATE` que provoca solape; un `INSERT` ya cancelado sí pasa |
| 6.4 | Los estados en inglés del documento **son rechazados**; los 6 reales **pasan** |
| 7 | `daily_metrics` con cifras **calculadas a mano** (19 citas, 400 de ingresos, ticket 133.33, 25.00% no-show) y `REFRESH CONCURRENTLY` |
| 8 | `barber_hueco_libre()`: domingo cerrado, cierre a las 20:00, bloqueos |
| 9 | **Las queries reales de n8n corren sin cambiar el esquema** (leer estado, leer ficha, los dos UPSERT) |
| 9 | El error tiene SQLSTATE **`23P01`**, capturable desde plpgsql |
| 10 | **Limpieza completa**: el esquema de prueba desaparece y `public` queda intacto |

### Dos bugs reales que encontró la validación

La validación no fue un trámite: encontró **dos defectos reales** en mi DDL, que
ya están corregidos. Esto es exactamente para lo que sirve probar en vez de
suponer.

1. **El `DROP MATERIALIZED VIEW` rompía la idempotencia.** La primera versión
   usaba `DROP MATERIALIZED VIEW IF EXISTS ...`, y en la segunda pasada Postgres
   fallaba con *"cannot drop materialized view daily_metrics because other
   objects depend on it"*, porque la vista `metricas_ultimos_30_dias` depende de
   ella. **Arreglado** añadiendo `CASCADE` (la vista se vuelve a crear más abajo,
   así que no se pierde nada).

2. **El orden de `REVOKE` y `REFRESH` rompía la segunda pasada.** Los `REVOKE`
   iban antes del `REFRESH`, y en un proyecto donde los roles `anon` o
   `authenticated` no existen todavía el script habría abortado. **Arreglado**
   moviéndolos después del `REFRESH` y envolviéndolos en un bloque `DO` que
   comprueba la existencia del rol antes de tocarlo.

También dejé de declarar `CREATE EXTENSION pgcrypto`: el Postgres local no la
tiene y `gen_random_uuid()` ya es parte del núcleo desde Postgres 13, así que
era una dependencia innecesaria que podía hacer fallar el script.

### Verificación de que el Postgres local quedó intacto

```
Esquemas                                              -> information_schema, public
Esquema de prueba existe?                             -> 0
Extensiones                                           -> plpgsql 1.0, unaccent 1.1, uuid-ossp 1.1
btree_gist / pgcrypto instaladas?                     -> 0
Tablas barber_*                                       -> 11
Roles que creo el script                              -> 0
daily_metrics en public?                              -> 0
barber_citas: filas                                   -> 0
n8n sigue con sus tablas (workflow/execution/creds)   -> 3
```

Todo igual que al empezar. No se tocó nada de producción ni de n8n.

---

## 13. Qué necesito de ti

Solo una cosa, y solo si quieres que n8n escriba solo en Supabase:

### La secret key

`Dashboard → Settings → API Keys → "Publishable and secret API keys"` →
copiar la que empieza por **`sb_secret_...`**.

`https://supabase.com/dashboard/project/zucgrcyzofelmiorvxhb/settings/api-keys`

Si no ves esa pestaña, pulsa antes **`Create new API keys`** (es seguro).

> ⚠️ **Pásala por un canal privado**, no por WhatsApp ni por un documento que
> pueda acabar en el repositorio. Esa clave salta RLS por completo: quien la
> tenga puede leer, escribir y borrar toda la base.

### Alternativa (recomendada para empezar)

**No me hace falta nada.** El SQL ya está validado. Abre el SQL Editor y pégalo
(sección 4). Con eso la base queda creada y lista. La secret key solo hace falta
para darle a n8n acceso automático, y ese paso se puede dar más adelante.

---

## 14. Lo que NO he hecho (para que no haya malentendidos)

- ❌ **No he creado nada en Supabase.** Ni una tabla. Es imposible con las claves
  dadas, y no voy a decir lo contrario.
- ❌ **No he tocado ningún workflow de n8n.** Solo evalué la integración, como
  pediste.
- ❌ **No he implementado pagos.** Los rechazaste.
- ❌ **No he dejado nada en el Postgres local.** El esquema de prueba, los roles
  temporales y los datos de prueba están borrados y verificados.

Y lo que sí está hecho y comprobado:

- ✅ Proyecto Supabase verificado como vivo (HTTP 200 reales).
- ✅ Límites de las claves verificados **empíricamente**, no supuestos.
- ✅ Esquema diseñado para **un solo barbero**, estados reales, sin pagos.
- ✅ DDL validado contra Postgres real: **92/92 comprobaciones**.
- ✅ Idempotencia probada con **3 pasadas** completas.
- ✅ Anti-doble-reserva probada en **9 escenarios** distintos.


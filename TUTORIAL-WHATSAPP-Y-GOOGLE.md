# Tutorial: conectar WhatsApp (Evolution API) y Google

Estado actual de tu máquina, ya verificado:

| Servicio | Estado | Dónde |
| --- | --- | --- |
| n8n 2.40.6 | Corriendo (HTTP 200) | http://localhost:5678 |
| Postgres (n8n) | Corriendo | interno |
| **Evolution API 2.3.7** | **Corriendo (HTTP 200)** | http://localhost:8080 |
| Evolution Manager (QR) | **Corriendo (HTTP 200)** | http://localhost:3000 |
| Instancia `hector` | `connecting` — espera tu escaneo | QR en `qr-whatsapp.png` |

Ya verifiqué que **n8n alcanza Evolution por la red interna** (`evolution_api:8080`
responde desde dentro del contenedor de n8n). Eso significa que no hace falta
exponer nada a internet para las pruebas locales.

> **Dos problemas reales que encontré y ya corregí**, por si vuelven a aparecer:
> 1. Postgres de Evolution no arrancaba porque Compose leía `${EVO_POSTGRES_...}`
>    del `.env` equivocado. Se pasó a `env_file` directo.
> 2. **El Manager oficial venía roto**: su `nginx.conf` incluía `must-revalidate`
>    en `gzip_proxied`, valor que nginx rechaza, así que reiniciaba en bucle.
>    Lo corregí montando `archivos/manager-nginx.conf`. Si actualizas la imagen,
>    revisa que ese archivo siga montado.

---

# PARTE 1 — Conectar tu WhatsApp (tu número personal)

## Paso 0: entrar al Manager (la pantalla de login)

Si ves el formulario **Evolution Manager → "Please enter your credentials"**,
llénalo así:

| Campo | Qué poner |
| --- | --- |
| **Server URL** | `http://localhost:8080` ← **NO el 3000** |
| **API Key Global** | `CLAVE_EVOLUTION_AQUI` |

**El error más común es dejar el Server URL en `http://localhost:3000`**
(que es lo que el formulario trae por defecto). Eso apunta al Manager mismo,
no a la API. Ya lo comprobé:

```
http://localhost:8080/instance/fetchInstances  -> application/json  ✅ la API
http://localhost:3000/instance/fetchInstances  -> text/html         ❌ el Manager
```

La API Key es la que generé para ti y también está en `G:\Barberia\.env.evolution`
(línea `AUTHENTICATION_API_KEY`). Si alguna vez la pierdes en el Manager, la
recuperas con:

```powershell
$docker = "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin\docker.exe"
$env:DOCKER_CONFIG = "G:\Barberia\.docker"
& $docker exec evolution_api printenv AUTHENTICATION_API_KEY
```

> **Si no puedes entrar al Manager**, no pasa nada: es solo una interfaz bonita.
> Todo lo esencial (QR, estado, enviar mensajes) se hace por la API del puerto
> 8080, que es la que n8n usa. El Manager es opcional.

## Paso 1: escanea el QR

Abre el archivo **`qr-whatsapp.png`** que está en tu carpeta, o entra a
**http://localhost:3000** (el Manager) y busca la instancia `hector`.

En tu teléfono:

1. Abre **WhatsApp**
2. Toca los **tres puntos** (arriba a la derecha) → **Dispositivos vinculados**
3. Toca **Vincular un dispositivo**
4. Escanea el QR de la pantalla

> **El QR caduca en ~60 segundos.** Si tarda, genera uno nuevo con el comando
> de "Si el QR caducó" al final de esta sección.

## Paso 2: verifica que quedó conectado

```powershell
$docker = "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin\docker.exe"
$env:DOCKER_CONFIG = "G:\Barberia\.docker"

# Ver el estado (debe decir "open" en connectionStatus)
& $docker exec evolution_api sh -c 'curl -s -H "apikey: $AUTHENTICATION_API_KEY" http://localhost:8080/instance/fetchInstances'
```

Debe aparecer `"connectionStatus":"open"` y tu número en `ownerJid`.

## Paso 3: prueba que recibe mensajes

Manda un WhatsApp a tu propio número desde **otro** teléfono (o pídele a alguien).
Luego revisa los registros:

```powershell
& $docker logs --tail 40 evolution_api
```

Debes ver el evento `messages.upsert`. Eso significa que WhatsApp ya llega a
Evolution.

## Paso 3.5: la pantalla "Webhook" del Manager → **NO configures nada ahí**

Cuando entras a **Events → Webhook** en el Manager y ves la lista de eventos
(`APPLICATION_STARTUP`, `CALL`, `MESSAGES_UPSERT`, …), **déjala como está y sal**.

**No marques eventos ni guardes.** El webhook ya está configurado por variables
de entorno, y hacerlo desde ahí duplicaría los mensajes. Te explico:

| Mecanismo | Cómo se configura | ¿Lo usas? |
| --- | --- | --- |
| **Webhook global** | `.env.evolution` → `WEBHOOK_GLOBAL_ENABLED` + `WEBHOOK_GLOBAL_URL` | **Sí, ya está activo** |
| **Webhook por instancia** | La pantalla que estás viendo | **No, déjalo vacío** |

Evolution soporta **los dos a la vez**, y si activas ambos **recibirás cada
mensaje dos veces** — el bot respondería doble al cliente. Ya verifiqué que tu
webhook por instancia está vacío (`/webhook/find/hector` devuelve `null`), así
que solo trabaja el global. **Así está bien.**

### ⚠️ LECCIÓN IMPORTANTE: los eventos no declarados valen `true`

Esto nos costó un **bucle de 518 ejecuciones en 10 minutos**, que es justo el
escenario que puede hacer que WhatsApp **banee tu número**.

Al principio solo declaré 6 eventos en el `.env.evolution`, pensando que los
demás quedaban apagados. **Error:** los eventos que NO declaras toman el valor
**por defecto de la imagen, que es `true`**. Así empezaron a llegar en masa
eventos como `chats.upsert`, y **cada uno disparaba una ejecución en n8n**.

**La solución** (ya aplicada): declarar **todos** los eventos explícitamente,
con solo uno en `true`.

```bash
# En .env.evolution — declarar los 27, aunque casi todos sean false
WEBHOOK_EVENTS_MESSAGES_UPSERT=true    # <- el único que necesitas
WEBHOOK_EVENTS_CHATS_UPSERT=false
WEBHOOK_EVENTS_SEND_MESSAGE=false
WEBHOOK_EVENTS_PRESENCE_UPDATE=false
# ... y así los 27
```

`MESSAGES_UPSERT` es el evento de "llegó un mensaje". Los demás generan
ejecuciones inútiles. Después de cambiar esto, **recrea el contenedor**:

```powershell
& $docker compose -f docker-compose.evolution.yml up -d --force-recreate evolution_api
```

### 🛡️ Protección adicional: el nodo `IF - No es del bot`

Además del arreglo anterior, hay un nodo **`IF - No es del bot`** justo después
de `Normalizacion`. Corta cualquier mensaje que venga con `fromMe=true` (es
decir, enviado por el propio bot).

Es una **segunda capa de defensa**: si algún día se vuelve a activar por error un
evento de mensajes salientes, el bot no se responderá a sí mismo.

> **Si ves el bot respondiendo a sus propios mensajes**, detén el workflow
> inmediatamente (interruptor *Active*) y revisa estas dos cosas: los eventos del
> `.env.evolution` y que el nodo `IF - No es del bot` siga existiendo.

## ⚠️ Aviso importante sobre usar tu número personal

> **Si algún día quieres cambiar la URL del webhook**, hazlo en `.env.evolution`
> y recrea el contenedor, no en esa pantalla:
> ```powershell
> & $docker compose -f docker-compose.evolution.yml up -d --force-recreate evolution_api
> ```

## ⚠️ Aviso importante sobre usar tu número personal

**Vas a perder WhatsApp en ese teléfono mientras esté vinculado.** No es un
error: al vincular como dispositivo, WhatsApp Web/API toma la sesión. En la
práctica:

- **Tu teléfono sigue funcionando** para WhatsApp normal (Baileys es
  multi-dispositivo), pero la sesión depende de que el teléfono esté encendido y
  con internet al menos una vez cada ~14 días.
- **No uses tu número personal para producción.** Para el VPS conviene un
  **número dedicado de la barbería**. Razón concreta: si WhatsApp detecta
  automatización en un número personal, puede **banearlo**, y perderías tu
  WhatsApp personal.
- Para pruebas locales está bien. Para producción: compra un chip aparte.

## Si el QR caducó

```powershell
$docker = "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin\docker.exe"
$env:DOCKER_CONFIG = "G:\Barberia\.docker"

# Pide un QR nuevo
& $docker exec evolution_api sh -c 'curl -s -H "apikey: $AUTHENTICATION_API_KEY" http://localhost:8080/instance/connect/hector'
```

Ese comando devuelve un JSON con `base64` (otro QR nuevo) y `pairingCode`.

> **Alternativa sin cámara:** el `pairingCode` sirve para vincular escribiendo un
> código en vez de escanear. En WhatsApp → Dispositivos vinculados →
> "Vincular con número de teléfono".

---

# PARTE 1.5 — ¿Cuánto cuesta esto? (respuesta corta: $0)

Buena noticia: **Evolution API es gratis, y legalmente gratis para uso
comercial.**

## Evolution API: $0

Lo confirmé en su documentación oficial de licenciamiento:

- **100 % gratuita**, open source bajo **Apache 2.0**
- **Self-hosted**: corre en tu máquina o en tu VPS
- **Sin límite de instancias, sin límite de mensajes**, y **sin funciones
  bloqueadas** por plan
- **Uso comercial permitido** (puedes cobrar por el servicio de barbería)
- **No hay funciones de pago** dentro del producto open source

**El único matiz:** a partir de la versión **2.4.0** (tú tienes la 2.3.7), pide
una **activación de licencia gratuita** la primera vez: das correo y teléfono, y
te registra en el tier `community`. Es gratis, no limita nada, y existe para que
la fundación mida cuánta gente usa el proyecto. Lo que se recopila son datos
técnicos agregados (versión, contadores, IP). **No recopila tus mensajes,
contactos ni números de clientes.**

> Como estás en la **2.3.7**, todavía **no te pide activación**. Si actualizas
> a 2.4.0 o superior, te aparecerá ese registro gratuito.

## Lo que sí cuesta dinero (para que no haya sorpresas)

| Concepto | Costo real |
| --- | --- |
| Evolution API | **$0** (open source) |
| n8n self-hosted | **$0** (fair-code, gratis para uso propio) |
| Docker Desktop | **$0** en tu caso (es gratis para uso personal / empresa pequeña) |
| Tu WhatsApp | **$0** — usas tu número normal |
| Google Calendar / Sheets | **$0** — las APIs son gratis en este volumen |
| **Uncensored AI (el modelo)** | **Se paga por uso** — aquí sí gastas |
| **VPS para producción** | **~$5-15 USD/mes** |

**Los dos únicos gastos reales son el modelo y el VPS.** De hecho, ya viste el
primero en tu captura: ~7.5 USD de consumo de tokens. Ese es el que hay que
vigilar, no Evolution.

## Comparación con la alternativa "oficial"

Podrías usar la **API oficial de WhatsApp Business** (Meta) en vez de Evolution.
Diferencias prácticas:

| | Evolution API | API oficial de Meta |
| --- | --- | --- |
| Costo | $0 | Por conversación (varía por país) |
| Alta | Escaneas un QR, listo | Trámite con Meta, número verificado, revisión |
| Riesgo | El número puede ser baneado si abusas | Es la vía oficial, sin riesgo de ban |
| Ideal para | Empezar, probar, negocio chico | Empresas con presupuesto y volumen |

Para una barbería, Evolution es la opción sensata: sin trámite y sin costo fijo.
Solo respeta el aviso de abajo sobre el número.

## VPS: qué buscar

Cuando pases a producción, necesitas un servidor Linux con Docker. Para este
stack (n8n + Postgres + Evolution + Redis) basta:

- **2 vCPU y 4 GB de RAM** como mínimo cómodo (con 2 GB va justo)
- **40 GB de disco** SSD
- Ubuntu 22.04 o 24.04
- Proveedores típicos: Hetzner (~$5/mes), DigitalOcean (~$12/mes), Vultr, Contabo

El mismo stack que ya corre en tu máquina sube tal cual: los dos
`docker-compose` y los `.env`. Lo único que cambia está en la **Parte 4**.

---

# PARTE 2 — Google: obtener los datos del Sheet y del Calendar

Esta es tu pregunta principal: **cómo obtienes los datos para el Sheet y Excel**.
Son dos cosas distintas y conviene no confundirlas:

| Qué | Para qué | Cómo se conecta |
| --- | --- | --- |
| **Google Calendar** | El agente agenda citas | Credencial OAuth2 en n8n |
| **Google Sheets** | El agente registra cada cita (tu "Excel") | Credencial OAuth2 en n8n |

Ambas usan **la misma** app de Google Cloud. La creas una vez y usas los mismos
Client ID y Secret en las dos credenciales de n8n.

## Paso 1: habilita las 3 APIs

En tu proyecto `n8n-Barberia` (el que ya tienes abierto):

Ve a **APIs y servicios → Biblioteca** y habilita una por una:

1. **Google Calendar API**
2. **Google Sheets API**
3. **Google Drive API** ← *obligatoria*: Google Sheets la necesita por dentro

Si falta la de Drive, Sheets falla aunque todo lo demás esté bien.

## Paso 2: configura la pantalla de consentimiento (aquí va tu "lista")

**APIs y servicios → Pantalla de consentimiento de OAuth**:

- Tipo de usuario: **Externo** → Crear
- Nombre de la app: `Barberia`
- Tu correo en "asistencia" y "contacto"
- Guardar y continuar en cada pantalla
- En **Usuarios de prueba** → **+ Add users** → **`crir627@gmail.com`** → Guardar

**Esa es la lista de la que preguntabas.** Sin tu correo ahí, Google te dirá
*"Acceso bloqueado: esta app no completó el proceso de verificación"*.

> **Y lo más importante:** en modo Prueba, **Google invalida el permiso cada 7
> días**. Cuando eso pase, el agente dejará de agendar sin avisar y tendrás que
> volver a autorizar. Si te cansa, en esa misma pantalla hay un botón
> **"Publicar app"**.

## Paso 3: crea el Client ID y Secret

**Aquí es donde casi todo el mundo se atora**, porque los datos NO están en la
página de APIs que estabas viendo (Biblioteca → Google Drive API). Están en otra
sección.

### Dónde exactamente

En el menú de la izquierda de Google Cloud busca **"Credenciales"** (está justo
debajo de "Biblioteca"). O entra directo:

```
https://console.cloud.google.com/apis/credentials?project=n8n-barberia-490416
```

### 3.1 Primero la pantalla de consentimiento

Al entrar verás un aviso: *"Para crear un ID de cliente de OAuth, primero
configura la pantalla de consentimiento"*. Clic en **Configurar pantalla de
consentimiento** y llena:

- Tipo de usuario: **Externo** → Crear
- Nombre de la app: `Barberia`
- Tu correo en "asistencia" y "contacto"
- **Guardar y continuar** en cada pantalla
- **Usuarios de prueba** → **+ Add users** → `crir627@gmail.com` → Guardar

### 3.2 Ahora sí: crear el Client ID

Vuelve a **Credenciales** → **+ Crear credenciales** → **ID de cliente de OAuth**.

- Tipo de aplicación: **Aplicación web** ← no elijas "Aplicación de escritorio"
- Nombre: `n8n barberia`
- **URIs de redireccionamiento autorizados** → **+ Agregar URI** → pega:

```
http://localhost:5678/rest/oauth2-credential/callback
```

- **Crear**

### 3.3 Copia los dos valores

| Lo que Google te muestra | Dónde va en n8n |
| --- | --- |
| **ID de cliente** (termina en `.apps.googleusercontent.com`) | **Client ID** |
| **Secreto de cliente** (empieza con `GOCSPX-`) | **Client Secret** |

> ⚠️ **El Secret se muestra completo una sola vez.** Cópialo en ese momento. Si lo
> pierdes, no pasa nada grave: creas uno nuevo desde la lista de credenciales.

### 3.4 Pégalos en n8n las dos veces

1. n8n → **Credentials → + Add credential** → **Google Calendar OAuth2 API**
2. Pega Client ID y Client Secret → **Sign in with Google** → tu cuenta
3. *"Google no ha verificado esta app"* → **Avanzado → Ir a Barberia (no
   seguro)** → **Permitir** → **Save**
4. Repite con **Google Sheets OAuth2 API** y los **mismos** valores

Es una sola app de Google, pero n8n guarda dos credenciales separadas, así que
autorizas dos veces.

### 3.5 Verifica que las 3 APIs estén habilitadas

Antes de seguir, confirma en **Biblioteca** que las tres digan *"API habilitada"*:

- **Google Calendar API**
- **Google Sheets API**
- **Google Drive API** ← indispensable: Sheets la usa por dentro

Si falta alguna, el flujo fallará aunque el Client ID esté perfecto. El error
típico cuando falta Drive es *"The caller does not have permission"*.

## Paso 4: los IDs de tus archivos ya están puestos

Buena noticia: **no tienes que buscar los IDs.** En el JSON que te entregué ya
vienen configurados los tuyos:

| Recurso | ID | Dónde se usa |
| --- | --- | --- |
| Hoja *Citas barbería* | `17iqMobaQBz29tZ5hP5Q9ejzSJUfkov8lkjB245vpoZY` | Registrar citas + trigger de recordatorios |
| Calendario *BARBER* | `391cc272be5989fd77b45438f2f61e9c754501eb5d1b3a...@group.calendar.google.com` | Agendar / cancelar / reagendar |

**Asegúrate de que la cuenta que autorices tenga acceso a ambos.** Si la hoja y
el calendario son de otra cuenta (o te los compartió el vendedor del flujo),
tendrás que compartirlos con `crir627@gmail.com`:

- **En Sheets:** botón *Compartir* → agrega tu correo como **Editor**
- **En Calendar:** *Configuración del calendario* → *Compartir con determinadas
  personas* → agrega tu correo con **"Hacer cambios en los eventos"**

## Sobre el "Excel"

Tu hoja *Citas barbería* en Google Sheets **es** tu base de datos. Puedes
descargarla como Excel cuando quieras (*Archivo → Descargar → Microsoft Excel*),
pero el agente trabaja sobre la hoja en línea, no sobre un `.xlsx` local.

Las columnas que el agente escribe están definidas en el flujo. Esta es la
estructura esperada:

| ID | Estatus | Nombre | Servicio | Precio del servicio | Día | Hora | Numero celular |
| --- | --- | --- | --- | --- | --- | --- | --- |

> **Un detalle que importa:** la columna se llama exactamente **`Día `** (con
> acento y con un espacio al final). Tu hoja ya la tiene así. Si la renombras, el
> registro deja de funcionar.

---

# PARTE 3 — Conectar todo y probar

## Paso 1: asigna las credenciales a los nodos

Crear la credencial no la asigna sola. Abre cada workflow y revisa que los nodos
sin triángulo rojo tengan su credencial:

**Workflow "Barberia — Agente de citas"**
- `OpenAI Chat Model` → *Uncensored AI (OpenAI-compatible)*
- `Consultar agenda`, `Agendar cita`, `Cancelar cita`, `Reagendar` → Google Calendar
- `Registrar en hoja de citas` → Google Sheets
- `Postgres Chat Memory` → Postgres (host `postgres`, no `localhost`)
- `Transcribe a recording`, `Describe imagen` → la credencial de **OpenAI** original

**Workflow "Barberia — Recordatorios"**
- `Google Sheets Trigger`, `Append or update row in sheet`,
  `OBTENER INFO DE CITA ELIMINADA` → Google Sheets

## Paso 2: activa los workflows ⚠️

**Esto es obligatorio y es el error más común.** Ahora mismo tus workflows están
**inactivos** (lo verifiqué: `active=false`).

El webhook `/webhook/hector` **solo existe cuando el workflow está activo**. Si
no lo activas, Evolution manda el mensaje a n8n y n8n responde 404: el bot
simplemente no contesta y parece que "no funciona la API de WhatsApp".

Actívalos con el interruptor **Active** (arriba a la derecha) en:
1. *Barberia — Agente de citas*
2. *Barberia — Recordatorios de cita*

Comprueba que el webhook quedó registrado:

```powershell
& $docker exec barberia-postgres psql -U barberia -d barberia -c 'SELECT method, "webhookId" FROM webhook_entity;'
```

## Paso 3: la prueba de verdad

Manda un WhatsApp a tu número desde otro teléfono:

```
Hola, quiero un corte mañana a las 4 de la tarde, me llamo Juan
```

Debe pasar esto, en orden:

1. El bot responde por WhatsApp
2. Se crea el evento en tu **Google Calendar**
3. Aparece una fila nueva en tu **hoja de Citas barbería**

Si el bot contesta pero **no** crea el evento → Calendar mal conectado.
Si responde pero **no** hay fila → Sheets mal conectado.
Si **no** contesta nada → el workflow no está activo, o el webhook no llega.
Revisa `& $docker logs --tail 40 evolution_api`.

---

# PARTE 4 — Cuando lo pases al VPS

Lo que cambia respecto a tu máquina local:

1. **`WEBHOOK_URL` de n8n**: dejará de ser `http://localhost:5678/` y será tu
   dominio (ej. `https://n8n.tudominio.com/`).
2. **La URL de callback de Google**: deberás **agregar** la nueva
   (`https://n8n.tudominio.com/rest/oauth2-credential/callback`) en el mismo
   Client ID. No borres la de localhost si sigues probando.
3. **El webhook de Evolution** apuntará al dominio público, no a
   `barberia-n8n:5678`.
4. **HTTPS obligatorio.** Google no acepta callbacks en HTTP que no sea localhost.
5. **El QR se vuelve a escanear** si migras el volumen, o cópialo. Es más limpio
   volver a vincular el número en el servidor.
6. **Ya con dominio, quita `127.0.0.1:`** de los puertos en los compose para que
   sea accesible (con un proxy inverso y certificado delante).

---

# Comandos útiles

```powershell
$docker = "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin\docker.exe"
$env:DOCKER_CONFIG = "G:\Barberia\.docker"

# Ver todos los contenedores
& $docker ps --format "{{.Names}}|{{.Status}}|{{.Ports}}"

# Arrancar / detener cada stack
& $docker compose up -d                                  # n8n + Postgres
& $docker compose -f docker-compose.evolution.yml up -d  # Evolution

# Registros en vivo
& $docker logs -f evolution_api
& $docker logs -f barberia-n8n

# Estado de WhatsApp
& $docker exec evolution_api sh -c 'curl -s -H "apikey: $AUTHENTICATION_API_KEY" http://localhost:8080/instance/fetchInstances'

# Reiniciar solo Evolution
& $docker restart evolution_api
```

## Si el bot deja de responder

Revisa en este orden:

1. ¿La instancia de WhatsApp sigue `open`? (si el teléfono estuvo apagado mucho
   tiempo, la sesión se cae → vuelve a escanear el QR)
2. ¿El workflow de n8n está **Active**?
3. ¿El contenedor `barberia-n8n` está arriba?
4. `& $docker logs --tail 50 evolution_api` — busca errores de webhook

## Seguridad de tus archivos

- `.env` y `.env.evolution` tienen contraseñas y la llave de Evolution.
  **No los compartas ni los subas a un repositorio.**
- La llave de Uncensored AI **no está en ningún archivo**: vive solo en n8n.
- La llave de Evolution está en `.env.evolution` (porque la API la lee al
  arrancar). Para el VPS, mejor cámbiala por una tuya distinta.
- Los puertos están atados a `127.0.0.1`: **nada de esto está expuesto a
  internet** en tu máquina local. Correcto mientras pruebas.
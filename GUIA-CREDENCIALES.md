# Guía: credenciales para que el agente funcione

n8n ya corre en **http://localhost:5678** y tus dos workflows están dentro.
Solo faltan las credenciales. Son **tres**.

---

## PARTE 1 — La llave de Uncensored AI (2 minutos)

### Paso a paso

1. Entra a **http://localhost:5678** con tu cuenta (`crir627@gmail.com`).
2. En el menú de la izquierda, clic en **Credentials**.
3. Arriba a la derecha, botón **+ Add credential** (o "Create credential").
4. En el buscador escribe **OpenAI**. Aparecerá **"OpenAI account"**.
   Elígela. (No busques "Uncensored"; n8n no la conoce por ese nombre. Se usa
   la credencial de OpenAI porque tu proveedor habla el mismo idioma.)
5. Se abre un formulario con estos campos. Llénalo así:

| Campo | Qué poner | ¿Importa el nombre? |
| --- | --- | --- |
| **Credential name** | `Uncensored AI (OpenAI-compatible)` | **Sí, escríbelo igual.** El workflow busca este nombre. |
| **API Key** | tu llave `uai_sk_live_...` | Sí |
| **Organization ID** | *(déjalo vacío)* | No |
| **Base URL** | `https://api.uncensored.com/api/v1` | **Sí, crítico** |

6. Baja hasta **Add Custom Header** y haz clic para desplegarlo. Pon:
   - **Header Name:** `x-api-key`
   - **Header Value:** tu misma llave `uai_sk_live_...`

   *(Tu proveedor acepta tanto esta cabecera como `Bearer`; ponerla garantiza
   que funcione cualquiera de las dos.)*

7. Clic en **Save**. Debe decir "Connection tested successfully".

### Los tres errores que la gente comete aquí

1. **Poner la Base URL con `/chat/completions` al final.** Mal. n8n lo agrega
   solo, y quedaría duplicado. Debe terminar en **`/api/v1`**.
2. **Poner una barra al final** (`/api/v1/`). Puede fallar. Sin barra final.
3. **Llamarla distinto.** Si la nombras "Mi OpenAI" el workflow no la encuentra
   y tendrás que reseleccionarla a mano en el nodo *OpenAI Chat Model*.

> **Ojo:** deja la credencial vieja de OpenAI aparte (si aún la tienes). Los nodos
> **Whisper** (transcribir audios) y **Describe imagen** sí siguen usando
> `api.openai.com`. Si apuntas todo a Uncensored, se rompen los audios e imágenes.

---

## PARTE 2 — Google: ¿necesito una "lista de excepción"?

**Respuesta corta: sí, algo parecido, y es obligatorio.** No se llama "lista de
excepción" sino **"usuarios de prueba" (test users)**, y sin ella Google te
bloquea con *"Acceso bloqueado: esta app no completó el proceso de verificación"*.

Pero antes de que hagas clic en nada, lee la **advertencia crítica** del final:
hay una decisión que te va a ahorrar un dolor de cabeza cada 7 días.

### Lo que vas a hacer (resumen)

```
Google Cloud Console
  └─ 1. Crear un proyecto                      ("Barberia")
  └─ 2. Habilitar 2 APIs: Calendar y Sheets  (+ Drive, ver nota)
  └─ 3. Pantalla de consentimiento OAuth      ← aquí agregas tu correo como
                                                 "usuario de prueba"
  └─ 4. Crear credencial OAuth "Aplicación web"  ← aquí va la URL de n8n
  └─ 5. Copiar Client ID y Client Secret → pegarlos en n8n (x2)
```

### Paso a paso detallado

**1. Crea el proyecto**

Entra a https://console.cloud.google.com con tu cuenta de Google. Arriba,
clic en el selector de proyecto → **Nuevo proyecto** → nómbralo `Barberia` →
**Crear**. Asegúrate de que el selector quede en ese proyecto.

**2. Habilita las APIs**

Ve a **APIs y servicios → Biblioteca** y habilita, una por una:

- **Google Calendar API**
- **Google Sheets API**
- **Google Drive API** ← *necesaria*, Google Sheets la requiere por dentro

**3. Pantalla de consentimiento (aquí está tu "lista de excepción")**

Ve a **APIs y servicios → Pantalla de consentimiento de OAuth**.

- Tipo de usuario: **Externo** → **Crear**
- Nombre de la app: `Barberia`
- Correo de asistencia y de contacto: el tuyo
- **Guardar y continuar** en cada pantalla
- En **Permisos**, no hace falta agregar nada; **Guardar y continuar**
- En **Usuarios de prueba** → **+ Add users** → escribe **tu propio correo
  de Gmail** (`crir627@gmail.com`) → **Guardar**

> **Esa es la "lista de excepción".** Solo los correos que estén ahí podrán
> autorizar la app. Si el correo de la barbería es distinto al tuyo, agrégalo
> también.

**4. Crea la credencial**

> **Los datos NO están en la página de APIs.** Ve a **Credenciales** en el menú
> de la izquierda (justo debajo de "Biblioteca"), o entra directo:
> ```
> https://console.cloud.google.com/apis/credentials?project=n8n-barberia-490416
> ```

Ve a **APIs y servicios → Credenciales → + Crear credenciales → ID de cliente
de OAuth**.

Si te dice que primero configures la pantalla de consentimiento, hazlo (paso 3)
y vuelve.

- Tipo de aplicación: **Aplicación web** ← no elijas "Aplicación de escritorio"
- Nombre: `n8n barberia`
- En **URIs de redireccionamiento autorizados** → **+ Agregar URI** → pega
  exactamente:

```
http://localhost:5678/rest/oauth2-credential/callback
```

- **Crear**. Google te muestra el **Client ID** (termina en
  `.apps.googleusercontent.com`) y el **Client Secret** (empieza con `GOCSPX-`).

> ⚠️ **El Secret se muestra completo una sola vez.** Cópialo en ese momento.

**5. Ponlas en n8n (dos veces)**

En n8n → **Credentials → + Add credential**:

- Busca **Google Calendar OAuth2 API** → pega Client ID y Client Secret →
  **Sign in with Google** → elige tu cuenta → te preguntará si confías en una
  app no verificada: clic en **Avanzado → Ir a Barberia (no seguro)** →
  **Permitir**. Guarda.
- Repite con **Google Sheets OAuth2 API**, mismos datos.

---

## ⚠️ La advertencia que te va a importar

**En modo "Prueba" (Testing), Google invalida el permiso cada 7 días.** Tu
agente dejará de agendar sin avisar, y volverás a autorizar una y otra vez.

Hay dos caminos:

| Opción | Ventaja | Costo |
| --- | --- | --- |
| **A. Dejarlo en Prueba** y reautorizar cada 7 días | Cero trámites | Se te cae el agente cada semana |
| **B. Publicar la app** (pasar a Producción) | El permiso ya no caduca | Hay que pasar revisión de Google... **salvo si es solo para ti** |

**El detalle salvador:** si la app la usas **únicamente con tu propia cuenta**,
puedes dejarla en modo Prueba y **no** hay verificación de Google de por medio;
el problema de los 7 días afecta sobre todo a tokens de apps en Prueba con
varios usuarios. La recomendación práctica:

1. Empieza en **Prueba** con tu correo como usuario de prueba. Funciona de
   inmediato.
2. Si a los días ves que el token caduca, entonces publica la app
   (**Pantalla de consentimiento → Publicar app**). Al ser uso interno y con
   permisos sensibles, Google puede pedirte revisión; para uso propio suele
   bastar con publicarla.

> Hay una tercera vía que evita todo esto: usar una **cuenta de servicio**
> (Service Account). **Pero no te la recomiendo aquí**, y esta es la razón
> técnica: tu flujo 2 usa el nodo **Google Sheets Trigger**, y ese trigger
> **no soporta cuentas de servicio** todavía (hay una propuesta abierta en el
> repositorio de n8n, sin integrar). Usar cuenta de servicio te obligaría a
> rediseñar cómo detectas las citas nuevas. Quédate con OAuth2.

### Si algo falla

| Mensaje | Causa | Solución |
| --- | --- | --- |
| "Acceso bloqueado: no completó la verificación" | Tu correo no está en usuarios de prueba | Agrégalo en la Pantalla de consentimiento |
| "redirect_uri_mismatch" | La URL no coincide | Debe ser exactamente `http://localhost:5678/rest/oauth2-credential/callback`, sin `/` final |
| "Error 403: access_denied" | Igual que el primero | Revisa usuarios de prueba |
| El token caduca cada 7 días | App en modo Prueba | Publica la app |

---

## PARTE 3 — Postgres (la memoria del agente, 1 minuto)

El agente recuerda las conversaciones en Postgres, que ya está corriendo.

1. n8n → **Credentials → + Add credential** → busca **Postgres**.
2. Llénalo así (los valores están en el archivo `.env` de tu carpeta):

| Campo | Valor |
| --- | --- |
| **Host** | `postgres` ← **así, tal cual.** No `localhost`: n8n y la base son contenedores distintos y se hablan por el nombre del servicio. |
| **Database** | `barberia` |
| **User** | `barberia` |
| **Password** | *(está en `G:\Barberia\.env`, línea `POSTGRES_PASSWORD`)* |
| **Port** | `5432` |
| **SSL** | desactivado |

3. **Save** → debe probar la conexión con éxito.

> **Esta es la trampa más común:** si pones `localhost` falla, porque dentro del
> contenedor de n8n "localhost" es él mismo, no la base de datos. Usa
> `postgres`.

---

## Al terminar: conecta las credenciales a los nodos

Crear la credencial no la asigna sola. Abre cada workflow y revisa que los nodos
tengan la credencial seleccionada (si aparece un triángulo rojo, falta):

**Workflow "Barberia — Agente de citas"**
- `OpenAI Chat Model` → **Uncensored AI (OpenAI-compatible)**
- `Consultar agenda`, `Agendar cita`, `Cancelar cita`, `Reagendar` → Google Calendar
- `Registrar en hoja de citas` → Google Sheets
- `Postgres Chat Memory` → Postgres
- `Transcribe a recording` y `Describe imagen` → **la de OpenAI original** (no la de Uncensored)

**Workflow "Barberia — Recordatorios"**
- `Google Sheets Trigger`, `Append or update row in sheet`,
  `OBTENER INFO DE CITA ELIMINADA` → Google Sheets

### Prueba final

En el workflow del agente, clic en **Chat** (abajo) y escribe:

```
quiero corte mañana a las 4 de la tarde, me llamo Juan
```

Debe responder confirmando la cita **y** crear el evento en tu Google Calendar.
Si responde pero no crea el evento, es que el Calendar no quedó bien conectado.

---

## Sobre el costo (vi tu captura)

Tu pantalla muestra **24.8 millones de tokens de entrada** y ~7.5 USD. Eso no es
casualidad: **el agente reenvía todo el historial en cada mensaje.** El prompt del
sistema son ~2,500 tokens, y con la memoria de Postgres cada mensaje del cliente
vuelve a mandar la conversación completa.

Tres formas de bajarlo:

1. **Cambia de modelo.** En el nodo *OpenAI Chat Model* → campo **Model**, prueba
   ID manual con un modelo económico del catálogo:
   - `deepseek-v4-flash` — el más barato de todos
   - `gemini-2.5-flash` — rápido y económico
   - `glm-4.7-flash` — muy barato
   Todos ellos soportan herramientas (lo verifiqué).
2. **Limita la memoria.** En el nodo *Postgres Chat Memory*, pon una **ventana
   de contexto** (por ejemplo 10 mensajes) en vez de historial ilimitado.
3. **Revisa en tu panel de Uncensored** el gasto por día los primeros días, para
   confirmar el consumo real antes de dejarlo abierto al público.
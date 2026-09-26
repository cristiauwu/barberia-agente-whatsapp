# CONTEXTO PARA SUBAGENTES — Barber Chinos

Lee esto **completo antes de tocar nada**. Evita que redescubras lo que ya
sabemos y que rompas cosas.

---

## Qué es el proyecto

Agente de WhatsApp para la barbería **Barber Chinos** (un solo barbero:
**Esteban Aguilera**). Atiende clientes, agenda citas contra Google Calendar,
avisa al dueño y tiene un panel web.

Directorio de trabajo: `G:\Barberia`

---

## Estado actual (verificado, no supongas otra cosa)

| Pieza | Estado |
|---|---|
| Workflows de n8n | **3**: agente (48 nodos), recordatorios (17), vigilancia (5) |
| `verify.py` | **192/192** ✅ |
| n8n | `http://localhost:5678` (Docker, contenedor `barberia-n8n`) |
| Evolution API | `http://localhost:8080` (contenedor `evolution_api`, instancia `hector`) |
| Postgres | `barberia-postgres`, publicado en `127.0.0.1:5432` |
| Panel admin | `http://localhost:8765` (contenedor propio, **con contraseña**) |
| Panel producción | `http://localhost:8099` |

Los puertos 5678, 8080, 3000, 8099 y 8765 están abiertos y funcionando.

---

## RESTRICCIONES DEL DUEÑO (no negociables)

1. **No** se aceptan pagos con tarjeta.
2. **No** se procesan audios, imágenes ni documentos.
3. **No** se usa CAPTCHA.
4. **Solo herramientas gratuitas.** Si una gratuita necesita una de pago,
   buscar la variante gratuita o descartar la idea.
5. **Un solo barbero.** No crear tablas ni métricas "por barbero".
6. La hora del negocio es **America/Mexico_City (−06:00)**, fija.
7. El servicio debe **terminar antes de las 20:00**. Domingo cerrado.
8. Canal: **solo WhatsApp**.

---

## Cómo ejecutar Python (IMPORTANTE)

Usa siempre `uv run python <ruta>`.

**El harness NO captura el stdout de procesos nativos.** Usa este patrón:

```powershell
$uv="C:\Users\kimbo\.cherrystudio\bin\uv.exe"
$o="$env:TEMP\salida.txt"
$p=Start-Process -FilePath $uv -ArgumentList @("run","python","RUTA.py") `
   -NoNewWindow -Wait -PassThru -RedirectStandardOutput $o `
   -RedirectStandardError "$env:TEMP\err.txt"
Get-Content $o -Raw
Get-Content "$env:TEMP\err.txt" -Raw
```

Si necesitas una dependencia: `uv run --with psycopg[binary] python x.py`

**NO uses `git`** (no está en el PATH; hace falta `cmd /c`).

---

## Credenciales (leer del archivo, NUNCA escribir a mano)

```python
# Clave de la API de n8n (267 caracteres)
KEY = open(r"G:\Barberia\archivos\.n8n-key.txt", encoding="utf-8").read().strip()
```

Otras claves:
- Evolución API: en `G:\Barberia\.env.evolution` (`AUTHENTICATION_API_KEY`)
- Postgres: en `G:\Barberia\.env` (`POSTGRES_PASSWORD`)
- Contraseña del panel: `G:\Barberia\archivos\admin\.pwd-sitio.txt`

**Nunca escribas una clave en el código ni en un documento.** Si necesitas
leerla, léela del archivo.

---

## Cómo hablar con el bot (simular un cliente)

Webhook: `POST http://localhost:5678/webhook/hector`

```python
import json, subprocess, urllib.request, uuid
DOCKER=(r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop"
        r"\resources\bin\docker.exe")
key=subprocess.run([DOCKER,"exec","evolution_api","printenv",
                    "AUTHENTICATION_API_KEY"],
                   capture_output=True,text=True).stdout.strip()

body={"event":"messages.upsert","instance":"hector",
  "server_url":"http://evolution_api:8080","apikey":key,
  "date_time":"2026-09-26T23:00:00.000Z",
  "data":{"key":{"id":"T"+uuid.uuid4().hex[:10].upper(),
    "remoteJid":JID,"fromMe":False},
    "pushName":"Prueba","message":{"conversation":TEXTO},
    "messageType":"conversation"}}
req=urllib.request.Request("http://localhost:5678/webhook/hector",
    data=json.dumps(body).encode(),method="POST")
req.add_header("Content-Type","application/json")
urllib.request.urlopen(req,timeout=140)
```

**JIDs válidos** (otros dan HTTP 400 en Evolution):
- Cliente de pruebas: `5214501111805@s.whatsapp.net`
- Dueño: `524521206246@s.whatsapp.net` o `5214521206246@s.whatsapp.net`

**Espera ~15 s entre mensajes.** El bot tiene memoria por JID.

---

## Cómo leer la respuesta del bot

```python
def api(p):
    r=urllib.request.Request("http://localhost:5678/api/v1"+p)
    r.add_header("X-N8N-API-KEY", KEY)
    return json.loads(urllib.request.urlopen(r,timeout=90).read().decode())

WID="barberiaAgenteUncensored"
ex=api(f"/executions?workflowId={WID}&limit=5")
det=api(f"/executions/{ex['data'][0]['id']}?includeData=true")
run=det["data"]["resultData"]["runData"]
# el texto entrante  -> run["Normalizacion"]
# la respuesta       -> run["Mandar mensaje"]
```

---

## Datos del negocio

| | |
|---|---|
| Dirección | Calle Pinzón #574 · 452-281-8144 |
| Horario | Lunes a sábado, 10:00–20:00 · domingo cerrado |
| Estacionamiento | **No** hay (confirmado por el dueño) |
| Pagos | Efectivo o transferencia |
| Wifi | Sí |
| Tolerancia de retraso | 5 a 10 minutos |

**Los 8 servicios:**

| Servicio | Precio | Duración |
|---|---|---|
| Corte desvanecido o tijera | $150 | 40 min |
| Arreglo de barba | $100 | 20 min |
| Ceja | $30 | 10 min |
| Mascarilla | $50 | 20 min |
| Corte de cabello dama | $250 | 50 min |
| Planchado express | $150 | 30 min |
| Peinado | $300 | 45 min |
| Depilación | según zona | 30 min |

---

## Reglas de formato de WhatsApp

- **Negrita: `*un asterisco*`.** Dos (`**`) NO funciona en WhatsApp.
- Máximo **10 líneas** por respuesta.
- Sin marcos ASCII, sin líneas en blanco de más, sin espacios al final.
- 1 emoji como máximo.

---

## Trampas ya conocidas (esto te ahorrará horas)

| Trampa | Solución |
|---|---|
| Cada `psql -c` es **sesión nueva** | Manda todo el guion en un solo `psql -f -` |
| `psql` manda los ERROR a **stderr** | Lee siempre `stderr` |
| Un `PUT` a un workflow **activo** falla | `deactivate` → `PUT` → `activate` |
| URL con nombre de workflow (espacios) | Usa el `id` |
| Chrome headless fuerza **504 px** mínimo | Usa un iframe de 390 px para el móvil |
| Medir animaciones antes de tiempo | El preloader tarda 3,3 s |
| Un iframe `http` **no puede leer** `file://` | Inyecta el script en el propio archivo |
| El modelo es un objeto `{value:...}`, no un string | `m.get("value") if isinstance(m,dict) else m` |

---

## Lo que NO debes hacer

- **No** modificar el prompt del agente ni los workflows (salvo que tu
  misión lo diga explícitamente).
- **No** crear workflows en n8n. Si lo haces para una prueba, **bórralos**.
- **No** dejar citas de prueba en Google Calendar ni filas en la hoja. Si
  creas alguna, **bórrala** y dilo en tu reporte.
- **No** tocar `barber_citas`, `barber_clientes`, `barber_pausas` sin
  restaurar el estado original.
- **No** subir nada a GitHub ni a ningún repo.
- **No** instalar servicios de pago.

---

## Cómo reportar

- Escribe tu reporte en el archivo que diga tu misión.
- **No inventes resultados.** Solo lo que hayas ejecutado y visto.
- Si algo no se puede probar, dilo explícitamente y por qué.
- Da **evidencia literal**: el texto exacto, el código HTTP, el SQLSTATE.
- Al terminar, menciona qué limpiaste.
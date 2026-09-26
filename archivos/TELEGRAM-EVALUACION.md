# Evaluación: ¿conviene añadir un canal de Telegram? — Barber Chinos

**Fecha:** 25/09/2026
**Alcance:** evaluar la propuesta "Telegram Bot — Canal interno del staff" del documento
`Herramientas_APIs_Complementarias.md` (línea 343).
**Restricciones aplicadas:** solo herramientas gratis, sin CAPTCHA, sin pagos con tarjeta,
sin procesar imágenes ni audio.

---

## VEREDICTO EN UNA LÍNEA

> **NO conviene.** Telegram es técnicamente viable (lo comprobé), es gratis y no pide
> tarjeta, pero **no resuelve ningún problema que este negocio tenga**. No hay "staff"
> al que abrir un canal interno, no hay ruido que separar, y no hay ninguna acción
> sensible que aprobar. Añadirlo cuesta trabajo manual del dueño y le obliga a vigilar
> una segunda app **para ver la misma información que ya recibe por WhatsApp**.
>
> **No implementé nada y no creé ningún workflow nuevo.** La razón está en la sección 4.
> Lo que sí propongo es más barato, cabe en lo que ya existe y arregla problemas medidos
> (sección 5).

---

## 1. Qué existe hoy (comprobado, no asumido)

### 1.1 Workflows en n8n (versión 2.40.6, `http://localhost:5678`)

| Workflow | id | Nodos | Activo |
|---|---|---|---|
| Barberia - Agente de citas (Uncensored AI) | `barberiaAgenteUncensored` | 52 | **sí** |
| Barberia - Recordatorios de cita | `barberiaRecordatorios` | 17 | **sí** |
| barberiaVigilancia | `5zd5go4TFKqIsgdT` | 5 | **sí** (cada 15 min) |
| `_verif-e2e-lectura-calendario` | `OKuQlE1nBbuPHg4Q` | 3 | sí — **temporal de otro agente, no lo toqué** |

- **No existe ningún nodo de tipo Telegram** en ninguno de los cuatro workflows
  (busqué `telegram` en el `type` de todos los nodos: 0 resultados).
- **No existe ninguna credencial `telegramApi`** entre las 7 registradas
  (n8nApi, httpHeaderAuth, googleSheetsTriggerOAuth2Api, openAiApi, postgres,
  googleSheetsOAuth2Api, googleCalendarOAuth2Api).

### 1.2 Los avisos al dueño SÍ funcionan (evidencia de ejecución real)

Ejecución **861** (`barberiaRecordatorios`, 2026-09-25T13:37:43Z) — el nodo
`Notificar cita nueva al encargado` **sí se ejecutó** y devolvió la respuesta real
de Evolution API:

```
remoteJid: 5214521206246@s.whatsapp.net
fromMe:    true
status:    PENDING
message:   "Nueva cita agendada:
            Cliente: Prueba Carga
            Servicio: corte desvanecido o tijera
            Precio: 150
            Hora y dia de la cita: 25/9/2026, 3:00:00 p.m."
```

Mismo resultado en las ejecuciones **852** (Cliente: Prueba Cancelar) y **847**
(Cliente: Cristia, Peinado, 300). El filtro `IF - Es cita agendada` está bien puesto:
la ejecución **838** llegó al filtro y **no** disparó aviso (era una cancelación), y la
cadena siguió sólo por la rama de recordatorios.

**Conclusión: el aviso de "cita nueva" está vivo y llega al dueño.**

### 1.3 El aviso de escalación está bien configurado

Nodo `Notificar al encargado` (`@n8n/n8n-nodes-langchain.toolHttpRequest`), disponible
como herramienta del AI Agent. Descripción real:

> *"Avisa al encargado de la barberia por WhatsApp cuando el cliente pide hablar con una
> persona, pide un descuento o un precio que no esta en la lista, quiere un servicio que
> no ofrecemos, tiene una queja, o cuando no pudiste resolver su solicitud."*

Destino: `POST http://evolution_api:8080/message/sendText/hector` con
`number = 524521206246@s.whatsapp.net`. Correcto.

### 1.4 Los 12 comandos del dueño existen (evidencia estructural)

El nodo `Router de comandos` de `barberiaAgenteUncensored` tiene **12 salidas reales**,
extraídas del workflow en vivo:

```
HOY, MAÑANA, SEMANA, LIBRE, CLIENTE, BLOQUEAR, CERRAR, ABRIR,
PRECIO, PAUSA, ESTADO, COMANDOS   (+ salida extra "No es comando")
```

Se resuelven en la cadena `Preparar rango de fechas` → `Leer agenda del rango` →
`Formatear agenda` → `Responder al operador`, **sin pasar por el modelo**: coste 0 tokens.
Confirmado en el código del nodo `Preparar rango de fechas`, que lee el texto del mensaje
directamente (`texto.split(/\s+/)[0].toUpperCase()`) y no consume ninguna llamada de IA.
El `Router de comandos` se alcanza sólo si `¿Es operador?` da verdadero, y eso se valida
contra la tabla `barber_operadores`.

### 1.5 Volumen real de avisos

| Dato medido | Valor |
|---|---|
| Mensajes enviados por el bot al dueño el día de pruebas | 150 (todos `fromMe=true`) |
| Citas reales en `barber_citas` | **0** |
| Escalaciones en `barber_escalaciones` | **0** |
| Clientes reales en `barber_clientes` | 2 (ambos de prueba) |
| Operadores en `barber_operadores` | **2 filas, pero es la MISMA persona** |
| Capacidad de agenda | 10:00–20:00, servicios de 20–50 min → **~8-10 citas/día máximo** |

Los 150 mensajes del día de pruebas son **de test**, no de producción. En operación real
el dueño recibiría **1 aviso por cita agendada** (máximo ~8-10 al día) **más** las
escalaciones, que hoy son 0.

---

## 2. Análisis de las cuatro preguntas

### a) ¿Hay "staff"? — **NO. Y esto invalida la premisa del documento.**

`barber_operadores` tiene dos filas, pero son el mismo JID en dos formatos:

```
524521206246@s.whatsapp.net  | Dueno | dueno | t
5214521206246@s.whatsapp.net | Dueno | dueno | t
```

**Esteban Aguilera es dueño, operador y único empleado.**

El documento justifica Telegram con *"canal separado y limpio para comunicación interna"*.
Una comunicación interna necesita **al menos dos partes**: quien reporta y quien recibe.
Aquí el que reporta (n8n) y el que recibe (Esteban) no forman un equipo: es un sistema
avisando a su único humano.

**Un canal interno para una sola persona no es un canal interno: es una segunda
notificación.** El resultado práctico es que Esteban tendría WhatsApp **y** Telegram
abiertos para no perderse nada — exactamente el problema que Telegram decía resolver,
pero duplicado.

### b) ¿El ruido es un problema real? — **NO, con los datos en la mano.**

Los avisos actuales son exactamente dos:

1. **Cita nueva** (`Notificar cita nueva al encargado`) — 1 por cita agendada.
   Con la agenda al máximo son ~8-10 al día, repartidos entre las 10:00 y las 20:00.
2. **Escalación** (`Notificar al encargado`) — sólo si el cliente pide descuento, queja,
   algo fuera del catálogo o hablar con una persona. Hoy: **0 escalaciones**.

Eso es **entre 5 y 10 mensajes al día en el peor caso, y son informativos, no basura**:
cada uno es una cita que el dueño necesita saber que existe. No hay spam de marketing,
ni notificaciones de sistema, ni grupos.

El "ruido" que describe el documento es un **supuesto, no una medición**. La evidencia
dice lo contrario: el flujo de avisos es pequeño, predecible y todo él relevante.
Separar 8 mensajes útiles al día en una segunda app **no reduce ruido: añade una app**.

Y hay un dato que remata el argumento: **un canal separado obliga al dueño a mirar
Telegram para no perderse una cita nueva**. Si no lo mira, pierde información que hoy
le llega sola. Telegram no filtra el ruido, lo **reparte**.

### c) ¿Qué aportaría Telegram que WhatsApp no?

Aquí hay que ser justos: **dos cosas sí son reales.**

| Ventaja real de Telegram | ¿Aplica a este negocio? |
|---|---|
| Botones interactivos (aprobar/rechazar) | Sólo sirve si hay algo que aprobar → ver abajo |
| HITL de n8n (`sendAndWait`) funciona bien con Telegram | Requiere una acción con dos caminos y consecuencias |

**¿Qué acción sería tan sensible que merezca aprobación?** Revisé todas las acciones del
sistema y estas son las candidatas:

| Acción | ¿Merece aprobación? | Por qué no |
|---|---|---|
| Cobrar / reembolsar | **No existe** | Los cobros son **presenciales en efectivo**. La restricción del usuario prohíbe tarjeta. No hay pasarela, no hay cargo, no hay reembolso que autorizar. |
| Cancelar una cita | **No** | Precio máximo del catálogo: **300 MXN** (peinado). No hay "cancelación de alto valor". |
| Crear bloqueo de agenda | **No** | El único que puede crearlo es el dueño y **ya lo hace él mismo** con su comando `BLOQUEAR` desde su propio WhatsApp. Aprobar lo que uno mismo acaba de pedir es un paso redundante. |
| Cambiar precio (`PRECIO`) | **No** | Comando exclusivo del dueño, autenticado por `¿Es operador?` contra `barber_operadores`. Ya está protegido, y quien lo pide es la misma persona que aprobaría. |
| Pausar a un cliente (`PAUSA`) | **No** | Igual: lo pide el dueño para sí mismo. |

**Conclusión:** el HITL de Telegram es una tecnología excelente **para un negocio con
empleados**, donde el operador necesita permiso del dueño. Aquí el dueño *es* el operador.
**No hay ninguna acción que aprobar**, y por tanto el 90% del valor diferencial de
Telegram no tiene dónde aplicarse.

Añado el matiz de infraestructura: implementar HITL con Telegram implica un nodo
`sendAndWait` que **deja la ejecución en pausa esperando la respuesta del humano**. En un
negocio de una sola persona que atiende clientes todo el día, eso significa ejecuciones
colgadas (status `waiting`) esperando a alguien que está cortando el pelo.

### d) ¿El coste de montarlo? — Todo el coste recae en el dueño, y es manual.

Telegram no cuesta dinero (correcto), pero cuesta **pasos que dependen de él**:

1. Instalar Telegram en su teléfono y crear cuenta.
2. Hablar con **@BotFather**, ejecutar `/newbot`, elegir nombre y usuario.
3. Copiar el **token** del bot y hacérnoslo llegar.
4. Abrir el chat del bot nuevo y pulsar **Iniciar** (sin esto el bot **no puede**
   escribirle: Telegram devuelve `chat not found`).
5. Obtener el `chat_id` (vía `getUpdates` en el navegador).
6. Crear la credencial `telegramApi` en n8n y asignarla a cada nodo.

Son 6 pasos y **no puedo hacer ninguno por él**: el token es suyo y no debo pedirlo ni
inventarlo. Esto añade un punto de fallo manual a un sistema que hoy funciona solo.

**Lo que sí verifiqué por si acaso:** la red no es el obstáculo. Desde este equipo
`https://api.telegram.org/` responde **HTTP 200**, y desde dentro del contenedor
`barberia-n8n` un `wget` al mismo endpoint devuelve **rc=0**. Un `getMe` con token falso
responde `{"ok":false,"error_code":404}` — es decir, **el servicio está accesible desde
n8n y funcionaría en cuanto hubiera token**. Es viable; simplemente no conviene.

---

## 3. Coste vs. beneficio

| Criterio | WhatsApp (lo que ya hay) | Telegram (lo propuesto) |
|---|---|---|
| Coste | $0 | $0 |
| Estado | **Funcionando, con evidencia de ejecución** | Por construir |
| Trabajo del dueño | 0 pasos | 6 pasos manuales |
| Info que recibe | Cita nueva + escalación + 12 comandos + vigilancia | Los mismos avisos |
| Dónde la mira | 1 app (la que ya usa con los clientes) | 2ª app |
| Botones / HITL | No | Sí — **pero no hay nada que aprobar** |
| Staff al que servir | — | **No existe** |

Telegram cuesta $0 en dinero y cuesta bastante en **atención, pasos manuales y superficie
de fallo**. Lo que devuelve es, como máximo, **duplicar** avisos que ya llegan. No hay un
solo criterio en el que Telegram gane.

---

## 4. Qué implementé

**Nada. Y fue una decisión deliberada, no un olvido.**

- **NO creé `barberiaAlertas`.** Un workflow que recibe eventos y los manda a un destino
  que el dueño no va a mirar es trabajo muerto, y encima quedaría en el listado contando
  como un cuarto workflow que "hace algo" cuando no hace nada útil.
- **NO creé el nodo de alerta "listo pero desactivado"** dentro de un workflow existente.
  Un nodo desactivado dentro de `barberiaRecordatorios` ensucia el flujo que hoy funciona
  y no aporta valor mientras no exista el token.
- **NO toqué ninguno de los tres workflows existentes**, ni sus respaldos.
- **NO pedí ni inventé ningún token.**
- **NO dejé ningún workflow activo que pueda fallar** por falta de credencial.

Resultado verificable: **la lista de workflows quedó exactamente igual que antes de
empezar** (`barberiaAgenteUncensored`, `barberiaRecordatorios`, `barberiaVigilancia`,
más el temporal `_verif-e2e-lectura-calendario` que dejó otro agente y que no me
corresponde borrar). **No añadí ninguno y no borré ninguno.**

Si más adelante se decidiera que sí o sí se quiere Telegram, el nodo ya viene en la imagen
de n8n (2.40.6 incluye `n8n-nodes-base` con el nodo Telegram) y la red está abierta, así
que montarlo sería cuestión de tener el token. Pero **hoy no hay razón para gastar ese
esfuerzo**.

---

## 5. Qué propongo en su lugar

La instrucción era clara: si no conviene Telegram, proponer **la mejora gratis que sí
aporte valor**. Evalué tres opciones y descarté dos.

### ❌ Descartada: agrupar avisos en un resumen ("reducir ruido")

Suena bien, pero **los datos no la justifican**. Con ~8-10 avisos al día, cada uno de una
cita distinta, agrupar significa **retrasar** el aviso de una cita nueva. Hoy el dueño se
entera al instante; agrupado se enteraría "cuando toque el resumen". **Cambiaría
información fresca por una bandeja más corta que nadie pidió.** No hay problema de ruido
que resolver.

### ❌ Descartada: implementar cambios ahora mismo en los workflows

Buena parte de la mejora real (sección 6) implica **editar `barberiaRecordatorios` y
`barberiaAgenteUncensored`**, que están activos y que en este momento otros agentes están
trabajando en paralelo (hay un workflow temporal de verificación vivo y respaldos
`ANTES-*` recién escritos). Editar esos dos a la vez desde aquí es la forma más rápida de
pisar trabajo ajeno. **No lo hice.** Lo dejo especificado, con la evidencia exacta, para
que se aplique de forma coordinada y con respaldo.

### ✅ Propuesta: arreglar lo que YA falla, antes de añadir nada

Esto es lo verdaderamente valioso y es **gratis, sobre herramientas que ya están
funcionando**. Salió de revisar el historial de ejecuciones, no de una suposición:

| Bug medido | Evidencia real | Impacto en el dueño |
|---|---|---|
| `Actualizar precio` revienta | Ejecuciones **878** (25/09 13:41) y **758**: `column "undefined" does not exist` | El comando `PRECIO` falla y el dueño no sabe por qué |
| `Responder al operador` da Bad request | Ejecuciones **770**, **759**: `Bad request - please check your parameters` | Comandos sin respuesta: el dueño escribe y el bot calla |
| Recordatorios con errores de Sheets | 9 ejecuciones en error: `Forbidden - perhaps check your credentials?` (611, 680, 687, 703), `Column names were updated after the node's setup` (720, 722), `Could not retrieve the columns from key row` (731, 732, 733) | **El recordatorio de 24 h y 1 h al cliente no sale** |

**De los tres, el tercero es el grave.** Un aviso que no llega al dueño le cuesta mirar el
celular; un **recordatorio que no llega al cliente le cuesta un no-show**, es decir, dinero
y un hueco muerto en la agenda de un negocio con un solo barbero.

Ese trabajo vale infinitamente más que un canal nuevo: **Telegram daría al dueño una
segunda forma de recibir avisos que quizá no llegan; arreglar el recordatorio hace que el
cliente sí llegue a su cita.**

Y un detalle que apareció de paso y conviene mirar: los avisos enviados por Evolution
salen con **`status: "PENDING"`**, no `"SENT"`/`"DELIVERY_ACK"`. Puede ser normal (la API
responde antes del acuse), pero **merece confirmarse mirando el teléfono**: si los
mensajes se quedan en `PENDING`, el dueño podría no estar recibiendo los avisos que
creemos que sí recibe. Esa comprobación sólo la puede hacer quien tiene el teléfono.

---

## 6. Límites y lo que depende del usuario

**Lo que yo no pude hacer (y por qué):**

1. **Confirmar con el teléfono del dueño** que los mensajes con `status: PENDING` se
   entregan de verdad. Sólo quien tiene el teléfono puede verlo.
2. **Aplicar los arreglos de la sección 5.** Requieren editar workflows activos que otros
   agentes están tocando en paralelo. Necesita una ventana coordinada y respaldo
   (`ANTES-*.json`), como manda el contexto del proyecto.
3. **Ejecutar `verify.py`.** No lo corrí porque **no modifiqué ningún workflow**: no había
   nada que verificar. Si alguien aplica los arreglos, debe correr
   `uv run python G:\Barberia\verify.py` (esperado 173/173) y después
   `uv run python G:\Barberia\archivos\sincronizar-archivos.py`.

**Lo que dependería del dueño si algún día se aprobara Telegram** (no lo recomiendo):

1. Instalar Telegram y crear cuenta.
2. Hablar con **@BotFather** → `/newbot` → elegir nombre y usuario.
3. Copiar el **token** que devuelve BotFather.
4. **Pulsar "Iniciar"** en el chat del bot nuevo (sin esto el bot no puede escribirle).
5. Abrir en el navegador
   `https://api.telegram.org/bot<TOKEN>/getUpdates` y copiar el `chat_id`.
6. En n8n: **Credentials → New → Telegram API**, pegar el token, guardar con el nombre
   `telegramApi`.
7. En cada nodo de Telegram: seleccionar esa credencial y poner el `chat_id`.
8. Activar el workflow **sólo al final**, cuando el paso 6 esté hecho.

Nada de esto lo puede hacer un agente: el token es del dueño y **no se debe pedir ni
inventar**.

---

## 7. Evidencia cruda recogida

```
=== WORKFLOWS (n8n 2.40.6) ===
5zd5go4TFKqIsgdT          barberiaVigilancia              active=True
OKuQlE1nBbuPHg4Q          _verif-e2e-lectura-calendario   active=True   <- temporal de otro agente
barberiaAgenteUncensored  Barberia - Agente de citas      active=True
barberiaRecordatorios     Barberia - Recordatorios        active=True

=== Nodos Telegram encontrados en TODOS los workflows ===
(0 resultados)

=== Credenciales (7, ninguna de tipo telegramApi) ===
Se7l2GF1O4CrF9jb  n8n API (local)                n8nApi
qaGW1Tvt5BqPujJ1  Evolution API                  httpHeaderAuth
cJgufKuA5Lxckkz8  Google Sheets Trigger account  googleSheetsTriggerOAuth2Api
KhicsxnD4N314cKC  Uncensored AI                  openAiApi
NUrqrDWN8OsBFmgV  Postgres account               postgres
lGEYmmJh1FvqzQi9  Google Sheets account          googleSheetsOAuth2Api
I6TpcTTP1cn1tviR  Google Calendar account        googleCalendarOAuth2Api

=== Postgres: el negocio es una sola persona ===
barber_operadores:
  524521206246@s.whatsapp.net  | Dueno | dueno | t
  5214521206246@s.whatsapp.net | Dueno | dueno | t     <- el mismo, en otro formato
barber_citas:        0 filas
barber_escalaciones: 0 filas
barber_clientes:     2 filas (ambas de prueba)

=== Router de comandos: 12 salidas reales ===
['HOY','MAÑANA','SEMANA','LIBRE','CLIENTE','BLOQUEAR','CERRAR','ABRIR',
 'PRECIO','PAUSA','ESTADO','COMANDOS']  + fallback "No es comando"

=== Aviso de cita nueva: SÍ se ejecuta (ejecución 861) ===
remoteJid: 5214521206246@s.whatsapp.net
fromMe:    true
status:    PENDING
message:   "Nueva cita agendada:\nCliente: Prueba Carga\n
            Servicio: corte desvanecido o tijera\nPrecio: 150\n
            Hora y dia de la cita: 25/9/2026, 3:00:00 p.m."

=== Filtro IF - Es cita agendada: correcto ===
Ejecución 838 (cancelación) -> llegó al filtro, NO disparó aviso.

=== Conectividad Telegram ===
host -> https://api.telegram.org/            HTTP 200
contenedor barberia-n8n -> wget             rc=0   (alcanzable desde n8n)
getMe con token falso -> {"ok":false,"error_code":404}
=> Telegram ES viable técnicamente. No conviene, pero no es por la red.

=== Errores reales en ejecuciones (últimas 250) ===
barberiaAgenteUncensored: 218 success / 7 error
   878  Actualizar precio       column "undefined" does not exist
   758  Actualizar precio       column "undefined" does not exist
   770  Responder al operador   Bad request - please check your parameters
   759  Responder al operador   Bad request - please check your parameters
   763  Mandar mensaje          Bad request - please check your parameters
   660  Mandar mensaje          Bad request - please check your parameters
barberiaRecordatorios:   2 success / 9 error / 9 waiting
   611/680/687/703  Append or update row in sheet  Forbidden - check your credentials?
   720/722          Append or update row in sheet  Column names were updated after setup
   731/732/733      Google Sheets Trigger           Could not retrieve the columns from key row
barberiaVigilancia:      2 success / 0 error

=== Instancia Evolution 'hector' ===
connectionStatus: open   ownerJid: 5214501111805@s.whatsapp.net   profileName: "Harfuchh"
_count: { Message: 575, Contact: 9, Chat: 19 }
```

### Archivos de evidencia

Los scripts y las salidas crudas quedaron en `G:\Barberia\archivos\_tg\`
(`01-inspeccion`, `02-datos`, `03-ejecuciones`, `04-nodos`, `05-comandos-errores`,
`06-evidencia-whatsapp`, `07-viabilidad`, `08-volumen`). Son de sólo lectura y no
modifican nada; se pueden borrar cuando no hagan falta.

---

## 8. Respuesta directa

**¿Telegram? No.** Es gratis y funciona, pero resuelve un problema que el negocio no
tiene: **no hay staff** al que abrir un canal interno (Esteban es el único y también el
dueño), **no hay ruido** que separar (5-10 avisos útiles al día), y **no hay ninguna
acción sensible que aprobar** (los cobros son en efectivo en el mostrador y todo lo
demás ya lo dispara el propio dueño desde su WhatsApp).

No implementé nada y no creé ningún workflow: no tenía sentido llenar el proyecto con un
cuarto flujo que nadie va a mirar. La lista de workflows quedó **idéntica** a como estaba.

Lo que propongo es más barato y arregla algo real: **los recordatorios al cliente están
fallando** (9 ejecuciones en error por credenciales y esquema de Google Sheets) y **el
comando `PRECIO` revienta** (`column "undefined" does not exist`). Eso sí cuesta dinero:
un recordatorio que no llega es un no-show y un hueco muerto en la agenda del único
barbero.
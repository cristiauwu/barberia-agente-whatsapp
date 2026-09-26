# Manual del dueño — Bot de citas por WhatsApp

**Barber Chinos — Peluquería & Barbería**
Calle Pinzón #574 · Teléfono de citas: **452-281-8144**
Horario: **lunes a sábado, 10:00 a 20:00 h**. Domingo cerrado.
La última cita del día debe **terminar** antes de las 20:00.

Este manual es para ti, el dueño. No necesitas saber nada de computación.

---

## 1. Qué hace este sistema

Tu WhatsApp de la barbería contesta solo, a cualquier hora, y agenda citas.
El cliente escribe, el bot le muestra precios y horarios y le aparta el lugar.
Cada cita se guarda en tu calendario y en tu hoja de registro.
Tú recibes un aviso por WhatsApp cuando entra una cita nueva o cuando un cliente pide algo que el bot no puede resolver.
Y tú puedes preguntarle la agenda, bloquear horarios, cerrar días y cambiar precios escribiéndole comandos.

**En una línea:** el bot atiende, tú vigilas y decides.

---

## 2. Cómo hablarle al bot como dueño

Tus comandos **no pasan por la inteligencia artificial**: son órdenes directas. Por eso son instantáneos y no gastan tokens (no cuestan dinero).

**Solo funcionan desde tus números registrados.** Si escribes desde otro WhatsApp, el sistema te trata como cliente. Hoy están dados de alta estos dos:

- `524521206246`
- `5214521206246`

**Reglas rápidas de todos los comandos:**

- Se escriben **en mayúsculas**, en un solo mensaje.
- Para reconocer el comando, el sistema mira **solo la primera palabra**. Después van los datos, separados por espacios.
- Si te equivocas en el formato, el bot te contesta con el formato correcto. No pasa nada.

### 2.1 `HOY` — agenda de hoy

```
HOY
```

**Recibes algo así:**

```
*Agenda de hoy, viernes 12 de junio*

11:00 a.m. Juan Pérez — Corte desvanecido o tijera · $150
4:00 p.m. María López — Corte de cabello dama · $250

*2 citas · $400 estimado*
Huecos: 10:00 a.m., 10:30 a.m., 12:00 p.m., 1:30 p.m., 5:00 p.m.
```

**Cuándo te sirve:** al abrir la barbería, para ver el día completo en 5 segundos y saber si hay huecos que puedas ofrecer por teléfono.

### 2.2 `MAÑANA` — agenda de mañana

```
MAÑANA
```

Recibes lo mismo que `HOY`, pero del día siguiente, con sus huecos libres.

**Cuándo te sirve:** al cerrar, para saber cómo viene el día siguiente y si te falta surtir algo.

### 2.3 `SEMANA` — próximos 7 días

```
SEMANA
```

**Recibes algo así:**

```
*Agenda de los próximos 7 días (desde viernes 12 de junio)*

*lunes 15 de junio*
10:00 a.m. Carlos Ruiz — Ceja

*miércoles 17 de junio*
1:00 p.m. Ana Gómez — Peinado

*2 citas en el periodo*
```

Solo aparecen los días que tienen citas.

**Cuándo te sirve:** los domingos por la noche o antes de un puente, para planear la semana.

### 2.4 `LIBRE` — qué espacio queda

```
LIBRE
```

Te muestra cómo va **hoy y los próximos 2 días**, agrupado por día, para que veas dónde hay espacio.

> **Nota honesta:** hoy este comando te da la vista de esos 3 días (con las citas que ya hay). Los huecos con hora exacta los ves en las líneas "Huecos:" de `HOY` y `MAÑANA`.

**Cuándo te sirve:** cuando un cliente te llama y quiere pasar "esta semana"; de un vistazo ves dónde lo puedes meter.

### 2.5 `CLIENTE` — ficha de un cliente

```
CLIENTE 4521206246
```

Pon el número del cliente (sus últimos 10 dígitos bastan).

**Recibes algo así:**

```
*Juan Pérez*
Visitas: 12
No-shows: 1
Ticket promedio: $180
Suele pedir: Corte desvanecido o tijera
Última visita: 28/05/2026
Citas próximas: 1
```

Si nunca ha agendado, te lo dice. Solo funciona con números que ya existen en el sistema.

**Cuándo te sirve:** antes de dar un trato especial, o para saber si el cliente que te reclama ya falló antes.

### 2.6 `BLOQUEAR` — apartar un rango del día

```
BLOQUEAR 14:00-15:30 comida
```

**Recibes:**

```
Listo. Bloqué *14:00 a 15:30* (comida).
```

El motivo es opcional; si no lo pones, queda como "ocupado". Puedes bloquear otro día pidiéndolo al inicio con la fecha en formato AAAA-MM-DD:

```
BLOQUEAR 2026-12-24 10:00-12:00 inventario
```

El bot **no ofrecerá** ese horario a los clientes.

**Cuándo te sirve:** para comer, para una reunión, para ir al banco o para atender una urgencia sin que el bot venda ese hueco.

### 2.7 `CERRAR` — cerrar un día completo

```
CERRAR 24 dic
```

**Recibes:**

```
Listo. Marqué el *2026-12-24* como cerrado.
```

Acepta tres formas de fecha:

| Lo que escribes | Cuándo cierra |
| --- | --- |
| `CERRAR 24 dic` | El 24 de diciembre (si ya pasó este año, entiende el del año que viene) |
| `CERRAR 2026-12-24` | Esa fecha exacta |
| `CERRAR hoy` / `CERRAR mañana` | Hoy o mañana |

**Cuándo te sirve:** vacaciones, día festivo, mantenimiento, o cuando te enfermas. Con eso el bot no agenda a nadie ese día.

### 2.8 `ABRIR` — quitar el cierre

```
ABRIR 24 dic
```

**Recibes:**

```
Listo. El *2026-12-24* vuelve a estar abierto.
```

Acepta las mismas formas de fecha que `CERRAR`.

**Cuándo te sirve:** si cerraste por error, o si decidiste abrir el día que habías cerrado.

### 2.9 `PRECIO` — cambiar el precio de un servicio

```
PRECIO ceja 40
```

**Recibes:**

```
Listo. *Ceja* ahora cuesta *$40*.
Duración: 10 min.
```

Puedes cambiar también la duración con un cuarto número:

```
PRECIO ceja 40 15
```

Claves válidas (así se llaman los servicios para este comando): `corte`, `barba`, `ceja`, `mascarilla`, `dama`, `planchado`, `peinado`, `depilacion`.

Si escribes una clave que no existe, el bot te devuelve la lista de claves válidas.

**Cuándo te sirve:** cuando subes un precio, lo cambias **una vez** y el bot ya cotiza el nuevo precio a todos.

### 2.10 `PAUSA` — que el bot se calle con un cliente

```
PAUSA 4521206246 2h
```

**Recibes algo así:**

```
Pausado por *2 h*.

El bot no le contestará hasta las *04:30 p.m.*

Reanuda solo.
```

El número de horas va de **1 a 72**. Solo funciona con clientes que ya existen.

**Cuándo te sirve:** cuando quieres tomar tú la conversación (un regateo, una queja, un caso especial) y no quieres que el bot se meta.

> **Importante:** no hay comando para quitar la pausa antes de tiempo. **Se quita sola** cuando vence. Por eso, si vas a contestarle tú en ese momento, usa `1h` en vez de `24h`.

### 2.11 `ESTADO` — salud del sistema

```
ESTADO
```

**Recibes algo así:**

```
*Estado del sistema*

Citas hoy: 6
Citas esta semana: 23
Escalaciones abiertas: 0
Pausas activas: 1
Operadores: 2

Bot activo ✅
```

**Cuándo te sirve:** cada mañana, para confirmar que todo está vivo. Si no te contesta, algo se cayó (ver sección 6).

### 2.12 `COMANDOS` — el menú de ayuda

```
COMANDOS
```

Te devuelve la lista de todo lo que puedes pedirle. Úsalo cuando olvides un formato.

### Resumen de los 12 comandos

| Comando | Qué hace | Ejemplo |
| --- | --- | --- |
| `HOY` | Agenda de hoy + huecos | `HOY` |
| `MAÑANA` | Agenda de mañana + huecos | `MAÑANA` |
| `SEMANA` | Próximos 7 días | `SEMANA` |
| `LIBRE` | Panorama de hoy y 2 días más | `LIBRE` |
| `CLIENTE` | Ficha de un cliente | `CLIENTE 4521206246` |
| `BLOQUEAR` | Aparta un rango del día | `BLOQUEAR 14:00-15:30 comida` |
| `CERRAR` | Cierra un día completo | `CERRAR 24 dic` |
| `ABRIR` | Quita el cierre | `ABRIR 24 dic` |
| `PRECIO` | Cambia precio (y duración) | `PRECIO ceja 40` |
| `PAUSA` | El bot no le contesta a ese cliente | `PAUSA 4521206246 2h` |
| `ESTADO` | Salud del sistema | `ESTADO` |
| `COMANDOS` | Menú de ayuda | `COMANDOS` |

---

## 3. Qué te llega automáticamente

No tienes que pedirlo. Te llega un WhatsApp solo, a tu número.

### 3.1 Cita nueva

Cada vez que un cliente agenda, te llega:

```
Nueva cita agendada:
Cliente: Juan Pérez
Servicio: Corte desvanecido o tijera
Precio: 150
Hora y dia de la cita: 12/6/2026, 4:00:00 p.m.
```

### 3.2 Avisos de escalación

El bot te escribe cuando **no puede resolver algo solo**. Le pasa esto:

| Situación | Por qué te avisa |
| --- | --- |
| El cliente pide un descuento | El bot no está autorizado a dar descuentos |
| El cliente se queja | Es un tema tuyo, no del bot |
| El cliente pide algo fuera del catálogo | El bot no inventa servicios |
| El cliente pide un precio que no está en la lista | El bot no inventa precios |
| El cliente pide hablar con una persona | Quiere trato humano |
| El bot no pudo resolver la solicitud | Te pasa la estafeta |

El aviso trae quién es el cliente, qué pidió y su número de WhatsApp **para que le respondas tú**.

### 3.3 Recordatorios al cliente (no a ti)

El sistema también le escribe **al cliente**, sin que hagas nada:

- **24 horas antes** de la cita: le recuerda y le pide responder *SI* o *NO*.
- **1 hora antes** de la cita: le recuerda y le pide avisar si no puede ir.

Si el cliente cancela, **el recordatorio se cancela también**: no le vuelve a llegar nada por una cita que ya no existe.

---

## 4. Cómo manejar los casos difíciles

| Situación | Qué haces |
| --- | --- |
| **El cliente quiere un descuento** | El bot ya te avisó. **Respóndele tú** desde tu WhatsApp, directo al cliente. Tú decides el precio. |
| **El bot se equivocó con una cita** | Manda `CLIENTE <número del cliente>` para ver su ficha, y abre el calendario *BARBER* para corregir el evento a mano. El bot ya te avisó si no pudo resolverlo. |
| **Un cliente me está escribiendo y quiero contestarle yo** | Manda `PAUSA <número> 2h`. Así el bot se calla y no se te cruza. Usa la pausa corta si vas a contestar ya. |
| **Me voy de viaje / cierro por vacaciones** | Manda `CERRAR <fecha>` por cada día que cierres. Ejemplo: `CERRAR 24 dic`. |
| **Voy a salir a comer** | Manda `BLOQUEAR 14:00-15:30 comida`. |
| **Subí el precio de la ceja** | Manda `PRECIO ceja 40`. |
| **El bot no contesta** | Manda `ESTADO`. Si no responde, ve a la sección 6. |
| **El bot contesta, pero la cita no aparece en el calendario** | Manda `ESTADO` y revisa la sección 6: casi siempre es el permiso de Google caducado. |
| **El bot ofrece un horario que yo quería libre** | Bloquéalo con `BLOQUEAR` (o `CERRAR` si es todo el día). El bot respeta bloqueos y cierres como si fueran citas ocupadas. |
| **Un cliente no llega y quieres saber si es costumbre** | Manda `CLIENTE <número>` y revisa la línea de *No-shows*. |

---

## 5. Cómo ver la agenda

Tienes **tres formas**. Cualquiera sirve; elige la que tengas a mano.

**1. Por WhatsApp (lo más rápido)**

```
HOY
```
```
SEMANA
```

**2. Google Calendar — el calendario se llama `BARBER`**

Ahí ves las citas como bloques de color, también los bloqueos que creaste y los días cerrados. Es la vista más gráfica del día.

**3. Google Sheets — la hoja se llama `Citas barbería`**

Es tu registro histórico. Cada cita es una fila, con estas columnas:

| ID | Estatus | Nombre | Servicio | Precio del servicio | Día | Hora | Numero celular |
| --- | --- | --- | --- | --- | --- | --- | --- |

- **Estatus** te dice qué pasó: `agendado`, `actualizado`, `cancelado`.
- **Día** va en formato AAAA-MM-DD y **Hora** en formato de 24 horas.
- Hay una columna interna más, *Execution ID*, que el sistema usa para cancelar los recordatorios. **No la borres ni la muevas.**

> **Regla:** no borres ni reordenes las columnas de la hoja. Si necesitas borrar filas viejas, borra filas completas, nunca columnas.

---

## 6. Qué hacer si algo falla

Hazlo en este orden. No te saltes pasos.

**Paso 1 — Pregúntale al bot.**

```
ESTADO
```

- **Si contesta** con "Bot activo ✅": el bot está vivo. Si el problema era que no le contestó a un cliente, revisa la línea *Pausas activas*. Puede que tú mismo hayas pausado a ese cliente.
- **Si no contesta:** sigue al paso 2.

**Paso 2 — Revisa que n8n esté encendido.**

1. Abre **Docker Desktop** (el ícono de la ballena).
2. Entra a la pestaña **Containers**.
3. Busca **`barberia-n8n`** y **`barberia-postgres`**.
4. Si están apagados, dale **play** a los dos.
5. Espera **2 minutos** (tarda en arrancar) y manda `ESTADO` otra vez.

**Paso 3 — Revisa que los flujos estén activos.**

1. Abre en tu navegador: **http://localhost:5678**
2. Entra a **Workflows**.
3. Deben aparecer dos, y los dos con el interruptor **Active** en verde:
   - *Barberia - Agente de citas (Uncensored AI)*
   - *Barberia - Recordatorios de cita*
4. Si alguno está en gris, actívalo.

**Paso 4 — Si el bot contesta pero NO agenda ni crea la cita.**

Casi siempre es lo mismo: **se venció el permiso de Google**. Pasa cuando la app quedó en modo "Prueba", y Google lo invalida **cada 7 días**.

Solución: en n8n entra a **Credentials**, abre la credencial de Google y dale **Sign in with Google** otra vez para reconectar la cuenta. Necesitas el correo de Google de la barbería y su contraseña.

> **Para que deje de pasar:** pide que se publique la app de Google (pasar de "Prueba" a "Producción"). Eso se hace una vez y ya no caduca.

**Paso 5 — Si nada de eso funciona.**

No te quedes trabado el día de trabajo. Haz esto y sigue atendiendo:

1. Anota la cita **a mano** en el calendario *BARBER*.
2. Apunta al cliente en una hoja de papel o en tu teléfono.
3. Contesta tú los WhatsApp hasta que se arregle.

Al final del día, con calma, revisa otra vez los pasos 2 y 3.

**Cómo saber en 5 segundos si el bot está vivo:**

```
ESTADO
```

Si te contesta, está vivo. Es la prueba más simple que existe.

---

## 7. Lo que el sistema todavía NO hace

Esto es importante que lo sepas para que no cuentes con ello.

**1. No manda recordatorios por la API oficial de WhatsApp Business.**
Los recordatorios de 24 h y 1 h hoy salen por la conexión actual (Evolution API), que es la conexión artesanal. Está **pendiente** migrar a la API oficial de Meta. En la práctica: los recordatorios funcionan, pero dependen de que la sesión de WhatsApp siga conectada.

**2. No cobra ni pide depósito.**
El bot no recibe dinero, ni tarjeta, ni transferencia, ni anticipo. **El pago se hace en la barbería, como siempre.** Si un cliente no llega, no hay nada que cobrarle.

**3. No tiene lista de espera automática.**
Si alguien cancela, el bot **no** le ofrece el hueco al siguiente cliente de la lista. Ese hueco queda libre. Para llenarlo, tienes que ofrecerlo tú (con `HOY` ves los huecos).

---

## 8. Recomendaciones de uso

**1. Revisa `ESTADO` cada mañana.**
Es tu chequeo de salud. Un mensaje, 3 segundos, y ya sabes si el día está en orden. Si no contesta, ya sabes que hay que revisar Docker.

**2. Usa `PAUSA` en vez de discutir con el bot.**
Cuando un cliente pida algo raro, no te pelees con el bot ni le des instrucciones largas: manda `PAUSA <número> 2h` y contéstale tú. Recuerda que la pausa **no se puede quitar antes**; se quita sola al vencer.

**3. Mantén la hoja limpia, pero sin mover columnas.**
Borra filas viejas completo, de vez en cuando, para que la hoja cargue rápido. **Nunca borres ni reordenes columnas**, y nunca toques *Execution ID*: sin ella el sistema no puede cancelar los recordatorios de las citas canceladas.

**4. Usa `SEMANA` para planear y `CERRAR` para tus días libres.**
Si cierras un día con el comando, el bot deja de ofrecerlo de inmediato. Si cierras con la boca, el bot sigue vendiendo ese día. Siempre `CERRAR` primero.

**5. Cambia los precios con `PRECIO`, nunca en el prompt.**
Es un solo comando y todos los clientes ven el precio nuevo al instante: `PRECIO ceja 40`. Es la forma de que el bot nunca cotice un precio viejo.

**Extra, porque cuesta dinero:** revisa tu gasto de tokens en el panel del proveedor los primeros días. Cada mensaje de cliente vuelve a mandar la conversación completa, así que el consumo sube rápido si el bot tiene mucho tráfico.

---

*Manual del dueño — sistema de citas por WhatsApp de Barber Chinos.*
*Si un comando te da un formato de error, el mismo mensaje te dice cómo escribirlo bien.*
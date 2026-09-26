# Panel del dueno — Barber Chinos (Barberia)

Dashboard visual de KPIs del negocio. **100% gratis, 100% local, sin cuentas,
sin tarjeta y sin CAPTCHA.** No expone la base de datos a internet.

## Que hay aqui

| Archivo | Para que sirve |
|---|---|
| `generar-dashboard.py` | Lee Postgres y escribe `dashboard.html`. Solo libreria estandar de Python. |
| `dashboard.html` | El panel ya generado. Se abre solo, sin internet, sin servidor. |
| `servidor-dashboard.py` | Sirve el panel en la red local (Wi-Fi) para verlo desde el celular. |
| `README.md` | Este archivo. |

## Uso rapido

### Opcion A — abrir el archivo (lo mas simple, sin servidor)

```powershell
C:\Users\kimbo\.cherrystudio\bin\uv.exe run python G:\Barberia\archivos\dashboard\generar-dashboard.py
start G:\Barberia\archivos\dashboard\dashboard.html
```

Para actualizarlo, vuelve a correr el mismo comando y recarga la pagina (F5).
Funciona sin internet.

### Opcion B — verlo desde el celular (recomendado)

```powershell
C:\Users\kimbo\.cherrystudio\bin\uv.exe run python G:\Barberia\archivos\dashboard\servidor-dashboard.py
```

Imprime dos direcciones. La segunda es la que se abre en el celular:

```
En ESTA computadora:  http://localhost:8099
En el CELULAR:        http://192.168.x.x:8099
```

El celular tiene que estar en **la misma red Wi-Fi** que esta PC. El servidor
regenera el panel cada 2 minutos, asi que el dueno solo refresca la pagina.

Para detenerlo: `Ctrl + C`.

## Si el celular no abre la pagina

Casi siempre es el **Firewall de Windows**. La primera vez que se levanta el
servidor Windows pregunta si permitir el acceso a la red; hay que marcar
**Redes privadas** y **Aceptar**. Si ya se rechazo, se puede abrir el puerto a mano
(en PowerShell **como Administrador**):

```powershell
New-NetFirewallRule -DisplayName "Dashboard Barberia 8099" -Direction Inbound `
  -Protocol TCP -LocalPort 8099 -Action Allow -Profile Private
```

Comprueba tambien:

- Que el celular este en el **mismo Wi-Fi** (no en datos moviles).
- Que el puerto 8099 este libre. Si esta ocupado, usa `--puerto 8100`.
- Que la PC no este hibernando.

## Como se mantiene al dia

El panel no se actualiza solo por estar abierto: **hay que regenerar el HTML**.
Dos formas:

1. Con el servidor (`servidor-dashboard.py`), que regenera cada 2 minutos.
2. Manual: volver a correr `generar-dashboard.py`.

Si mas adelante se quiere automatizar, basta un Programador de tareas de Windows
que ejecute el generador cada N minutos. **No se toco ningun workflow de n8n.**

## KPIs que muestra

- Ingresos de hoy, de la semana y del mes (solo citas `atendido`).
- Numero de citas atendidas en cada periodo.
- Ticket promedio del dia y del mes.
- No-shows y cancelaciones del mes.
- Citas de los proximos 7 dias y su ingreso potencial.
- Serie de ingresos de los ultimos 30 dias.
- Top servicios por ingresos del mes.
- Horas pico (horas con mas citas atendidas).
- Reparto de estados de las citas del mes.
- Clientes nuevos vs recurrentes del mes.
- Agenda de hoy y proximas citas.

## Notas tecnicas

- La zona horaria del negocio se fija explicitamente en `America/Mexico_City`
  (offset fijo -06:00), asi que los cortes de dia/semana/mes no dependen de la
  configuracion de la PC.
- El generador lee las credenciales de `G:\Barberia\.env`. **No hay contrasenas
  escritas en ningun archivo de esta carpeta.**
- El panel se ve bien con **0 citas**: muestra ceros y textos de "sin datos",
  sin errores ni graficos rotos.
- La hoja de Google y los workflows de n8n no se tocaron.
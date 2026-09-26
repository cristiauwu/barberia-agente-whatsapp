# DASHBOARD-GUIA — Panel visual del dueño (Barber Chinos)

> Barbero único: **Esteban Aguilera**. Sistema local en Docker. Fecha de este informe: 2026-09-25.

---

## 1. Qué se hizo, en una línea

Se implementó un **dashboard HTML estático generado por un script de Python**
que lee el Postgres local y escribe un archivo autocontenido, servido por un
servidor HTTP local para verlo desde el celular del dueño en la misma Wi-Fi.

**Estado: funcionando y verificado. 55/55 comprobaciones OK.**

---

## 2. Las opciones que evalué y por qué descarté cada una

El documento `Herramientas_APIs_Complementarias.md` (sección 3) recomienda
**Looker Studio** y menciona **Metabase** y **Grafana**. Las evalué con criterio
contra los criterios del encargo, y las tres fallan por motivos distintos.

### ❌ Looker Studio (la opción "recomendada" del documento) — descartada

| Criterio | Resultado |
|---|---|
| ¿Funciona local sin exponer la BD? | **NO.** Looker Studio es SaaS de Google: vive en internet y necesita llegar a la base. Habría que publicar el Postgres en internet o montar un túnel. |
| ¿Necesita cuenta de tercero? | **SÍ.** Cuenta de Google obligatoria. |
| ¿Cabe en gratis? | Sí en precio, pero a costa de exponer la base. |
| ¿El dueño lo abre del celular? | Sí. |
| Tiempo de montaje | Bajo, pero el requisito de exponer la BD lo descalifica. |

**Motivo de descarte:** el encargo prohíbe explícitamente exponer la base de datos
a internet y prohíbe túneles públicos. Además, el documento lo diseña contra
**Supabase**, que hoy no tiene tablas ni `service_role` key, mientras que los datos
reales están en el **Postgres local**. Para un negocio de un solo barbero, publicar
la base de datos en internet es un riesgo desproporcionado.

### ❌ Metabase self-hosted — descartada

Es una buena herramienta y **cabe en el compose** (por eso la monté primero).
La descarté por coste/beneficio real, no por incapacidad técnica:

- **Arranque lento:** 1-3 minutos hasta estar usable, y el dueño tendría que
  esperar eso cada vez que se reinicie la PC. Verifiqué que la imagen pesa y que
  el healthcheck tarda; es un servicio más que mantener vivo.
- **Configuración inicial obligatoria:** Metabase exige crear un usuario
  administrador con contraseña por navegador antes de mostrar nada. Eso deja un
  paso manual pendiente sí o sí (y el encargo pide crear usuario local y no
  exponer credenciales en el informe).
- **Consumo:** es una JVM; se suma al consumo de Docker en una PC que ya corre
  n8n, Evolution, Postgres y Redis.
- **No aporta nada que el dueño use:** las alertas automáticas y el SQL nativo
  son funciones de analista. El dueño quiere **ver** sus números.

**Conclusión:** Metabase resuelve un problema que este negocio no tiene, y añade
un servicio lento y un usuario con contraseña que mantener.

### ❌ Grafana — descartada

Grafana es excelente para **métricas operacionales** (series de tiempo, latencia,
CPU), que es justo lo que dice el propio documento (`[cite:08e6f57c-1]`: "Para
métricas operacionales de n8n mismo").

- Modelado de negocio incómodo: mostrar "top servicios por ingresos" o
  "clientes nuevos vs recurrentes" obliga a contorsiones de SQL al estilo
  *time series*, que no es su fuerte.
- Un servicio más en el compose, con su propio usuario admin y su propio arranque.
- **Motivo de descarte:** es la herramienta correcta para el problema equivocado.

### ❌ Otras que consideré

- **Supabase + dashboard del propio Supabase:** requiere crear tablas por el SQL
  Editor (paso manual) y depende de una cuenta de tercero; además hoy **no hay
  datos ahí** (los datos están en el Postgres local). Descartada.
- **Excel / Power BI / Google Sheets:** Power BI de escritorio no es una vista
  cómoda para el celular; Sheets implicaría volver a la hoja como fuente de
  verdad, que es justo el techo que el documento quiere romper. Descartadas.
- **Redash / Apache Superset / DBeaver:** misma familia que Metabase/Grafana:
  otro servicio pesado, otro usuario admin, otro arranque lento, para leer la
  misma base. Descartadas por el mismo motivo.
- **Looker Studio "solo con exportaciones a CSV":** implicaría un paso manual
  periódico; sin automatizar no es un panel, es una tarea.

### ✅ ELEGIDA — Página HTML estática generada por Python

La idea que el propio encargo apuntaba como "la más simple y sin riesgo":

| Criterio | Resultado |
|---|---|
| ¿Funciona local, sin exponer la BD? | **SÍ.** El único que lee la base es un script en esta PC, por el socket de Docker. Nunca sale nada. |
| ¿Necesita cuenta de tercero? | **NO.** Ninguna. |
| ¿Cabe en gratis sin trucos? | **SÍ.** Python + Postgres local. Sin servicio, sin cuenta, sin tarjeta, sin CAPTCHA. |
| ¿Cuánto tarda en montarse? | **Instantáneo.** ~1 segundo generar el HTML. Sin descargas, sin arranques. |
| ¿El dueño lo abre desde el celular? | **SÍ.** Por `http://IP-LAN:8099`, en la misma Wi-Fi. |
| ¿Funciona sin internet? | **SÍ.** Ni un CDN, ni una fuente, ni una imagen externa. |

**Sobre la decisión de no usar n8n:** el encargo sugería un flujo de n8n.
Lo descarté a propósito porque **modificar los workflows de n8n estaba
prohibido**, y añadir un nodo de "generar HTML" habría exigido tocar un workflow
(o crear uno nuevo con nombre temporal que luego habría que borrar). Un script
suelto hace el mismo trabajo, se puede probar sin arrancar nada y no arriesga el
agente de citas que está en producción.

---

## 3. Cómo abrirlo (pasos exactos)

### Opción A — lo más simple: abrir el archivo (sin servidor)

```powershell
# 1. Regenerar el panel con los datos de ahora
C:\Users\kimbo\.cherrystudio\bin\uv.exe run python G:\Barberia\archivos\dashboard\generar-dashboard.py

# 2. Abrirlo
start G:\Barberia\archivos\dashboard\dashboard.html
```

Para actualizarlo: repetir el paso 1 y recargar (F5). **Funciona sin internet.**

### Opción B — verlo desde el celular (recomendado)

```powershell
C:\Users\kimbo\.cherrystudio\bin\uv.exe run python G:\Barberia\archivos\dashboard\servidor-dashboard.py
```

Salida real de la verificación:

```
  Panel de 'Barber Chinos' listo.

  En ESTA computadora:  http://localhost:8099
  En el CELULAR:        http://192.168.x.x:8099
  Se regenera cada 120 segundos.

  El celular debe estar en la MISMA red Wi-Fi que esta PC.
  Para detener: Ctrl + C
```

Abrir en el celular la segunda dirección (la de la IP). El servidor regenera el
panel cada 2 minutos; el dueño solo refresca la página.

**Si el celular no carga:** casi siempre es el Firewall de Windows. En la primera
ejecución Windows pregunta si permitir el acceso; marcar **Redes privadas**.
Si ya se rechazó, abrir el puerto una vez (PowerShell **como Administrador**):

```powershell
New-NetFirewallRule -DisplayName "Dashboard Barberia 8099" -Direction Inbound `
  -Protocol TCP -LocalPort 8099 -Action Allow -Profile Private
```

### Archivos creados

```
G:\Barberia\archivos\dashboard\
   generar-dashboard.py    lee Postgres y escribe el HTML (solo stdlib)
   dashboard.html          el panel ya generado (se abre solo, sin internet)
   servidor-dashboard.py   lo sirve en la Wi-Fi local para el celular
   README.md               resumen corto de uso
G:\Barberia\archivos\DASHBOARD-GUIA.md     este informe
G:\Barberia\archivos\probar-dashboard.py   la verificación automática
```

**No se tocó ningún workflow de n8n ni los `docker-compose.yml` existentes.**

---

## 4. Qué muestra y de qué consulta sale

Toda la información sale de **una sola consulta** (`SQL_KPIS` en
`generar-dashboard.py`) que fija `SET TIME ZONE 'America/Mexico_City'` y devuelve
7 bloques. Abajo, cada KPI y su origen.

### Tarjetas de dinero y citas (`===@@resumen@@===`)

Base de todo: **solo cuentas las citas con `estado = 'atendido'`** y con
`precio` e `inicio` no nulos. Una cita `agendado` o `confirmado` **todavía no es
dinero**.

| KPI | Consulta |
|---|---|
| Ingresos hoy | `sum(precio) ... WHERE estado='atendido' AND inicio::date = current_date` |
| Ingresos semana | ídem, `inicio::date >= date_trunc('week', current_date)::date` |
| Ingresos mes | ídem, `inicio::date >= date_trunc('month', current_date)::date` |
| Citas atendidas hoy/semana/mes | `count(*)` con los mismos filtros |
| Ticket promedio hoy/mes | `round(avg(precio),2)` con los mismos filtros |
| No-shows del mes | `count(*) WHERE estado='no_show'` en el mes |
| Cancelaciones del mes | `count(*) WHERE estado='cancelado'` en el mes |
| Próximas 7 días | `count(*) WHERE estado IN ('agendado','confirmado') AND inicio >= now() AND inicio < now() + interval '7 days'` |
| Potencial 7 días | `sum(precio)` de esas mismas citas |

### Los demás bloques

| Bloque | Consulta |
|---|---|
| Ingresos por día (30 días) | `generate_series(current_date-29, current_date, '1 day')` con `LEFT JOIN` a las citas atendidas. El `LEFT JOIN` es lo que garantiza que haya **30 columnas aunque no haya ni una cita**: los días sin datos salen en gris, no desaparecen. |
| Top servicios del mes | `GROUP BY servicio` sobre citas atendidas del mes, `ORDER BY sum(precio) DESC` |
| Horas pico | `GROUP BY extract(hour FROM inicio)` sobre citas atendidas (histórico) |
| Estado de las citas del mes | `GROUP BY estado` del mes en curso |
| No-shows y cancelaciones | Las cifras del resumen, representadas como barras sobre el total de citas del mes |
| Clientes nuevos vs recurrentes | Nuevo = `jid` cuyo `min(inicio::date)` cae dentro del mes en curso. Recurrente = el resto de clientes distintos atendidos en el mes. |
| Citas de hoy | Detalle de las citas con `inicio::date = current_date` |
| Próximas citas | Las 8 siguientes agendadas/confirmadas |

### Decisiones de negocio aplicadas

- **Un solo barbero.** El panel tiene un bloque "Equipo" que dice
  explícitamente *"Barbero único: Esteban Aguilera"* y **no hay desglose por
  barbero**: con un solo profesional, esa tabla sería una fila repetida sin
  información. Esto corrige el "Performance por barbero" que proponía el
  documento.
- **No se inventan servicios.** El panel muestra el nombre de `servicio` tal
  como está en la base (`corte`, `barba`, `peinado`…). No hay lista hardcodeada.
- **Zona horaria fija.** Todo se calcula con `America/Mexico_City`, así que el
  corte del día, la semana y el mes no dependen de cómo esté configurada la PC.
- **Domingo cerrado** no afecta al panel: si no hay citas, la barra del día
  simplemente sale en cero.

---

## 5. Los límites — qué NO muestra y por qué

Esto es importante y no lo voy a maquillar.

1. **No se actualiza solo.** El panel es una **foto**: hay que regenerar el HTML
   (`generar-dashboard.py`) o dejar corriendo el servidor, que regenera cada 2
   minutos. No hay un disparador automático. **Se puede automatizar** con el
   Programador de tareas de Windows, pero eso quedó fuera de alcance porque
   implicaba tocar n8n o dejar un proceso permanente decidiéndolo yo.

2. **No hay ingresos por método de pago.** La tabla `barber_citas` no tiene
   columna de método de pago. No existe el dato, así que no se puede mostrar.

3. **No hay comparativa contra periodos anteriores.** El documento proponía
   "+12% vs ayer". Se puede calcular (los datos están), pero el panel muestra
   valores absolutos. Con la base recién empezando, un "+∞% vs ayer" sería ruido,
   no información.

4. **No hay heatmap día × hora.** Muestra las **horas** pico, que es lo que se
   pidió, pero no el cruce con el día de la semana. Con 5 citas de prueba ese
   cruce serían 42 casillas vacías; se vería peor que útil. Cuando haya volumen,
   es una mejora natural.

5. **El "cliente nuevo" depende del CRM.** La definición de "nuevo" usa
   `barber_citas.jid`. Si una cita se guardó sin `jid` (puede pasar: la columna
   admite `NULL`), esa cita **no cuenta** para nuevos/recurrentes, aunque sí
   cuenta para ingresos. Es una limitación heredada del esquema, no del panel.

6. **No hay exportación a PDF ni envío por WhatsApp.** No estaba pedido y
   enviar por WhatsApp habría implicado tocar el workflow del agente, que estaba
   prohibido. El navegador del celular puede compartir la página si hace falta.

7. **No hay autenticación.** Cualquiera en la misma Wi-Fi que abra la URL ve el
   panel. En la red de un local de barbería es aceptable, pero **conviene
   saberlo**. El servidor solo sirve `/dashboard.html`: no expone el resto del
   disco (está verificado: `.env`, el propio script y cualquier otra ruta dan 404).

8. **No lee de Google Sheets ni de Supabase.** Lee del **Postgres local**, que es
   donde el agente está escribiendo hoy. Si más adelante se migra a Supabase, hay
   que cambiar de dónde lee el generador.

---

## 6. Lo que quedó pendiente de hacer a mano

1. **Regenerar el panel periódicamente** (o dejar el servidor corriendo). El
   panel no se refresca solo. Si el dueño quiere que siempre esté al día, la
   forma limpia es una tarea programada de Windows cada 15-30 minutos que
   ejecute `generar-dashboard.py`. **No lo dejé programado** porque el encargo
   pedía no tocar workflows y no me consta que se quiera un proceso automático.

2. **Permitir el puerto 8099 en el Firewall de Windows**, la primera vez. Requiere
   un clic en el aviso de Windows (o el comando `New-NetFirewallRule` de arriba,
   como Administrador). **No lo ejecuté**: requiere elevación, que esta sesión no
   tiene.

3. **Fijar la IP de la PC** (opcional). Si el router le cambia la IP, la
   dirección del celular cambia. Se resuelve con una reserva DHCP en el router.

4. **Decidir si el panel debe enviarse por WhatsApp.** No se implementó por la
   regla de no tocar n8n. Si se quiere, es un workflow nuevo aparte que mande la
   URL local (solo funciona dentro de la Wi-Fi).

---

## 7. Verificación real (evidencia)

Script: `G:\Barberia\archivos\probar-dashboard.py`
Comando: `uv run python G:\Barberia\archivos\probar-dashboard.py`

Salida real (recortada a lo esencial; las 55 líneas completas se reproducen
corriendo el script):

```
[1] El HTML generado es valido, autocontenido y responsive
  [OK]   Tiene media query para celular
  [OK]   Etiquetas <div> balanceadas  122 abiertos / 122 cerrados
  [OK]   Sin recursos externos (0 CDNs / 0 http)  autocontenido
  [OK]   Sin <script> (no necesita JS)
  [OK]   CSS embebido en <style>

[2] Con la base tal como esta (0 citas de prueba) no se rompe
  [OK]   Las 8 tarjetas de KPI existen  encontradas: 8
  [OK]   Reconoce la base vacia (0 citas -> aviso)
  [OK]   El grafico de 30 dias tiene 30 columnas  columnas: 30

[3] El servidor local responde y no expone nada mas
  [OK]   GET / devuelve 200  status=200
  [OK]   Manda Cache-Control: no-store
  [OK]   Bloquea /..%2f.env  status=404
  [OK]   Bloquea /generar-dashboard.py  status=404
  [OK]   Bloquea /secretos.txt  status=404

[4] Con datos de prueba los KPIs cuadran (calculado a mano vs HTML)
  linea base: hoy=0.0 sem=0.0 mes=0.0 no_show=0 canc=0 fut7=0
  insertadas 6 citas de prueba y 3 clientes
  tras insertar: hoy=$250 sem=$250 mes=$500 no_show=1 canc=1 fut7=1
  [OK]   Ingresos hoy cuadra  HTML=$250  esperado=250.0
  [OK]   Ingresos semana cuadra  HTML=$250  esperado=250.0
  [OK]   Ingresos mes cuadra  HTML=$500  esperado=500.0
  [OK]   No-shows del mes cuadra  HTML=1  esperado=1
  [OK]   Ticket promedio hoy cuadra  HTML=$125  esperado=125.00 (2 citas)

[5] Limpieza y estado final de la base
  [OK]   No queda ninguna cita de prueba  quedan: 0
  [OK]   No queda ningun cliente de prueba  quedan: 0
  [OK]   Los KPIs volvieron a la linea base  mes: 0 -> 0

 RESULTADO: 55/55 comprobaciones OK. TODO PASA.
```

**El caso de prueba cuadra a mano:** se insertaron 3 citas atendidas de
$150 + $100 + $250 = **$500**. El panel mostró **$500** en el mes, **$250** hoy
y en la semana (las dos de hoy; la de hace 8 días queda fuera de la semana en
curso), y **$125** de ticket promedio del día ($250 / 2 citas). Los tres coinciden.

**Estado de la base tras la prueba:** idéntico al inicial —
`barber_citas = 0`, `barber_clientes = 2`, `barber_operadores = 2`,
y el resto en 0. No quedó nada de prueba.

**Verificación visual:** se capturaron pantallas con Chrome sin interfaz a un
ancho de **390 px** (celular típico), en los dos escenarios:

- Sin datos: se ve el aviso "Sin datos todavía", las 8 tarjetas en $0 / —, y
  cada bloque con su texto de "sin datos". Ningún hueco roto.
- Con datos: barras de servicios, horas pico, reparto de estados con colores,
  tabla de citas de hoy con su etiqueta de estado, y el gráfico de 30 días.

En ambos casos el diseño pasa a **2 columnas** de tarjetas y las tablas siguen
siendo legibles en 390 px.

---

## 8. Resumen de por qué esta opción y no las del documento

| | Looker Studio | Metabase | Grafana | **HTML (elegida)** |
|---|---|---|---|---|
| Base expuesta a internet | **Sí** | No | No | **No** |
| Cuenta de tercero | **Sí** | No | No | **No** |
| Servicio extra que mantener | Sí (SaaS) | Sí (JVM lenta) | Sí | **Ninguno** |
| Paso manual con contraseña | Sí | **Sí (admin)** | **Sí (admin)** | **No** |
| Tiempo hasta ver algo | Minutos | 1-3 min + wizard | Minutos | **~1 segundo** |
| Funciona sin internet | **No** | Sí | Sí | **Sí** |
| Se ve bien con 0 datos | n/d | n/d | n/d | **Sí (probado)** |
| Costo | $0 | $0 | $0 | **$0** |

La conclusión práctica: para **un barbero, un negocio y una PC local**, la
herramienta más potente no es la que tiene más funciones, sino la que **de verdad
está funcionando hoy**, se abre desde el celular sin internet y no obliga a
exponer la base de datos.
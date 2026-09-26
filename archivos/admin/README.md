# Panel administrativo de Barber Chinos

El panel de seis secciones consulta los registros del negocio y permite enviar mensajes de WhatsApp a clientes del CRM. Se genera como HTML con estilos, iconos y fuentes embebidos, pero **debe abrirse desde el servidor**: `file://` ya no ofrece datos ni acciones. Los datos se consultan en Postgres; el envío sale únicamente del backend hacia Evolution API.

## Ponerlo en marcha en desarrollo

Desde la raíz del repositorio:

```sh
uv run python archivos/admin/generar-admin.py
uv run python archivos/admin/servidor-admin.py --hash-password
```

El segundo comando solicita una contraseña de al menos 12 caracteres y devuelve un hash. Guárdalo en `ADMIN_PASSWORD_HASH`, **no** la contraseña sin cifrar. Configura las variables de entorno en la sesión del servidor, no en el HTML ni en un archivo versionado:

| Variable | Finalidad |
|---|---|
| `ADMIN_DB_DSN` | DSN de Postgres con un usuario dedicado de **solo lectura** (`CONNECT`, `USAGE public`, `SELECT` sobre `barber_citas`, `barber_clientes`, `barber_servicios`). No uses las credenciales de administración/n8n. |
| `ADMIN_PRICE_DB_DSN` | DSN **distinto** del de lectura, rol `barber_admin_price` con permiso `EXECUTE` sobre una sola función de edición de precio (sin acceso directo a tablas). Requerido únicamente cuando las escrituras estén habilitadas. |
| `ADMIN_PRICE_UPDATES_ENABLED` | `false` por defecto. Poner `true` **solo después** de probar que W1 en producción consulta el catálogo actualizado antes de responder precios; nunca habilitar si conserva precios fijos en el prompt. |
| `ADMIN_PASSWORD_HASH` | Hash obtenido con `--hash-password`. |
| `ADMIN_SESSION_SECRET` | Cadena aleatoria de al menos 64 caracteres, generada con un generador criptográfico. |
| `ADMIN_PUBLIC_ORIGIN` | Origen exacto que ve el navegador; para desarrollo local, `http://127.0.0.1:8765`. |
| `EVOLUTION_URL` | Base de Evolution API alcanzable desde el servidor, por ejemplo `http://127.0.0.1:8080`. |
| `EVOLUTION_API_KEY` | Clave de API protegida en el entorno del backend. |
| `EVOLUTION_INSTANCE` | Nombre de la instancia de WhatsApp. |

Instala el driver en el entorno del proyecto: `uv run --with 'psycopg[binary]>=3,<4' python archivos/admin/servidor-admin.py`. Abre el `ADMIN_PUBLIC_ORIGIN` configurado e inicia sesión. La interfaz no almacena credenciales en el navegador; la sesión es una cookie `HttpOnly`, `SameSite=Strict` y `Secure` si usas HTTPS, y las escrituras exigen token CSRF. Para cerrar la sesión, pulsa «Cerrar sesión».

El servidor por defecto escucha solo en `127.0.0.1:8765` y no debe exponerse públicamente. `ADMIN_BIND`, `ADMIN_PORT` y `ADMIN_JOURNAL_PATH` son opcionales. El registro SQLite de idempotencia de envíos debe permanecer en almacenamiento privado y persistente, con **una sola instancia** de este servidor por registro. El administrador no requiere iniciar otro workflow de n8n; la API de Evolution sí debe estar en ejecución para enviar.

### Uso desde el teléfono

En desarrollo, conectar el teléfono a la misma red **no basta**: el panel transporta datos de clientes y habilita envíos, así que no abras su puerto por HTTP plano en la LAN. Configura un certificado TLS cuyo nombre sea válido y **confiable en el teléfono**, fija `ADMIN_PUBLIC_ORIGIN=https://<nombre>:<puerto>`, configura `ADMIN_BIND` en la interfaz local con `ADMIN_TLS_CERT` y `ADMIN_TLS_KEY`, y limita el puerto a la red confiable con el firewall. Una alternativa es conectar el teléfono por una VPN privada que termine en un servidor HTTPS. El proceso se niega a escuchar en una interfaz pública sin certificado. No desactives la verificación TLS del navegador para eludir la advertencia. Cuando migre a VPS, mantén la API y el HTML en el mismo origen detrás de HTTPS, con el puerto interno restringido a loopback y secretos rotados fuera del repositorio.

## Qué muestran los datos

- **Inicio:** citas del día y próximas citas registradas, ingresos, asistencia y evolución de los últimos 30 días.
- **Agenda:** registros de `barber_citas` con fecha, estado, paginación y acción de mensaje si la cita tiene cliente vinculado.
- **Clientes:** fichas buscables de `barber_clientes`, visitas y acción de mensaje.
- **Servicios:** catálogo de `barber_servicios` y actividad observada en citas atendidas; permite editar precios cuando está habilitado. «Depilación» muestra «Según zona» (el 0 de Postgres es un marcador, **no** un servicio gratis ni un precio editable).
- **Reportes:** ingresos de citas marcadas `atendido` con precio, y conteos por servicio/hora. No son cobros comprobados.
- **Configuración:** información sobre acceso, origen de datos y mensajería.

**Google Calendar sigue siendo la fuente de verdad de la agenda.** Postgres guarda un espejo que puede estar vacío o desactualizado aunque Calendar tenga citas. Un cero en este panel **no** certifica que la barbería no tenga reservas. La interfaz debe mostrar la procedencia y última actualización real del espejo, además de indicar si no hay datos; no se agenda ni cancela en este panel. No confundas la hora de respuesta de la API con la fecha de sincronización de una cita.

El botón «Mensaje» abre una confirmación y envía el texto únicamente al cliente registrado en el CRM. La respuesta «aceptado por Evolution» confirma la aceptación de la solicitud, **no la entrega ni la lectura** en WhatsApp. Ante un timeout o estado desconocido no se reintenta automáticamente: comprueba el resultado antes de iniciar otro envío. Hay limitación de frecuencia por destinatario e idempotencia para evitar dobles pulsaciones. No envíes mensajes de prueba a clientes reales.

## Edición segura de precios (deshabilitada inicialmente)

1. Comprueba que la instancia local de Postgres es **la misma** que leerá W1 y respáldala. Con un administrador de base de datos aplica manualmente `archivos/admin/precios-admin.sql` en una ventana coordinada: añade `precio_version`, auditoría transaccional y un rol `barber_admin_price` que solo ejecuta `admin_cambiar_precio`. Revisa previamente que `depilacion` tiene precio 0 y que no haya permisos previos de `PUBLIC` que impidan el aislamiento. El script no se ejecuta al iniciar el servidor. Usa `psql -v ON_ERROR_STOP=1 -f archivos/admin/precios-admin.sql` y establece la contraseña del nuevo rol **fuera** del repositorio (`psql \password barber_admin_price`). El rol de lectura debe conservar `SELECT` sobre `barber_servicios`; antes de aplicar la migración el listado seguirá siendo de solo lectura y mostrará `precioVersion=null`. **No uses el DSN de n8n ni el propietario como credencial web.**
2. Despliega y comprueba W1 con catálogo dinámico desde `barber_servicios`: los ocho servicios deben estar completos, incluidos los precios actuales, y depilación debe responder «precio según la zona». La versión local no demuestra que W1 esté publicado ni que use este Postgres. Conserva `ADMIN_PRICE_UPDATES_ENABLED=false` hasta completar esta comprobación.
3. Configura `ADMIN_PRICE_DB_DSN` con el rol restringido y habilita `ADMIN_PRICE_UPDATES_ENABLED=true` solo entonces. Reinicia el servidor. Cada actualización exige sesión, origen exacto y CSRF; el usuario ve precio anterior y nuevo, confirma expresamente y recibe un conflicto 409 si otro actor cambió la versión. Actualiza la lista para resolverlo. El precio de las citas existentes no se reescribe.

`GET /api/admin/servicios` añade `precioVersion` por servicio y `preciosEditables` global. `POST /api/admin/servicios/precio` recibe exclusivamente `{ "clave":"corte", "precio":"180.00", "version":1 }` (MXN, cadena decimal positiva de hasta 999999.99 con dos decimales) y devuelve `{ "clave":"corte", "precio":"180.00", "precioVersion":2 }`. Un 409 `PRICE_CONFLICT` exige volver a leer; no se debe reintentar ciegamente. El historial de precio, versión y solicitud queda en `barber_admin_precio_audit`. El precio 0 de `depilacion` queda protegido también en Postgres, incluso frente al comando PRECIO del propietario. **La sincronización de datos para el agente debe probarse antes de abrir el editor a producción.**

## API y mantenimiento

Las rutas `/api/admin/sesion`, `/resumen`, `/citas`, `/clientes`, `/servicios`, `/servicios/precio`, `/reportes`, `/login`, `/logout` y `/mensajes` comparten el prefijo `/api/admin/` y el mismo origen del HTML. Las respuestas usan `{ "ok": true, "data": ... }` o `{ "ok": false, "error": { "code": "...", "message": "..." } }`. Las rutas de datos y envío requieren sesión; el envío y cierre requieren `Origin` exacto y `X-CSRF-Token`. No guardes claves Evolution ni DSN en JavaScript. `generar-admin.py` es el origen del HTML generado; edita `plantilla.html` y `app.js.html`, nunca solo `barber-chinos-admin.html`.

Pruebas sin envíos reales: `uv run python -m unittest discover -s archivos/admin -p 'test*.py'`; genera de nuevo el HTML y verifica `verify.py` junto a `archivos/dashboard/verificar-patrones.py`. Los scripts históricos `verificar-file-real.py` y `verificar-vistas.py` comprueban la **antigua maqueta offline** y deben sustituirse o adaptarse para el servidor autenticado, no interpretarse como pruebas del panel nuevo. Evita ejecutar scripts de prueba que alteran Postgres en producción.

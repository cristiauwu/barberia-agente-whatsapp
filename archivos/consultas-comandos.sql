-- Consultas y tablas para los comandos del dueño.
--
-- Se añaden dos tablas que el esquema original no tenía:
--   barber_servicios -> precio y duración por servicio (comando PRECIO)
--   barber_pausas    -> clientes a los que el bot no debe contestar (PAUSA)
--
-- Los estados válidos de cita son: agendado, confirmado, atendido, no_show,
-- cancelado, reprogramado. Zona horaria del negocio: America/Mexico_City
-- (UTC-06:00 fijo, México no usa horario de verano desde 2022).

BEGIN;

-- ---------------------------------------------------------------------------
-- Tabla nueva: servicios (fuente única de precios)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS barber_servicios (
    clave        text PRIMARY KEY,
    nombre       text NOT NULL,
    precio       numeric NOT NULL DEFAULT 0,
    duracion_min integer,
    activo       boolean NOT NULL DEFAULT true,
    actualizado_en timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT barber_servicios_precio_chk CHECK (precio >= 0),
    CONSTRAINT barber_servicios_duracion_chk
        CHECK (duracion_min IS NULL OR duracion_min > 0)
);

COMMENT ON TABLE barber_servicios IS
    'Catálogo de servicios con precio y duración. Fuente única para el comando PRECIO.';
COMMENT ON COLUMN barber_servicios.clave IS
    'Identificador corto usado en el comando: corte, barba, ceja, mascarilla, dama, planchado, peinado, depilacion.';
COMMENT ON COLUMN barber_servicios.precio IS
    'Precio en pesos. Para depilación queda en 0 porque depende de la zona.';

-- Siembra idempotente con los precios reales del negocio
INSERT INTO barber_servicios (clave, nombre, precio, duracion_min) VALUES
    ('corte',      'Corte desvanecido o tijera', 150, 40),
    ('barba',      'Arreglo de barba',           100, 20),
    ('ceja',       'Ceja',                        30, 10),
    ('mascarilla', 'Mascarilla',                  50, 20),
    ('dama',       'Corte de cabello dama',      250, 50),
    ('planchado',  'Planchado express',          150, 30),
    ('peinado',    'Peinado',                    300, 45),
    ('depilacion', 'Depilación',                   0, 30)
ON CONFLICT (clave) DO NOTHING;

-- ---------------------------------------------------------------------------
-- Tabla nueva: pausas (el bot deja de contestar a un cliente)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS barber_pausas (
    jid       text PRIMARY KEY,
    hasta     timestamptz NOT NULL,
    motivo    text,
    creado_en timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE barber_pausas IS
    'Clientes a los que el bot NO debe contestar hasta la hora indicada. La usa el comando PAUSA.';
COMMENT ON COLUMN barber_pausas.jid IS
    'JID de WhatsApp del cliente (ej. 5214501111805@s.whatsapp.net).';
COMMENT ON COLUMN barber_pausas.hasta IS
    'Momento en que expira la pausa. Pasado ese instante el bot vuelve a contestar.';

CREATE INDEX IF NOT EXISTS idx_barber_pausas_hasta ON barber_pausas (hasta);

COMMIT;

-- ===========================================================================
-- @@FIN-DDL
--
-- TODO LO QUE SIGUE SON PLANTILLAS, NO SE EJECUTAN CON `psql -f`.
-- Usan variables de psql (:'nombre') que se pasan con -v al invocarlas.
-- El script probar-consultas.py solo aplica la parte de arriba (hasta este
-- marcador) y luego ejecuta cada plantilla por separado con sus valores.
-- ===========================================================================

-- COMANDO: HOY / MAÑANA / SEMANA / LIBRE -- citas de un rango
-- Variables: :'desde' y :'hasta' (timestamptz)
-- Devuelve hora local de México, cliente, servicio, precio y estado.
SELECT
    to_char(c.inicio AT TIME ZONE 'America/Mexico_City', 'HH24:MI') AS hora,
    to_char(c.inicio AT TIME ZONE 'America/Mexico_City', 'YYYY-MM-DD') AS fecha,
    coalesce(nullif(c.nombre, ''), cl.nombre, 'Sin nombre') AS cliente,
    c.servicio,
    c.precio,
    c.estado
FROM barber_citas c
LEFT JOIN barber_clientes cl ON cl.jid = c.jid
WHERE c.inicio >= :'desde'::timestamptz
  AND c.inicio <= :'hasta'::timestamptz
  AND c.estado IN ('agendado', 'confirmado')
ORDER BY c.inicio;

-- COMANDO: HOY -- resumen en una sola fila (numero de citas y total)
SELECT
    count(*) AS citas,
    coalesce(sum(precio), 0) AS total_estimado
FROM barber_citas
WHERE inicio >= :'desde'::timestamptz
  AND inicio <= :'hasta'::timestamptz
  AND estado IN ('agendado', 'confirmado');

-- COMANDO: CLIENTE -- ficha completa buscando por número
-- Variables: :'busqueda' (texto parcial: sirve el número con o sin
-- @s.whatsapp.net y con o sin el prefijo 52 / 521).
--
-- NORMALIZACIÓN: un número mexicano tiene 10 dígitos útiles. Los formatos
-- de WhatsApp son 52 + 10 y 521 + 10, así que se comparan los ÚLTIMOS 10
-- dígitos. NO se usa replace(jid,'521','') ni regexp '^521?' porque
-- borrarían el "52" de cualquier número que empiece con 52 (por ejemplo
-- 529991112233 quedaría en 9991112233, y 524521206246 en 4206246).
SELECT
    cl.jid,
    cl.nombre,
    cl.telefono,
    cl.etiqueta,
    cl.visitas,
    cl.no_shows,
    cl.cancelaciones_tardias,
    cl.ticket_promedio,
    cl.servicio_habitual,
    cl.barbero_preferido,
    cl.nota_interna,
    to_char(cl.primera_visita AT TIME ZONE 'America/Mexico_City', 'DD/MM/YYYY') AS primera,
    to_char(cl.ultima_visita  AT TIME ZONE 'America/Mexico_City', 'DD/MM/YYYY') AS ultima,
    cl.marketing_ok,
    (SELECT count(*) FROM barber_citas c
      WHERE c.jid = cl.jid AND c.inicio > now()
        AND c.estado IN ('agendado', 'confirmado')) AS citas_futuras
FROM barber_clientes cl
WHERE cl.jid LIKE '%' || :'busqueda' || '%'
   OR right(regexp_replace(cl.telefono, '\D', '', 'g'), 10)
      = right(regexp_replace(:'busqueda', '\D', '', 'g'), 10)
   OR right(regexp_replace(split_part(cl.jid, '@', 1), '\D', '', 'g'), 10)
      = right(regexp_replace(:'busqueda', '\D', '', 'g'), 10)
LIMIT 5;

-- COMANDO: PRECIO -- listar el catálogo de servicios
SELECT clave, nombre, precio, duracion_min
FROM barber_servicios
WHERE activo
ORDER BY precio DESC;

-- COMANDO: PRECIO -- actualizar el precio (y opcionalmente la duración)
-- Variables: :'clave', :'precio', :'duracion' (puede ser NULL)
UPDATE barber_servicios
   SET precio = :'precio'::numeric,
       duracion_min = coalesce(nullif(:'duracion', '')::integer, duracion_min),
       actualizado_en = now()
 WHERE clave = :'clave'
RETURNING clave, nombre, precio, duracion_min;

-- COMANDO: PAUSA -- insertar o extender una pausa
-- Variables: :'jid' y :'horas'
INSERT INTO barber_pausas (jid, hasta, motivo)
VALUES (:'jid', now() + (:'horas' || ' hours')::interval, 'comando del dueño')
ON CONFLICT (jid) DO UPDATE
   SET hasta = greatest(barber_pausas.hasta, excluded.hasta),
       motivo = excluded.motivo
RETURNING jid, hasta;

-- COMANDO: PAUSA -- ¿este cliente está pausado ahora mismo?
-- Variable: :'jid'
SELECT jid, hasta, motivo
FROM barber_pausas
WHERE jid = :'jid' AND hasta > now();

-- COMANDO: PAUSA -- listar las pausas vigentes (para el comando ESTADO)
SELECT jid, hasta, motivo FROM barber_pausas WHERE hasta > now()
ORDER BY hasta;

-- COMANDO: BLOQUEAR / CERRAR -- bloqueos vigentes (para que el agente no
-- ofrezca esos huecos ni esos días)
SELECT id, inicio, fin, motivo
FROM barber_bloqueos
WHERE fin >= now()
ORDER BY inicio;

-- COMANDO: ESTADO -- salud del sistema en una sola fila
SELECT
    (SELECT count(*) FROM barber_citas
      WHERE inicio >= date_trunc('day', now() AT TIME ZONE 'America/Mexico_City')
        AND inicio <  date_trunc('day', now() AT TIME ZONE 'America/Mexico_City') + interval '1 day'
        AND estado IN ('agendado', 'confirmado')) AS citas_hoy,
    (SELECT count(*) FROM barber_citas
      WHERE inicio >= now() AND inicio < now() + interval '7 days'
        AND estado IN ('agendado', 'confirmado')) AS citas_semana,
    (SELECT count(*) FROM barber_escalaciones
      WHERE coalesce(estado, 'abierta') = 'abierta') AS escalaciones_abiertas,
    (SELECT count(*) FROM barber_pausas WHERE hasta > now()) AS pausas_activas,
    (SELECT count(*) FROM barber_operadores WHERE activo) AS operadores_activos,
    (SELECT max(ts) FROM barber_auditoria) AS ultima_auditoria;
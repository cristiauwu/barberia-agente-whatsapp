-- =====================================================================
-- supabase-esquema.sql
-- Barber Chinos - Peluqueria & Barberia
-- Espejo del sistema local (n8n + WhatsApp + Google Calendar) en Supabase
--
-- DONDE PEGAR ESTO (leer SUPABASE-GUIA.md para el detalle):
--   Supabase Dashboard -> tu proyecto -> "SQL Editor" (icono </>)
--   -> "New query" -> pegar TODO este archivo -> boton "Run".
--
-- IDEMPOTENTE
--   Se puede ejecutar tantas veces como quieras sin romper nada y sin
--   duplicar datos: usa CREATE ... IF NOT EXISTS, DO $$ ... $$ con
--   comprobaciones en pg_constraint/pg_matviews, DROP TRIGGER IF EXISTS y
--   ON CONFLICT DO NOTHING.
--
-- QUE **NO** HACE ESTE ARCHIVO
--   - No crea la tabla "barbers" ni campos "barber_id": el negocio tiene
--     UN SOLO BARBERO (Esteban Aguilera). No hay multi-barbero ni
--     "commission_pct".
--   - No crea nada de pagos: el usuario rechazo explicitamente el cobro
--     con tarjeta. No hay "payment_method" ni tabla de pagos.
--   - No usa "price_charged": el sistema real usa la columna "precio".
--   - No usa "reminder_2h_sent": los recordatorios reales son de 24 h y
--     1 h (nodos "RECORDATORIO 24 H" / "RECORDATORIO 1 H").
--
-- ADAPTACIONES RESPECTO AL DOCUMENTO PROPUESTO (ver SUPABASE-GUIA.md):
--   - Estados en espanol: agendado, confirmado, atendido, no_show,
--     cancelado, reprogramado (los reales del sistema).
--   - La constraint anti-doble-reserva es SIN barber_id: solo un barbero,
--     asi que basta el rango temporal.
--   - Se respeta el prefijo "barber_" para que las tablas de n8n
--     (workflow_entity, execution_entity, ...) no choquen nunca y para que
--     el dia que se apunte n8n a Supabase las queries funcionen igual.
--
-- ZONA HORARIA
--   America/Mexico_City, offset fijo -06:00 (Mexico no usa horario de
--   verano). Todo se guarda en timestamptz (UTC) y se muestra en -06:00.
-- =====================================================================


-- =====================================================================
-- 0) EXTENSIONES
-- =====================================================================
-- btree_gist es IMPRESCINDIBLE: permite mezclar una igualdad (=) con el
-- solapamiento de rangos (&&) dentro de un mismo indice GiST, que es lo
-- que necesita la constraint EXCLUDE anti-doble-reserva.
--
-- En el plan GRATIS de Supabase btree_gist SI esta disponible (viene en
-- el catalogo estandar de extensiones de la imagen de Postgres de
-- Supabase). El SQL Editor corre como rol postgres, que tiene permiso
-- para CREATE EXTENSION. Si aun asi fallara, ver la seccion
-- "PLAN B SIN btree_gist" al final de este archivo.
CREATE EXTENSION IF NOT EXISTS btree_gist;

-- pgcrypto aporta gen_random_uuid(), util si algun dia se pasa a UUID.
CREATE EXTENSION IF NOT EXISTS pgcrypto;


-- =====================================================================
-- 1) barber_clientes - ficha unica por cliente de WhatsApp (CRM)
-- =====================================================================
CREATE TABLE IF NOT EXISTS public.barber_clientes (
    jid                   text        PRIMARY KEY,
    nombre                text,
    telefono              text,
    primera_visita        timestamp,
    visitas               integer     NOT NULL DEFAULT 0,
    ultima_visita         timestamp,
    ticket_promedio       numeric(10,2),
    no_shows              integer     NOT NULL DEFAULT 0,
    cancelaciones_tardias integer     NOT NULL DEFAULT 0,
    servicio_habitual     text,
    barbero_preferido     text,
    nota_interna          text,
    fecha_nacimiento      date,
    marketing_ok          boolean     NOT NULL DEFAULT false,
    etiqueta              text,
    creado_en             timestamp   NOT NULL DEFAULT now(),
    CONSTRAINT barber_clientes_visitas_chk  CHECK (visitas IS NULL OR visitas >= 0),
    CONSTRAINT barber_clientes_no_shows_chk CHECK (no_shows IS NULL OR no_shows >= 0),
    CONSTRAINT barber_clientes_cancel_chk   CHECK (cancelaciones_tardias IS NULL OR cancelaciones_tardias >= 0),
    CONSTRAINT barber_clientes_ticket_chk   CHECK (ticket_promedio IS NULL OR ticket_promedio >= 0),
    CONSTRAINT barber_clientes_etiqueta_chk CHECK (
        etiqueta IS NULL OR etiqueta IN (
            'nuevo', 'frecuente', 'vip', 'en_riesgo',
            'problematico', 'consulta', 'inactivo'
        )
    )
);

COMMENT ON TABLE  public.barber_clientes IS
    'Ficha de cada cliente de WhatsApp (CRM del agente). La PK es el JID de WhatsApp, p.ej. 5214501111805@s.whatsapp.net. Espejo 1:1 de la tabla local barber_clientes.';
COMMENT ON COLUMN public.barber_clientes.jid             IS 'Identificador WhatsApp (JID). Clave primaria y llave de union con el resto de tablas barber_.';
COMMENT ON COLUMN public.barber_clientes.visitas         IS 'Contador historico de visitas atendidas (default 0).';
COMMENT ON COLUMN public.barber_clientes.ticket_promedio IS 'Gasto promedio por visita en pesos (numeric 10,2).';
COMMENT ON COLUMN public.barber_clientes.no_shows        IS 'Veces que el cliente no se presento a una cita agendada.';
COMMENT ON COLUMN public.barber_clientes.cancelaciones_tardias IS 'Cancelaciones avisadas con poco margen (menos de 2 h).';
COMMENT ON COLUMN public.barber_clientes.marketing_ok    IS 'Espejo de barber_consentimiento.marketing_ok: true = acepto promociones.';
COMMENT ON COLUMN public.barber_clientes.etiqueta        IS 'Segmento operativo. Valores validos: nuevo, frecuente, vip, en_riesgo, problematico, consulta, inactivo.';
COMMENT ON COLUMN public.barber_clientes.barbero_preferido IS 'Legado del diseno multi-barbero. Aqui solo puede ser Esteban Aguilera; se conserva por compatibilidad con el sistema local.';


-- =====================================================================
-- 2) barber_servicios - catalogo real de servicios y precios
-- =====================================================================
CREATE TABLE IF NOT EXISTS public.barber_servicios (
    clave          text        PRIMARY KEY,
    nombre         text        NOT NULL,
    precio         numeric     NOT NULL DEFAULT 0,
    duracion_min   integer,
    activo         boolean     NOT NULL DEFAULT true,
    actualizado_en timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT barber_servicios_precio_chk   CHECK (precio >= 0),
    CONSTRAINT barber_servicios_duracion_chk CHECK (duracion_min IS NULL OR duracion_min > 0)
);

COMMENT ON TABLE  public.barber_servicios IS
    'Catalogo de servicios con precio y duracion REALES de Barber Chinos. Es la fuente que usa el agente para calcular cuando TERMINA una cita (regla: debe terminar antes de las 20:00).';
COMMENT ON COLUMN public.barber_servicios.clave        IS 'Clave corta del servicio: corte, barba, ceja, mascarilla, dama, planchado, peinado, depilacion.';
COMMENT ON COLUMN public.barber_servicios.duracion_min IS 'Duracion en minutos. Critica para calcular el fin de cita y para la constraint anti-solape.';

-- Catalogo REAL (de la tabla local barber_servicios). Idempotente: si ya
-- existe la clave, solo refresca nombre/precio/duracion.
INSERT INTO public.barber_servicios (clave, nombre, precio, duracion_min, activo) VALUES
    ('corte',      'Corte desvanecido o tijera', 150, 40, true),
    ('barba',      'Arreglo de barba',           100, 20, true),
    ('ceja',       'Ceja',                        30, 10, true),
    ('mascarilla', 'Mascarilla',                  50, 20, true),
    ('dama',       'Corte de cabello dama',      250, 50, true),
    ('planchado',  'Planchado express',          150, 30, true),
    ('peinado',    'Peinado',                    300, 45, true),
    ('depilacion', 'Depilacion',                   0, 30, true)
ON CONFLICT (clave) DO UPDATE
    SET nombre       = EXCLUDED.nombre,
        precio       = EXCLUDED.precio,
        duracion_min = EXCLUDED.duracion_min,
        activo       = EXCLUDED.activo;


-- =====================================================================
-- 3) barber_operadores - numeros autorizados a mandar comandos
-- =====================================================================
CREATE TABLE IF NOT EXISTS public.barber_operadores (
    jid       text      PRIMARY KEY,
    nombre    text,
    rol       text,
    activo    boolean   NOT NULL DEFAULT true,
    creado_en timestamp NOT NULL DEFAULT now(),
    CONSTRAINT barber_operadores_rol_chk CHECK (
        rol IS NULL OR rol IN ('dueno', 'barbero')
    )
);

COMMENT ON TABLE  public.barber_operadores IS
    'Lista blanca de numeros de WhatsApp con permiso de mandar comandos al agente. El nodo "Es operador?" del workflow lee esta tabla: si el JID no esta aqui con activo = true, el agente atiende como cliente normal.';
COMMENT ON COLUMN public.barber_operadores.rol IS 'Rol del operador: dueno (control total) o barbero.';

-- Los dos JID reales del dueno (los que ya estan en la tabla local).
INSERT INTO public.barber_operadores (jid, nombre, rol, activo) VALUES
    ('524521206246@s.whatsapp.net', 'Dueno', 'dueno', true),
    ('5214521206246@s.whatsapp.net', 'Dueno', 'dueno', true)
ON CONFLICT (jid) DO NOTHING;


-- =====================================================================
-- 4) barber_citas - LA TABLA CENTRAL. 1 fila = 1 cita.
-- =====================================================================
-- La PK "id" es el ID del evento de Google Calendar: eso da idempotencia
-- natural a la sincronizacion (ON CONFLICT (id) DO UPDATE).
CREATE TABLE IF NOT EXISTS public.barber_citas (
    id             text        PRIMARY KEY,
    jid            text        REFERENCES public.barber_clientes (jid)
                               ON UPDATE CASCADE ON DELETE SET NULL,
    nombre         text,
    servicio       text,
    precio         numeric(10,2),
    inicio         timestamptz,
    fin            timestamptz,
    estado         text,
    -- Recordatorios REALES del sistema: 24 h y 1 h. Nada de 2 h.
    recordatorio_24h_enviado_en timestamptz,
    recordatorio_1h_enviado_en  timestamptz,
    creado_en      timestamptz NOT NULL DEFAULT now(),
    actualizado_en timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT barber_citas_estado_chk CHECK (
        estado IS NULL OR estado IN (
            'agendado', 'confirmado', 'atendido',
            'no_show', 'cancelado', 'reprogramado'
        )
    ),
    CONSTRAINT barber_citas_precio_chk CHECK (precio IS NULL OR precio >= 0),
    CONSTRAINT barber_citas_rango_chk  CHECK (inicio IS NULL OR fin IS NULL OR fin > inicio)
);

COMMENT ON TABLE  public.barber_citas IS
    'Estado actual de cada cita: una fila por evento de Google Calendar (la PK es el ID del evento). Espejo del calendario para consultar disponibilidad, recordatorios y metricas sin pegarle a la API de Google.';
COMMENT ON COLUMN public.barber_citas.id       IS 'ID del evento en Google Calendar (PK, idempotencia natural de la sincronizacion).';
COMMENT ON COLUMN public.barber_citas.jid      IS 'Cliente de la cita (barber_clientes.jid). NULL si el evento existe en Calendar pero el cliente aun no esta en el CRM.';
COMMENT ON COLUMN public.barber_citas.servicio IS 'Texto del servicio tal como llega de la hoja (p.ej. "Corte desvanecido o tijera").';
COMMENT ON COLUMN public.barber_citas.precio   IS 'Precio cobrado en pesos. El sistema real usa "precio", NO "price_charged".';
COMMENT ON COLUMN public.barber_citas.estado   IS 'Maquina de estados REAL en espanol. Valores: agendado, confirmado, atendido, no_show, cancelado, reprogramado.';
COMMENT ON COLUMN public.barber_citas.recordatorio_24h_enviado_en IS 'Momento en que se envio el recordatorio de 24 h. NULL = aun no enviado.';
COMMENT ON COLUMN public.barber_citas.recordatorio_1h_enviado_en  IS 'Momento en que se envio el recordatorio de 1 h. NULL = aun no enviado.';
COMMENT ON COLUMN public.barber_citas.actualizado_en IS 'Se actualiza solo en cada UPDATE (trigger trg_barber_citas_touch).';

-- ---------------------------------------------------------------------
-- 4.1) INDICES PARA REPORTES Y CONSULTAS CALIENTES
-- ---------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_barber_citas_jid            ON public.barber_citas (jid);
CREATE INDEX IF NOT EXISTS idx_barber_citas_estado         ON public.barber_citas (estado);
CREATE INDEX IF NOT EXISTS idx_barber_citas_inicio         ON public.barber_citas (inicio DESC);
CREATE INDEX IF NOT EXISTS idx_barber_citas_estado_inicio  ON public.barber_citas (estado, inicio);
-- Indice parcial: la consulta mas caliente del agente es "citas vivas
-- (agendado/confirmado) a partir de ahora".
CREATE INDEX IF NOT EXISTS idx_barber_citas_vivas
    ON public.barber_citas (inicio)
    WHERE estado IN ('agendado', 'confirmado');
-- Indices parciales para que los recordatorios encuentren rapido lo que
-- falta por enviar (el indice no indexa las filas ya enviadas).
CREATE INDEX IF NOT EXISTS idx_barber_citas_rec24_pendiente
    ON public.barber_citas (inicio)
    WHERE recordatorio_24h_enviado_en IS NULL AND estado IN ('agendado', 'confirmado');
CREATE INDEX IF NOT EXISTS idx_barber_citas_rec1_pendiente
    ON public.barber_citas (inicio)
    WHERE recordatorio_1h_enviado_en IS NULL AND estado IN ('agendado', 'confirmado');

-- ---------------------------------------------------------------------
-- 4.2) TRIGGER: mantener actualizado_en al dia
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.barber_touch_actualizado_en()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.actualizado_en := now();
    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION public.barber_touch_actualizado_en() IS
    'Trigger generico de barber_: sella NEW.actualizado_en con now() en cada UPDATE.';

DROP TRIGGER IF EXISTS trg_barber_citas_touch ON public.barber_citas;
CREATE TRIGGER trg_barber_citas_touch
    BEFORE UPDATE ON public.barber_citas
    FOR EACH ROW EXECUTE FUNCTION public.barber_touch_actualizado_en();


-- =====================================================================
-- 5) LA JOYA: CONSTRAINT ANTI-DOBLE-RESERVA
-- =====================================================================
-- Hace IMPOSIBLE que dos citas vivas se solapen. No es una validacion de
-- aplicacion: si dos procesos (n8n, un humano, cualquiera) intentan meter
-- citas que se empalman, Postgres rechaza la segunda con error 23P01
-- (exclusion_violation) y hay que elegir otro horario.
--
-- DIFERENCIA CON EL DOCUMENTO ORIGINAL:
--   El original hacia  EXCLUDE USING gist (barber_id WITH =, rango WITH &&)
--   Eso solo tiene sentido con VARIOS barberos. Aqui hay UNO SOLO
--   (Esteban Aguilera), asi que "barber_id" seria una columna constante
--   que no aporta nada: se elimina y la exclusion queda solo sobre el
--   rango temporal.
--
--   WHERE (estado IN ('agendado','confirmado')) en lugar de
--   ('pending','confirmed'): solo las citas VIVAS bloquean el horario.
--   Una cita atendida, cancelada o no_show libera su hueco.
--
-- Nota: tstzrange(inicio, fin, '[)') es semiabierto, o sea:
--   10:00-10:40 y 10:40-11:20 NO se solapan (correcto: una empieza
--   justo cuando termina la otra).
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'barber_citas_sin_solape'
          AND conrelid = 'public.barber_citas'::regclass
    ) THEN
        ALTER TABLE public.barber_citas
            ADD CONSTRAINT barber_citas_sin_solape
            EXCLUDE USING gist (
                tstzrange(inicio, fin, '[)') WITH &&
            )
            WHERE (
                inicio IS NOT NULL
                AND fin IS NOT NULL
                AND estado IN ('agendado', 'confirmado')
            );
    END IF;
END
$$;

COMMENT ON CONSTRAINT barber_citas_sin_solape ON public.barber_citas IS
    'ANTI-DOBLE-RESERVA: imposible que dos citas vivas (agendado/confirmado) se solapen. Un solo barbero, por eso no lleva barber_id. Error al violarla: SQLSTATE 23P01 exclusion_violation.';


-- =====================================================================
-- 6) barber_bloqueos - festivos, vacaciones, ausencias
-- =====================================================================
CREATE TABLE IF NOT EXISTS public.barber_bloqueos (
    id        bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    inicio    timestamptz,
    fin       timestamptz,
    motivo    text,
    creado_en timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT barber_bloqueos_rango_chk CHECK (inicio IS NULL OR fin IS NULL OR fin >= inicio)
);

COMMENT ON TABLE public.barber_bloqueos IS
    'Bloqueos de agenda que el agente respeta al ofrecer horarios: festivos, vacaciones de Esteban y ausencias puntuales. Un bloqueo que cubre el horario pedido lo descarta.';

CREATE INDEX IF NOT EXISTS idx_barber_bloqueos_inicio ON public.barber_bloqueos (inicio);


-- =====================================================================
-- 7) barber_pausas - el bot en pausa para un numero
-- =====================================================================
CREATE TABLE IF NOT EXISTS public.barber_pausas (
    jid       text        PRIMARY KEY,
    hasta     timestamptz NOT NULL,
    motivo    text,
    creado_en timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.barber_pausas IS
    'Pausa del bot para un JID hasta un momento dado (comando PAUSA). Mientras hasta > now(), el agente no responde a ese numero.';

CREATE INDEX IF NOT EXISTS idx_barber_pausas_hasta ON public.barber_pausas (hasta);


-- =====================================================================
-- 8) barber_escalaciones - casos que el bot no pudo cerrar solo
-- =====================================================================
CREATE TABLE IF NOT EXISTS public.barber_escalaciones (
    id         bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    jid        text,
    motivo     text,
    resumen    text,
    creado_en  timestamptz NOT NULL DEFAULT now(),
    estado     text        DEFAULT 'abierta',
    resolucion text,
    cerrada_en timestamptz,
    CONSTRAINT barber_escalaciones_estado_chk CHECK (
        estado IS NULL OR estado IN ('abierta', 'cerrada')
    ),
    CONSTRAINT barber_escalaciones_motivo_chk CHECK (
        motivo IS NULL OR motivo IN (
            'descuento', 'queja', 'servicio_inexistente',
            'precio_no_listado', 'error_sistema', 'humano'
        )
    )
);

COMMENT ON TABLE public.barber_escalaciones IS
    'Bandeja de casos que el agente no pudo cerrar solo (pide descuento, se queja, pide un servicio inexistente, error del sistema o pide humano). Es la cola de trabajo del dueno.';
COMMENT ON COLUMN public.barber_escalaciones.motivo IS 'Motivo tipificado: descuento, queja, servicio_inexistente, precio_no_listado, error_sistema, humano.';
COMMENT ON COLUMN public.barber_escalaciones.estado IS 'abierta = pendiente de atencion humana; cerrada = ya resuelta (ver resolucion).';

CREATE INDEX IF NOT EXISTS idx_barber_escalaciones_estado ON public.barber_escalaciones (estado);


-- =====================================================================
-- 9) barber_lista_espera - clientes esperando que se libere un hueco
-- =====================================================================
CREATE TABLE IF NOT EXISTS public.barber_lista_espera (
    id              bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    jid             text,
    servicio        text,
    duracion_min    integer,
    ventana_deseada text,
    creado_en       timestamptz NOT NULL DEFAULT now(),
    atendido        boolean     NOT NULL DEFAULT false,
    CONSTRAINT barber_lista_espera_duracion_chk CHECK (duracion_min IS NULL OR duracion_min > 0)
);

COMMENT ON TABLE public.barber_lista_espera IS
    'Clientes que pidieron cita cuando no habia hueco. El agente los avisa cuando se libera (o se cancela) una cita compatible.';
COMMENT ON COLUMN public.barber_lista_espera.ventana_deseada IS 'Texto libre del cliente, p.ej. "sabado por la tarde".';
COMMENT ON COLUMN public.barber_lista_espera.atendido        IS 'true = ya se le ofrecio/agendo hueco; sale de la cola activa.';

CREATE INDEX IF NOT EXISTS idx_barber_lista_espera_pendiente
    ON public.barber_lista_espera (atendido, creado_en);


-- =====================================================================
-- 10) barber_consentimiento - prueba del permiso de marketing
-- =====================================================================
CREATE TABLE IF NOT EXISTS public.barber_consentimiento (
    jid          text        PRIMARY KEY,
    marketing_ok boolean     NOT NULL DEFAULT false,
    ts           timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.barber_consentimiento IS
    'Prueba de consentimiento de marketing por cliente (que dijo y cuando). Se mantiene aparte del CRM porque es evidencia de cumplimiento; barber_clientes.marketing_ok es solo un espejo cacheado.';


-- =====================================================================
-- 11) barber_auditoria - bitacora de cada accion del agente
-- =====================================================================
CREATE TABLE IF NOT EXISTS public.barber_auditoria (
    id          bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    ts          timestamptz NOT NULL DEFAULT now(),
    jid         text,
    intencion   text,
    herramienta text,
    argumentos  jsonb,
    resultado   text,
    exito       boolean
);

COMMENT ON TABLE public.barber_auditoria IS
    'Bitacora de cada accion del agente (que entendio, que herramienta llamo, con que argumentos y como termino). Sirve para depurar y medir el exito por herramienta.';
COMMENT ON COLUMN public.barber_auditoria.intencion   IS 'Intencion detectada: agendar, cancelar, reprogramar, consultar_precio, ...';
COMMENT ON COLUMN public.barber_auditoria.argumentos  IS 'Argumentos exactos de la llamada en jsonb, tal como los genero el modelo.';
COMMENT ON COLUMN public.barber_auditoria.exito       IS 'true = la accion termino bien; false = fallo o quedo escalada.';

CREATE INDEX IF NOT EXISTS idx_barber_auditoria_ts    ON public.barber_auditoria (ts DESC);
CREATE INDEX IF NOT EXISTS idx_barber_auditoria_jid   ON public.barber_auditoria (jid);
CREATE INDEX IF NOT EXISTS idx_barber_auditoria_exito ON public.barber_auditoria (exito);
-- GIN sobre el jsonb de argumentos: permite responder "que citas se
-- agendaron pidiendo tal servicio" o "cuantas escrituras sin precio".
CREATE INDEX IF NOT EXISTS idx_barber_auditoria_argumentos
    ON public.barber_auditoria USING gin (argumentos);


-- =====================================================================
-- 12) VISTA MATERIALIZADA DE KPIs DIARIOS
-- =====================================================================
-- Adaptada a los ESTADOS REALES (atendido / no_show / cancelado) y a la
-- columna REAL de dinero ("precio", no "price_charged").
--
--   atendido     -> la cita SI se hizo y se cobro
--   no_show      -> no se presento (perdida)
--   cancelado    -> cancelada por cualquiera de las dos partes
--   reprogramado -> se movio a otra fecha (NO cuenta como perdida)
--
-- La subconsulta interior normaliza "duracion_min" una sola vez por fila
-- (fin - inicio si esta; si no, la duracion del catalogo; si no, 40 min)
-- y la exterior agrega por dia. Asi el CASE de tasa de no-show no repite
-- la logica de duracion.
-- CASCADE es necesario para que el script sea IDEMPOTENTE: en la 2a pasada
-- la vista metricas_ultimos_30_dias depende de la matview, y sin CASCADE
-- Postgres se negaria a borrarla ("other objects depend on it"). La vista
-- se vuelve a crear mas abajo, asi que no se pierde nada.
DROP MATERIALIZED VIEW IF EXISTS public.daily_metrics CASCADE;

CREATE MATERIALIZED VIEW public.daily_metrics AS
SELECT
    dia,
    COUNT(*)                                                      AS citas_totales,
    COUNT(*) FILTER (WHERE estado = 'atendido')                   AS atendidas,
    COUNT(*) FILTER (WHERE estado = 'no_show')                    AS no_shows,
    COUNT(*) FILTER (WHERE estado = 'cancelado')                  AS canceladas,
    COUNT(*) FILTER (WHERE estado = 'reprogramado')               AS reprogramadas,
    COUNT(*) FILTER (WHERE estado IN ('agendado', 'confirmado'))  AS pendientes,
    COALESCE(SUM(precio) FILTER (WHERE estado = 'atendido'), 0)   AS ingresos,
    COALESCE(ROUND(AVG(precio) FILTER (WHERE estado = 'atendido'), 2), 0) AS ticket_promedio,
    COUNT(DISTINCT jid) FILTER (WHERE estado = 'atendido')        AS clientes_unicos,
    COALESCE(SUM(duracion_min), 0)                                AS minutos_agenda,
    -- Tasa de no-show del dia en % (0-100), sobre las citas YA RESUELTAS.
    -- Un dia sin citas resueltas da 0 en vez de NULL: asi el reporte no
    -- tiene huecos y no hay que usar COALESCE en cada consulta.
    CASE
        WHEN COUNT(*) FILTER (WHERE estado IN ('atendido', 'no_show')) = 0 THEN 0
        ELSE ROUND(
            100.0 * COUNT(*) FILTER (WHERE estado = 'no_show')
            / COUNT(*) FILTER (WHERE estado IN ('atendido', 'no_show')), 2)
    END                                                           AS tasa_no_show_pct
FROM (
    SELECT
        (c.inicio AT TIME ZONE 'America/Mexico_City')::date AS dia,
        c.precio,
        c.estado,
        c.jid,
        COALESCE(
            (EXTRACT(EPOCH FROM (c.fin - c.inicio)) / 60.0)::integer,
            (SELECT s.duracion_min
               FROM public.barber_servicios s
              WHERE lower(c.servicio) LIKE '%' || lower(s.clave) || '%'
                 OR lower(s.nombre)   LIKE '%' || lower(c.servicio) || '%'
              ORDER BY s.duracion_min
              LIMIT 1),
            40
        ) AS duracion_min
    FROM public.barber_citas c
    WHERE c.inicio IS NOT NULL
) AS citas
GROUP BY dia
WITH NO DATA;

COMMENT ON MATERIALIZED VIEW public.daily_metrics IS
    'KPIs por dia (hora local -06:00): citas, atendidas, no_shows, canceladas, ingresos, ticket promedio, clientes unicos, minutos de agenda y tasa de no-show. Refrescar con: REFRESH MATERIALIZED VIEW CONCURRENTLY public.daily_metrics;';

-- El UNIQUE es requisito para poder refrescar CONCURRENTLY, o sea
-- recalcular SIN bloquear las lecturas mientras corre.
CREATE UNIQUE INDEX IF NOT EXISTS daily_metrics_dia_uidx
    ON public.daily_metrics (dia);

-- Vista normal (no materializada) para conectar Looker Studio / Metabase:
-- siempre lee la materializada, que es instantanea.
CREATE OR REPLACE VIEW public.metricas_ultimos_30_dias AS
SELECT
    dia, citas_totales, atendidas, no_shows, canceladas,
    ingresos, ticket_promedio, tasa_no_show_pct
FROM public.daily_metrics
WHERE dia >= (now() AT TIME ZONE 'America/Mexico_City')::date - 30
ORDER BY dia DESC;

COMMENT ON VIEW public.metricas_ultimos_30_dias IS
    'Los ultimos 30 dias de daily_metrics, listo para conectar Looker Studio o Metabase.';


-- =====================================================================
-- 13) FUNCION DE APOYO: barber_hueco_libre()
-- =====================================================================
-- Devuelve true si el hueco [p_inicio, p_fin) esta libre para citas vivas,
-- respetando ademas bloqueos y el horario real del negocio:
--   - lunes a sabado (domingo cerrado)
--   - la cita debe TERMINAR antes de las 20:00 (no solo empezar)
--
-- La constraint EXCLUDE sigue siendo la red de seguridad definitiva; esta
-- funcion sirve para PREGUNTAR antes de intentar y poder dar un mensaje
-- util al cliente en vez de chocar contra el error de Postgres.
CREATE OR REPLACE FUNCTION public.barber_hueco_libre(
    p_inicio timestamptz,
    p_fin    timestamptz
)
RETURNS boolean
LANGUAGE sql
STABLE
AS $$
    SELECT
        p_inicio IS NOT NULL
        AND p_fin IS NOT NULL
        AND p_fin > p_inicio
        AND EXTRACT(ISODOW FROM (p_inicio AT TIME ZONE 'America/Mexico_City')) BETWEEN 1 AND 6
        AND (p_inicio AT TIME ZONE 'America/Mexico_City')::time >= time '10:00'
        AND (p_fin    AT TIME ZONE 'America/Mexico_City')::time <= time '20:00'
        AND NOT EXISTS (
            SELECT 1 FROM public.barber_citas c
            WHERE c.estado IN ('agendado', 'confirmado')
              AND c.inicio IS NOT NULL AND c.fin IS NOT NULL
              AND tstzrange(c.inicio, c.fin, '[)') && tstzrange(p_inicio, p_fin, '[)')
        )
        AND NOT EXISTS (
            SELECT 1 FROM public.barber_bloqueos b
            WHERE b.inicio IS NOT NULL AND b.fin IS NOT NULL
              AND tstzrange(b.inicio, b.fin, '[)') && tstzrange(p_inicio, p_fin, '[)')
        );
$$;

COMMENT ON FUNCTION public.barber_hueco_libre(timestamptz, timestamptz) IS
    'true si el hueco [inicio, fin) esta libre: lun-sab, dentro de 10:00-20:00 y terminando antes de las 20:00, sin cita viva que se solape y sin bloqueo. La constraint barber_citas_sin_solape sigue siendo la garantia final.';


-- =====================================================================
-- 14) SEGURIDAD (RLS)
-- =====================================================================
-- RLS se ACTIVA pero SIN NINGUNA POLITICA. Traduccion: la publishable key
-- (la unica que existe hoy) no puede leer NI escribir NADA por la API
-- REST. Es el ajuste correcto y seguro.
--
-- El rol service_role y el SQL Editor saltan RLS, asi que n8n podra
-- escribir cuando tenga la secret key SIN necesidad de abrir politicas.
--
-- NO agregues aqui politicas "FOR ALL USING (true)": dejaria los datos de
-- tus clientes (telefonos, agenda, ingresos) legibles y modificables por
-- cualquiera que vea la publishable key, que es publica por diseno.
ALTER TABLE public.barber_clientes    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.barber_servicios   ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.barber_operadores  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.barber_citas       ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.barber_bloqueos    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.barber_pausas      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.barber_escalaciones ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.barber_lista_espera ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.barber_consentimiento ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.barber_auditoria   ENABLE ROW LEVEL SECURITY;

-- La vista materializada y la vista normal NO soportan RLS (Postgres no lo
-- implementa para vistas ni matviews). Su acceso se controla con GRANT: se
-- quita el SELECT a los roles publicos para que un panel con la publishable
-- key no pueda leer los ingresos del negocio.
--
-- Al ir despues del REFRESH (ver seccion 15) la vista y la matview ya
-- existen, asi que estos GRANT funcionan en cualquier pasada.
-- NOTA: si tu proyecto todavia no tiene los roles anon/authenticated
-- creados, estas dos sentencias dan error; en ese caso borralas, no son
-- imprescindibles (el DDL las deja sin permiso por defecto de todas formas).


-- =====================================================================
-- 15) REFRESCO DE LA VISTA MATERIALIZADA Y PERMISOS DE LECTURA
-- =====================================================================
-- Rellena daily_metrics ahora mismo (nacio WITH NO DATA).
-- CONCURRENTLY no bloquea las lecturas: es lo que debe usar n8n en su
-- schedule diario. Requiere que la vista ya tenga datos (hecho aqui).
REFRESH MATERIALIZED VIEW public.daily_metrics;

-- Ahora que la matview y la vista ya existen, se les quita el SELECT a los
-- roles publicos. Se hace con un DO para no romper en proyectos donde
-- anon/authenticated todavia no existan.
DO $$
DECLARE
    rol text;
BEGIN
    FOREACH rol IN ARRAY ARRAY['anon', 'authenticated'] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = rol) THEN
            EXECUTE format('REVOKE ALL ON public.daily_metrics FROM %I', rol);
            EXECUTE format('REVOKE ALL ON public.metricas_ultimos_30_dias FROM %I', rol);
        END IF;
    END LOOP;
END
$$;


-- =====================================================================
-- VERIFICACION (descomentar y correr para comprobar que quedo bien)
-- =====================================================================
-- SELECT tablename FROM pg_tables
--  WHERE schemaname = 'public' AND tablename LIKE 'barber\_%' ORDER BY 1;
--
-- SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint
--  WHERE conrelid = 'public.barber_citas'::regclass ORDER BY 1;
--
-- SELECT * FROM public.barber_servicios ORDER BY clave;
--
-- SELECT * FROM public.metricas_ultimos_30_dias LIMIT 5;


-- =====================================================================
-- PLAN B SIN btree_gist (solo si CREATE EXTENSION btree_gist fallara)
-- =====================================================================
-- En el plan gratis de Supabase btree_gist SI esta disponible, asi que
-- este plan B no deberia hacer falta. Se documenta por completitud.
--
-- OPCION B1 - Indice UNICO sobre la clave del hueco exacto.
--   Sirve para el caso "una cita por hora en punto", que es el 95% de
--   esta barberia (agenda en bloques). No cubre solapes parciales.
--
--     CREATE UNIQUE INDEX IF NOT EXISTS barber_citas_hueco_uk
--         ON public.barber_citas (
--             (date_trunc('minute', inicio AT TIME ZONE 'America/Mexico_City'))
--         )
--         WHERE estado IN ('agendado', 'confirmado');
--
-- OPCION B2 - Trigger de validacion (funciona siempre, mas lento).
--   Antes de insertar/actualizar, cuenta las citas vivas que se solapan;
--   si hay alguna, aborta la transaccion. Mismo efecto, sin GiST.
--
--     CREATE OR REPLACE FUNCTION public.barber_validar_solape()
--     RETURNS trigger LANGUAGE plpgsql AS $fn$
--     BEGIN
--         IF NEW.inicio IS NULL OR NEW.fin IS NULL
--            OR NEW.estado NOT IN ('agendado', 'confirmado') THEN
--             RETURN NEW;
--         END IF;
--         IF EXISTS (
--             SELECT 1 FROM public.barber_citas c
--             WHERE c.id <> NEW.id
--               AND c.estado IN ('agendado', 'confirmado')
--               AND tstzrange(c.inicio, c.fin, '[)')
--                   && tstzrange(NEW.inicio, NEW.fin, '[)')
--         ) THEN
--             RAISE EXCEPTION
--                 'Horario ocupado: ya hay una cita viva en ese rango';
--         END IF;
--         RETURN NEW;
--     END;
--     $fn$;
--
--     DROP TRIGGER IF EXISTS trg_barber_citas_solape ON public.barber_citas;
--     CREATE TRIGGER trg_barber_citas_solape
--         BEFORE INSERT OR UPDATE ON public.barber_citas
--         FOR EACH ROW EXECUTE FUNCTION public.barber_validar_solape();
--
-- ATENCION: B2 tiene una carrera teorica (dos transacciones simultaneas
-- pueden pasar ambas el IF EXISTS). B1 y la constraint EXCLUDE no la
-- tienen. Por eso EXCLUDE es la opcion preferida.
-- =====================================================================
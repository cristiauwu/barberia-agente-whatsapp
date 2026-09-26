
-- ===========================================================================
--  Esquema de la barbería en Supabase (plan gratis)
--  Adaptado a: UN SOLO BARBERO (Esteban Aguilera), sin pagos con tarjeta,
--  estados en español, recordatorios a 24 h y 1 h.
--  Idempotente: se puede ejecutar varias veces.
-- ===========================================================================

-- ---------------------------------------------------------------------------
-- 1) Extensiones
-- ---------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS btree_gist;   -- necesario para la EXCLUDE
CREATE EXTENSION IF NOT EXISTS unaccent;     -- búsqueda sin acentos
CREATE EXTENSION IF NOT EXISTS pgcrypto;     -- gen_random_uuid()

-- ---------------------------------------------------------------------------
-- 2) Servicios (catálogo). Espeja barber_servicios del Postgres local.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS barber_servicios (
    clave          text PRIMARY KEY,
    nombre         text NOT NULL,
    precio         numeric(10,2) NOT NULL DEFAULT 0,
    duracion_min   integer,
    categoria      text,
    activo         boolean NOT NULL DEFAULT true,
    descripcion    text,
    actualizado_en timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT barber_servicios_precio_chk CHECK (precio >= 0),
    CONSTRAINT barber_servicios_duracion_chk
        CHECK (duracion_min IS NULL OR duracion_min > 0)
);

COMMENT ON TABLE barber_servicios IS
    'Catálogo de servicios con precio y duración. Precio 0 = se confirma al llegar.';

INSERT INTO barber_servicios (clave, nombre, precio, duracion_min, categoria) VALUES
    ('corte',      'Corte desvanecido o tijera', 150, 40, 'corte'),
    ('barba',      'Arreglo de barba',           100, 20, 'barba'),
    ('ceja',       'Ceja',                        30, 10, 'cuidado'),
    ('mascarilla', 'Mascarilla',                  50, 20, 'cuidado'),
    ('dama',       'Corte de cabello dama',      250, 50, 'corte'),
    ('planchado',  'Planchado express',          150, 30, 'corte'),
    ('peinado',    'Peinado',                    300, 45, 'corte'),
    ('depilacion', 'Depilación',                   0, 30, 'cuidado')
ON CONFLICT (clave) DO NOTHING;

-- ---------------------------------------------------------------------------
-- 3) Clientes
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS barber_clientes (
    jid                 text PRIMARY KEY,
    nombre              text,
    telefono            text,
    primera_visita      timestamptz,
    ultima_visita       timestamptz,
    visitas             integer NOT NULL DEFAULT 0,
    no_shows            integer NOT NULL DEFAULT 0,
    cancelaciones_tardias integer NOT NULL DEFAULT 0,
    ticket_promedio     numeric(10,2),
    total_gastado       numeric(10,2) NOT NULL DEFAULT 0,
    servicio_habitual   text,
    nota_interna        text,
    etiqueta            text,
    marketing_ok        boolean NOT NULL DEFAULT false,
    creado_en           timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT barber_clientes_visitas_chk CHECK (visitas >= 0),
    CONSTRAINT barber_clientes_noshows_chk CHECK (no_shows >= 0),
    CONSTRAINT barber_clientes_etiqueta_chk CHECK (
        etiqueta IS NULL OR etiqueta IN
        ('nuevo','frecuente','vip','en_riesgo','problematico','consulta','inactivo'))
);

COMMENT ON TABLE barber_clientes IS
    'Ficha del cliente. La llave es el JID de WhatsApp.';

-- ---------------------------------------------------------------------------
-- 4) Citas — nombre local, para que migrar sea copia directa
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS barber_citas (
    id             text PRIMARY KEY,     -- es el ID del evento de Google Calendar
    jid            text REFERENCES barber_clientes(jid) ON DELETE SET NULL,
    nombre         text,
    servicio       text,
    precio         numeric(10,2),
    inicio         timestamptz NOT NULL,
    fin            timestamptz NOT NULL,
    estado         text NOT NULL DEFAULT 'agendado',
    metodo_pago    text,                 -- solo informativo (efectivo/transferencia)
    notas          text,
    recordatorio_24h_enviado boolean NOT NULL DEFAULT false,
    recordatorio_1h_enviado  boolean NOT NULL DEFAULT false,
    creado_en      timestamptz NOT NULL DEFAULT now(),
    actualizado_en timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT barber_citas_estado_chk CHECK (estado IN
        ('agendado','confirmado','atendido','no_show','cancelado','reprogramado')),
    CONSTRAINT barber_citas_precio_chk CHECK (precio IS NULL OR precio >= 0),
    CONSTRAINT barber_citas_rango_chk CHECK (fin >= inicio)
);

COMMENT ON TABLE barber_citas IS
    'Citas. El id es el del evento de Google Calendar: por eso cancelar y reprogramar funcionan.';

-- 🔥 LA CLAVE: imposible empalmar dos citas activas.
-- Con UN solo barbero, se excluye por rango de tiempo sin agrupar por barbero.
-- `btree_gist` permite combinar `=` y `&&` en un mismo índice.
DO $do$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'barber_citas_no_solape'
  ) THEN
    ALTER TABLE barber_citas ADD CONSTRAINT barber_citas_no_solape
      EXCLUDE USING gist (
        tstzrange(inicio, fin) WITH &&
      ) WHERE (estado IN ('agendado','confirmado'));
  END IF;
END
$do$;

CREATE INDEX IF NOT EXISTS idx_citas_inicio ON barber_citas (inicio DESC);
CREATE INDEX IF NOT EXISTS idx_citas_estado ON barber_citas (estado);
CREATE INDEX IF NOT EXISTS idx_citas_jid ON barber_citas (jid);

-- ---------------------------------------------------------------------------
-- 5) Operadores (quién puede mandar comandos)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS barber_operadores (
    jid      text PRIMARY KEY,
    nombre   text,
    rol      text,
    activo   boolean NOT NULL DEFAULT true,
    creado_en timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT barber_operadores_rol_chk CHECK (
        rol IS NULL OR rol IN ('dueno','barbero'))
);

COMMENT ON TABLE barber_operadores IS
    'Números autorizados a mandar comandos. El dueño es uno solo.';

INSERT INTO barber_operadores (jid, nombre, rol) VALUES
    ('524521206246@s.whatsapp.net', 'Esteban Aguilera', 'dueno'),
    ('5214521206246@s.whatsapp.net', 'Esteban Aguilera', 'dueno')
ON CONFLICT (jid) DO NOTHING;

-- ---------------------------------------------------------------------------
-- 6) Escalaciones (lo que el bot no pudo resolver)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS barber_escalaciones (
    id         bigserial PRIMARY KEY,
    jid        text,
    motivo     text,
    resumen    text,
    estado     text DEFAULT 'abierta',
    resolucion text,
    creado_en  timestamptz NOT NULL DEFAULT now(),
    cerrada_en timestamptz,
    CONSTRAINT barber_escalaciones_motivo_chk CHECK (
        motivo IS NULL OR motivo IN ('descuento','queja','servicio_inexistente',
                                     'precio_no_listado','error_sistema','humano')),
    CONSTRAINT barber_escalaciones_estado_chk CHECK (
        estado IS NULL OR estado IN ('abierta','cerrada'))
);

-- ---------------------------------------------------------------------------
-- 7) Bloqueos (comida, festivos, vacaciones)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS barber_bloqueos (
    id     bigserial PRIMARY KEY,
    inicio timestamptz NOT NULL,
    fin    timestamptz NOT NULL,
    motivo text,
    creado_en timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT barber_bloqueos_rango_chk CHECK (fin >= inicio)
);

-- ---------------------------------------------------------------------------
-- 8) Pausas (el bot deja de contestar a un cliente)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS barber_pausas (
    jid    text PRIMARY KEY,
    hasta  timestamptz NOT NULL,
    motivo text,
    creado_en timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_pausas_hasta ON barber_pausas (hasta);

-- ---------------------------------------------------------------------------
-- 9) Conocimiento (FAQs para la búsqueda de texto completo, gratis)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS barber_conocimiento (
    id         bigserial PRIMARY KEY,
    pregunta   text NOT NULL UNIQUE,
    respuesta  text NOT NULL,
    sinonimos  text DEFAULT '',
    categoria  text DEFAULT 'general',
    activo     boolean NOT NULL DEFAULT true,
    creado_en  timestamptz NOT NULL DEFAULT now(),
    actualizado_en timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE barber_conocimiento IS
    'FAQs del negocio. Se busca con texto completo nativo de Postgres: gratis, sin embeddings.';

INSERT INTO barber_conocimiento (pregunta, respuesta, sinonimos, categoria) VALUES
    ('¿Dónde están ubicados?',
     'Estamos en *Calle Pinzón #574*. Ahí mismo te atendemos.',
     'ubicacion direccion llegar como llego domicilio donde local estan',
     'general'),
    ('¿Cuál es el horario?',
     'Abrimos de *lunes a sábado de 10:00 a 20:00*. El domingo estamos cerrados.',
     'horario abren abierto cierran cerrado horas atienden que hora',
     'general'),
    ('¿Cuánto cuesta el corte?',
     'El *corte desvanecido o tijera* cuesta *$150* y dura 40 minutos.',
     'precio cuesta corte costo cuanto vale tarifa caballero',
     'servicios'),
    ('¿Cuánto cuesta el corte de dama?',
     'El *corte de cabello para dama* cuesta *$250* y dura 50 minutos.',
     'precio cuesta dama mujer corte costo cuanto',
     'servicios'),
    ('¿Cuánto dura el corte?',
     'El *corte* dura *40 minutos*. Deja tiempo extra si vienes en hora pico.',
     'duracion dura tarda tiempo minutos cuanto el corte',
     'servicios'),
    ('¿Cuánto cuesta el arreglo de barba?',
     'El *arreglo de barba* cuesta *$100* y dura 20 minutos.',
     'precio barba cuesta costo cuanto perfilado',
     'servicios'),
    ('¿Cuánto cuesta la ceja?',
     'La *ceja* cuesta *$30* y dura 10 minutos.',
     'precio ceja cuesta cuanto cejas',
     'servicios'),
    ('¿Cuánto cuesta la depilación?',
     'La *depilación* depende de la zona: ceja, bigote, nariz, orejas, barba, axilas o piernas. Pregúntame por la zona y te digo el precio.',
     'depilacion depilar precio zona cuanto cuesta',
     'servicios'),
    ('¿Puedo cancelar mi cita?',
     'Sí. Avísame por aquí y la cancelo. Lo único que pedimos es que no sea a última hora.',
     'cancelar cancelacion anular no puedo ir quitar',
     'citas'),
    ('¿Puedo cambiar mi cita de día u hora?',
     'Sí, sin problema. Dime para qué día y hora la quieres mover.',
     'cambiar mover reprogramar reagendar otro dia hora',
     'citas'),
    ('¿Se puede pasar sin cita?',
     'Sí, puedes llegar directo. Pero como atiendo de uno en uno, si tienes cita te atiendo primero.',
     'walkin sin cita llegar directo pasar espontaneo',
     'citas'),
    ('¿Abren el domingo?',
     'No, el domingo estamos cerrados. Atendemos de lunes a sábado.',
     'domingo cerrado descanso abren',
     'general'),
    ('¿Aceptan tarjeta?',
     'El pago se hace directo en el local. Si necesitas confirmar el método, pregúntame y lo reviso.',
     'pago pagar efectivo transferencia tarjeta metodo',
     'general'),
    ('¿Hacen descuento?',
     'Déjame preguntarle al encargado y te confirmo en un momento.',
     'descuento promocion oferta rebaja barato',
     'general'),
    ('¿Hacen corte para niño?',
     'Sí, se hace con el mismo corte desvanecido o tijera de *$150*.',
     'nino hijo menor edad infantil acompanante',
     'servicios')
ON CONFLICT (pregunta) DO NOTHING;

-- Índice de texto completo (gratis, nativo, sin modelos de embedding)
CREATE INDEX IF NOT EXISTS idx_conocimiento_tsv ON barber_conocimiento
  USING gin (to_tsvector('spanish', coalesce(pregunta,'') || ' ' ||
                         coalesce(sinonimos,'') || ' ' ||
                         coalesce(respuesta,'')));

-- ---------------------------------------------------------------------------
-- 10) Vista materializada de KPIs (reportes instantáneos)
-- ---------------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS barber_metricas_diarias;
CREATE MATERIALIZED VIEW barber_metricas_diarias AS
SELECT
    (inicio AT TIME ZONE 'America/Mexico_City')::date AS dia,
    count(*) FILTER (WHERE estado = 'atendido')                AS atendidas,
    count(*) FILTER (WHERE estado = 'no_show')                 AS no_shows,
    count(*) FILTER (WHERE estado = 'cancelado')               AS canceladas,
    count(*) FILTER (WHERE estado = 'agendado')                AS agendadas,
    coalesce(sum(precio) FILTER (WHERE estado = 'atendido'), 0) AS ingresos,
    coalesce(round(avg(precio) FILTER (WHERE estado = 'atendido'), 2), 0)
                                                               AS ticket_promedio,
    count(DISTINCT jid) FILTER (WHERE estado = 'atendido')     AS clientes_unicos
FROM barber_citas
GROUP BY 1;

CREATE UNIQUE INDEX IF NOT EXISTS idx_metricas_dia
  ON barber_metricas_diarias (dia);

COMMENT ON MATERIALIZED VIEW barber_metricas_diarias IS
    'KPIs por día. Se refresca con: REFRESH MATERIALIZED VIEW CONCURRENTLY barber_metricas_diarias;';

-- ---------------------------------------------------------------------------
-- 11) Función de búsqueda de conocimiento (gratis, nativa)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION barber_buscar(p_texto text, p_limite int DEFAULT 3)
RETURNS TABLE (pregunta text, respuesta text, categoria text, rank real)
LANGUAGE sql STABLE AS $fn$
  SELECT k.pregunta, k.respuesta, k.categoria,
         ts_rank(to_tsvector('spanish',
                   coalesce(k.pregunta,'') || ' ' || coalesce(k.sinonimos,'') ||
                   ' ' || coalesce(k.respuesta,'')),
                 plainto_tsquery('spanish', p_texto))::real AS rank
  FROM barber_conocimiento k
  WHERE k.activo
    AND to_tsvector('spanish',
          coalesce(k.pregunta,'') || ' ' || coalesce(k.sinonimos,'') ||
          ' ' || coalesce(k.respuesta,''))
        @@ plainto_tsquery('spanish', p_texto)
  ORDER BY rank DESC, k.pregunta
  LIMIT p_limite;
$fn$;

COMMENT ON FUNCTION barber_buscar(text, int) IS
    'Devuelve las FAQs mas parecidas a lo que escribio el cliente.';

-- =====================================================================
-- esquema-postgres.sql
-- Sistema de citas de barberia "Barber Chinos" (agente n8n + WhatsApp)
-- Base de datos: barberia   |   Postgres 17 (contenedor: barberia-postgres)
-- =====================================================================
--
-- QUE HACE ESTE ARCHIVO
--   Crea las 8 tablas de negocio del agente, sus indices, sus restricciones
--   CHECK y la fila del operador dueno.
--
-- IDEMPOTENTE
--   Se puede ejecutar cuantas veces se quiera: usa CREATE TABLE / INDEX IF
--   NOT EXISTS, DROP TRIGGER IF EXISTS y ON CONFLICT DO NOTHING.
--
-- SEGURIDAD / N8N
--   Todas las tablas llevan el prefijo "barber_" para NO chocar nunca con las
--   tablas internas de n8n (workflow_entity, credentials_entity, chat_hub_*,
--   execution_entity, ...) que viven en el mismo esquema public de esta BD.
--   Ningun objeto de este archivo usa nombres genericos sin prefijo.
--
-- CREDENCIALES
--   Este archivo NO contiene usuario ni contrasena. Las inyecta el cliente
--   (psql -U <POSTGRES_USER>, PGPASSWORD) desde las variables de entorno
--   definidas en G:\Barberia\.env.
--
-- USO MANUAL (equivalente a lo que hace aplicar-esquema.py)
--   docker exec -i -e PGPASSWORD="$POSTGRES_PASSWORD" barberia-postgres \
--     psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -f - \
--     < esquema-postgres.sql
--
-- USO RECOMENDADO
--   python archivos\aplicar-esquema.py
-- =====================================================================

BEGIN;

-- Zona horaria del negocio (solo afecta la sesion; timestamptz guarda UTC).
SET TIME ZONE 'America/Mexico_City';

-- =====================================================================
-- 1) barber_clientes - ficha unica por cliente de WhatsApp
-- =====================================================================
CREATE TABLE IF NOT EXISTS barber_clientes (
    jid                  text        PRIMARY KEY,
    nombre               text,
    telefono             text,
    primera_visita       timestamp,
    visitas              integer     NOT NULL DEFAULT 0,
    ultima_visita        timestamp,
    ticket_promedio      numeric(10,2),
    no_shows             integer     NOT NULL DEFAULT 0,
    cancelaciones_tardias integer    NOT NULL DEFAULT 0,
    servicio_habitual    text,
    barbero_preferido    text,
    nota_interna         text,
    fecha_nacimiento     date,
    marketing_ok         boolean     NOT NULL DEFAULT false,
    etiqueta             text,
    creado_en            timestamp   NOT NULL DEFAULT now(),
    CONSTRAINT barber_clientes_visitas_chk        CHECK (visitas IS NULL OR visitas >= 0),
    CONSTRAINT barber_clientes_no_shows_chk       CHECK (no_shows IS NULL OR no_shows >= 0),
    CONSTRAINT barber_clientes_cancel_chk         CHECK (cancelaciones_tardias IS NULL OR cancelaciones_tardias >= 0),
    CONSTRAINT barber_clientes_ticket_chk         CHECK (ticket_promedio IS NULL OR ticket_promedio >= 0),
    CONSTRAINT barber_clientes_etiqueta_chk       CHECK (
        etiqueta IS NULL OR etiqueta IN (
            'nuevo', 'frecuente', 'vip', 'en_riesgo',
            'problematico', 'consulta', 'inactivo'
        )
    )
);

COMMENT ON TABLE  barber_clientes IS
    'Ficha de cada cliente de WhatsApp (CRM del agente). La PK es el JID de WhatsApp, p.ej. 5214501111805@s.whatsapp.net. Acumula historial de visitas, no-shows, ticket promedio y preferencias para personalizar la atencion.';
COMMENT ON COLUMN barber_clientes.jid            IS 'Identificador WhatsApp (JID). Clave primaria y llave de union con el resto de tablas barber_.';
COMMENT ON COLUMN barber_clientes.visitas        IS 'Contador historico de visitas atendidas (default 0).';
COMMENT ON COLUMN barber_clientes.ticket_promedio IS 'Gasto promedio por visita en pesos (numeric 10,2).';
COMMENT ON COLUMN barber_clientes.no_shows       IS 'Veces que no se presento a una cita agendada.';
COMMENT ON COLUMN barber_clientes.cancelaciones_tardias IS 'Cancelaciones avisadas con poco margen (menos de 2 h).';
COMMENT ON COLUMN barber_clientes.marketing_ok   IS 'Espejo de barber_consentimiento.marketing_ok: true = el cliente acepto promociones.';
COMMENT ON COLUMN barber_clientes.etiqueta       IS 'Segmento operativo. Valores validos: nuevo, frecuente, vip, en_riesgo, problematico, consulta, inactivo.';

-- =====================================================================
-- 2) barber_citas - estado actual de cada cita (1 fila = 1 evento Calendar)
-- =====================================================================
CREATE TABLE IF NOT EXISTS barber_citas (
    id             text        PRIMARY KEY,
    jid            text        REFERENCES barber_clientes (jid)
                               ON UPDATE CASCADE ON DELETE SET NULL,
    nombre         text,
    servicio       text,
    precio         numeric(10,2),
    inicio         timestamptz,
    fin            timestamptz,
    estado         text,
    creado_en      timestamptz NOT NULL DEFAULT now(),
    actualizado_en timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT barber_citas_estado_chk CHECK (
        estado IS NULL OR estado IN (
            'agendado', 'confirmado', 'atendido',
            'no_show', 'cancelado', 'reprogramado'
        )
    ),
    CONSTRAINT barber_citas_precio_chk CHECK (precio IS NULL OR precio >= 0),
    CONSTRAINT barber_citas_rango_chk  CHECK (inicio IS NULL OR fin IS NULL OR fin >= inicio)
);

COMMENT ON TABLE  barber_citas IS
    'Estado actual de cada cita: una fila por evento de Google Calendar (la PK es el ID del evento). Es el espejo local del calendario para consultar disponibilidad, recordatorios y metricas sin pegarle a la API de Google.';
COMMENT ON COLUMN barber_citas.id             IS 'ID del evento en Google Calendar (PK, idempotencia natural de la sincronizacion).';
COMMENT ON COLUMN barber_citas.jid            IS 'Cliente de la cita (barber_clientes.jid). Puede ser NULL si el evento existe en Calendar pero el cliente aun no esta en el CRM.';
COMMENT ON COLUMN barber_citas.estado         IS 'Maquina de estados cerrada. Valores validos: agendado, confirmado, atendido, no_show, cancelado, reprogramado.';
COMMENT ON COLUMN barber_citas.actualizado_en IS 'Se actualiza automaticamente en cada UPDATE (trigger trg_barber_citas_touch).';

CREATE INDEX IF NOT EXISTS idx_barber_citas_jid       ON barber_citas (jid);
CREATE INDEX IF NOT EXISTS idx_barber_citas_estado    ON barber_citas (estado);
CREATE INDEX IF NOT EXISTS idx_barber_citas_inicio    ON barber_citas (inicio);
-- Extra: consulta caliente "proximas citas vivas ordenadas por fecha".
CREATE INDEX IF NOT EXISTS idx_barber_citas_estado_inicio ON barber_citas (estado, inicio);

-- Mantiene actualizado_en al dia sin que el workflow tenga que escribirlo.
CREATE OR REPLACE FUNCTION barber_touch_actualizado_en() RETURNS trigger AS $$
BEGIN
    NEW.actualizado_en := now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION barber_touch_actualizado_en() IS
    'Trigger generico de barber_: sella NEW.actualizado_en con now() en cada UPDATE.';

DROP TRIGGER IF EXISTS trg_barber_citas_touch ON barber_citas;
CREATE TRIGGER trg_barber_citas_touch
    BEFORE UPDATE ON barber_citas
    FOR EACH ROW EXECUTE FUNCTION barber_touch_actualizado_en();

-- =====================================================================
-- 3) barber_escalaciones - casos que el bot no pudo resolver solo
-- =====================================================================
CREATE TABLE IF NOT EXISTS barber_escalaciones (
    id          serial      PRIMARY KEY,
    jid         text,
    motivo      text,
    resumen     text,
    creado_en   timestamptz NOT NULL DEFAULT now(),
    estado      text        DEFAULT 'abierta',
    resolucion  text,
    cerrada_en  timestamptz,
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

COMMENT ON TABLE  barber_escalaciones IS
    'Bandeja de casos que el agente no pudo cerrar por si mismo (pide descuento, se queja, pide un servicio que no existe, error del sistema o pide hablar con un humano). Es la cola de trabajo del dueno.';
COMMENT ON COLUMN barber_escalaciones.motivo IS 'Motivo tipificado: descuento, queja, servicio_inexistente, precio_no_listado, error_sistema, humano.';
COMMENT ON COLUMN barber_escalaciones.estado IS 'abierta = pendiente de atencion humana; cerrada = ya resuelta (ver resolucion).';

CREATE INDEX IF NOT EXISTS idx_barber_escalaciones_estado ON barber_escalaciones (estado);

-- =====================================================================
-- 4) barber_operadores - numeros autorizados a mandar comandos
-- =====================================================================
CREATE TABLE IF NOT EXISTS barber_operadores (
    jid       text      PRIMARY KEY,
    nombre    text,
    rol       text,
    activo    boolean   NOT NULL DEFAULT true,
    creado_en timestamp NOT NULL DEFAULT now(),
    CONSTRAINT barber_operadores_rol_chk CHECK (
        rol IS NULL OR rol IN ('dueno', 'barbero')
    )
);

COMMENT ON TABLE  barber_operadores IS
    'Lista blanca de numeros de WhatsApp con permiso de mandar comandos al agente (dueno y barberos). Si el JID no esta aqui y activo = true, el agente solo atiende como cliente normal.';
COMMENT ON COLUMN barber_operadores.rol IS 'Rol del operador: dueno (control total) o barbero (agenda propia).';

-- Operador de ejemplo: el dueno. Idempotente.
INSERT INTO barber_operadores (jid, nombre, rol, activo)
VALUES ('5215520894522@s.whatsapp.net', 'Dueno', 'dueno', true)
ON CONFLICT (jid) DO NOTHING;

-- =====================================================================
-- 5) barber_bloqueos - festivos, vacaciones y bloqueos puntuales
-- =====================================================================
CREATE TABLE IF NOT EXISTS barber_bloqueos (
    id        serial      PRIMARY KEY,
    inicio    timestamptz,
    fin       timestamptz,
    motivo    text,
    creado_en timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT barber_bloqueos_rango_chk CHECK (inicio IS NULL OR fin IS NULL OR fin >= inicio)
);

COMMENT ON TABLE  barber_bloqueos IS
    'Bloqueos de agenda que el agente debe respetar al ofrecer horarios: festivos, vacaciones del barbero y ausencias puntuales. Un bloqueo que cubre el horario pedido lo descarta.';

CREATE INDEX IF NOT EXISTS idx_barber_bloqueos_inicio ON barber_bloqueos (inicio);

-- =====================================================================
-- 6) barber_lista_espera - clientes esperando que se libere un hueco
-- =====================================================================
CREATE TABLE IF NOT EXISTS barber_lista_espera (
    id              serial      PRIMARY KEY,
    jid             text,
    servicio        text,
    duracion_min    integer,
    ventana_deseada text,
    creado_en       timestamptz NOT NULL DEFAULT now(),
    atendido        boolean     NOT NULL DEFAULT false,
    CONSTRAINT barber_lista_espera_duracion_chk CHECK (duracion_min IS NULL OR duracion_min > 0)
);

COMMENT ON TABLE  barber_lista_espera IS
    'Clientes que pidieron cita cuando no habia hueco. El agente los avisa cuando se libera (o se cancela) una cita compatible con el servicio y la ventana deseada.';
COMMENT ON COLUMN barber_lista_espera.ventana_deseada IS 'Texto libre del cliente, p.ej. "sabado por la tarde" o "cualquier dia despues de las 6pm".';
COMMENT ON COLUMN barber_lista_espera.atendido        IS 'true = ya se le ofrecio/agendo hueco; sale de la cola activa.';

CREATE INDEX IF NOT EXISTS idx_barber_lista_espera_pendiente
    ON barber_lista_espera (atendido, creado_en);

-- =====================================================================
-- 7) barber_auditoria - bitacora de cada accion del agente
-- =====================================================================
CREATE TABLE IF NOT EXISTS barber_auditoria (
    id         serial      PRIMARY KEY,
    ts         timestamptz NOT NULL DEFAULT now(),
    jid        text,
    intencion  text,
    herramienta text,
    argumentos jsonb,
    resultado  text,
    exito      boolean
);

COMMENT ON TABLE  barber_auditoria IS
    'Bitacora de cada accion del agente (que entendio, que herramienta llamo, con que argumentos y como termino). Sirve para depurar, medir el exito por herramienta y detectar loops.';
COMMENT ON COLUMN barber_auditoria.intencion   IS 'Intencion detectada en el mensaje del cliente, p.ej. agendar, cancelar, reprogramar, consultar_precio.';
COMMENT ON COLUMN barber_auditoria.herramienta IS 'Herramienta/tool invocada por el agente (Calendar, Sheets, Postgres, ...).';
COMMENT ON COLUMN barber_auditoria.argumentos  IS 'Argumentos exactos de la llamada en jsonb, tal como los genero el modelo.';
COMMENT ON COLUMN barber_auditoria.exito       IS 'true = la accion termino bien; false = fallo o quedo escalada.';

CREATE INDEX IF NOT EXISTS idx_barber_auditoria_ts      ON barber_auditoria (ts DESC);
CREATE INDEX IF NOT EXISTS idx_barber_auditoria_jid     ON barber_auditoria (jid);
CREATE INDEX IF NOT EXISTS idx_barber_auditoria_exito   ON barber_auditoria (exito);

-- =====================================================================
-- 8) barber_consentimiento - permiso explicito de marketing
-- =====================================================================
CREATE TABLE IF NOT EXISTS barber_consentimiento (
    jid          text        PRIMARY KEY,
    marketing_ok boolean     NOT NULL DEFAULT false,
    ts           timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE  barber_consentimiento IS
    'Prueba de consentimiento de marketing por cliente (que dijo, cuando y desde que numero). Se mantiene aparte del CRM porque es evidencia de cumplimiento, no un dato de conveniencia: barber_clientes.marketing_ok es solo un espejo cacheado.';
COMMENT ON COLUMN barber_consentimiento.ts IS 'Momento en que el cliente otorgo o retiro el consentimiento (ultima actualizacion).';

COMMIT;

-- =====================================================================
-- VERIFICACION RAPIDA (opcional, descomentar para correr a mano)
-- =====================================================================
-- SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename LIKE 'barber\_%' ORDER BY 1;
-- SELECT jid, nombre, rol, activo FROM barber_operadores;
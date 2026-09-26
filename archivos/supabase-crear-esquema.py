#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Crea el esquema REAL de la barbería en Supabase.

CONEXIÓN (resuelta):
  El host directo db.<ref>.supabase.co solo resuelve a IPv6 y el contenedor
  no tiene IPv6. La vía que funciona es el Connection Pooler:
      host:   aws-0-us-east-2.pooler.supabase.com
      puerto: 5432
      user:   postgres.<project-ref>
  Comprobado: Postgres 17.6, puedo crear tablas, y TODAS las extensiones
  que hacen falta están disponibles (btree_gist, unaccent, pg_trgm,
  pgcrypto, vector).

DISEÑO (adaptado a la realidad del negocio, NO copiado del documento):
  - UN SOLO BARBERO: Esteban Aguilera. Nada de tabla `barbers` ni
    `commission_pct`.
  - Estados en español: agendado, confirmado, atendido, no_show,
    cancelado, reprogramado.
  - Recordatorios de 24 h y 1 h (el documento decía 2 h).
  - SIN pagos: el usuario rechazó todo lo de tarjeta. Se guarda
    `metodo_pago` como texto libre (efectivo/transferencia) y nada más.
  - Se usa la constraint EXCLUDE con btree_gist para que sea IMPOSIBLE
    empalmar dos citas: esa es la mejor idea del documento y aquí se
    aprovecha adaptada a un solo barbero.
  - Vista materializada de KPIs para reportes instantáneos.
  - Los nombres de tabla espejan los locales (barber_*) para que migrar
    sea una copia directa.
"""
import os
import subprocess
import sys


def _leer_password_supabase() -> str:
    """Lee la password de Supabase sin tenerla escrita en el codigo.

    Orden: variable de entorno -> archivos locales -> error claro.
    Esos archivos estan en .gitignore, asi que la clave nunca se publica.
    """
    import os
    v = os.environ.get("SUPABASE_PASSWORD")
    if v:
        return v.strip()
    for ruta in (r"G:\Barberia\archivos\.supabase-pass.txt",
                 r"G:\Barberia\archivos\.supabase-conn.txt"):
        try:
            with open(ruta, encoding="utf-8") as f:
                lineas = [x.strip() for x in f if x.strip()]
        except OSError:
            continue
        for l in lineas:
            # en el archivo de conexion la password va en la 4a linea
            if l.startswith("password="):
                return l.split("=", 1)[1].strip()
        if len(lineas) >= 4:
            return lineas[3]
    raise SystemExit(
        "Falta la password de Supabase.\n"
        "Ponla en la variable SUPABASE_PASSWORD o crea el archivo\n"
        "  G:\\Barberia\\archivos\\.supabase-pass.txt\n"
        "con una sola linea que contenga la password."
    )


try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DOCKER = (r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop"
          r"\resources\bin\docker.exe")
os.environ["DOCKER_CONFIG"] = r"G:\Barberia\.docker"

# Datos de conexión guardados por supabase-pooler.py
RUTA_CONN = r"G:\Barberia\archivos\.supabase-conn.txt"
PWD = _leer_password_supabase()

ESQUEMA = r"""
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
"""


def conectar():
    """Lee los datos del pooler guardados por supabase-pooler.py."""
    if not os.path.exists(RUTA_CONN):
        return None
    with open(RUTA_CONN, encoding="utf-8") as f:
        lineas = [l.strip() for l in f if l.strip()]
    if len(lineas) < 3:
        return None
    return lineas[0], lineas[1], lineas[2]


def psql(host, puerto, usuario, sql, usar_archivo=False, timeout=120):
    args = [DOCKER, "exec",
            "-e", f"PGPASSWORD={PWD}",
            "-e", "PGSSLMODE=require",
            "-e", f"PGCONNECT_TIMEOUT=25",
            "barberia-postgres",
            "psql", "-h", host, "-p", str(puerto), "-U", usuario,
            "-d", "postgres"]
    args += ["-f", sql] if usar_archivo else ["-c", sql]
    try:
        p = subprocess.run(args, capture_output=True, text=True,
                           encoding="utf-8", errors="replace",
                           timeout=timeout)
    except subprocess.TimeoutExpired:
        return "", "TIMEOUT"
    return (p.stdout or "").strip(), (p.stderr or "").strip()


def main():
    conn = conectar()
    if not conn:
        print("Falta archivos\\.supabase-conn.txt")
        print("Ejecuta primero: supabase-pooler.py")
        return 1
    host, puerto, usuario = conn
    print("=" * 72)
    print("CREANDO EL ESQUEMA EN SUPABASE")
    print("=" * 72)
    print(f"  {usuario}@{host}:{puerto}")
    print()

    # Escribir el SQL a un archivo y copiarlo al contenedor (es largo y
    # psql -c no admite varias sentencias con DO $$ ... $$ de forma fiable)
    ruta_local = r"G:\Barberia\archivos\supabase-esquema-real.sql"
    with open(ruta_local, "w", encoding="utf-8") as f:
        f.write(ESQUEMA)
    destino = "/tmp/_esquema_supabase.sql"
    subprocess.run([DOCKER, "cp", ruta_local,
                    f"barberia-postgres:{destino}"], capture_output=True)

    out, err = psql(host, puerto, usuario, destino, usar_archivo=True)
    errores = [l for l in err.split("\n") if "ERROR" in l]
    if errores:
        print("  ERRORES al aplicar el esquema:")
        for l in errores[:12]:
            print(f"    {l[:170]}")
        return 1
    print("  esquema aplicado sin errores")
    avisos = [l for l in err.split("\n") if "NOTICE" in l]
    if avisos:
        print(f"  ({len(avisos)} avisos NOTICE, normal en un esquema idempotente)")

    print()
    print("=" * 72)
    print("VERIFICACION")
    print("=" * 72)
    o, _ = psql(host, puerto, usuario,
                "SELECT string_agg(tablename, ', ' ORDER BY tablename) "
                "FROM pg_tables WHERE schemaname='public';")
    print(f"  tablas: {o}")
    o, _ = psql(host, puerto, usuario,
                "SELECT count(*) FROM barber_servicios;")
    print(f"  servicios: {o}")
    o, _ = psql(host, puerto, usuario,
                "SELECT count(*) FROM barber_conocimiento;")
    print(f"  FAQs: {o}")
    o, _ = psql(host, puerto, usuario,
                "SELECT count(*) FROM pg_matviews WHERE matviewname="
                "'barber_metricas_diarias';")
    print(f"  vista de metricas: {'creada' if o == '1' else 'FALTA'}")

    print()
    print("=== LA CONSTRAINT ANTI-SOLAPE FUNCIONA? (prueba real) ===")
    print("  insertando dos citas que se empalman...")
    o, e = psql(host, puerto, usuario, """
BEGIN;
INSERT INTO barber_clientes (jid, nombre) VALUES
  ('prueba1@s.whatsapp.net','Prueba Uno'),
  ('prueba2@s.whatsapp.net','Prueba Dos');
INSERT INTO barber_citas (id,jid,nombre,servicio,precio,inicio,fin,estado)
VALUES ('p1','prueba1@s.whatsapp.net','Prueba Uno','Corte',150,
        '2027-01-15 11:00-06','2027-01-15 11:40-06','agendado');
INSERT INTO barber_citas (id,jid,nombre,servicio,precio,inicio,fin,estado)
VALUES ('p2','prueba2@s.whatsapp.net','Prueba Dos','Barba',100,
        '2027-01-15 11:30-06','2027-01-15 11:50-06','agendado');
ROLLBACK;
""")
    if "barber_citas_no_solape" in e:
        print("  OK   la segunda cita fue RECHAZADA por la constraint")
        print("       (imposible doble reserva, garantizado por la BD)")
    elif "ERROR" in e:
        print(f"  AVISO otro error: {[l for l in e.split(chr(10)) if 'ERROR' in l][:1]}")
    else:
        print("  MAL  la segunda cita se inserto: la constraint NO protege")
        return 1

    print()
    print("=== prueba valida: dos citas SIN empalmar ===")
    o, e = psql(host, puerto, usuario, """
BEGIN;
INSERT INTO barber_citas (id,jid,nombre,servicio,precio,inicio,fin,estado)
VALUES ('p3','prueba1@s.whatsapp.net','Prueba Uno','Corte',150,
        '2027-01-15 12:00-06','2027-01-15 12:40-06','agendado');
SELECT 'insertada OK' AS r;
ROLLBACK;
""")
    print(f"  {o or e[:90]}")

    print()
    print("=== la busqueda de conocimiento funciona? ===")
    for q in ("donde estan ubicados", "a que hora abren", "cuanto cuesta la barba",
              "puedo cancelar", "abren domingo"):
        o, _ = psql(host, puerto, usuario,
                    f"SELECT pregunta FROM barber_buscar('{q}', 1);")
        print(f"  {q!r:28} -> {o or '(sin resultados)'}")

    print()
    print("  datos de prueba limpiados con ROLLBACK (nada quedo en la tabla)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
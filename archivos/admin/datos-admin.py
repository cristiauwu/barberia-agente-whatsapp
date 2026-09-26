"""Consultas de lectura y actualización restringida de precios en Postgres.

ADMIN_DB_DSN es solo lectura; ADMIN_PRICE_DB_DSN tiene únicamente los permisos
concedidos en precios-admin.sql. No usar el rol n8n/owner en el servidor.
"""
from datetime import date, datetime, timezone
from decimal import Decimal


class PriceConflict(Exception):
    """The catalog entry was removed or another writer changed its version."""


NOTICE = ("Fuente: barber_citas (Postgres). Google Calendar y Google Sheets son "
          "fuentes separadas y pueden no estar sincronizadas. Ingresos: solo "
          "citas atendidas con precio y fecha; no son cobros comprobados. "
          "Un cero puede significar que todavía no se registraron citas en Postgres.")


def clean(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def rows(cur):
    names = [col[0] for col in cur.description]
    return [{key: clean(value) for key, value in zip(names, record)}
            for record in cur.fetchall()]


class Datos:
    def __init__(self, connect, connect_price=None):
        self.connect = connect
        self.connect_price = connect_price

    def cambiar_precio(self, clave, precio, version, request_id):
        """Single DB transaction: the restricted SQL function performs CAS + audit."""
        if self.connect_price is None:
            raise RuntimeError("Price editing is not configured")
        with self.connect_price() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT precio, version FROM public.admin_cambiar_precio(%s, %s::numeric, %s, %s::uuid)",
                            (clave, precio, version, request_id))
                record = cur.fetchone()
                if record is None:
                    raise PriceConflict()
                return {"clave": clave, "precio": str(record[0]), "precioVersion": record[1]}


    def query(self, sql, params=()):
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SET TRANSACTION READ ONLY")
                cur.execute("SET LOCAL TIME ZONE 'America/Mexico_City'")
                cur.execute(sql, params)
                return rows(cur)

    def meta(self):
        state = self.query("SELECT count(*) AS total, max(actualizado_en) AS \"ultimaActualizacion\" FROM barber_citas")[0]
        return {"generadoEn": datetime.now(timezone.utc).isoformat(),
                "ultimaActualizacionCitas": state["ultimaActualizacion"],
                "citasRegistradas": state["total"],
                "sinCitas": state["total"] == 0,
                "fuente": "Postgres barber_citas/barber_clientes/barber_servicios",
                "advertencia": NOTICE}

    def kpis(self):
        r = self.query("""
            SELECT
              coalesce(sum(precio) FILTER (WHERE estado='atendido' AND inicio::date=current_date),0) AS "ingresosHoy",
              coalesce(sum(precio) FILTER (WHERE estado='atendido' AND inicio::date>=date_trunc('week',current_date)::date),0) AS "ingresosSemana",
              coalesce(sum(precio) FILTER (WHERE estado='atendido' AND inicio::date>=date_trunc('month',current_date)::date),0) AS "ingresosMes",
              round(avg(precio) FILTER (WHERE estado='atendido' AND inicio::date=current_date),2) AS "ticketPromedioHoy",
              round(avg(precio) FILTER (WHERE estado='atendido' AND inicio::date>=date_trunc('month',current_date)::date),2) AS "ticketPromedioMes",
              count(*) FILTER (WHERE estado='no_show' AND inicio::date>=date_trunc('month',current_date)::date) AS "noShowsMes",
              count(*) FILTER (WHERE estado='cancelado' AND inicio::date>=date_trunc('month',current_date)::date) AS "cancelacionesMes",
              count(*) FILTER (WHERE estado IN ('agendado','confirmado') AND inicio>=now() AND inicio<now()+interval '7 days') AS "proximas7Dias",
              coalesce(sum(precio) FILTER (WHERE estado IN ('agendado','confirmado') AND inicio>=now() AND inicio<now()+interval '7 days'),0) AS "potencial7Dias"
            FROM barber_citas WHERE inicio IS NOT NULL
        """)[0]
        return r

    def grafica(self):
        return self.query("""
            SELECT d::date AS fecha, coalesce(sum(c.precio),0) AS ingresos
            FROM generate_series(current_date-29,current_date,interval '1 day') d
            LEFT JOIN barber_citas c ON c.inicio::date=d::date
              AND c.estado='atendido' AND c.precio IS NOT NULL
            GROUP BY d ORDER BY d
        """)

    def citas(self, page=1, size=20, fecha=None, desde=None):
        where = "WHERE inicio IS NOT NULL"
        params = []
        if fecha:
            where += " AND inicio::date=%s"
            params.append(fecha)
        elif desde:
            where += " AND inicio::date >= %s"
            params.append(desde)
        total = self.query("SELECT count(*) AS total FROM barber_citas " + where, params)[0]["total"]
        items = self.query("""SELECT id,jid,nombre,servicio,precio,inicio,fin,estado
                            FROM barber_citas """ + where +
                           " ORDER BY inicio DESC,id DESC LIMIT %s OFFSET %s",
                           params + [size, (page-1)*size])
        return {"items": items, "pagination": {"page": page, "pageSize": size,
                "totalItems": total, "totalPages": (total+size-1)//size}, "meta": self.meta()}

    def clientes(self, page=1, size=20, buscar=""):
        where = ""
        params = []
        if buscar:
            where = "WHERE (nombre ILIKE %s OR telefono ILIKE %s OR jid ILIKE %s)"
            params = ["%" + buscar.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"]*3
            # PostgreSQL LIKE uses backslash as the default escape character.
        total = self.query("SELECT count(*) AS total FROM barber_clientes " + where, params)[0]["total"]
        items = self.query("""SELECT jid,nombre,telefono,visitas,
                          ultima_visita AS "ultimaVisita",ticket_promedio AS "ticketPromedio",
                          no_shows AS "noShows",cancelaciones_tardias AS "cancelacionesTardias",
                          servicio_habitual AS "servicioHabitual",etiqueta,marketing_ok AS "marketingOk"
                          FROM barber_clientes """ + where +
                           " ORDER BY ultima_visita DESC NULLS LAST,jid LIMIT %s OFFSET %s",
                           params + [size, (page-1)*size])
        return {"items": items, "pagination": {"page": page, "pageSize": size,
                "totalItems": total, "totalPages": (total+size-1)//size}, "meta": self.meta()}

    def servicios(self):
        items = self.query("""
            SELECT s.clave,s.nombre,s.precio,
                   max((to_jsonb(s)->>'precio_version')::bigint) AS "precioVersion",
                   s.duracion_min AS "duracionMin",s.activo,
                   count(c.id) AS "citasMes",coalesce(sum(c.precio),0) AS "ingresosMes",
                   CASE WHEN s.duracion_min>0 AND count(c.id)>0 THEN
                     round(sum(c.precio)*60/count(c.id)/s.duracion_min,2)
                   END AS "rentabilidadHora"
            FROM barber_servicios s LEFT JOIN barber_citas c ON c.servicio=s.nombre
             AND c.estado='atendido' AND c.precio IS NOT NULL
             AND c.inicio::date >= date_trunc('month',current_date)::date
            GROUP BY s.clave,s.nombre,s.precio,s.duracion_min,s.activo
            ORDER BY s.nombre
        """)
        return {"items": items, "meta": self.meta()}

    def resumen(self):
        return {"kpis": self.kpis(), "hoy": self.query("""
            SELECT id,jid,nombre,servicio,precio,inicio,fin,estado FROM barber_citas
            WHERE inicio::date=current_date ORDER BY inicio,id LIMIT 100
        """), "proximas": self.query("""
            SELECT id,jid,nombre,servicio,precio,inicio,fin,estado FROM barber_citas
            WHERE estado IN ('agendado','confirmado') AND inicio>=now()
            ORDER BY inicio,id LIMIT 8
        """), "grafica30": self.grafica(), "meta": self.meta()}

    def reportes(self):
        return {"kpis": self.kpis(), "grafica30": self.grafica(),
                "ocupacion": self.query("""
                    SELECT lpad(extract(hour from inicio)::int::text,2,'0')||':00' AS hora,
                           count(*) AS citas FROM barber_citas
                    WHERE estado='atendido' AND inicio IS NOT NULL
                    GROUP BY 1 ORDER BY 1
                """), "servicios": self.query("""
                    SELECT coalesce(servicio,'(sin servicio)') AS nombre,count(*) AS citas,
                           coalesce(sum(precio),0) AS ingresos FROM barber_citas
                    WHERE estado='atendido' AND precio IS NOT NULL AND inicio IS NOT NULL
                      AND inicio::date>=date_trunc('month',current_date)::date
                    GROUP BY 1 ORDER BY ingresos DESC,nombre
                """), "meta": self.meta()}

    def resolve_jid(self, cliente_id=None, cita_id=None):
        if cliente_id:
            result = self.query("SELECT jid FROM barber_clientes WHERE jid=%s LIMIT 1", (cliente_id,))
        else:
            result = self.query("SELECT c.jid FROM barber_citas c JOIN barber_clientes b ON b.jid=c.jid WHERE c.id=%s LIMIT 1", (cita_id,))
        return result[0]["jid"] if result else None

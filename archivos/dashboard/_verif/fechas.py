#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueba de zona horaria America/Mexico_City y corte de mes.

Comprueba:
  1. Cual es la zona por defecto del contenedor (sin SET).
  2. Que `current_date` cambia si NO se hace SET TIME ZONE.
  3. Que a las 19:00/23:00 de Mexico (ya dia siguiente en UTC) la fecha
     del negocio sigue siendo la de Mexico.
  4. Que el generador realmente emite esa fecha en el HTML.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, r"G:\Barberia\archivos\dashboard\_verif")
from db import consultar, ejecutar

print("=" * 70)
print("1) ZONA POR DEFECTO DEL CONTENEDOR (sin SET TIME ZONE)")
print("=" * 70)
rc, out, err = ejecutar(r"""
\pset footer off
\echo --- sin SET ---
SELECT current_setting('TimeZone') AS zona_defecto,
       to_char(now(),'YYYY-MM-DD HH24:MI:SS') AS ahora,
       current_date::text AS fecha_actual_date,
       (now())::date::text AS fecha_de_now;
""")
print(out, err)

print("=" * 70)
print("2) CON SET TIME ZONE 'America/Mexico_City' (lo que hace el panel)")
print("=" * 70)
rc, out, err = ejecutar(r"""
\pset footer off
SET TIME ZONE 'America/Mexico_City';
SELECT current_setting('TimeZone') AS zona,
       to_char(now(),'YYYY-MM-DD HH24:MI:SS') AS ahora_mx,
       current_date::text AS fecha_actual_date,
       (now() AT TIME ZONE 'UTC')::text AS utc;
""")
print(out, err)

print("=" * 70)
print("3) HORA DE MEXICO vs UTC EN EL MISMO INSTANTE")
print("=" * 70)
rc, out, err = ejecutar(r"""
\pset footer off
SET TIME ZONE 'America/Mexico_City';
SELECT
  to_char(now(),'YYYY-MM-DD HH24:MI') AS fecha_hora_negocio,
  to_char(now() AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI') AS fecha_hora_utc,
  CASE WHEN (now())::date <> (now() AT TIME ZONE 'UTC')::date
       THEN 'DIFIEREN (UTC ya es otro dia)' ELSE 'IGUALES' END AS aviso,
  current_date::text AS current_date_session,
  (now() AT TIME ZONE 'UTC')::date::text AS date_utc;
""")
print(out, err)

print("=" * 70)
print("4) ESCENARIO 19:00 MEXICO (= 01:00 UTC del dia siguiente)")
print("=" * 70)
rc, out, err = ejecutar(r"""
\pset footer off
SET TIME ZONE 'America/Mexico_City';
-- instante congelado: 2026-09-26 01:00 UTC == 2026-09-25 19:00 Mexico
WITH instante AS (SELECT TIMESTAMPTZ '2026-09-26 01:00:00+00' AS t)
SELECT to_char(t,'YYYY-MM-DD HH24:MI') AS hora_negocio,
       to_char(t AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI') AS hora_utc,
       (t)::date::text AS fecha_negocio,
       (t AT TIME ZONE 'UTC')::date::text AS fecha_utc,
       CASE WHEN (t)::date = (t AT TIME ZONE 'UTC')::date
            THEN 'coinciden' ELSE 'DIFIEREN -> el panel debe usar fecha_negocio'
       END AS veredicto
  FROM instante;
""")
print(out, err)

print("=" * 70)
print("5) LA FECHA QUE EMITE EL PANEL")
print("=" * 70)
HTML = Path(r"G:\Barberia\archivos\dashboard\dashboard.html").read_text(encoding="utf-8")
for pat in (r"Hoy: <b>(.*?)</b>", r"Generado: <b>(.*?)</b>"):
    m = re.search(pat, HTML)
    print("  ", pat, "->", m.group(1) if m else "(no encontrado)")

s = consultar(r"""SET TIME ZONE 'America/Mexico_City';
\echo ===@@f@@===
SELECT to_char(current_date,'YYYY-MM-DD') AS fecha_mx,
       (now() AT TIME ZONE 'UTC')::date::text AS fecha_utc;
""")
print("  SQL fecha_mx =", s["f"][0]["fecha_mx"], " fecha_utc =", s["f"][0]["fecha_utc"])

print("=" * 70)
print("6) CORTE DE MES: suma solo el mes en curso?")
print("=" * 70)
s = consultar(r"""
SET TIME ZONE 'America/Mexico_City';
\echo ===@@c@@===
SELECT to_char(inicio,'YYYY-MM') AS mes,
       count(*) FILTER (WHERE estado='atendido' AND precio IS NOT NULL) AS atendidas_con_precio,
       COALESCE(sum(precio) FILTER (WHERE estado='atendido' AND precio IS NOT NULL),0) AS dinero
  FROM barber_citas WHERE inicio IS NOT NULL GROUP BY 1 ORDER BY 1;
""")
for f in s["c"]:
    print("  ", f)

print("=" * 70)
print("7) QUE NO_SHOW / CANCELADO NO SUMAN DINERO")
print("=" * 70)
s = consultar(r"""
SET TIME ZONE 'America/Mexico_City';
\echo ===@@n@@===
SELECT
  COALESCE(sum(precio) FILTER (WHERE estado='atendido' AND precio IS NOT NULL
     AND inicio::date >= date_trunc('month',current_date)::date),0) AS ingreso_mes_panel,
  COALESCE(sum(precio) FILTER (WHERE estado='no_show'
     AND inicio::date >= date_trunc('month',current_date)::date),0) AS precios_no_show,
  COALESCE(sum(precio) FILTER (WHERE estado='cancelado'
     AND inicio::date >= date_trunc('month',current_date)::date),0) AS precios_cancelado,
  COALESCE(sum(precio) FILTER (WHERE estado IN ('atendido','no_show','cancelado')
     AND precio IS NOT NULL
     AND inicio::date >= date_trunc('month',current_date)::date),0) AS suma_ingenua_todo;
""")
print("  ", s["n"][0])
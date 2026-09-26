#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compara los KPIs del HTML contra SQL directo. Imprime tabla."""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, r"G:\Barberia\archivos\dashboard\_verif")
from db import consultar

HTML = Path(r"G:\Barberia\archivos\dashboard\dashboard.html").read_text(encoding="utf-8")

SQL = r"""
SET TIME ZONE 'America/Mexico_City';
\pset footer off
\echo ===@@k@@===
WITH at AS (SELECT * FROM barber_citas WHERE estado='atendido' AND precio IS NOT NULL AND inicio IS NOT NULL)
SELECT
  (SELECT count(*) FROM barber_citas) AS citas_totales,
  COALESCE((SELECT sum(precio) FROM at WHERE inicio::date = current_date),0) AS ing_hoy,
  COALESCE((SELECT sum(precio) FROM at WHERE inicio::date >= date_trunc('week',current_date)::date),0) AS ing_sem,
  COALESCE((SELECT sum(precio) FROM at WHERE inicio::date >= date_trunc('month',current_date)::date),0) AS ing_mes,
  COALESCE((SELECT count(*) FROM at WHERE inicio::date = current_date),0) AS n_hoy,
  COALESCE((SELECT count(*) FROM at WHERE inicio::date >= date_trunc('week',current_date)::date),0) AS n_sem,
  COALESCE((SELECT count(*) FROM at WHERE inicio::date >= date_trunc('month',current_date)::date),0) AS n_mes,
  COALESCE((SELECT round(avg(precio),2) FROM at WHERE inicio::date=current_date),0) AS tk_hoy,
  COALESCE((SELECT round(avg(precio),2) FROM at WHERE inicio::date >= date_trunc('week',current_date)::date),0) AS tk_sem,
  COALESCE((SELECT round(avg(precio),2) FROM at WHERE inicio::date >= date_trunc('month',current_date)::date),0) AS tk_mes,
  COALESCE((SELECT count(*) FROM barber_citas WHERE estado='no_show' AND inicio IS NOT NULL AND inicio::date >= date_trunc('month',current_date)::date),0) AS no_show_mes,
  COALESCE((SELECT count(*) FROM barber_citas WHERE estado='cancelado' AND inicio IS NOT NULL AND inicio::date >= date_trunc('month',current_date)::date),0) AS canc_mes,
  COALESCE((SELECT count(*) FROM barber_citas WHERE inicio IS NOT NULL AND inicio::date >= date_trunc('month',current_date)::date),0) AS prog_mes,
  COALESCE((SELECT count(*) FROM barber_citas WHERE estado IN ('agendado','confirmado') AND inicio >= now()),0) AS futuras,
  COALESCE((SELECT count(*) FROM barber_citas WHERE estado IN ('agendado','confirmado') AND inicio >= now() AND inicio < now()+interval '7 days'),0) AS futuras_7,
  COALESCE((SELECT sum(precio) FROM barber_citas WHERE estado IN ('agendado','confirmado') AND inicio >= now() AND inicio < now()+interval '7 days'),0) AS ing_fut_7,
  (SELECT to_char(current_date,'YYYY-MM-DD')) AS fecha_hoy,
  current_setting('TimeZone') AS zona;
\echo ===@@mes_por_mes@@===
SELECT to_char(inicio,'YYYY-MM') AS mes, estado, count(*), sum(precio) AS dinero
  FROM barber_citas WHERE inicio IS NOT NULL GROUP BY 1,2 ORDER BY 1,2;
\echo ===@@no_atendido_dinero@@===
SELECT estado, count(*) AS n, COALESCE(sum(precio),0) AS suma_precios
  FROM barber_citas WHERE estado IN ('no_show','cancelado') GROUP BY 1;
\echo ===@@sin_precio@@===
SELECT estado, count(*) AS n FROM barber_citas WHERE precio IS NULL GROUP BY 1;
\echo ===@@servicios_null@@===
SELECT servicio IS NULL AS srv_null, count(*) FROM barber_citas GROUP BY 1;
"""

s = consultar(SQL)
k = s["k"][0]
for kk, vv in k.items():
    print(f"  SQL {kk} = {vv}")

print("\n--- valores en el HTML ---")
# extrae KPIs renderizados
kp = re.findall(r"<div class='kpi-t'>(.*?)</div><div class='kpi-v'>(.*?)</div>"
                r"<div class='kpi-p'>(.*?)</div>", HTML)
for t, v, p in kp:
    print(f"  {t} = {v}   ({p})")

print("\n--- comparacion ---")
esperado = {
    "Ingresos hoy": k["ing_hoy"], "Ingresos semana": k["ing_sem"],
    "Ingresos mes": k["ing_mes"], "No-shows del mes": k["no_show_mes"],
    "Cancelaciones del mes": k["canc_mes"], "Proximas 7 dias": k["futuras_7"],
}
def dinero(v):
    n = float(v)
    return f"${n:,.0f}"

fallos = 0
for t, v, p in kp:
    t2 = t.strip()
    if t2 in ("Ingresos hoy", "Ingresos semana", "Ingresos mes"):
        exp = dinero(esperado[t2])
    elif t2 in ("No-shows del mes", "Cancelaciones del mes", "Proximas 7 dias"):
        exp = str(int(float(esperado[t2])))
    else:
        continue
    ok = (v == exp)
    if not ok:
        fallos += 1
    print(f"  {'OK ' if ok else 'MAL'} {t2}: HTML={v} SQL={exp}")

print(f"\nFALLOS: {fallos}")
print("\n--- corte de mes (por mes) ---")
for f in s["mes_por_mes"]:
    print("  ", f)
print("\n--- no_show/cancelado suman dinero? ---")
for f in s["no_atendido_dinero"]:
    print("  ", f)
print("\n--- citas sin precio (depilacion etc.) ---")
for f in s["sin_precio"]:
    print("  ", f)
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evidencia fina (usa ejecutar y lee texto crudo, sin parsear CSV)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, r"G:\Barberia\archivos\dashboard\_verif")
from db import ejecutar

HTML = Path(r"G:\Barberia\archivos\dashboard\dashboard.html").read_text(encoding="utf-8")
AQUI = Path(r"G:\Barberia\archivos\dashboard")


def q(titulo, sql):
    print("\n" + "=" * 72)
    print(titulo)
    print("=" * 72)
    rc, out, err = ejecutar("SET TIME ZONE 'America/Mexico_City';\n\\pset footer off\n" + sql)
    print(out.rstrip())
    if err.strip():
        print("ERR:", err.strip())


q("1) ATENDIDAS SIN PRECIO (Depilacion): desaparecen de los indicadores",
  """
SELECT
  count(*) FILTER (WHERE estado='atendido')                                        AS atendidas_total,
  count(*) FILTER (WHERE estado='atendido' AND precio IS NOT NULL
        AND inicio::date >= date_trunc('month',current_date)::date)                AS mes_con_precio,
  count(*) FILTER (WHERE estado='atendido' AND precio IS NULL
        AND inicio::date >= date_trunc('month',current_date)::date)                AS mes_sin_precio,
  count(*) FILTER (WHERE estado='atendido' AND precio IS NULL)                     AS total_sin_precio
FROM barber_citas;
SELECT servicio, count(*) AS n FROM barber_citas
 WHERE estado='atendido' AND precio IS NULL GROUP BY 1 ORDER BY 2 DESC;
""")

print("\n  Tarjeta 'Ingresos mes' en el HTML:")
m = re.search(r"Ingresos mes</div><div class='kpi-v'>([^<]*)</div><div class='kpi-p'>([^<]*)</div>", HTML)
print("   ", m.groups() if m else "(no encontrada)")

q("2) NOMBRES LARGOS insertados",
  """
SELECT nombre, length(nombre) AS largo FROM barber_clientes
 ORDER BY length(nombre) DESC LIMIT 5;
""")

print("\n" + "=" * 72)
print("3) PROXIMAS CITAS: filas renderizadas vs futuras en BD")
print("=" * 72)
m = re.search(r"Proximas citas.*?<tbody>(.*?)</tbody>", HTML, re.S | re.I)
print("  filas en la tabla:", m.group(1).count("<tr>") if m else "?")
q("", """
SELECT count(*) AS futuras_totales FROM barber_citas
 WHERE estado IN ('agendado','confirmado') AND inicio >= now();
""")

print("\n" + "=" * 72)
print("4) GRAFICO 30 DIAS")
print("=" * 72)
m = re.search(r"<div class='tendencia'>(.*?)</div>\s*<div class='eje'", HTML, re.S)
if m:
    alturas = re.findall(r"style='height:([\d.]+)%'", m.group(1))
    print("  barras:", len(alturas), " vacias:", m.group(1).count("barra-v vacia"))
    print("  alturas:", alturas)
    if alturas:
        v = [float(a) for a in alturas]
        print("  min:", min(v), " max:", max(v),
              " barras <=3% (casi invisibles):", sum(1 for a in v if a <= 3))

print("\n" + "=" * 72)
print("5) CSS: por que se desborda la tabla en movil")
print("=" * 72)
src = (AQUI / "generar-dashboard.py").read_text(encoding="utf-8")
for i, l in enumerate(src.splitlines(), 1):
    t = l.strip()
    if t.startswith("table{") or "tbody td{font-size:15px" in t \
       or "thead th{font-size:12px" in t or "table-layout" in t \
       or "overflow-x" in t or "word-break" in t:
        print(f"  {i}: {t}")
print("  > NO existe table-layout:fixed, ni overflow-x:auto, ni word-break")
print("  > table{width:100%} con layout automatico: el ancho MINIMO de")
print("    contenido puede pasar del 100% y desborda el .panel.")
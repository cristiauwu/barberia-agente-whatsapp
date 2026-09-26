#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Limpia el extremo y prueba la cita de las 19:00 hora de Mexico.

Ahora mismo el reloj da ~19:0x en Mexico = ~01:0x UTC del dia SIGUIENTE.
Es exactamente el escenario del fallo clasico. Inserto una cita a las 19:00
de hoy (hora de Mexico, o sea ya 'manana' en UTC) y compruebo que el panel
la cuenta como HOY.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, r"G:\Barberia\archivos\dashboard\_verif")
from db import ejecutar, consultar

UV = r"C:\Users\kimbo\.cherrystudio\bin\uv.exe"
GEN = r"G:\Barberia\archivos\dashboard\generar-dashboard.py"
HTML = Path(r"G:\Barberia\archivos\dashboard\dashboard.html")

print("=== 1. borrar las 200 citas extremas ===")
rc, out, err = ejecutar("DELETE FROM barber_citas WHERE id LIKE 'verif-mill-%';")
print("  rc:", rc, "err:", err[:200])

print("\n=== 2. reloj: Mexico vs UTC ===")
s = consultar(r"""
SET TIME ZONE 'America/Mexico_City';
\echo ===@@r@@===
SELECT to_char(now() AT TIME ZONE 'America/Mexico_City','YYYY-MM-DD HH24:MI') AS mx,
       to_char(now() AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI') AS utc,
       current_date::text AS fecha_negocio,
       (now() AT TIME ZONE 'UTC')::date::text AS fecha_utc;
""")
r = s["r"][0]
for k, v in r.items():
    print(f"  {k} = {v}")

print("\n=== 3. insertar cita a las 19:00 hora de Mexico (hoy) ===")
# 19:00 Mexico hoy = 01:00 UTC manana
rc, out, err = ejecutar(r"""
SET TIME ZONE 'America/Mexico_City';
INSERT INTO barber_citas (id,jid,nombre,servicio,precio,inicio,fin,estado)
SELECT 'verif-1900',
       'verif-vip@s.whatsapp.net',
       'Cliente 19:00 Mexico',
       'Peinado', 300,
       (current_date + interval '19 hours')::timestamptz,
       (current_date + interval '19 hours 45 min')::timestamptz,
       'atendido'
WHERE NOT EXISTS (SELECT 1 FROM barber_citas WHERE id='verif-1900');
""")
print("  rc:", rc, "err:", err[:300])

s = consultar(r"""
SET TIME ZONE 'America/Mexico_City';
\echo ===@@i@@===
SELECT id, to_char(inicio,'YYYY-MM-DD HH24:MI (TZH:TZM)') AS inicio_local,
       to_char(inicio AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI') AS inicio_utc,
       (inicio)::date::text AS fecha_negocio,
       (inicio AT TIME ZONE 'UTC')::date::text AS fecha_utc
  FROM barber_citas WHERE id='verif-1900';
""")
print("  ", s["i"])

print("\n=== 4. regenerar el panel ===")
p = subprocess.run([UV, "run", "python", GEN], capture_output=True, text=True,
                   encoding="utf-8", errors="replace", timeout=300)
print("  rc:", p.returncode)
for l in (p.stdout or "").strip().splitlines():
    print("   ", l)

print("\n=== 5. el HTML cuenta la cita de 19:00 como HOY? ===")
html = HTML.read_text(encoding="utf-8")
print("  'Hoy: viernes 25 de septiembre de 2026' presente:",
      "Hoy: <b>viernes 25 de septiembre de 2026</b>" in html)
print("  'Cliente 19:00 Mexico' aparece en Citas de hoy:",
      "Cliente 19:00 Mexico" in html)
m = re.search(r"Ingresos hoy(.*?)Ingresos semana", html, re.S)
if m:
    txt = re.sub(r"<[^>]+>", " ", m.group(1))
    print("  tarjeta 'Ingresos hoy':", " ".join(txt.split())[:90])
# cuantas filas tiene la tabla de hoy
m = re.search(r"Citas de hoy.*?<tbody>(.*?)</tbody>", html, re.S)
if m:
    filas = m.group(1).count("<tr>")
    print("  filas en 'Citas de hoy':", filas)
    ult = re.findall(r"<td>([^<]*)</td>", m.group(1))
    print("  celdas:", ult[:10])
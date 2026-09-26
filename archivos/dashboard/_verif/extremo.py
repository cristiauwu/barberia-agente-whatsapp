#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Caso EXTREMO de numeros: mete cifras de mas de un millon y mide si los
KPIs se salen de su tarjeta. Restaura despues."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, r"G:\Barberia\archivos\dashboard\_verif")
from db import ejecutar

GEN = r"G:\Barberia\archivos\dashboard\generar-dashboard.py"
UV = r"C:\Users\kimbo\.cherrystudio\bin\uv.exe"

SQL_IN = r"""
SET TIME ZONE 'America/Mexico_City';
-- extremo: 200 citas de $6,173.85 el MISMO dia -> mes ~ $1,234,770
INSERT INTO barber_citas (id,jid,nombre,servicio,precio,inicio,fin,estado)
SELECT 'verif-mill-'||g,
       'verif-vip@s.whatsapp.net',
       'Cliente de Gasto Altísimo (VIP histórico)',
       'Peinado', 6173.85,
       date_trunc('day', current_date) + interval '10 hours',
       date_trunc('day', current_date) + interval '10 hours 45 min',
       'atendido'
  FROM generate_series(1,200) g
ON CONFLICT (id) DO NOTHING;
"""

SQL_OUT = "DELETE FROM barber_citas WHERE id LIKE 'verif-mill-%';"


def generar():
    r = subprocess.run([UV, "run", "python", GEN], capture_output=True,
                       text=True, encoding="utf-8", errors="replace",
                       timeout=300)
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


rc, out, err = ejecutar(SQL_IN)
print("insert rc:", rc, "err:", err[:400])
code, out2, err2 = generar()
print("generar rc:", code)
for l in out2.splitlines():
    print("  ", l)

Path(r"G:\Barberia\archivos\dashboard\_verif\_EXTREMO_ACTIVO.txt").write_text(
    "activo", encoding="utf-8")
print("\nEXTREMO ACTIVO. Siguiente paso: medir el HTML.")
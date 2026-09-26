#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Comprueba que no_show/cancelado no suman dinero, y el rol de conexion."""
import sys
sys.path.insert(0, r"G:\Barberia\archivos\dashboard\_verif")
from db import consultar, ejecutar

print("=" * 70)
print("NO_SHOW / CANCELADO SUMAN DINERO? (los ingresos solo deben contar atendido)")
print("=" * 70)
rc, out, err = ejecutar(r"""
SET TIME ZONE 'America/Mexico_City';
\pset footer off
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
print(out)
print("ERR:", err, "RC:", rc)

print("=" * 70)
print("ROL DE CONEXION DEL PANEL / PERMISOS")
print("=" * 70)
rc, out, err = ejecutar(r"""
\pset footer off
SELECT current_user, session_user,
       (SELECT rolsuper FROM pg_roles WHERE rolname=current_user) AS superusuario;
SELECT rolname, rolsuper, rolcreatedb, rolcreaterole, rolcanlogin
  FROM pg_roles ORDER BY rolname;
""")
print(out)
print("ERR:", err, "RC:", rc)

print("=" * 70)
print("TZ DEL CONTENEDOR (de donde sale la zona por defecto)")
print("=" * 70)
DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
import subprocess, os
os.environ["DOCKER_CONFIG"] = r"G:\Barberia\.docker"
for var in ("TZ", "PGTZ"):
    p = subprocess.run([DOCKER, "exec", "barberia-postgres", "printenv", var],
                       capture_output=True, text=True, timeout=60)
    print(f"  {var} = {p.stdout.strip()!r} (rc={p.returncode})")
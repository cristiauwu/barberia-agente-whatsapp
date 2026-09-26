#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Manejo de errores del generador SIN tocar Postgres real.

Importa el modulo y monkeypatchea el contenedor para simular:
  A) contenedor inexistente (Postgres no responde)
  B) timeout / docker ausente
No modifica ningun archivo del proyecto.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RUTA = r"G:\Barberia\archivos\dashboard\generar-dashboard.py"
spec = importlib.util.spec_from_file_location("gen", RUTA)
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)

print("=" * 72)
print("A) CONTENEDOR POSTGRES INEXISTENTE")
print("=" * 72)
gen.CONTENEDOR = "barberia-postgres-NO-EXISTE"
try:
    gen.consultar("SELECT 1;")
    print("  NO lanzo excepcion (inesperado)")
except Exception as e:
    print("  lanzo:", type(e).__name__)
    print("  mensaje:", str(e)[:300].replace("\n", " | "))

print()
print("=" * 72)
print("B) DOCKER.EXE INEXISTENTE")
print("=" * 72)
gen.DOCKER = r"C:\ruta\que\no\existe\docker.exe"
try:
    gen.consultar("SELECT 1;")
    print("  NO lanzo excepcion (inesperado)")
except Exception as e:
    print("  lanzo:", type(e).__name__)
    print("  mensaje:", str(e)[:300].replace("\n", " | "))

print()
print("=" * 72)
print("C) main() devuelve codigo y NO escribe el HTML si falla")
print("=" * 72)
HTML = Path(r"G:\Barberia\archivos\dashboard\dashboard.html")
antes = HTML.stat().st_mtime
gen.CONTENEDOR = "barberia-postgres-NO-EXISTE"
gen.DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
sys.argv = ["generar-dashboard.py"]
rc = gen.main()
print("  main() rc =", rc)
print("  dashboard.html intacto (mtime igual):", HTML.stat().st_mtime == antes)

print()
print("=" * 72)
print("D) FILAS VACIAS: que hace _parsear y el render con 0 filas?")
print("=" * 72)
print("  _parsear([])      ->", gen._parsear([]))
print("  _parsear([''])    ->", gen._parsear([""]))
print("  _parsear(['a,b','1,2']) ->", gen._parsear(["a,b", "1,2"]))
print()
print("  bloque_tendencia([])  ->", gen.bloque_tendencia([])[:80].replace("\n", " "))
print("  bloque_servicios([])  ->", gen.bloque_servicios([])[:80].replace("\n", " "))
print("  bloque_horas([])      ->", gen.bloque_horas([])[:80].replace("\n", " "))
print("  bloque_estados([])    ->", gen.bloque_estados([])[:80].replace("\n", " "))
print("  bloque_hoy([])        ->", gen.bloque_hoy([])[:80].replace("\n", " "))
print("  bloque_proximas([])   ->", gen.bloque_proximas([])[:80].replace("\n", " "))

print()
print("=" * 72)
print("E) SQL: hay interpolacion de valores? (inyeccion)")
print("=" * 72)
src = Path(RUTA).read_text(encoding="utf-8")
print("  SQL_KPIS es una constante literal:", "SQL_KPIS = r\"\"\"" in src)
print("  consultar() recibe `sql` y lo manda por stdin:", "input=sql.encode" in src)
print("  usa -f - (nada se interpola en el shell):", '"-f", "-"' in src)
print("  usa shell=True?:", "shell=True" in src)
print("  argumentos del generador:", [l.strip() for l in src.splitlines()
      if "add_argument" in l])
print("  -> no hay ningun dato externo que entre al SQL; el script es estatico.")
print("  -> el unico argumento (--salida) NO se usa para SQL, solo como ruta de")
print("     archivo de salida: se podria escribir en cualquier ruta del disco si")
print("     alguien ejecuta el script a mano con --salida C:\\...\\x.html")
d = gen.dinero("1234567.891")
print("  dinero('1234567.891') =", d)
print("  esc('<script>') =", gen.esc("<script>")[:40])
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Comprueba en CUAL de las dos bases existe la constraint anti-solape.

El verificador del documento dijo "no existe" en el Postgres LOCAL, pero
supabase-verificar.py dice "constraint anti-solape OK" en SUPABASE. Antes
de escribir nada en la documentacion hay que saber cual es la verdad, y
resulta que NO es la misma en las dos bases.

Esto importa mucho: la restriccion que impide dobles reservas solo
protege si esta en la base que realmente recibe las citas.
"""
import os
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DOCKER = (r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop"
          r"\resources\bin\docker.exe")
os.environ["DOCKER_CONFIG"] = r"G:\Barberia\.docker"

CONSULTA = """
SELECT 'EXCLUDE' AS tipo, conname AS nombre, pg_get_constraintdef(oid) AS def
  FROM pg_constraint
 WHERE conrelid='barber_citas'::regclass AND contype='x'
UNION ALL
SELECT 'EXTENSION', extname, ''
  FROM pg_extension WHERE extname IN ('btree_gist','pgvector')
UNION ALL
SELECT 'COLUMNA', column_name, data_type
  FROM information_schema.columns
 WHERE table_name='barber_citas' AND column_name='rango'
ORDER BY 1,2;
"""


def local():
    p = subprocess.run([DOCKER, "exec", "barberia-postgres", "psql",
                        "-U", "barberia", "-d", "barberia", "-t", "-A", "-F",
                        " | ", "-c", CONSULTA],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=120)
    return (p.stdout or "").strip(), (p.stderr or "").strip()


def supabase():
    """Se conecta al pooler de Supabase con psycopg2."""
    pwd = ""
    for ruta in (r"G:\Barberia\archivos\.supabase-pass.txt",
                 r"G:\Barberia\archivos\.supabase-conn.txt"):
        try:
            texto = open(ruta, encoding="utf-8").read().strip().split("\n")
        except OSError:
            continue
        for l in texto:
            if l.startswith("password="):
                pwd = l.split("=", 1)[1].strip()
        if not pwd and len(texto) >= 4:
            pwd = texto[3].strip()
    if not pwd:
        return "no tengo la password", ""
    try:
        import psycopg2  # noqa
    except ImportError:
        return "falta psycopg2", ""
    try:
        c = psycopg2.connect(
            host="aws-0-us-east-2.pooler.supabase.com", port=5432,
            user="postgres.zucgrcyzofelmiorvxhb", password=pwd,
            dbname="postgres", sslmode="require", connect_timeout=25)
        cur = c.cursor()
        cur.execute(CONSULTA)
        out = "\n".join(" | ".join(str(x) for x in f) for f in cur.fetchall())
        c.close()
        return out, ""
    except Exception as e:
        return "", str(e)[:200]


print("=" * 70)
print("¿DONDE ESTA LA CONSTRAINT ANTI-SOLAPE?")
print("=" * 70)

print("\n--- POSTGRES LOCAL (barberia-postgres) ---")
o, e = local()
print("  " + (o.replace("\n", "\n  ") if o else "(NADA: sin EXCLUDE, sin extension, sin columna rango)"))
if e:
    print(f"  stderr: {e[:120]}")

print("\n--- SUPABASE ---")
o2, e2 = supabase()
if o2:
    for l in o2.split("\n"):
        print("  " + l[:150])
else:
    print(f"  no se pudo consultar: {e2 or '(vacio)'}")

print()
print("=" * 70)
print("CONCLUSION")
print("=" * 70)
tiene_local = "EXCLUDE" in o
tiene_sb = "EXCLUDE" in o2
print(f"  Postgres local : {'SI tiene' if tiene_local else 'NO tiene'} la restriccion")
print(f"  Supabase       : {'SI tiene' if tiene_sb else 'NO tiene'} la restriccion")
print()
if tiene_sb and not tiene_local:
    print("  La proteccion existe SOLO en Supabase, que hoy es una copia sin")
    print("  uso. El Postgres local, que es el que n8n escribe, NO la tiene.")
    print("  => La afirmacion 'la base impide las dobles reservas' es FALSA")
    print("     para el sistema en produccion. Hay que corregirlo en los dos")
    print("     sitios: el documento y la base.")
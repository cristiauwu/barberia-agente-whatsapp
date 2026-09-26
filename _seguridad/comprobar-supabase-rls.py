#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Comprueba si Supabase de verdad protege los datos o si mi test mintio.

MI TEST ANTERIOR DIJO "CRITICO: tablas legibles" porque la API REST
respondio HTTP 200. Pero devolvio **0 filas**. Eso es exactamente lo que
hace RLS cuando NO hay politica que permita leer: responde 200 con lista
vacia, no un 401. Es decir: mi test confundio "no da error" con "no
protege".

La forma correcta de saberlo: comparar lo que ve la CONEXION DIRECTA
(el dueno, con la password) contra lo que ve la CLAVE PUBLICA.
  - Si la directa ve 8 servicios y la publica ve 0 -> RLS protege. BIEN.
  - Si las dos ven 8                                  -> esta abierto. MAL.
"""
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

PUB1 = "sb_publishable_vTcYIYR7h7n357m9dohntQ_lEPaJENw"
PUB2 = "sb_publishable_lXrbroKwpGHTqqCYoMpb3w_9FUwRjiM"
PROY = "zucgrcyzofelmiorvxhb"
BASE = f"https://{PROY}.supabase.co/rest/v1"
TABLAS = ["barber_clientes", "barber_citas", "barber_servicios",
          "barber_conocimiento", "barber_operadores", "barber_pausas",
          "barber_bloqueos", "barber_escalaciones"]


def con_clave(clave, tabla, limite=100):
    req = urllib.request.Request(
        f"{BASE}/{tabla}?select=*&limit={limite}")
    req.add_header("apikey", clave)
    req.add_header("Authorization", f"Bearer {clave}")
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            cuerpo = r.read().decode()
            return r.status, json.loads(cuerpo) if cuerpo.strip() else []
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, None
    except Exception as e:
        return None, str(e)


def con_password():
    """Lo que ve el dueno por conexion directa (la verdad)."""
    pwd = ""
    for l in open(r"G:\Barberia\archivos\.supabase-conn.txt",
                  encoding="utf-8"):
        if l.startswith("password="):
            pwd = l.split("=", 1)[1].strip()
    try:
        import psycopg2
    except ImportError:
        return None
    try:
        c = psycopg2.connect(
            host="aws-0-us-east-2.pooler.supabase.com", port=5432,
            user="postgres.zucgrcyzofelmiorvxhb", password=pwd,
            dbname="postgres", sslmode="require", connect_timeout=25)
        cur = c.cursor()
        cur.execute("""
            SELECT c.relname,
                   c.relrowsecurity,
                   COALESCE(s.n_live_tup, 0)
              FROM pg_class c
              JOIN pg_namespace n ON n.oid = c.relnamespace
              LEFT JOIN pg_stat_user_tables s ON s.relid = c.oid
             WHERE n.nspname='public' AND c.relkind='r'
               AND c.relname LIKE 'barber%'
             ORDER BY c.relname;""")
        filas = cur.fetchall()
        c.close()
        return filas
    except Exception as e:
        print(f"  no pude conectar: {str(e)[:100]}")
        return None


print("=" * 72)
print("¿SUPABASE PROTEGE LOS DATOS? (comparando las dos vistas)")
print("=" * 72)

print("\n--- lo que ve el DUENO (conexion directa) ---")
directo = con_password()
if directo:
    estados = {}
    for nombre, rls, filas in directo:
        estados[nombre] = (rls, filas)
        print(f"  {nombre:26} RLS={'SI' if rls else 'NO':<3} filas~{filas}")
else:
    print("  (no disponible)")
    estados = {}

print("\n--- lo que ve CUALQUIERA con la clave publica ---")
publico = {}
for t in TABLAS:
    st, datos = con_clave(PUB1, t)
    n = len(datos) if isinstance(datos, list) else "?"
    publico[t] = n
    marca = "OK  " if n == 0 else "MAL "
    print(f"  {marca} {t:26} HTTP {st}  {n} filas visibles")

print()
print("--- la clave 2 ---")
for t in ("barber_clientes", "barber_servicios"):
    st, datos = con_clave(PUB2, t)
    n = len(datos) if isinstance(datos, list) else "?"
    print(f"  {'OK  ' if n == 0 else 'MAL '} {t:26} HTTP {st}  {n} filas")

print()
print("=" * 72)
print("VEREDICTO")
print("=" * 72)
if not estados:
    print("  No pude comparar: falta la conexion directa.")
    sys.exit(2)

riesgos = []
for t in TABLAS:
    rls, filas_reales = estados.get(t, (False, 0))
    visto = publico.get(t, 0)
    if isinstance(visto, int) and visto > 0:
        riesgos.append((t, rls, filas_reales, visto))
        print(f"  CRITICO {t}: la clave publica ve {visto} filas")
    elif rls:
        print(f"  OK  {t}: RLS lo bloquea (la publica ve 0, la directa {filas_reales})")
    else:
        print(f"  --  {t}: sin RLS marcado, pero la publica ve 0 "
              f"(tiene datos: {filas_reales})")

print()
if riesgos:
    print("  HAY DATOS EXPUESTOS. Hay que cerrarlo antes de vender.")
else:
    print("  OK  ninguna tabla expone datos por la clave publica.")
    print("  El REST devuelve 200 con lista vacia: eso es RLS denegando.")
    print("  ES EL COMPORTAMIENTO CORRECTO.")
print("=" * 72)
sys.exit(1 if riesgos else 0)
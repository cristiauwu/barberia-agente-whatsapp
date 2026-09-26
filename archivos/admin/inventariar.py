#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extrae el inventario REAL del sistema para documentarlo con precision.

Saca, de la fuente (n8n en vivo y Postgres), todo lo que hace falta para
que otro agente entienda la arquitectura sin adivinar:
  - los 3 workflows con TODOS sus nodos (nombre, tipo, posicion)
  - las conexiones entre nodos (quien llama a quien)
  - el esquema de Postgres (tablas, columnas, indices, constraints)
  - las credenciales que se usan (por nombre, sin exponer nada)
"""
import json
import os
import subprocess
import sys
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

N8N = "http://localhost:5678/api/v1"
KEY = open(r"G:\Barberia\archivos\.n8n-key.txt", encoding="utf-8").read().strip()
DOCKER = (r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop"
          r"\resources\bin\docker.exe")
os.environ["DOCKER_CONFIG"] = r"G:\Barberia\.docker"
SALIDA = r"G:\Barberia\archivos\admin\INVENTARIO.json"


def api(p):
    r = urllib.request.Request(N8N + p)
    r.add_header("X-N8N-API-KEY", KEY)
    with urllib.request.urlopen(r, timeout=90) as x:
        return json.loads(x.read().decode())


def sql(q):
    p = subprocess.run([DOCKER, "exec", "barberia-postgres", "psql",
                        "-U", "barberia", "-d", "barberia", "-t", "-A", "-F",
                        "|", "-c", q], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=120)
    return (p.stdout or "").strip()


out = {"workflows": [], "tablas": [], "indices": [], "constraints": []}

print("=" * 70)
print("WORKFLOWS")
print("=" * 70)
wfs = api("/workflows?limit=50")["data"]
for w in wfs:
    det = api(f"/workflows/{w['id']}")
    nodos = []
    for n in det["nodes"]:
        nodos.append({
            "nombre": n["name"],
            "tipo": n["type"],
            "pos": [round(n["position"][0]), round(n["position"][1])],
            "notas": (n.get("notes") or "")[:200],
            "credenciales": [c.get("name") for c in
                             (n.get("credentials") or {}).values()],
        })
    # conexiones: quien sale hacia quien
    conex = []
    for origen, salidas in (det.get("connections") or {}).items():
        for tipo, ramas in salidas.items():
            for i, rama in enumerate(ramas or []):
                for destino in (rama or []):
                    conex.append({"de": origen, "a": destino["node"],
                                  "tipo": tipo, "salida": i})
    out["workflows"].append({
        "id": w["id"], "nombre": w["name"], "activo": w.get("active"),
        "n_nodos": len(det["nodes"]), "n_conexiones": len(conex),
        "nodos": nodos, "conexiones": conex,
    })
    print(f"  {w['name']:34} {len(det['nodes']):>3} nodos  "
          f"{len(conex):>3} conexiones  activo={w.get('active')}")

print()
print("=" * 70)
print("ESQUEMA DE POSTGRES")
print("=" * 70)
tablas = sql("""SELECT tablename FROM pg_tables
                WHERE schemaname='public' ORDER BY tablename;""")
for t in [x for x in tablas.split("\n") if x.strip()]:
    cols = sql(f"""SELECT column_name||':'||data_type||
                   CASE WHEN is_nullable='NO' THEN '!NOTNULL' ELSE '' END
                   FROM information_schema.columns
                   WHERE table_name='{t}' ORDER BY ordinal_position;""")
    n = sql(f"SELECT count(*) FROM {t};")
    columnas = [c for c in cols.split("\n") if c.strip()]
    out["tablas"].append({"nombre": t, "filas": n, "columnas": columnas})
    print(f"  {t:26} {len(columnas):>3} columnas  {n:>6} filas")

print()
for tipo, consulta in (
    ("indices", """SELECT indexname||' -> '||indexdef FROM pg_indexes
                   WHERE schemaname='public' ORDER BY tablename,indexname;"""),
    ("constraints", """SELECT conname||' : '||pg_get_constraintdef(oid)
                       FROM pg_constraint
                       WHERE connamespace='public'::regnamespace
                       ORDER BY conname;"""),
):
    for l in [x for x in sql(consulta).split("\n") if x.strip()]:
        out[tipo].append(l)

print(f"  indices: {len(out['indices'])}   constraints: {len(out['constraints'])}")

json.dump(out, open(SALIDA, "w", encoding="utf-8"), ensure_ascii=False,
          indent=1)
print()
print(f"  escrito: {SALIDA}")
print(f"  tamano: {os.path.getsize(SALIDA)//1024} KB")
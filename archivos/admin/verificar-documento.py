#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Comprueba que lo que dice ARQUITECTURA.md sea verdad.

Un documento de arquitectura que miente es peor que no tenerlo. Este
script contrasta las afirmaciones concretas del documento contra el
sistema real (n8n en vivo, Postgres, los archivos).
"""
import json
import os
import re
import subprocess
import sys
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RAIZ = r"G:\Barberia"
DOC = os.path.join(RAIZ, "ARQUITECTURA.md")
N8N = "http://localhost:5678/api/v1"
KEY = open(os.path.join(RAIZ, "archivos", ".n8n-key.txt"),
           encoding="utf-8").read().strip()
DOCKER = (r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop"
          r"\resources\bin\docker.exe")
os.environ["DOCKER_CONFIG"] = os.path.join(RAIZ, ".docker")

doc = open(DOC, encoding="utf-8").read()
fallos = 0


def api(p):
    r = urllib.request.Request(N8N + p)
    r.add_header("X-N8N-API-KEY", KEY)
    with urllib.request.urlopen(r, timeout=90) as x:
        return json.loads(x.read().decode())


def sql(q):
    p = subprocess.run([DOCKER, "exec", "barberia-postgres", "psql",
                        "-U", "barberia", "-d", "barberia", "-t", "-A", "-c", q],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=120)
    return (p.stdout or "").strip()


def check(nombre, real, esperado_en_doc):
    """Comprueba que el valor real coincida con el que afirma el documento."""
    global fallos
    ok = str(real) == str(esperado_en_doc)
    if not ok:
        fallos += 1
    print(f"  {'OK  ' if ok else 'MAL '} {nombre}: real={real} doc={esperado_en_doc}")


print("=" * 70)
print("EL DOCUMENTO CONTRA EL SISTEMA REAL")
print("=" * 70)

# ---- workflows -------------------------------------------------------
print("\n[1] WORKFLOWS")
wfs = {w["name"]: w for w in api("/workflows?limit=50")["data"]}
check("hay 3 workflows", len(wfs), 3)
for nombre, nodos in (("Barberia - Agente de citas (Uncensored AI)", 45),
                      ("Barberia - Recordatorios de cita", 17),
                      ("barberiaVigilancia", 5)):
    w = wfs.get(nombre)
    check(f"nodos de '{nombre[:28]}'",
          len(w["nodes"]) if w else "no existe", nodos)

print("\n[2] EL DOCUMENTO DICE 67 NODOS EN TOTAL")
total = sum(len(w["nodes"]) for w in wfs.values())
check("suma de nodos", total, 67)

# ---- el router de comandos ------------------------------------------
print("\n[3] EL ROUTER DE COMANDOS")
ID_AGENTE = wfs["Barberia - Agente de citas (Uncensored AI)"]["id"]
wf = api(f"/workflows/{ID_AGENTE}")
sw = next((n for n in wf["nodes"]
           if n["name"] == "Router de comandos"), None)
if sw:
    n_salidas = len(sw["parameters"].get("rules", {}).get("values", []))
    check("reglas del Router", n_salidas, 12)
else:
    print("  MAL no encontre el Router"); fallos += 1

# ---- la memoria ------------------------------------------------------
print("\n[4] LA VENTANA DE MEMORIA")
mem = next((n for n in wf["nodes"] if "memoryPostgresChat" in n["type"]), None)
if mem:
    check("contextWindowLength",
          mem["parameters"].get("contextWindowLength"), 12)
else:
    print("  MAL no encontre la memoria"); fallos += 1

# ---- el modelo -------------------------------------------------------
print("\n[5] EL MODELO")
mod = next((n for n in wf["nodes"] if "lmChatOpenAi" in n["type"]), None)
if mod:
    m = mod["parameters"].get("model")
    # n8n devuelve {'__rl':True,'value':'gpt-4o',...} o un string simple
    valor = m.get("value") if isinstance(m, dict) else m
    check("modelo", valor, "gpt-4o")
else:
    print("  MAL no encontre el modelo"); fallos += 1

# ---- herramientas del agente ----------------------------------------
print("\n[6] LAS HERRAMIENTAS DEL AGENTE")
n_herr = 0
for origen, salidas in (wf.get("connections") or {}).items():
    for tipo, ramas in salidas.items():
        if tipo != "ai_tool":
            continue
        for rama in (ramas or []):
            n_herr += len(rama or [])
check("herramientas ai_tool", n_herr, 6)

# ---- postgres --------------------------------------------------------
print("\n[7] POSTGRES")
for tabla, filas in (("barber_servicios", 8), ("barber_conocimiento", 58),
                     ("barber_operadores", 2)):
    check(f"filas de {tabla}", sql(f"SELECT count(*) FROM {tabla};"), filas)

check("la constraint anti-solape existe en el LOCAL",
      "1" if "barber_citas_no_solape" in sql(
          "SELECT conname FROM pg_constraint WHERE conname='barber_citas_no_solape';")
      else "0", "1")
check("la extension btree_gist esta",
      "1" if "btree_gist" in sql(
          "SELECT extname FROM pg_extension WHERE extname='btree_gist';")
      else "0", "1")

check("la funcion de busqueda existe",
      "1" if sql("SELECT proname FROM pg_proc WHERE proname LIKE 'barber_buscar%';")
      else "0", "1")

# ---- la hoja ---------------------------------------------------------
print("\n[8] LA HOJA DE CALCULO (lo que dice el documento)")
check("el gid", "941506024" in doc, True)
check("la columna 'Dia ' con espacio", "Día " in doc, True)
check("la columna Execution ID", "Execution ID" in doc, True)

# ---- el calendario ---------------------------------------------------
print("\n[9] EL CALENDARIO")
check("el id del calendario en el doc",
      "b5e08030160a7cead790f900fafd3728792af6d2eac8a22b1dedb7844c09143c" in doc,
      True)

# ---- las credenciales ------------------------------------------------
print("\n[10] LAS CREDENCIALES")
creds = api("/credentials?limit=50")["data"]
check("numero de credenciales", len(creds), 7)
nombres_doc = ["Evolution API", "Postgres account", "Google Calendar account",
               "Google Sheets account", "Google Sheets Trigger account",
               "Uncensored AI", "n8n API (local)"]
for n in nombres_doc:
    ok = any(n.lower() in c["name"].lower() for c in creds)
    if not ok:
        fallos += 1
    print(f"  {'OK  ' if ok else 'MAL '} credencial '{n}'")

# ---- los paneles -----------------------------------------------------
print("\n[11] LOS PANELES")
check("existe el panel de produccion",
      os.path.exists(os.path.join(RAIZ, "archivos", "dashboard",
                                  "dashboard.html")), True)
ruta_admin = os.path.join(RAIZ, "archivos", "admin",
                          "barber-chinos-admin.html")
check("existe el panel administrativo", os.path.exists(ruta_admin), True)
if os.path.exists(ruta_admin):
    kb = os.path.getsize(ruta_admin) / 1024
    check("tamano del panel admin (~438 KB)", round(kb), 438)

# ---- verify.py -------------------------------------------------------
print("\n[12] LAS 187 COMPROBACIONES")
vp = os.path.join(RAIZ, "verify.py")
if os.path.exists(vp):
    p = subprocess.run(["uv", "run", "python", vp], cwd=RAIZ,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=600)
    m = re.search(r"RESULTADO:\s*(\d+)\s*de\s*(\d+)", p.stdout or "")
    if m:
        check("verify.py pasa", f"{m.group(1)}/{m.group(2)}", "187/187")
    else:
        print("  MAL no pude leer el resultado de verify.py"); fallos += 1

print()
print("=" * 70)
print(f"AFIRMACIONES FALSAS EN EL DOCUMENTO: {fallos}")
print("=" * 70)
sys.exit(0 if fallos == 0 else 1)
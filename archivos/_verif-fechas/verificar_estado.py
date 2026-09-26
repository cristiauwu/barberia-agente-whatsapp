#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Comprueba el calendario y la hoja despues de las pruebas en vivo."""
import json
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"G:\Barberia\archivos\_verif")
DIR = r"G:\Barberia\archivos\_verif-fechas"
DOCKER = (r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop"
          r"\resources\bin\docker.exe")
os.environ["DOCKER_CONFIG"] = r"G:\Barberia\.docker"

import cal  # noqa: E402

r = cal.listar("2026-09-01T00:00:00-06:00", "2027-03-01T23:59:59-06:00")
ev = (r.get("eventos") if isinstance(r, dict) else
      (r[0] or {}).get("json", {}).get("eventos", [])) or []
cal.limpiar_wf()

antes = json.load(open(DIR + r"\respaldo_calendario.json", encoding="utf-8"))
ids_antes = {e["id"] for e in antes}
ids_ahora = {e["id"] for e in ev}
print("=" * 72)
print("CALENDARIO")
print("=" * 72)
print("eventos ANTES de las pruebas:", len(antes))
print("eventos AHORA:", len(ev))
nuevos = [e for e in ev if e["id"] not in ids_antes]
perdidos = [e for e in antes if e["id"] not in ids_ahora]
print("\nEVENTOS NUEVOS (creados por las pruebas):", len(nuevos))
for e in nuevos:
    print(f"  {e['id']} | {e['start']} .. {e['end']} | {e['summary']}")
print("\nEVENTOS DESAPARECIDOS:", len(perdidos))
for e in perdidos:
    print(f"  {e['id']} | {e['start']} | {e['summary']}")
json.dump(ev, open(DIR + r"\calendario_despues.json", "w",
                   encoding="utf-8"), ensure_ascii=False, indent=1)

# ---- hoja ----
print()
print("=" * 72)
print("HOJA DE CITAS")
print("=" * 72)
KEY = open(r"G:\Barberia\archivos\.n8n-key.txt", encoding="utf-8").read().strip()
import urllib.request  # noqa: E402
DOCKER_CRED = None


def api(p):
    q = urllib.request.Request("http://localhost:5678/api/v1" + p)
    q.add_header("X-N8N-API-KEY", KEY)
    with urllib.request.urlopen(q, timeout=120) as x:
        return json.loads(x.read().decode())


# leer la hoja via un workflow temporal: mas simple, usar el nodo de lectura
wf = {
 "name": "_verif-fechas-hoja",
 "nodes": [
   {"parameters": {"httpMethod": "POST", "path": "verifhoja",
                   "responseMode": "lastNode", "options": {}},
    "type": "n8n-nodes-base.webhook", "typeVersion": 2, "position": [0, 0],
    "id": "wh1", "name": "Webhook", "webhookId": "wh-verif-hoja"},
   {"parameters": {"operation": "read", "documentId": {
       "__rl": True, "value": "1lvSVFWU2ApvK7p5BsFHI68Icur46P6hI8o8r9ozhBfk",
       "mode": "list", "cachedResultName": "Citas barbería"},
     "sheetName": {"__rl": True, "value": "941506024", "mode": "list",
                   "cachedResultName": "Hoja 1"},
     "filtersUI": {}, "options": {}},
    "type": "n8n-nodes-base.googleSheets", "typeVersion": 4.5,
    "position": [220, 0], "id": "gs1", "name": "Leer",
    "credentials": {"googleSheetsOAuth2Api": {
        "id": "ZgyQLpceAgCMrPWu", "name": "Google Sheets account"}}},
 ], "connections": {"Webhook": {"main": [[{"node": "Leer", "type": "main",
                                           "index": 0}]]}},
 "settings": {"executionOrder": "v1"}}

# localizar la credencial real de Sheets usada por el agente
wfa = json.load(open(DIR + r"\wf_agente.json", encoding="utf-8"))
nod = next(n for n in wfa["nodes"] if n["name"] == "Registrar en hoja de citas")
print("credencial de la hoja en el agente:",
      json.dumps(nod.get("credentials"), ensure_ascii=False))
wf["nodes"][1]["credentials"] = nod["credentials"]

# el workflow temporal se crea y se borra
import time  # noqa: E402
st = None
try:
    q = urllib.request.Request(
        "http://localhost:5678/api/v1/workflows",
        data=json.dumps(wf).encode(), method="POST")
    q.add_header("X-N8N-API-KEY", KEY)
    q.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(q, timeout=90) as x:
        creado = json.loads(x.read().decode())
    wid = creado["id"]
    q = urllib.request.Request(
        f"http://localhost:5678/api/v1/workflows/{wid}/activate",
        data=b"{}", method="POST")
    q.add_header("X-N8N-API-KEY", KEY)
    q.add_header("Content-Type", "application/json")
    urllib.request.urlopen(q, timeout=90).read()
    time.sleep(4)
    q = urllib.request.Request("http://localhost:5678/webhook/verifhoja",
                               data=b"{}", method="POST")
    q.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(q, timeout=120) as x:
        filas = json.loads(x.read().decode())
    print("filas en la hoja:", len(filas) if isinstance(filas, list) else filas)
    json.dump(filas, open(DIR + r"\hoja_despues.json", "w",
                          encoding="utf-8"), ensure_ascii=False, indent=1)
    if isinstance(filas, list):
        for f in filas:
            j = f.get("json", f)
            print("  ", json.dumps(j, ensure_ascii=False)[:200])
    time.sleep(2)
    q = urllib.request.Request(
        f"http://localhost:5678/api/v1/workflows/{wid}/deactivate",
        data=b"{}", method="POST")
    q.add_header("X-N8N-API-KEY", KEY)
    q.add_header("Content-Type", "application/json")
    urllib.request.urlopen(q, timeout=90).read()
    time.sleep(1)
    q = urllib.request.Request(
        f"http://localhost:5678/api/v1/workflows/{wid}", method="DELETE")
    q.add_header("X-N8N-API-KEY", KEY)
    urllib.request.urlopen(q, timeout=90).read()
    print("workflow temporal de hoja eliminado")
except Exception as e:
    print("ERROR leyendo la hoja:", e)
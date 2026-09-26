#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lee TODA la hoja de citas con un workflow temporal y la borra despues."""
import json
import os
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
DIR = r"G:\Barberia\archivos\_verif-fechas"
KEY = open(r"G:\Barberia\archivos\.n8n-key.txt", encoding="utf-8").read().strip()
BASE = "http://localhost:5678/api/v1"


def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    q = urllib.request.Request(BASE + path, data=data, method=method)
    q.add_header("X-N8N-API-KEY", KEY)
    q.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(q, timeout=120) as x:
        txt = x.read().decode()
        return json.loads(txt) if txt.strip() else {}


wfa = json.load(open(DIR + r"\wf_agente.json", encoding="utf-8"))
nod = next(n for n in wfa["nodes"] if n["name"] == "Registrar en hoja de citas")
creds = nod["credentials"]

wf = {
 "name": "_verif-fechas-hoja",
 "nodes": [
   {"parameters": {"httpMethod": "POST", "path": "verifhoja2",
                   "responseMode": "lastNode", "options": {}},
    "type": "n8n-nodes-base.webhook", "typeVersion": 2, "position": [0, 0],
    "id": "wh1", "name": "Webhook", "webhookId": "wh-verif-hoja2"},
   {"parameters": {"operation": "read", "documentId": {
       "__rl": True, "value": "1lvSVFWU2ApvK7p5BsFHI68Icur46P6hI8o8r9ozhBfk",
       "mode": "list", "cachedResultName": "Citas barbería"},
     "sheetName": {"__rl": True, "value": "941506024", "mode": "list",
                   "cachedResultName": "Hoja 1"},
     "filtersUI": {}, "options": {}},
    "type": "n8n-nodes-base.googleSheets", "typeVersion": 4.5,
    "position": [220, 0], "id": "gs1", "name": "Leer",
    "credentials": creds},
   {"parameters": {"jsCode":
       "const items = $input.all().map(i => i.json);\n"
       "return [{ json: { filas: items } }];\n"},
    "type": "n8n-nodes-base.code", "typeVersion": 2, "position": [440, 0],
    "id": "c1", "name": "Juntar"},
 ], "connections": {"Webhook": {"main": [[{"node": "Leer", "type": "main",
                                           "index": 0}]]},
                    "Leer": {"main": [[{"node": "Juntar", "type": "main",
                                        "index": 0}]]}},
 "settings": {"executionOrder": "v1"}}

creado = call("POST", "/workflows", wf)
wid = creado["id"]
try:
    call("POST", f"/workflows/{wid}/activate", {})
    time.sleep(4)
    q = urllib.request.Request("http://localhost:5678/webhook/verifhoja2",
                               data=b"{}", method="POST")
    q.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(q, timeout=120) as x:
        r = json.loads(x.read().decode())
    filas = r["filas"] if isinstance(r, dict) else r
    print("FILAS EN LA HOJA:", len(filas))
    for f in filas:
        print("  ", json.dumps(f, ensure_ascii=False))
    json.dump(filas, open(DIR + r"\hoja_despues.json", "w",
                          encoding="utf-8"), ensure_ascii=False, indent=1)
finally:
    time.sleep(2)
    try:
        call("POST", f"/workflows/{wid}/deactivate", {})
    except Exception as e:
        print("deactivate:", e)
    time.sleep(1)
    call("DELETE", f"/workflows/{wid}")
    print("workflow temporal eliminado")
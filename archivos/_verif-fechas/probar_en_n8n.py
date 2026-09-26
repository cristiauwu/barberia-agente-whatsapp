#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRUEBA DEFINITIVA v2: ejecuta el jsCode REAL de la herramienta dentro del
propio entorno de ejecucion de n8n (nodo Code), no con `docker exec node`.

Motivo: el resultado del caso '05/01/2027' difirio entre `docker exec node`
(1 de mayo) y la ejecucion real del agente (30 de abril). Hay que probar en
el MISMO motor que usa n8n.
"""
import json
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
    with urllib.request.urlopen(q, timeout=180) as x:
        txt = x.read().decode()
        return json.loads(txt) if txt.strip() else {}


wf = call("GET", "/workflows/barberiaAgenteUncensored")
js = next(n for n in wf["nodes"] if n["name"] == "Que dia es")["parameters"]["jsCode"]

CASOS = [
    ("1a", "2026-09-28T12:00:00-06:00"), ("1b", "2026-09-29T12:00:00-06:00"),
    ("1c", "2026-09-30T12:00:00-06:00"), ("1d", "2026-10-01T12:00:00-06:00"),
    ("1e", "2026-10-02T12:00:00-06:00"), ("1f", "2026-10-03T12:00:00-06:00"),
    ("1g", "2026-09-27T12:00:00-06:00"),
    ("2a", "2026-09-28T19:00:00-06:00"), ("2b", "2026-09-29T01:00:00Z"),
    ("2c", "2026-09-29T01:00:00+00:00"), ("2d", "2026-09-29T01:00:00.000Z"),
    ("2e", "2026-09-28T18:59:00-06:00"), ("2f", "2026-09-28T20:00:00-06:00"),
    ("2g", "2026-09-28T06:00:00Z"), ("2h", "2026-09-27T19:00:00-06:00"),
    ("2i", "2026-09-28T01:00:00Z"),
    ("3a", "2026-09-28T00:00:00-06:00"), ("3b", "2026-09-28T23:59:00-06:00"),
    ("3c", "2026-09-29T05:59:00Z"), ("3d", "2026-09-29T06:00:00Z"),
    ("3e", "2026-09-29T05:59:59Z"),
    ("4a", "2026-08-31T10:00:00-06:00"), ("4b", "2026-09-01T10:00:00-06:00"),
    ("4c", "2026-08-31T23:59:00-06:00"), ("4d", "2026-09-01T06:00:00Z"),
    ("4e", "2026-09-30T23:00:00-06:00"), ("4f", "2026-10-01T05:00:00Z"),
    ("5a", "2026-12-31T22:00:00-06:00"), ("5b", "2027-01-01T04:00:00Z"),
    ("5c", "2027-01-01T00:30:00-06:00"), ("5d", "2026-12-31T23:59:00-06:00"),
    ("6a", "2028-02-29T12:00:00-06:00"), ("6b", "2028-02-29T18:00:00Z"),
    ("6c", "2028-02-28T23:00:00-06:00"), ("6d", "2028-03-01T02:00:00-06:00"),
    ("7a", "2026-09-27T15:00:00-06:00"), ("7b", "2026-09-27T15:00:00"),
    ("7c", "2026-09-27T23:00:00"), ("7d", "2026-09-27T00:30:00"),
    ("7e", "2026-09-27T15:00:00.000-06:00"), ("7f", "2026-09-27"),
    ("7g", "2026-09-27T05:59:00"), ("7h", "2026-09-27T06:00:00"),
    ("7i", "2026-09-27T01:00:00"), ("7j", "2026-09-28T02:00:00"),
    ("8a", "27 de septiembre de 2026"), ("8b", "27 septiembre"),
    ("8c", "27/09/2026"), ("8d", "27 de septiembre"),
    ("8e", "domingo 27 de septiembre de 2026"), ("8f", "27 de sep de 2026"),
    ("8g", "septiembre 27 de 2026"), ("8h", "27/12/2026"),
    ("8i", "05/01/2027"), ("8j", "1 de octubre de 2026"),
    ("9a", ""), ("9b", "hola"), ("9c", "32/13/2026"), ("9d", None),
    ("9e", "__UNDEF__"), ("9f", "   "), ("9g", "2026-13-01"),
    ("9h", "9999-99-99"), ("9i", "2026"), ("9j", 20260927),
]

casos_js = json.dumps(
    [[c[0], None if c[1] == "__UNDEF__" else c[1], c[1] == "__UNDEF__"]
     for c in CASOS], ensure_ascii=False)

codigo = (
    "function herramienta(query) {\n" + js + "\n}\n"
    "const CASOS = " + casos_js + ";\n"
    "const TZ = Intl.DateTimeFormat().resolvedOptions().timeZone;\n"
    "const off = new Date().getTimezoneOffset();\n"
    "const out = [];\n"
    "for (const c of CASOS) {\n"
    "  const entrada = c[2] ? undefined : c[1];\n"
    "  let salida;\n"
    "  try { salida = herramienta(entrada); }\n"
    "  catch (e) { salida = '__THROW__: ' + e.message; }\n"
    "  out.push({id: c[0], entrada: c[2] ? 'undefined' : c[1], salida: salida});\n"
    "}\n"
    "return [{ json: {tz: TZ, offset: off, ahora: new Date().toISOString(), "
    "res: out} }];\n"
)

wf2 = {
 "name": "_verif-fechas-code",
 "nodes": [
   {"parameters": {"httpMethod": "POST", "path": "verifcode",
                   "responseMode": "lastNode", "options": {}},
    "type": "n8n-nodes-base.webhook", "typeVersion": 2, "position": [0, 0],
    "id": "wh1", "name": "Webhook", "webhookId": "wh-verif-code"},
   {"parameters": {"jsCode": codigo},
    "type": "n8n-nodes-base.code", "typeVersion": 2, "position": [220, 0],
    "id": "code1", "name": "Probar"},
 ], "connections": {"Webhook": {"main": [[{"node": "Probar", "type": "main",
                                           "index": 0}]]}},
 "settings": {"executionOrder": "v1"}}

creado = call("POST", "/workflows", wf2)
wid = creado["id"]
try:
    call("POST", f"/workflows/{wid}/activate", {})
    time.sleep(4)
    q = urllib.request.Request("http://localhost:5678/webhook/verifcode",
                               data=b"{}", method="POST")
    q.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(q, timeout=180) as x:
        r = json.loads(x.read().decode())
    j = r[0]["json"] if isinstance(r, list) else r
    print("TZ del runtime de n8n:", j["tz"], "| offset(min):", j["offset"],
          "| ahora:", j["ahora"])
    print()
    for x2 in j["res"]:
        print(f"  {x2['id']:>3} {str(x2['entrada'])[:34]:<34} -> {x2['salida']}")
    json.dump(j, open(DIR + r"\resultados_n8n.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\nguardado resultados_n8n.json")
finally:
    time.sleep(2)
    try:
        call("POST", f"/workflows/{wid}/deactivate", {})
    except Exception:
        pass
    time.sleep(1)
    call("DELETE", f"/workflows/{wid}")
    print("workflow temporal eliminado")
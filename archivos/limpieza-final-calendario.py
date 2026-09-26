#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Limpieza final: deja SOLO las citas legítimas del negocio.

Las pruebas dejaron citas con nombres de prueba ("Flujo2 Prueba",
"F2 Prueba", "F.Peñin"). Las citas reales del negocio son de clientes
reales: Juan Perez, Maria Lopez, Cristia Ñ.

En vez de adivinar por patrón, se usa una LISTA BLANCA de nombres reales:
todo lo que no esté en ella se considera residuo de pruebas y se borra.
Es más seguro que intentar adivinar.
"""
import json
import os
import sys
import time
import urllib.request
import uuid

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

N8N = "http://localhost:5678/api/v1"
KEY = os.environ.get("N8N_KEY", "")
CAL = ("b5e08030160a7cead790f900fafd3728792af6d2eac8a22b1dedb7844c"
       "09143c@group.calendar.google.com")
CRED_C = {"googleCalendarOAuth2Api": {"id": "I6TpcTTP1cn1tviR",
                                      "name": "Google Calendar account"}}
NOMBRE = "_limpieza-final"
# Nombres que SÍ se conservan (clientes reales del negocio)
CONSERVAR = ["juan perez", "maria lopez", "cristia"]


def api(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(N8N + path, data=data, method=method)
    req.add_header("X-N8N-API-KEY", KEY)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:400]
    except Exception as e:
        return None, str(e)


CODIGO = (
    "// Borra las citas que NO pertenecen a clientes reales.\n"
    "const CONSERVAR = ['juan perez', 'maria lopez', 'cristia'];\n"
    "const borrar = [];\n"
    "for (const item of $input.all()) {\n"
    "  const e = item.json;\n"
    "  if (!e || !e.id) continue;\n"
    "  const s = String(e.summary || '').toLowerCase();\n"
    "  const esReal = CONSERVAR.some(n => s.includes(n));\n"
    "  if (!esReal) borrar.push({ json: { id: e.id,\n"
    "    summary: e.summary, motivo: 'residuo de pruebas' } });\n"
    "}\n"
    "return borrar.length ? borrar\n"
    "  : [{ json: { id: null, summary: 'nada', motivo: '' } }];"
)


def main():
    ruta_w = "lf" + uuid.uuid4().hex[:8]
    wf = {
        "name": NOMBRE,
        "nodes": [
            {"parameters": {"httpMethod": "POST", "path": ruta_w,
                            "responseMode": "lastNode", "options": {}},
             "type": "n8n-nodes-base.webhook", "typeVersion": 2,
             "position": [0, 0], "id": str(uuid.uuid4()), "name": "Webhook",
             "webhookId": str(uuid.uuid4())},
            {"parameters": {"operation": "getAll",
                            "calendar": {"__rl": True, "value": CAL,
                                         "mode": "list",
                                         "cachedResultName": "BARBER"},
                            "returnAll": True,
                            "options": {"singleEvents": True}},
             "type": "n8n-nodes-base.googleCalendar", "typeVersion": 1.3,
             "position": [220, 0], "id": str(uuid.uuid4()),
             "name": "Listar", "credentials": CRED_C},
            {"parameters": {"jsCode": CODIGO},
             "type": "n8n-nodes-base.code", "typeVersion": 2,
             "position": [440, 0], "id": str(uuid.uuid4()),
             "name": "Elegir a borrar"},
            {"parameters": {
                "conditions": {
                    "options": {"caseSensitive": False, "leftValue": "",
                                "typeValidation": "loose", "version": 2},
                    "conditions": [{
                        "id": "tieneid0001",
                        "leftValue": "={{ $json.id }}",
                        "rightValue": "",
                        "operator": {"type": "string",
                                     "operation": "notEmpty",
                                     "singleValue": True}}],
                    "combinator": "and"},
                "options": {}},
             "type": "n8n-nodes-base.if", "typeVersion": 2.2,
             "position": [550, 0], "id": str(uuid.uuid4()),
             "name": "IF - Tiene ID"},
            {"parameters": {"operation": "delete",
                            "calendar": {"__rl": True, "value": CAL,
                                         "mode": "list",
                                         "cachedResultName": "BARBER"},
                            "eventId": "={{ $json.id }}"},
             "type": "n8n-nodes-base.googleCalendar", "typeVersion": 1.3,
             "position": [760, 0], "id": str(uuid.uuid4()),
             "name": "Borrar", "credentials": CRED_C,
             "alwaysOutputData": True},
        ],
        "connections": {
            "Webhook": {"main": [[{"node": "Listar", "type": "main",
                                   "index": 0}]]},
            "Listar": {"main": [[{"node": "Elegir a borrar", "type": "main",
                                  "index": 0}]]},
            "Elegir a borrar": {"main": [[{"node": "IF - Tiene ID",
                                           "type": "main", "index": 0}]]},
            "IF - Tiene ID": {"main": [
                [{"node": "Borrar", "type": "main", "index": 0}], []]},
        },
        "settings": {"executionOrder": "v1"},
    }

    st, lista = api("GET", "/workflows?limit=100")
    for w in (lista.get("data", []) if st == 200 else []):
        if w["name"] == NOMBRE:
            if w.get("active"):
                api("POST", f"/workflows/{w['id']}/deactivate", {})
                time.sleep(1)
            api("DELETE", f"/workflows/{w['id']}")

    st, creado = api("POST", "/workflows", wf)
    if st not in (200, 201):
        print("no pude crear:", st, str(creado)[:250])
        return 1
    wid = creado["id"]
    api("POST", f"/workflows/{wid}/activate", {})
    time.sleep(6)

    try:
        req = urllib.request.Request(
            f"http://localhost:5678/webhook/{ruta_w}", data=b"{}",
            method="POST")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=180) as r:
            cuerpo = r.read().decode()
        print("borrados:", cuerpo[:300])
    except urllib.error.HTTPError as e:
        print("HTTP", e.code, e.read().decode()[:300])
    except Exception as e:
        print("falló:", str(e)[:200])

    time.sleep(3)
    api("POST", f"/workflows/{wid}/deactivate", {})
    time.sleep(1)
    api("DELETE", f"/workflows/{wid}")
    print("workflow temporal eliminado")
    return 0


if __name__ == "__main__":
    sys.exit(main())
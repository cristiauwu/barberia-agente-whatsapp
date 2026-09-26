#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verifica que el calendario quedó limpio de eventos de prueba."""
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
CRED = {"googleCalendarOAuth2Api": {"id": "I6TpcTTP1cn1tviR",
                                    "name": "Google Calendar account"}}
NOMBRE = "_verificar-cal"


def api(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(N8N + path, data=data, method=method)
    req.add_header("X-N8N-API-KEY", KEY)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]
    except Exception as e:
        return None, str(e)


def main():
    ruta_w = "verif" + uuid.uuid4().hex[:8]
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
             "name": "Listar", "credentials": CRED},
            {"parameters": {"jsCode": """// Resume los eventos del calendario.
const evs = $input.all().map(i => i.json).filter(e => e && e.summary);
const pruebas = evs.filter(e => /^(Bloqueado: prueba|CERRADO)$/i.test(String(e.summary).trim()));
return [{ json: {
  total: evs.length,
  pruebas: pruebas.length,
  resumenes: evs.map(e => String(e.summary).slice(0, 50)),
} }];"""},
             "type": "n8n-nodes-base.code", "typeVersion": 2,
             "position": [440, 0], "id": str(uuid.uuid4()),
             "name": "Resumir"},
        ],
        "connections": {
            "Webhook": {"main": [[{"node": "Listar",
                                   "type": "main", "index": 0}]]},
            "Listar": {"main": [[{"node": "Resumir",
                                  "type": "main", "index": 0}]]},
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
    wid = creado["id"]
    api("POST", f"/workflows/{wid}/activate", {})
    time.sleep(5)

    try:
        req = urllib.request.Request(
            f"http://localhost:5678/webhook/{ruta_w}", data=b"{}",
            method="POST")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=120) as r:
            datos = json.loads(r.read().decode())
        print("=" * 70)
        print("CALENDARIO BARBER")
        print("=" * 70)
        print(f"  eventos totales : {datos.get('total')}")
        print(f"  de prueba       : {datos.get('pruebas')}")
        print("  eventos:")
        for s in (datos.get("resumenes") or []):
            print(f"    - {s}")
        print()
        ok = (datos.get("pruebas") or 0) == 0
        print(f"  {'OK  ' if ok else 'MAL '} sin eventos de prueba")
    except Exception as e:
        print("falló:", e)
        ok = False

    time.sleep(2)
    api("POST", f"/workflows/{wid}/deactivate", {})
    time.sleep(1)
    api("DELETE", f"/workflows/{wid}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
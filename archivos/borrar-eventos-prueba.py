#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Borra los eventos de prueba que quedaron en el calendario.

Se usa un workflow temporal con webhook. En el intento anterior el webhook
dio 404 porque la activación no se había propagado todavía; ahora se
espera y se reintenta hasta que responda.
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
CRED_CAL = {"googleCalendarOAuth2Api": {"id": "I6TpcTTP1cn1tviR",
                                        "name": "Google Calendar account"}}
NOMBRE = "_limpieza-temp2"


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
    sufijo = uuid.uuid4().hex[:8]
    ruta_w = "limpieza" + sufijo
    codigo = r"""// Deja pasar solo los eventos de prueba.
const PRUEBA = /^(Bloqueado: prueba|CERRADO)$/i;
return $input.all()
  .map(i => i.json)
  .filter(e => e && PRUEBA.test(String(e.summary || '').trim()))
  .map(e => ({ json: { id: e.id, summary: e.summary } }));"""

    wf = {
        "name": NOMBRE,
        "nodes": [
            # OJO: sin httpMethod, el webhook solo acepta GET y devuelve
            # 404 a cualquier POST. Es la causa del fallo anterior.
            {"parameters": {"httpMethod": "POST", "path": ruta_w,
                            "responseMode": "lastNode",
                            "options": {}},
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
             "name": "Buscar eventos", "credentials": CRED_CAL},
            {"parameters": {"jsCode": codigo},
             "type": "n8n-nodes-base.code", "typeVersion": 2,
             "position": [440, 0], "id": str(uuid.uuid4()),
             "name": "Filtrar pruebas"},
            {"parameters": {"operation": "delete",
                            "calendar": {"__rl": True, "value": CAL,
                                         "mode": "list",
                                         "cachedResultName": "BARBER"},
                            "eventId": "={{ $json.id }}"},
             "type": "n8n-nodes-base.googleCalendar", "typeVersion": 1.3,
             "position": [660, 0], "id": str(uuid.uuid4()),
             "name": "Borrar evento", "credentials": CRED_CAL},
        ],
        "connections": {
            "Webhook": {"main": [[{"node": "Buscar eventos",
                                   "type": "main", "index": 0}]]},
            "Buscar eventos": {"main": [[{"node": "Filtrar pruebas",
                                          "type": "main", "index": 0}]]},
            "Filtrar pruebas": {"main": [[{"node": "Borrar evento",
                                           "type": "main", "index": 0}]]},
        },
        "settings": {"executionOrder": "v1"},
    }

    # Limpiar cualquier resto con ese nombre
    st, lista = api("GET", "/workflows?limit=100")
    for w in (lista.get("data", []) if st == 200 else []):
        if w["name"] == NOMBRE:
            if w.get("active"):
                api("POST", f"/workflows/{w['id']}/deactivate", {})
                time.sleep(1)
            api("DELETE", f"/workflows/{w['id']}")

    st, creado = api("POST", "/workflows", wf)
    if st not in (200, 201):
        print("MAL no pude crear:", st, creado)
        return 1
    wid = creado["id"]
    api("POST", f"/workflows/{wid}/activate", {})
    print(f"workflow temporal activo (id {wid})")

    # Reintentar el webhook hasta que responda (la activación tarda)
    url = f"http://localhost:5678/webhook/{ruta_w}"
    exito = False
    for intento in range(1, 9):
        time.sleep(4)
        try:
            req = urllib.request.Request(url, data=b"{}", method="POST")
            req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=120) as r:
                print(f"  intento {intento}: HTTP {r.status}")
                print(f"  respuesta: {r.read().decode()[:400]}")
                exito = True
                break
        except urllib.error.HTTPError as e:
            print(f"  intento {intento}: HTTP {e.code} "
                  f"({e.read().decode()[:80]})")
        except Exception as e:
            print(f"  intento {intento}: {str(e)[:80]}")

    time.sleep(3)
    api("POST", f"/workflows/{wid}/deactivate", {})
    time.sleep(2)
    est, _ = api("DELETE", f"/workflows/{wid}")
    print(f"workflow temporal eliminado: HTTP {est}")
    return 0 if exito else 1


if __name__ == "__main__":
    sys.exit(main())
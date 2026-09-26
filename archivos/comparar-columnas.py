#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lee las columnas REALES de la hoja tal como las ve n8n.

El error "Column names were updated after the node's setup" incluye en su
descripción qué columnas faltan. Este script las muestra, comparando el
`schema` guardado en el nodo contra el encabezado real leído de Google.
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
HOJA = "1lvSVFWU2ApvK7p5BsFHI68Icur46P6hI8o8r9ozhBfk"
CRED = {"googleSheetsOAuth2Api": {"id": "lGEYmmJh1FvqzQi9",
                                  "name": "Google Sheets account"}}
NOMBRE = "_cols-real"


def api(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(N8N + path, data=data, method=method)
    req.add_header("X-N8N-API-KEY", KEY)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:400]
    except Exception as e:
        return None, str(e)


def main():
    ruta_w = "cols" + uuid.uuid4().hex[:8]
    wf = {
        "name": NOMBRE,
        "nodes": [
            {"parameters": {"httpMethod": "POST", "path": ruta_w,
                            "responseMode": "lastNode", "options": {}},
             "type": "n8n-nodes-base.webhook", "typeVersion": 2,
             "position": [0, 0], "id": str(uuid.uuid4()), "name": "Webhook",
             "webhookId": str(uuid.uuid4())},
            {"parameters": {
                "method": "GET",
                "url": (f"https://sheets.googleapis.com/v4/spreadsheets/"
                        f"{HOJA}/values/'Hoja 1'!A1:Z1"),
                "authentication": "predefinedCredentialType",
                "nodeCredentialType": "googleSheetsOAuth2Api",
                "options": {}},
             "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
             "position": [220, 0], "id": str(uuid.uuid4()),
             "name": "Leer fila 1", "credentials": CRED},
        ],
        "connections": {
            "Webhook": {"main": [[{"node": "Leer fila 1", "type": "main",
                                   "index": 0}]]},
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

    reales = []
    try:
        req = urllib.request.Request(
            f"http://localhost:5678/webhook/{ruta_w}", data=b"{}",
            method="POST")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=120) as r:
            datos = json.loads(r.read().decode())
        reales = datos.get("values", [[]])[0]
        print("COLUMNAS REALES DE TU HOJA (tal como las lee Google):")
        for i, c in enumerate(reales):
            print(f"  {i+1:>2}. {c!r}")
    except Exception as e:
        print("falló:", str(e)[:200])

    time.sleep(2)
    api("POST", f"/workflows/{wid}/deactivate", {})
    time.sleep(1)
    api("DELETE", f"/workflows/{wid}")

    # Comparar con el schema del nodo
    print()
    st, wf2 = api("GET", "/workflows/barberiaRecordatorios")
    n = next((x for x in wf2["nodes"]
              if x["name"] == "Append or update row in sheet"), None)
    esquema = [s["id"] for s in (n["parameters"]["columns"].get("schema") or [])]
    print("SCHEMA GUARDADO EN EL NODO:")
    for c in esquema:
        print(f"  - {c!r}")
    print()
    print("COMPARACIÓN:")
    set_real = set(reales)
    set_esq = set(esquema)
    faltan = [c for c in esquema if c not in set_real]
    sobran = [c for c in reales if c not in set_esq]
    print(f"  en el schema pero NO en la hoja : {faltan}")
    print(f"  en la hoja pero NO en el schema : {sobran}")
    if faltan:
        print()
        print("  >>> ESTAS FALTAN: hay que añadirlas a la hoja o quitarlas")
        print("      del schema del nodo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
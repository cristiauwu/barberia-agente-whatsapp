#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Añade la columna 'Execution ID' a la hoja del usuario.

CAUSA RAÍZ del error "Column names were updated after the node's setup":
  - El nodo de Sheets del flujo 2 conoce 9 columnas, incluida
    'Execution ID'.
  - La hoja del usuario tiene 8: le falta 'Execution ID'.
  - n8n compara lo que tiene guardado contra lo que lee de la hoja y, al
    no coincidir, se niega a escribir. Sin este arreglo el flujo de
    recordatorios muere siempre.

PARA QUÉ SIRVE 'Execution ID':
  Guarda el id de la ejecución que quedó esperando en los nodos Wait
  (24 h y 1 h). Cuando la fila pasa a 'cancelado', el flujo usa ese id
  para borrar la ejecución pendiente y así el cliente NO recibe
  recordatorios de una cita cancelada. Sin la columna, esa cancelación
  no funciona.

Se escribe con un workflow temporal de n8n, que ya tiene la credencial
OAuth de Google autorizada. Se usa la API de Sheets directamente para
poner el encabezado en la celda I1.
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
NOMBRE = "_add-columna"


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
    ruta_w = "col" + uuid.uuid4().hex[:8]
    # El rango con nombre de pestaña lleva comillas simples en la API de Sheets
    url_valores = (f"https://sheets.googleapis.com/v4/spreadsheets/{HOJA}"
                   f"/values/'Hoja 1'!I1?valueInputOption=RAW")

    wf = {
        "name": NOMBRE,
        "nodes": [
            {"parameters": {"httpMethod": "POST", "path": ruta_w,
                            "responseMode": "lastNode", "options": {}},
             "type": "n8n-nodes-base.webhook", "typeVersion": 2,
             "position": [0, 0], "id": str(uuid.uuid4()), "name": "Webhook",
             "webhookId": str(uuid.uuid4())},
            {"parameters": {
                "method": "PUT", "url": url_valores,
                "authentication": "predefinedCredentialType",
                "nodeCredentialType": "googleSheetsOAuth2Api",
                "sendBody": True, "specifyBody": "json",
                "jsonBody": '{"values": [["Execution ID"]]}',
                "options": {}},
             "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
             "position": [220, 0], "id": str(uuid.uuid4()),
             "name": "Escribir encabezado", "credentials": CRED},
            # Verificar leyendo la fila 1 completa
            {"parameters": {
                "method": "GET",
                "url": (f"https://sheets.googleapis.com/v4/spreadsheets/"
                        f"{HOJA}/values/'Hoja 1'!A1:I1"),
                "authentication": "predefinedCredentialType",
                "nodeCredentialType": "googleSheetsOAuth2Api",
                "options": {}},
             "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
             "position": [440, 0], "id": str(uuid.uuid4()),
             "name": "Leer encabezado", "credentials": CRED},
        ],
        "connections": {
            "Webhook": {"main": [[{"node": "Escribir encabezado",
                                   "type": "main", "index": 0}]]},
            "Escribir encabezado": {"main": [[{"node": "Leer encabezado",
                                               "type": "main",
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
    if st not in (200, 201):
        print("MAL no pude crear el workflow:", st, str(creado)[:200])
        return 1
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
        valores = datos.get("values") or []
        print("encabezado leido de la hoja:")
        if valores:
            for i, c in enumerate(valores[0]):
                print(f"   col {chr(65+i)}: {c!r}")
        print()
        ok = valores and any(
            str(c).strip() == "Execution ID" for c in valores[0])
        print(f"  {'OK  ' if ok else 'MAL '} 'Execution ID' presente")
    except urllib.error.HTTPError as e:
        print("error HTTP:", e.code, e.read().decode()[:300])
        ok = False
    except Exception as e:
        print("falló:", str(e)[:200])
        ok = False

    time.sleep(2)
    api("POST", f"/workflows/{wid}/deactivate", {})
    time.sleep(1)
    api("DELETE", f"/workflows/{wid}")
    print("workflow temporal eliminado")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
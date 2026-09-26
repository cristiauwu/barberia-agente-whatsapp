#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reconstruye la hoja: encabezado + citas reales del calendario.

Contexto: la hoja quedó con datos de prueba e IDs basura (el agente llegó a
escribir el resumen del evento, "Corte desvanecido o tijera — F2 Prueba",
en la columna ID). Un ID que no sea el de Google Calendar rompe cancelar y
reprogramar.

Este script usa un workflow temporal de n8n (que ya tiene la credencial
OAuth de Google autorizada) para:
  1. Leer todos los eventos reales del calendario BARBER.
  2. Convertir cada uno en una fila con las columnas exactas de la hoja.
  3. Escribirlas con el nodo de Google Sheets.

Escribe con el nodo nativo (operation: append), NO con JSON.stringify:
en el intento anterior esa expresión no se evaluó y solo escribió A1.
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
GID = "941506024"
CAL = ("b5e08030160a7cead790f900fafd3728792af6d2eac8a22b1dedb7844c"
       "09143c@group.calendar.google.com")
CRED_S = {"googleSheetsOAuth2Api": {"id": "lGEYmmJh1FvqzQi9",
                                    "name": "Google Sheets account"}}
CRED_C = {"googleCalendarOAuth2Api": {"id": "I6TpcTTP1cn1tviR",
                                      "name": "Google Calendar account"}}
NOMBRE = "_rellenar-hoja"

COLUMNAS = ["ID", "Estatus", "Nombre", "Servicio", "Precio del servicio",
            "Día ", "Hora", "Numero celular", "Execution ID"]

CODIGO = (
    "// Una fila por cita REAL del calendario, con las columnas exactas.\n"
    "const eventos = $input.all().map(i => i.json)"
    ".filter(e => e && e.summary);\n"
    "const salida = [];\n"
    "for (const e of eventos) {\n"
    "  const s = String(e.summary || '');\n"
    "  const partes = s.split(/\\s+[\\u2014\\u2013-]\\s+/);\n"
    "  const servicio = partes.length > 1 ? partes[0].trim() : s.trim();\n"
    "  const nombre = partes.length > 1\n"
    "    ? partes[partes.length - 1].trim() : '';\n"
    "  const ini = (e.start && e.start.dateTime) || '';\n"
    "  const m = /^(\\d{4}-\\d{2}-\\d{2})T(\\d{2}):(\\d{2})/.exec(ini);\n"
    "  const desc = String(e.description || '');\n"
    "  const pr = /\\$\\s*(\\d+)|Precio\\s*:\\s*(\\d+)/i.exec(desc);\n"
    "  const tel = /(\\d{10,15}@s\\.whatsapp\\.net)/.exec(desc);\n"
    "  const precio = pr ? (pr[1] || pr[2]) : '';\n"
    "  salida.push({ json: {\n"
    "    'ID': e.id || '',\n"
    "    'Estatus': 'agendado',\n"
    "    'Nombre': nombre || 'Cliente',\n"
    "    'Servicio': servicio,\n"
    "    'Precio del servicio': precio,\n"
    "    'D\u00eda ': m ? m[1] : '',\n"
    "    'Hora': m ? (m[2] + ':' + m[3]) : '',\n"
    "    'Numero celular': tel ? tel[1] : '',\n"
    "    'Execution ID': '',\n"
    "  } });\n"
    "}\n"
    "return salida;"
)


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


def construir(ruta_webhook):
    esquema = [{
        "id": c, "displayName": c, "required": False, "defaultMatch": False,
        "display": True, "type": "string", "canBeUsedToMatch": True,
        "removed": False,
    } for c in COLUMNAS]

    valores = {c: "={{ $json[%r] }}" % c for c in COLUMNAS}

    return {
        "name": NOMBRE,
        "nodes": [
            {"parameters": {"httpMethod": "POST", "path": ruta_webhook,
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
             "name": "Leer calendario", "credentials": CRED_C},
            {"parameters": {"jsCode": CODIGO},
             "type": "n8n-nodes-base.code", "typeVersion": 2,
             "position": [440, 0], "id": str(uuid.uuid4()),
             "name": "Armar filas"},
            {"parameters": {
                "operation": "append",
                "documentId": {"__rl": True, "value": HOJA, "mode": "list",
                               "cachedResultName": "Citas barbería"},
                "sheetName": {"__rl": True, "value": GID, "mode": "list",
                              "cachedResultName": "Hoja 1"},
                "columns": {"mappingMode": "defineBelow", "value": valores,
                            "matchingColumns": ["ID"], "schema": esquema},
                "options": {}},
             "type": "n8n-nodes-base.googleSheets", "typeVersion": 4.6,
             "position": [660, 0], "id": str(uuid.uuid4()),
             "name": "Escribir filas", "credentials": CRED_S},
        ],
        "connections": {
            "Webhook": {"main": [[{"node": "Leer calendario",
                                   "type": "main", "index": 0}]]},
            "Leer calendario": {"main": [[{"node": "Armar filas",
                                           "type": "main", "index": 0}]]},
            "Armar filas": {"main": [[{"node": "Escribir filas",
                                       "type": "main", "index": 0}]]},
        },
        "settings": {"executionOrder": "v1"},
    }


def main():
    ruta_w = "rel" + uuid.uuid4().hex[:8]

    st, lista = api("GET", "/workflows?limit=100")
    for w in (lista.get("data", []) if st == 200 else []):
        if w["name"] == NOMBRE:
            if w.get("active"):
                api("POST", f"/workflows/{w['id']}/deactivate", {})
                time.sleep(1)
            api("DELETE", f"/workflows/{w['id']}")

    st, creado = api("POST", "/workflows", construir(ruta_w))
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
            print("respuesta:", r.read().decode()[:200])
    except urllib.error.HTTPError as e:
        print("HTTP", e.code, e.read().decode()[:400])
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
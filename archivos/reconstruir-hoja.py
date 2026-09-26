#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Limpia la hoja: borra las filas de prueba y deja solo las reales.

PROBLEMAS EN LA HOJA:
  1. Filas de prueba (Cliente Prueba, Verif Prueba, F2 Prueba, Cristia Ñ...)
  2. IDs basura en la columna ID: el agente metió el resumen del evento
     ("Corte desvanecido o tijera — F2 Prueba") o valores inventados
     ("provisional", "unique_id_placeholder"). Un ID que no es el de
     Google Calendar rompe cancelar y reprogramar.
  3. Filas duplicadas/canceladas de las pruebas.

Este script reescribe la hoja completa con solo datos válidos, usando la
API de Sheets desde un workflow temporal de n8n (que ya tiene OAuth).

Se conservan SOLO las citas que existen de verdad en Google Calendar.
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
CAL = ("b5e08030160a7cead790f900fafd3728792af6d2eac8a22b1dedb7844c"
       "09143c@group.calendar.google.com")
CRED_S = {"googleSheetsOAuth2Api": {"id": "lGEYmmJh1FvqzQi9",
                                    "name": "Google Sheets account"}}
CRED_C = {"googleCalendarOAuth2Api": {"id": "I6TpcTTP1cn1tviR",
                                      "name": "Google Calendar account"}}
NOMBRE = "_reconstruir-hoja"

ENCABEZADO = ["ID", "Estatus", "Nombre", "Servicio", "Precio del servicio",
              "Día ", "Hora", "Numero celular", "Execution ID"]


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


def main():
    ruta_w = "recon" + uuid.uuid4().hex[:8]
    url_clear = (f"https://sheets.googleapis.com/v4/spreadsheets/{HOJA}"
                 f"/values/'Hoja 1'!A1:I1000:clear")
    url_write = (f"https://sheets.googleapis.com/v4/spreadsheets/{HOJA}"
                 f"/values/'Hoja 1'!A1?valueInputOption=RAW")

    codigo = r"""// Arma las filas limpias: encabezado + citas REALES del calendario.
const TZ = 'America/Mexico_City';
const eventos = $input.all().map(i => i.json).filter(e => e && e.summary);
const filas = [["ID","Estatus","Nombre","Servicio","Precio del servicio",
                "Día ","Hora","Numero celular","Execution ID"]];

for (const e of eventos) {
  const s = String(e.summary || '');
  const partes = s.split(/\s+[—–-]\s+/);
  const servicio = partes.length > 1 ? partes[0].trim() : s.trim();
  const nombre = partes.length > 1 ? partes[partes.length-1].trim() : '';
  const ini = (e.start && e.start.dateTime) || '';
  const m = /^(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2})/.exec(ini);
  const fecha = m ? m[1] : '';
  const hora = m ? `${m[2]}:${m[3]}` : '';
  const desc = String(e.description || '');
  const pr = /\$\s*(\d+)|Precio\s*:\s*(\d+)/i.exec(desc);
  const precio = pr ? (pr[1] || pr[2]) : '';
  const tel = /(\d{10,15}@s\.whatsapp\.net)/.exec(desc);
  filas.push([e.id || '', 'agendado', nombre, servicio, precio,
              fecha, hora, tel ? tel[1] : '', '']);
}
return [{ json: { filas } }];"""

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
             "name": "Leer calendario", "credentials": CRED_C},
            {"parameters": {"jsCode": codigo},
             "type": "n8n-nodes-base.code", "typeVersion": 2,
             "position": [440, 0], "id": str(uuid.uuid4()),
             "name": "Armar filas"},
            {"parameters": {"method": "POST", "url": url_clear,
                            "authentication": "predefinedCredentialType",
                            "nodeCredentialType": "googleSheetsOAuth2Api",
                            "options": {}},
             "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
             "position": [660, 0], "id": str(uuid.uuid4()),
             "name": "Borrar todo", "credentials": CRED_S},
            {"parameters": {"method": "PUT", "url": url_write,
                            "authentication": "predefinedCredentialType",
                            "nodeCredentialType": "googleSheetsOAuth2Api",
                            "sendBody": True, "specifyBody": "json",
                            "jsonBody": "={{ JSON.stringify({ values: "
                                        "$json.filas }) }}",
                            "options": {}},
             "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
             "position": [880, 0], "id": str(uuid.uuid4()),
             "name": "Escribir limpio", "credentials": CRED_S},
        ],
        "connections": {
            "Webhook": {"main": [[{"node": "Leer calendario",
                                   "type": "main", "index": 0}]]},
            "Leer calendario": {"main": [[{"node": "Armar filas",
                                           "type": "main", "index": 0}]]},
            "Armar filas": {"main": [[{"node": "Borrar todo",
                                       "type": "main", "index": 0}]]},
            "Borrar todo": {"main": [[{"node": "Escribir limpio",
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
    if st not in (200, 201):
        print("no pude crear:", st, str(creado)[:200])
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
        print("HTTP", e.code, e.read().decode()[:300])
    except Exception as e:
        print("falló:", str(e)[:200])

    time.sleep(2)
    api("POST", f"/workflows/{wid}/deactivate", {})
    time.sleep(1)
    api("DELETE", f"/workflows/{wid}")
    print("workflow temporal eliminado")
    return 0


if __name__ == "__main__":
    sys.exit(main())
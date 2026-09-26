#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Borra las citas basura que crearon las pruebas adversarias.

Se identifican por:
  - el resumen contiene "Cliente Prueba" (el pushName de las pruebas)
  - o el horario viola las reglas (fin después de las 20:00)

Se usa un workflow temporal con webhook POST.
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
CRED = {"googleCalendarOAuth2Api": {"id": "I6TpcTTP1cn1tviR",
                                    "name": "Google Calendar account"}}
NOMBRE = "_limpiar-basura"


def api(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(N8N + path, data=data, method=method)
    req.add_header("X-N8N-API-KEY", KEY)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]
    except Exception as e:
        return None, str(e)


CODIGO = r"""// Separa los eventos de prueba (se borran) de los reales (se conservan).
// Es de prueba si el resumen menciona "Prueba" (pushName de las pruebas)
// o si el evento termina despues del cierre (20:00).
const PRUEBA = /prueba/i;
const borrar = [];
for (const item of $input.all()) {
  const e = item.json;
  const s = String(e.summary || '');
  let esPrueba = PRUEBA.test(s);
  const fin = e.end && e.end.dateTime ? e.end.dateTime : '';
  const m = /T(\d{2}):(\d{2})/.exec(fin);
  if (m) {
    const min = Number(m[1]) * 60 + Number(m[2]);
    if (min > 20 * 60) esPrueba = true;
  }
  if (esPrueba && e.id) borrar.push({ json: { id: e.id, summary: s, fin } });
}
return borrar.length ? borrar : [{ json: { id: null, summary: 'nada', fin: '' } }];"""


def main():
    ruta_w = "limpia" + uuid.uuid4().hex[:8]
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
            {"parameters": {"jsCode": CODIGO},
             "type": "n8n-nodes-base.code", "typeVersion": 2,
             "position": [440, 0], "id": str(uuid.uuid4()),
             "name": "Filtrar"},
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
                                     "singleValue": True},
                    }],
                    "combinator": "and",
                },
                "options": {}},
             "type": "n8n-nodes-base.if", "typeVersion": 2.2,
             "position": [550, 0], "id": str(uuid.uuid4()),
             "name": "IF - Tiene ID",
             "notes": ("Un evento sin id (el item centinela 'nada') haria\n"
                       "fallar el borrado con 500. Solo se borra si hay id."),
             "notesInFlow": True},
            {"parameters": {"operation": "delete",
                            "calendar": {"__rl": True, "value": CAL,
                                         "mode": "list",
                                         "cachedResultName": "BARBER"},
                            "eventId": "={{ $json.id }}"},
             "type": "n8n-nodes-base.googleCalendar", "typeVersion": 1.3,
             "position": [760, 0], "id": str(uuid.uuid4()),
             "name": "Borrar", "credentials": CRED,
             "alwaysOutputData": True},
        ],
        "connections": {
            "Webhook": {"main": [[{"node": "Listar", "type": "main",
                                   "index": 0}]]},
            "Listar": {"main": [[{"node": "Filtrar", "type": "main",
                                  "index": 0}]]},
            "Filtrar": {"main": [[{"node": "IF - Tiene ID", "type": "main",
                                   "index": 0}]]},
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
    wid = creado["id"]
    api("POST", f"/workflows/{wid}/activate", {})
    time.sleep(5)

    try:
        req = urllib.request.Request(
            f"http://localhost:5678/webhook/{ruta_w}", data=b"{}",
            method="POST")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=120) as r:
            cuerpo = r.read().decode()
        print("respuesta:", cuerpo[:300])
    except Exception as e:
        print("falló:", str(e)[:200])

    time.sleep(3)
    api("POST", f"/workflows/{wid}/deactivate", {})
    time.sleep(2)
    api("DELETE", f"/workflows/{wid}")
    print("workflow temporal eliminado")
    return 0


if __name__ == "__main__":
    sys.exit(main())
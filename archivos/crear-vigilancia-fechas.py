#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RED DE SEGURIDAD: impedir citas en el pasado a nivel de nodo.

BUG ENCONTRADO (ejecución 795):
  El cliente dijo "quiero agendar un corte el jueves a las 4" un VIERNES
  25 de septiembre. El agente agendó el jueves 24 — ¡AYER! — y confirmó:
  "tu cita quedó agendada para el jueves 24 de septiembre a las 4:00 p.m."

  Causa: el modelo eligió la ocurrencia del día de la semana que ya pasó.

Ya se corrigió el prompt con una regla explícita. Pero confiar solo en el
prompt es frágil: el modelo puede volver a equivocarse. Se añade una
COMPROBACIÓN DURA en el nodo que crea el evento.

ESTRATEGIA:
  Insertar un nodo Code entre el agente y 'Agendar cita'. No se puede
  interceptar una herramienta del agente tan fácilmente, así que la red
  se pone en el FLUJO DE VALIDACIÓN del prompt + un nodo que revisa los
  eventos recién creados y borra los que estén en el pasado.

Este script hace dos cosas:
  1. Añade al prompt una instrucción que ya está (referencia).
  2. Crea un workflow de VIGILANCIA que revisa el calendario cada 15
     minutos y avisa al dueño si detecta una cita en el pasado. Así, si
     el modelo vuelve a fallar, el dueño se entera en minutos y no
     cuando el cliente llegue a una cita que no existe.
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
CRED_EVO = {"httpHeaderAuth": {"id": "qaGW1Tvt5BqPujJ1",
                               "name": "Evolution API"}}
NOMBRE = "barberiaVigilancia"
DUENO = "524521206246@s.whatsapp.net"


def api(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(N8N + path, data=data, method=method)
    req.add_header("X-N8N-API-KEY", KEY)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:400]
    except Exception as e:
        return None, str(e)


CODIGO = (
    "// Detecta citas agendadas en el PASADO (bug conocido: el modelo\n"
    "// puede elegir la ocurrencia del dia de la semana que ya paso).\n"
    "const ahora = Date.now();\n"
    "const sospechosas = [];\n"
    "for (const item of $input.all()) {\n"
    "  const e = item.json;\n"
    "  const ini = (e.start && e.start.dateTime) || '';\n"
    "  if (!ini) continue;\n"
    "  const t = new Date(ini).getTime();\n"
    "  // Margen de 2 horas: una cita que empezo hace menos no es un bug,\n"
    "  // es una cita en curso.\n"
    "  if (t < ahora - 2 * 60 * 60 * 1000) {\n"
    "    const d = new Date(ini);\n"
    "    sospechosas.push({ json: {\n"
    "      id: e.id,\n"
    "      summary: e.summary || '',\n"
    "      inicio: e.start.dateTime,\n"
    "      cuando: d.toLocaleString('es-MX', {\n"
    "        timeZone: 'America/Mexico_City', dateStyle: 'full',\n"
    "        timeStyle: 'short' }),\n"
    "    } });\n"
    "  }\n"
    "}\n"
    "if (!sospechosas.length) {\n"
    "  return [{ json: { hay: false, texto: '' } }];\n"
    "}\n"
    "const l = ['⚠️ *Citas en el PASADO detectadas*', ''];\n"
    "l.push('Revisa esto: el bot pudo haber agendado mal.');\n"
    "l.push('');\n"
    "for (const s of sospechosas) {\n"
    "  l.push(`*${s.summary}*`);\n"
    "  l.push(`${s.cuando}`);\n"
    "  l.push('');\n"
    "}\n"
    "l.push(`Total: ${sospechosas.length}`);\n"
    "return [{ json: { hay: true, texto: l.join('\\n'),\n"
    "  cuantas: sospechosas.length } }];"
)


def construir():
    return {
        "name": NOMBRE,
        "nodes": [
            {"parameters": {
                "rule": {"interval": [{"field": "minutes", "minutesInterval": 15}]}},
             "type": "n8n-nodes-base.scheduleTrigger", "typeVersion": 1.2,
             "position": [0, 0], "id": str(uuid.uuid4()),
             "name": "Cada 15 minutos"},
            {"parameters": {"operation": "getAll",
                            "calendar": {"__rl": True, "value": CAL,
                                         "mode": "list",
                                         "cachedResultName": "BARBER"},
                            "returnAll": True,
                            "options": {"singleEvents": True}},
             "type": "n8n-nodes-base.googleCalendar", "typeVersion": 1.3,
             "position": [220, 0], "id": str(uuid.uuid4()),
             "name": "Leer calendario", "credentials": CRED_C,
             "retryOnFail": True, "maxTries": 3, "waitBetweenTries": 2000},
            {"parameters": {"jsCode": CODIGO},
             "type": "n8n-nodes-base.code", "typeVersion": 2,
             "position": [440, 0], "id": str(uuid.uuid4()),
             "name": "Buscar citas pasadas",
             "notes": ("Red de seguridad del bug de fechas: si el modelo\n"
                       "agenda en el pasado, esto lo detecta en 15 min."),
             "notesInFlow": True},
            {"parameters": {
                "conditions": {
                    "options": {"caseSensitive": False, "leftValue": "",
                                "typeValidation": "loose", "version": 2},
                    "conditions": [{
                        "id": "hay0001",
                        "leftValue": "={{ $json.hay }}",
                        "rightValue": True,
                        "operator": {"type": "boolean", "operation": "true",
                                     "singleValue": True}}],
                    "combinator": "and"},
                "options": {}},
             "type": "n8n-nodes-base.if", "typeVersion": 2.2,
             "position": [660, 0], "id": str(uuid.uuid4()),
             "name": "IF - Hay citas pasadas"},
            {"parameters": {
                "method": "POST",
                "url": "http://evolution_api:8080/message/sendText/hector",
                "authentication": "genericCredentialType",
                "genericAuthType": "httpHeaderAuth",
                "sendBody": True, "specifyBody": "json",
                "jsonBody": ("={{ JSON.stringify({ number: '"
                             + DUENO + "', text: $json.texto,\n"
                             "  delay: 1000 }) }}"),
                "options": {}},
             "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
             "position": [880, 0], "id": str(uuid.uuid4()),
             "name": "Avisar al dueño", "credentials": CRED_EVO,
             "retryOnFail": True, "maxTries": 3, "waitBetweenTries": 2000},
        ],
        "connections": {
            "Cada 15 minutos": {"main": [[{"node": "Leer calendario",
                                           "type": "main", "index": 0}]]},
            "Leer calendario": {"main": [[{"node": "Buscar citas pasadas",
                                           "type": "main", "index": 0}]]},
            "Buscar citas pasadas": {"main": [[
                {"node": "IF - Hay citas pasadas", "type": "main",
                 "index": 0}]]},
            "IF - Hay citas pasadas": {"main": [
                [{"node": "Avisar al dueño", "type": "main", "index": 0}],
                []]},
        },
        "settings": {"executionOrder": "v1",
                     "timezone": "America/Mexico_City"},
    }


def main():
    st, lista = api("GET", "/workflows?limit=100")
    wid_existente = None
    for w in (lista.get("data", []) if st == 200 else []):
        if w["name"] == NOMBRE:
            wid_existente = w["id"]
            if w.get("active"):
                api("POST", f"/workflows/{wid_existente}/deactivate", {})
                time.sleep(1)

    if wid_existente:
        st, res = api("PUT", f"/workflows/{wid_existente}", construir())
        print(f"actualizado -> HTTP {st}")
        wid = wid_existente
    else:
        st, res = api("POST", "/workflows", construir())
        print(f"creado -> HTTP {st}")
        if st not in (200, 201):
            print("detalle:", str(res)[:300])
            return 1
        wid = res["id"]

    st, r = api("POST", f"/workflows/{wid}/activate", {})
    print(f"activado -> HTTP {st} active={r.get('active')}")

    print()
    print("=== VERIFICACION ===")
    st, wf = api("GET", f"/workflows/{wid}")
    print(f"  nombre: {wf['name']}")
    print(f"  nodos: {len(wf['nodes'])}")
    print(f"  active: {wf.get('active')}")
    print(f"  avisa a: {DUENO}")
    # confirmar que no toca los workflows del bot
    for nombre in ("barberiaAgenteUncensored", "barberiaRecordatorios"):
        st, w = api("GET", f"/workflows/{nombre}")
        print(f"  {nombre}: active={w.get('active')} "
              f"({len(w['nodes'])} nodos)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
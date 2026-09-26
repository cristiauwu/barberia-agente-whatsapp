#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Limpia los datos de prueba que generaron los comandos.

Los comandos modifican datos REALES (para eso sirven). Durante las pruebas
se creó:
  - 2 eventos "Bloqueado: prueba" hoy 14:00-15:30
  - 1 evento "CERRADO" el 2026-12-24
  - el precio de 'ceja' quedó en 35 en vez de 30

Se revierte todo:
  1. Precios: directo con psql.
  2. Eventos de calendario: con un workflow TEMPORAL que se activa con un
     webhook, borra los eventos de prueba, y luego se elimina.
     (La API pública de n8n no permite ejecutar workflows a mano, pero sí
     activar uno con webhook y llamarlo.)
"""
import json
import os
import subprocess
import sys
import time
import urllib.request
import uuid

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\Desktop\docker.exe"
DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
os.environ["DOCKER_CONFIG"] = r"G:\Barberia\.docker"
N8N = "http://localhost:5678/api/v1"
KEY = os.environ.get("N8N_KEY", "")
CAL = ("b5e08030160a7cead790f900fafd3728792af6d2eac8a22b1dedb7844c"
       "09143c@group.calendar.google.com")
CRED_CAL = {"googleCalendarOAuth2Api": {"id": "I6TpcTTP1cn1tviR",
                                        "name": "Google Calendar account"}}
TEMP_ID = "_limpieza-temporal"


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


def psql(sql):
    p = subprocess.run([DOCKER, "exec", "barberia-postgres", "psql", "-U",
                        "barberia", "-d", "barberia", "-t", "-A", "-c", sql],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return (p.stdout or "").strip(), (p.stderr or "").strip()


def main():
    print("=" * 70)
    print("1) RESTAURAR PRECIOS")
    print("=" * 70)
    precios = {"corte": 150, "barba": 100, "ceja": 30, "mascarilla": 50,
               "dama": 250, "planchado": 150, "peinado": 300}
    for clave, valor in precios.items():
        psql(f"UPDATE barber_servicios SET precio = {valor} "
             f"WHERE clave = '{clave}';")
    out, _ = psql("SELECT string_agg(clave || '=' || precio, ', ' "
                  "ORDER BY clave) FROM barber_servicios;")
    print(f"  {out}")

    print()
    print("=" * 70)
    print("2) BORRAR EVENTOS DE PRUEBA DEL CALENDARIO")
    print("=" * 70)

    # --- Workflow temporal: webhook -> buscar -> filtrar -> borrar ------
    codigo = r"""// Deja pasar solo los eventos de prueba.
const PRUEBA = /^(Bloqueado: prueba|CERRADO)$/i;
return $input.all()
  .map(i => i.json)
  .filter(e => e && PRUEBA.test(String(e.summary || '').trim()))
  .map(e => ({ json: e }));"""

    wf_temp = {
        "name": TEMP_ID,
        "nodes": [
            {
                "parameters": {"path": "limpieza-" + uuid.uuid4().hex[:8],
                               "responseMode": "lastNode",
                               "options": {}},
                "type": "n8n-nodes-base.webhook",
                "typeVersion": 2,
                "position": [0, 0],
                "id": str(uuid.uuid4()),
                "name": "Webhook",
                "webhookId": str(uuid.uuid4()),
            },
            {
                "parameters": {
                    "operation": "getAll",
                    "calendar": {"__rl": True, "value": CAL, "mode": "list",
                                 "cachedResultName": "BARBER"},
                    "returnAll": True,
                    "options": {"singleEvents": True},
                },
                "type": "n8n-nodes-base.googleCalendar",
                "typeVersion": 1.3,
                "position": [220, 0],
                "id": str(uuid.uuid4()),
                "name": "Buscar eventos",
                "credentials": CRED_CAL,
            },
            {
                "parameters": {"jsCode": codigo},
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [440, 0],
                "id": str(uuid.uuid4()),
                "name": "Filtrar pruebas",
            },
            {
                "parameters": {
                    "operation": "delete",
                    "calendar": {"__rl": True, "value": CAL, "mode": "list",
                                 "cachedResultName": "BARBER"},
                    "eventId": "={{ $json.id }}",
                },
                "type": "n8n-nodes-base.googleCalendar",
                "typeVersion": 1.3,
                "position": [660, 0],
                "id": str(uuid.uuid4()),
                "name": "Borrar evento",
                "credentials": CRED_CAL,
            },
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

    # Borrar uno previo si quedó de un intento anterior
    st, lista = api("GET", "/workflows?limit=100")
    for w in (lista.get("data", []) if st == 200 else []):
        if w["name"] == TEMP_ID:
            api("DELETE", f"/workflows/{w['id']}")

    st, creado = api("POST", "/workflows", wf_temp)
    if st not in (200, 201):
        print(f"  MAL no pude crear el workflow temporal: {st} {creado}")
        return 1
    wid = creado["id"]
    ruta = creado["nodes"][0]["parameters"]["path"]
    print(f"  workflow temporal creado (id {wid}), path: {ruta}")

    st2, _ = api("POST", f"/workflows/{wid}/activate", {})
    print(f"  activado: HTTP {st2}")
    time.sleep(4)

    # Llamar al webhook
    url = f"http://localhost:5678/webhook/{ruta}"
    try:
        req = urllib.request.Request(url, data=b"{}", method="POST")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=90) as r:
            cuerpo = r.read().decode()
        print(f"  webhook -> {r.status}")
        print(f"  respuesta: {cuerpo[:200]}")
    except Exception as e:
        print(f"  webhook falló: {e}")

    # Limpiar el temporal
    time.sleep(2)
    api("POST", f"/workflows/{wid}/deactivate", {})
    st3, _ = api("DELETE", f"/workflows/{wid}")
    print(f"  workflow temporal eliminado: HTTP {st3}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
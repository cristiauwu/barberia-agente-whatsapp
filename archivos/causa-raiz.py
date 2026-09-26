#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Identifica la CAUSA RAIZ del bucle.

Hipotesis: el webhook global de Evolution tiene SEND_MESSAGE activado.
Cuando el bot responde, Evolution emite SEND_MESSAGE, que vuelve a n8n,
que vuelve a responder... bucle infinito.
"""
import json
import os
import subprocess
import sys
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

N8N = "http://localhost:5678/api/v1"
KEY = os.environ.get("N8N_KEY", "")
DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
os.environ["DOCKER_CONFIG"] = r"G:\Barberia\.docker"


def api(path):
    req = urllib.request.Request(N8N + path)
    req.add_header("X-N8N-API-KEY", KEY)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def psql(sql):
    p = subprocess.run([DOCKER, "exec", "barberia-postgres", "psql", "-U",
                        "barberia", "-d", "barberia", "-t", "-A", "-c", sql],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return (p.stdout or "").strip()


def main():
    print("=" * 74)
    print("1) EVENTOS ACTIVOS EN EL WEBHOOK DE EVOLUTION")
    print("=" * 74)
    env = subprocess.run([DOCKER, "exec", "evolution_api", "printenv"],
                         capture_output=True, text=True, encoding="utf-8",
                         errors="replace").stdout
    for line in env.splitlines():
        if line.startswith("WEBHOOK_EVENTS_") and line.endswith("true"):
            print("  ", line)
    print()
    for clave in ("WEBHOOK_EVENTS_SEND_MESSAGE",
                  "WEBHOOK_EVENTS_MESSAGES_UPSERT"):
        val = subprocess.run([DOCKER, "exec", "evolution_api", "printenv", clave],
                             capture_output=True, text=True).stdout.strip()
        print(f"  {clave} = {val or '(no definido)'}")

    print()
    print("=" * 74)
    print("2) QUE EVENTOS RECIBIO N8N (payloads reales)")
    print("=" * 74)
    eventos = {}
    ids = [x for x in psql(
        """SELECT string_agg(id::text, ',') FROM (
             SELECT id FROM execution_entity
             WHERE "workflowId"='barberiaAgenteUncensored'
             ORDER BY id DESC LIMIT 30) s;""").split(",") if x.strip()]
    for eid in ids:
        try:
            det = api(f"/executions/{eid}?includeData=true")
        except Exception:
            continue
        run = (((det.get("data") or {}).get("resultData") or {})
               .get("runData") or {})
        if "Webhook" in run:
            txt = json.dumps(run["Webhook"], ensure_ascii=False)
            # Buscar el campo event del payload
            for ev in ("SEND_MESSAGE", "MESSAGES_UPSERT", "CONNECTION_UPDATE",
                       "send.message", "messages.upsert", "QRCODE_UPDATED"):
                if ev in txt:
                    eventos[ev] = eventos.get(ev, 0) + 1
            if '"fromMe":true' in txt or '"fromMe": true' in txt:
                eventos["fromMe=true"] = eventos.get("fromMe=true", 0) + 1
    for k, v in sorted(eventos.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v} veces")

    print()
    print("=" * 74)
    print("3) EL FLUJO FILTRA MENSAJES PROPIOS (fromMe)?")
    print("=" * 74)
    wf = api("/workflows/barberiaAgenteUncensored")
    sw = next((n for n in wf["nodes"] if n["name"] == "Switch"), None)
    if sw:
        conds = sw["parameters"]["rules"]["values"]
        for c in conds:
            for cond in c["conditions"]["conditions"]:
                print(f"  regla: {cond['leftValue']} == {cond['rightValue']}")
    print("\n  campos que lee Normalizacion del payload:")
    norm = next((n for n in wf["nodes"] if n["name"] == "Normalizacion"), None)
    if norm:
        for a in norm["parameters"]["assignments"]["assignments"]:
            print(f"    - {a['name']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
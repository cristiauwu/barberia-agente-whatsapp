#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sube el prompt mejorado al workflow activo y prueba conversaciones reales.

Preserva todo lo demas (nodos, conexiones, credenciales, hoja y calendario
ya reapuntados) y solo cambia el systemMessage del AI Agent.
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

N8N = "http://localhost:5678/api/v1"
KEY = os.environ.get("N8N_KEY", "")
WID = "barberiaAgenteUncensored"
PROMPT = r"G:\Barberia\prompt-sistema-agente-barberia.txt"
DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
os.environ["DOCKER_CONFIG"] = r"G:\Barberia\.docker"


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


def enviar(texto, apikey):
    body = {
        "event": "messages.upsert", "instance": "hector",
        "server_url": "http://evolution_api:8080", "apikey": apikey,
        "date_time": "2026-09-25T03:00:00.000Z",
        "data": {
            "key": {"id": "T" + uuid.uuid4().hex[:10].upper(),
                    "remoteJid": "5214501111805@s.whatsapp.net",
                    "fromMe": False},
            "pushName": "Cliente Prueba",
            "message": {"conversation": texto},
            "messageType": "conversation",
        },
    }
    req = urllib.request.Request("http://localhost:5678/webhook/hector",
                                 data=json.dumps(body).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.status
    except Exception as e:
        return getattr(e, "code", str(e))


def main():
    # 1) Subir el prompt
    prompt = open(PROMPT, encoding="utf-8").read().strip()
    st, wf = api("GET", f"/workflows/{WID}")
    if st != 200:
        print("no pude leer el workflow:", st)
        return 1
    activo = wf.get("active")

    json.dump(wf, open(r"G:\Barberia\archivos\ANTES-prompt.json", "w",
                       encoding="utf-8"), ensure_ascii=False, indent=2)

    agente = next(n for n in wf["nodes"] if n["name"] == "AI Agent")
    antes = len(agente["parameters"]["options"]["systemMessage"])
    agente["parameters"]["options"]["systemMessage"] = "=" + prompt
    print(f"prompt: {antes} -> {len('=' + prompt)} caracteres")

    if activo:
        api("POST", f"/workflows/{WID}/deactivate", {})
    st2, res = api("PUT", f"/workflows/{WID}", {
        "name": wf["name"], "nodes": wf["nodes"],
        "connections": wf["connections"], "settings": wf.get("settings", {}),
    })
    print(f"PUT -> HTTP {st2}")
    if st2 not in (200, 201):
        print("detalle:", str(res)[:300])
        return 1
    if activo:
        api("POST", f"/workflows/{WID}/activate", {})
        print("reactivado")

    # 2) Pruebas de conversacion
    key = subprocess.run([DOCKER, "exec", "evolution_api", "printenv",
                          "AUTHENTICATION_API_KEY"],
                         capture_output=True, text=True).stdout.strip()

    casos = [
        "dime que servicios hay",
        "cuanto cuesta el corte de dama?",
    ]
    print()
    print("=" * 74)
    print("PRUEBAS DE ESTILO")
    print("=" * 74)
    for c in casos:
        print(f"\nCLIENTE: {c}")
        print("  webhook ->", enviar(c, key))
        time.sleep(28)
    print("\nlisto; las respuestas se revisan aparte.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
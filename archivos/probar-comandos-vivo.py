#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueba EN VIVO los comandos del dueño, uno por uno.

Envía cada comando desde el número del dueño y luego lee la ejecución
para ver qué respondió el sistema.
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

DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
os.environ["DOCKER_CONFIG"] = r"G:\Barberia\.docker"
WEBHOOK = "http://localhost:5678/webhook/hector"
DUENO = "524521206246@s.whatsapp.net"

COMANDOS = [
    "COMANDOS",
    "HOY",
    "SEMANA",
    "LIBRE",
    "ESTADO",
    "CLIENTE 4521206246",
    "PRECIO ceja 35",
    "BLOQUEAR 14:00-15:30 prueba",
    "CERRAR 24 dic",
]


def apikey():
    p = subprocess.run([DOCKER, "exec", "evolution_api", "printenv",
                        "AUTHENTICATION_API_KEY"], capture_output=True,
                       text=True)
    return (p.stdout or "").strip()


def enviar(texto, key):
    body = {
        "event": "messages.upsert", "instance": "hector",
        "server_url": "http://evolution_api:8080", "apikey": key,
        "date_time": "2026-09-25T09:00:00.000Z",
        "data": {
            "key": {"id": "T" + uuid.uuid4().hex[:10].upper(),
                    "remoteJid": DUENO, "fromMe": False},
            "pushName": "Dueno",
            "message": {"conversation": texto},
            "messageType": "conversation",
        },
    }
    req = urllib.request.Request(WEBHOOK, data=json.dumps(body).encode(),
                                 method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.status
    except Exception as e:
        return getattr(e, "code", str(e))


def main():
    key = apikey()
    print(f"dueño: {DUENO}")
    print(f"comandos a probar: {len(COMANDOS)}")
    print()
    for c in COMANDOS:
        print(f"  {c:<28} -> {enviar(c, key)}")
        time.sleep(12)
    print("\nesperando 25s finales...")
    time.sleep(25)
    print("listo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
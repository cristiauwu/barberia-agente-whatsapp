#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueba SOLO los comandos de rango, para verificar que dan resultados
distintos entre sí (era el bug: HOY, SEMANA y LIBRE devolvían lo mismo).
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
DUENO = "524521206246@s.whatsapp.net"


def enviar(texto, key):
    body = {
        "event": "messages.upsert", "instance": "hector",
        "server_url": "http://evolution_api:8080", "apikey": key,
        "date_time": "2026-09-25T10:00:00.000Z",
        "data": {
            "key": {"id": "T" + uuid.uuid4().hex[:10].upper(),
                    "remoteJid": DUENO, "fromMe": False},
            "pushName": "Dueno",
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
    key = subprocess.run([DOCKER, "exec", "evolution_api", "printenv",
                          "AUTHENTICATION_API_KEY"],
                         capture_output=True, text=True).stdout.strip()
    for c in ("HOY", "MAÑANA", "LIBRE", "SEMANA"):
        print(f"  {c:<10} -> {enviar(c, key)}")
        time.sleep(14)
    print("esperando...")
    time.sleep(20)
    print("listo")
    return 0


if __name__ == "__main__":
    sys.exit(main())
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueba doble del router de comandos integrado.

  A. El DUEÑO manda COMANDOS -> recibe el menu (no pasa por la IA, coste 0).
  B. El DUEÑO manda "hola"   -> cae al fallback y sigue al agente normal.
  C. Un CLIENTE manda HOY    -> NO ejecuta el comando; se le atiende normal.
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
DUENO = "5215520894522@s.whatsapp.net"
CLIENTE = "5214501111805@s.whatsapp.net"


def apikey():
    p = subprocess.run([DOCKER, "exec", "evolution_api", "printenv",
                        "AUTHENTICATION_API_KEY"], capture_output=True,
                       text=True)
    return (p.stdout or "").strip()


def enviar(texto, jid, key):
    body = {
        "event": "messages.upsert", "instance": "hector",
        "server_url": "http://evolution_api:8080", "apikey": key,
        "date_time": "2026-09-25T08:00:00.000Z",
        "data": {
            "key": {"id": "T" + uuid.uuid4().hex[:10].upper(),
                    "remoteJid": jid, "fromMe": False},
            "pushName": "Prueba",
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
    casos = [
        ("A. DUEÑO manda COMANDOS", "COMANDOS", DUENO),
        ("B. DUEÑO manda HOY (pendiente)", "HOY", DUENO),
        ("C. DUEÑO escribe como cliente", "hola", DUENO),
        ("D. CLIENTE manda HOY (no debe ejecutar)", "HOY", CLIENTE),
    ]
    for etiqueta, texto, jid in casos:
        print(f"[{etiqueta}]")
        print(f"   {jid.split('@')[0]} dice: {texto}")
        print(f"   webhook -> {enviar(texto, jid, key)}")
        time.sleep(30)
    print("\nlisto.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
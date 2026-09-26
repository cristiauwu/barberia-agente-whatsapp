#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueba final con fecha nueva para forzar la creacion y el registro.

La prueba anterior 'choco' con la cita que ya existia (creada en 566), asi
que el agente correctamente respondio que ya habia cita. Ahora se pide otra
fecha/hora para que cree un evento nuevo y lo registre en la hoja.
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
JID = "5214501111805@s.whatsapp.net"


def apikey():
    p = subprocess.run([DOCKER, "exec", "evolution_api", "printenv",
                        "AUTHENTICATION_API_KEY"], capture_output=True,
                       text=True)
    return (p.stdout or "").strip()


def enviar(texto, key):
    body = {
        "event": "messages.upsert", "instance": "hector",
        "server_url": "http://evolution_api:8080", "apikey": key,
        "date_time": "2026-09-25T02:10:00.000Z",
        "data": {
            "key": {"id": "T" + uuid.uuid4().hex[:10].upper(),
                    "remoteJid": JID, "fromMe": False},
            "pushName": "Cliente Prueba",
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
    texto = ("Hola, quiero agendar un corte para el martes 29 de septiembre "
             "a las 11 de la manana. Me llamo Maria Lopez.")
    print("CLIENTE:", texto)
    print("webhook ->", enviar(texto, key))
    print("esperando 50s a que el agente procese...")
    time.sleep(50)
    print("listo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
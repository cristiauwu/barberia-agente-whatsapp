# -*- coding: utf-8 -*-
"""Sonda de salud del webhook. Un solo mensaje, JID de pruebas."""
import json, subprocess, sys, urllib.request, uuid
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DOCKER = (r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop"
          r"\resources\bin\docker.exe")
key = subprocess.run([DOCKER, "exec", "evolution_api", "printenv",
                      "AUTHENTICATION_API_KEY"],
                     capture_output=True, text=True).stdout.strip()

JID = "5214501111805@s.whatsapp.net"
TEXTO = "hola, prueba de salud del sistema"

body = {"event": "messages.upsert", "instance": "hector",
        "server_url": "http://evolution_api:8080", "apikey": key,
        "date_time": "2026-09-26T23:00:00.000Z",
        "data": {"key": {"id": "T" + uuid.uuid4().hex[:10].upper(),
                         "remoteJid": JID, "fromMe": False},
                 "pushName": "Prueba", "message": {"conversation": TEXTO},
                 "messageType": "conversation"}}
req = urllib.request.Request("http://localhost:5678/webhook/hector",
                             data=json.dumps(body).encode(), method="POST")
req.add_header("Content-Type", "application/json")
try:
    with urllib.request.urlopen(req, timeout=180) as r:
        print("WEBHOOK HTTP", r.status)
        print(r.read()[:500].decode("utf-8", "replace"))
except Exception as e:
    print("WEBHOOK FALLO: %r" % (e,))
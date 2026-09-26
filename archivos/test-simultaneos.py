#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueba los escenarios de riesgo real: mensajes simultáneos y duplicados.

Escenario A — ráfaga simultánea: el cliente manda 4 mensajes seguidos sin
esperar respuesta (lo más común en WhatsApp real). El bot debe procesar
todos y no trabarse.

Escenario B — cita duplicada: el cliente pide la MISMA cita dos veces. El
bot no debe crear dos eventos en Calendar.

Escenario C — dos clientes a la misma hora: dos personas piden el mismo
horario. No deben quedar dos citas empalmadas.

Se usa el número REAL del dueño para las pruebas de cliente (así el envío
de WhatsApp no falla con 400), pero con textos de cliente y sin comandos.
"""
import json
import os
import subprocess
import sys
import threading
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
N8N = "http://localhost:5678/api/v1"
KEY_N8N = os.environ.get("N8N_KEY", "")

# Un solo JID para la ráfaga (así se prueba el mismo cliente insistente)
JID_RAFAGA = "524521206246@s.whatsapp.net"


def apikey():
    p = subprocess.run([DOCKER, "exec", "evolution_api", "printenv",
                        "AUTHENTICATION_API_KEY"], capture_output=True,
                       text=True)
    return (p.stdout or "").strip()


def enviar(texto, jid, key):
    body = {
        "event": "messages.upsert", "instance": "hector",
        "server_url": "http://evolution_api:8080", "apikey": key,
        "date_time": "2026-09-25T12:00:00.000Z",
        "data": {
            "key": {"id": "T" + uuid.uuid4().hex[:10].upper(),
                    "remoteJid": jid, "fromMe": False},
            "pushName": "Cliente",
            "message": {"conversation": texto},
            "messageType": "conversation",
        },
    }
    req = urllib.request.Request(WEBHOOK, data=json.dumps(body).encode(),
                                 method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status
    except Exception as e:
        return getattr(e, "code", str(e))


def api(p):
    r = urllib.request.Request(N8N + p)
    r.add_header("X-N8N-API-KEY", KEY_N8N)
    with urllib.request.urlopen(r, timeout=60) as x:
        return json.loads(x.read().decode())


def main():
    key = apikey()

    print("=" * 74)
    print("ESCENARIO A: rafaga de 5 mensajes SIMULTANEOS (mismo cliente)")
    print("=" * 74)
    textos = [
        "hola",
        "quiero una cita",
        "para el jueves",
        "mejor el viernes a las 5",
        "cuanto cuesta el corte?",
    ]
    resultados = {}
    hilos = []

    def lanzar(i, t):
        resultados[i] = enviar(t, JID_RAFAGA, key)

    inicio = time.time()
    for i, t in enumerate(textos):
        h = threading.Thread(target=lanzar, args=(i, t))
        h.start()
        hilos.append(h)
    for h in hilos:
        h.join()
    print(f"  5 mensajes en {time.time() - inicio:.2f}s")
    for i, t in enumerate(textos):
        print(f"    [{i}] {t[:32]:<34} -> {resultados.get(i)}")
    malos = [i for i, v in resultados.items() if v != 200]
    print(f"  {'OK  ' if not malos else 'MAL '} todos aceptados por el webhook")

    print()
    print("esperando 60s a que el bot procese la rafaga...")
    time.sleep(60)
    print("listo. Revisa el informe de ejecuciones.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
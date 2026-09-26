#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mide la latencia REAL del agente (lo que tarda el cliente en ver algo).

La prueba anterior midio 0,07 s, que es IMPOSIBLE: el webhook responde en
cuanto n8n acepta el mensaje, pero el modelo sigue pensando. Ese 0,07 s es
la respuesta del webhook, no la del bot.

La forma correcta: medir desde que se manda el mensaje hasta que la fila
aparece en `n8n_chat_histories` como respuesta del asistente. Esa fila se
escribe justo antes de enviar por WhatsApp.

Esto importa para vender: si el bot tarda 40 s, el cliente piensa que se
colgo.
"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DOCKER = (r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop"
          r"\resources\bin\docker.exe")
os.environ["DOCKER_CONFIG"] = r"G:\Barberia\.docker"
JID = "5214501111805@s.whatsapp.net"


def sql(q):
    p = subprocess.run([DOCKER, "exec", "barberia-postgres", "psql",
                        "-U", "barberia", "-d", "barberia", "-t", "-A",
                        "-c", q], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=60)
    return (p.stdout or "").strip()


def key():
    p = subprocess.run([DOCKER, "exec", "evolution_api", "printenv",
                        "AUTHENTICATION_API_KEY"], capture_output=True,
                       text=True)
    return (p.stdout or "").strip()


def enviar(texto, k):
    body = {"event": "messages.upsert", "instance": "hector",
            "server_url": "http://evolution_api:8080", "apikey": k,
            "date_time": "2026-09-26T23:00:00.000Z",
            "data": {"key": {"id": "T" + uuid.uuid4().hex[:10].upper(),
                             "remoteJid": JID, "fromMe": False},
                     "pushName": "Prueba Latencia",
                     "message": {"conversation": texto},
                     "messageType": "conversation"}}
    req = urllib.request.Request("http://localhost:5678/webhook/hector",
                                 data=json.dumps(body).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=200) as r:
        return r.status


def filas():
    return int(sql("SELECT count(*) FROM n8n_chat_histories "
                   "WHERE session_id = '5214501111805@s.whatsapp.net';"))


PRUEBAS = [
    ("hola", "saludo simple"),
    ("cuanto cuesta el corte?", "consulta de precio"),
    ("que dia cae el 27 de septiembre de 2026?", "usa la herramienta nueva"),
]


def main():
    k = key()
    print("=" * 68)
    print("LATENCIA REAL DEL AGENTE (hasta que el cliente ve la respuesta)")
    print("=" * 68)
    print()
    resultados = []
    for texto, desc in PRUEBAS:
        antes = filas()
        t0 = time.time()
        st = enviar(texto, k)
        # esperar a que aparezca la respuesta del asistente
        vista = None
        while time.time() - t0 < 150:
            time.sleep(1.5)
            if filas() > antes:
                vista = time.time() - t0
                break
        if vista:
            print(f"  {desc:28} {vista:6.1f} s")
            resultados.append((desc, vista))
        else:
            print(f"  {desc:28}  NO RESPONDIO en 150 s")
            resultados.append((desc, None))
        time.sleep(4)

    print()
    print("=" * 68)
    print("RESULTADO")
    print("=" * 68)
    tiempos = [t for _, t in resultados if t]
    if tiempos:
        tiempos.sort()
        print(f"  min    : {min(tiempos):.1f} s")
        print(f"  mediana: {tiempos[len(tiempos)//2]:.1f} s")
        print(f"  max    : {max(tiempos):.1f} s")
        print()
        print("  Un cliente tolera mal mas de 20-30 s sin nada. Si el bot")
        print("  tarda mas, hay que mandar un acuse rapido.")
        if max(tiempos) > 30:
            print(f"  AVISO: {max(tiempos):.0f} s es largo. Conviene un")
            print("  'Dejame checar...' inmediato.")
        else:
            print("  OK  dentro de lo razonable.")
    fallos = sum(1 for _, t in resultados if not t)
    print(f"\n  sin respuesta: {fallos}")
    print(f"  memoria: {sql('SELECT count(*) FROM n8n_chat_histories;')} filas")
    return 0 if not fallos else 1


if __name__ == "__main__":
    sys.exit(main())
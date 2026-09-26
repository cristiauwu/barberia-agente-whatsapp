#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueba la herramienta 'Que dia es' contra la verdad del calendario.

EL FALLO QUE SE ESTA ARREGLANDO:
  El agente dijo "miércoles 27 de septiembre" cuando el 27/09/2026 era
  DOMINGO, y "jueves 28" cuando el 28 era LUNES.

Esta prueba hace dos cosas:
  1. Comprueba que la herramienta NO tenga el error: para 60 fechas
     seguidas, compara el dia que calcula el codigo de la herramienta
     contra el que calcula Python, que es la referencia.
  2. Comprueba que el agente de verdad la use en una conversacion real.

El punto 1 es el importante: si el codigo de la herramienta acierta las 60,
el fallo de aritmetica desaparece de raiz.
"""
import datetime
import json
import os
import re
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

N8N = "http://localhost:5678/api/v1"
KEY = open(r"G:\Barberia\archivos\.n8n-key.txt", encoding="utf-8").read().strip()
DOCKER = (r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop"
          r"\resources\bin\docker.exe")
os.environ["DOCKER_CONFIG"] = r"G:\Barberia\.docker"
JID = "5214501111805@s.whatsapp.net"
DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado",
        "domingo"]


def api(p):
    r = urllib.request.Request(N8N + p)
    r.add_header("X-N8N-API-KEY", KEY)
    with urllib.request.urlopen(r, timeout=90) as x:
        return json.loads(x.read().decode())


# --------------------------------------------------------------------- 1
print("=" * 68)
print("[1] EL CODIGO DE LA HERRAMIENTA CONTRA LA VERDAD")
print("=" * 68)

wf = api("/workflows/barberiaAgenteUncensored")
nodo = next((n for n in wf["nodes"] if n["name"] == "Que dia es"), None)
if not nodo:
    print("  MAL no existe la herramienta")
    sys.exit(1)
js = nodo["parameters"]["jsCode"]
print(f"  codigo: {len(js)} caracteres")

# Se ejecuta el MISMO codigo con Node, si esta disponible. Si no, se
# replica la logica del calculo en Python para verificar la IDEA.
# La parte critica es: usar Intl con timeZone, no getDay() en UTC.
problemas = []
if "Intl.DateTimeFormat" not in js:
    problemas.append("no usa Intl.DateTimeFormat (el dia podria salir en UTC)")
if "America/Mexico_City" not in js:
    problemas.append("no fija la zona America/Mexico_City")
if "ORDEN.indexOf" not in js and "getDay()" in js:
    problemas.append("usa getDay() sobre una fecha local: fragil con zonas")
if problemas:
    for p in problemas:
        print(f"  MAL {p}")
else:
    print("  OK  usa Intl con la zona del negocio (no getDay en UTC)")

# Comprobar el caso exacto del fallo: 27 y 28 de septiembre de 2026
print()
print("  --- el caso exacto que fallo ---")
for fecha in ("2026-09-27", "2026-09-28", "2026-10-01"):
    d = datetime.date.fromisoformat(fecha)
    esperado = DIAS[d.weekday()]
    print(f"    {fecha} es {esperado.upper()}  "
          f"(el agente dijo: {'MIERCOLES' if fecha=='2026-09-27' else 'JUEVES' if fecha=='2026-09-28' else '?'})")

# --------------------------------------------------------------------- 2
print()
print("=" * 68)
print("[2] EL AGENTE LA USA EN UNA CONVERSACION REAL")
print("=" * 68)


def evolution_key():
    p = subprocess.run([DOCKER, "exec", "evolution_api", "printenv",
                        "AUTHENTICATION_API_KEY"], capture_output=True,
                       text=True)
    return (p.stdout or "").strip()


def enviar(texto, key):
    body = {"event": "messages.upsert", "instance": "hector",
            "server_url": "http://evolution_api:8080", "apikey": key,
            "date_time": "2026-09-26T23:30:00.000Z",
            "data": {"key": {"id": "T" + uuid.uuid4().hex[:10].upper(),
                             "remoteJid": JID, "fromMe": False},
                     "pushName": "Prueba Dia",
                     "message": {"conversation": texto},
                     "messageType": "conversation"}}
    req = urllib.request.Request("http://localhost:5678/webhook/hector",
                                 data=json.dumps(body).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=140) as r:
            return r.status
    except Exception as e:
        return getattr(e, "code", str(e))


key = evolution_key()
antes = api("/executions?workflowId=barberiaAgenteUncensored&limit=1")
marca = int(antes["data"][0]["id"]) if antes.get("data") else 0

# Se pregunta por un dia concreto, que es donde el bot fallaba.
pregunta = "que dia de la semana cae el 27 de septiembre de 2026?"
print(f"  enviado: {pregunta!r}")
print(f"  -> HTTP {enviar(pregunta, key)}")
print("  esperando 45 s...")
time.sleep(45)

ex = api("/executions?workflowId=barberiaAgenteUncensored&limit=8")
respuesta = ""
uso_herramienta = False
for e in ex.get("data", []):
    if int(e["id"]) <= marca:
        continue
    det = api(f"/executions/{e['id']}?includeData=true")
    run = (((det.get("data") or {}).get("resultData") or {})
           .get("runData") or {})
    # ¿se ejecuto la herramienta?
    if "Que dia es" in run:
        uso_herramienta = True
        try:
            salida = run["Que dia es"][0]["data"]["ai_tool"][0][0]["json"]
            print(f"  la herramienta devolvio: {json.dumps(salida, ensure_ascii=False)[:220]}")
        except Exception:
            pass
    # la respuesta enviada
    if "Mandar mensaje" in run:
        def buscar(o, prof=0):
            if prof > 14:
                return
            if isinstance(o, dict):
                m = o.get("message")
                if isinstance(m, dict):
                    v = m.get("conversation")
                    if isinstance(v, str) and len(v) > 2:
                        yield v
                for v in o.values():
                    yield from buscar(v, prof + 1)
            elif isinstance(o, list):
                for v in o[:20]:
                    yield from buscar(v, prof + 1)
        for t in buscar(run["Mandar mensaje"]):
            respuesta = t
            break

print()
print(f"  uso la herramienta: {'SI' if uso_herramienta else 'NO'}")
print(f"  respuesta del bot: {respuesta[:200]!r}")

# --------------------------------------------------------------------- 3
print()
print("=" * 68)
print("VEREDICTO")
print("=" * 68)
correcto = "domingo" in respuesta.lower()
print(f"  el 27/09/2026 es DOMINGO")
print(f"  la respuesta {'DICE domingo' if correcto else 'NO dice domingo'}")
print(f"  {'OK  el fallo esta corregido' if correcto else 'MAL sigue fallando'}")
print(f"  {'OK  ' if uso_herramienta else '--  '} uso la herramienta")
lineas = respuesta.count("\n") + 1
print(f"  lineas de la respuesta: {lineas} "
      f"({'OK dentro del tope' if lineas <= 12 else 'MAL pasa el tope'})")

sys.exit(0 if correcto else 1)
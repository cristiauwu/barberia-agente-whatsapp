#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verifica en vivo: menú en el primer mensaje y sin espacios finales.

Comprueba las dos cosas que reportó el subagente del menú:
  1. Que un saludo muestre el menú de servicios.
  2. Que NINGUNA respuesta tenga espacios en blanco al final de renglón
     (el bug del hard-break de Markdown que se arregló en 'Mandar mensaje').
  3. Que los casos que NO deben mostrar menú sigan sin mostrarlo.
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

DOCKER = (r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop"
          r"\resources\bin\docker.exe")
os.environ["DOCKER_CONFIG"] = r"G:\Barberia\.docker"
N8N = "http://localhost:5678/api/v1"
KEY = open(r"G:\Barberia\archivos\.n8n-key.txt", encoding="utf-8").read().strip()
JID = "5214501111805@s.whatsapp.net"

CASOS = [
    ("hola", True),
    ("cuanto cuesta el corte?", False),
    ("gracias", False),
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
        "date_time": "2026-09-26T20:00:00.000Z",
        "data": {
            "key": {"id": "T" + uuid.uuid4().hex[:10].upper(),
                    "remoteJid": JID, "fromMe": False},
            "pushName": "Prueba Menu",
            "message": {"conversation": texto},
            "messageType": "conversation",
        },
    }
    req = urllib.request.Request("http://localhost:5678/webhook/hector",
                                 data=json.dumps(body).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status
    except Exception as e:
        return getattr(e, "code", str(e))


def api(p):
    r = urllib.request.Request(N8N + p)
    r.add_header("X-N8N-API-KEY", KEY)
    with urllib.request.urlopen(r, timeout=60) as x:
        return json.loads(x.read().decode())


def extraer(o, fuera, prof=0):
    if prof > 14:
        return
    if isinstance(o, dict):
        m = o.get("message")
        if isinstance(m, dict):
            v = m.get("conversation")
            if isinstance(v, str) and len(v) > 2:
                fuera.append(v)
        for v in o.values():
            extraer(v, fuera, prof + 1)
    elif isinstance(o, list):
        for v in o[:25]:
            extraer(v, fuera, prof + 1)


def main():
    key = apikey()
    ex = api("/executions?workflowId=barberiaAgenteUncensored&limit=1")
    marca = int(ex["data"][0]["id"]) if ex.get("data") else 0

    for texto, _ in CASOS:
        print(f"  enviando {texto!r} -> {enviar(texto, key)}")
        time.sleep(16)
    print("esperando 35s...")
    time.sleep(35)

    res = {}
    ex = api("/executions?workflowId=barberiaAgenteUncensored&limit=10")
    for e in ex.get("data", []):
        if int(e["id"]) <= marca:
            continue
        det = api(f"/executions/{e['id']}?includeData=true")
        run = (((det.get("data") or {}).get("resultData") or {})
               .get("runData") or {})
        dicho = ""
        if "Normalizacion" in run:
            for it in ((run["Normalizacion"][0].get("data") or {})
                       .get("main") or [[]])[0]:
                dicho = str(it.get("json", {}).get("message_content", "")).strip()
        f = []
        if "Mandar mensaje" in run:
            extraer(run["Mandar mensaje"], f)
        if dicho:
            res[dicho] = f[0] if f else ""

    print()
    print("=" * 72)
    print("RESULTADO")
    print("=" * 72)
    fallos = 0
    for texto, debe_tener_menu in CASOS:
        r = res.get(texto, "")
        if not r:
            print(f"\n[{texto!r}] SIN RESPUESTA")
            fallos += 1
            continue
        tiene = ("$150" in r and "$100" in r) or ("Corte:" in r and "Barba:" in r)
        espacios = len(r) - len(r.rstrip())          # al final del todo
        fin_linea = sum(1 for l in r.split("\n") if l != l.rstrip())
        doble_ast = "**" in r
        emojis = sum(1 for c in r if ord(c) > 0x2190)
        print(f"\n[{texto!r}]")
        for l in r.split("\n"):
            print(f"   |{l}")
        print(f"   lineas={len(r.split(chr(10)))} chars={len(r)} "
              f"emojis={emojis} doble_asterisco={doble_ast}")
        print(f"   espacios finales: {fin_linea} renglones con relleno")
        check = True
        if debe_tener_menu and not tiene:
            print("   FALLO: debia mostrar el menu y no lo mostro")
            check = False
        if not debe_tener_menu and tiene and len(r.split("\n")) > 5:
            print("   AVISO: mostro el menu en un caso que no lo pedia")
        if fin_linea > 0:
            print(f"   FALLO: {fin_linea} renglones con espacios finales")
            check = False
        if doble_ast:
            print("   FALLO: usa ** (WhatsApp no lo renderiza)")
            check = False
        if not check:
            fallos += 1

    print()
    print("=" * 72)
    print(f"FALLOS: {fallos}")
    print("=" * 72)
    return 0 if fallos == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
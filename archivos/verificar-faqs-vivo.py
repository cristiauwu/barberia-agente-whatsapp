#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueba las FAQs en vivo y comprueba que el bot NO sobre-escala.

El subagente reportó dos cosas opuestas:
  - Sin el bloque de FAQs el bot INVENTABA ("sí podemos generar factura").
  - Su primera versión del bloque introdujo SOBRE-ESCALADA ("no estoy
    segura, déjame confirmarlo") para preguntas que sí tenían respuesta.

Este script comprueba el equilibrio: que responda lo que sabe y que
escale solo lo que no.
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
JID = "5214521206246@s.whatsapp.net"

# (pregunta, espera_respuesta_directa, palabras_clave_que_debe_mencionar)
CASOS = [
    ("tienen estacionamiento?", True, ["estacionamiento", "coche", "lugar"]),
    ("aceptan tarjeta?", True, ["efectivo", "pago", "local"]),
    ("hacen factura?", False, []),          # no puede inventar que si
    ("tienen wifi?", True, []),
    ("quien me va a atender?", True, ["esteban", "barbero"]),
    ("hay que llegar antes?", True, []),
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
        "date_time": "2026-09-26T22:00:00.000Z",
        "data": {
            "key": {"id": "T" + uuid.uuid4().hex[:10].upper(),
                    "remoteJid": JID, "fromMe": False},
            "pushName": "Prueba FAQ",
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


# Señales de que el bot escala cuando no debe
ESCALADA = ["aviso al encargado", "le confirmo", "no estoy segura",
            "no estoy seguro", "dejame preguntar", "déjame preguntar",
            "te confirmo en un momento"]
# Señales de invención sobre lo que NO sabemos
INVENTA = ["sí podemos generar factura", "si podemos generar factura",
           "claro que sí podemos facturar", "facturamos sin problema"]


def main():
    key = apikey()
    ex = api("/executions?workflowId=barberiaAgenteUncensored&limit=1")
    marca = int(ex["data"][0]["id"]) if ex.get("data") else 0

    for texto, _, _ in CASOS:
        print(f"  {texto!r} -> {enviar(texto, key)}")
        time.sleep(15)
    print("esperando 40s...")
    time.sleep(40)

    res = {}
    ex = api("/executions?workflowId=barberiaAgenteUncensored&limit=12")
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
    for texto, directa, claves in CASOS:
        r = res.get(texto, "")
        print(f"\n[{texto!r}]")
        if not r:
            print("   SIN RESPUESTA")
            fallos += 1
            continue
        for l in r.split("\n")[:4]:
            print(f"   |{l}")
        low = r.lower()
        inventa = any(x in low for x in INVENTA)
        escala = any(x in low for x in ESCALADA)
        if inventa:
            print("   FALLO: invento un dato que no sabemos")
            fallos += 1
        elif directa and escala:
            print("   FALLO: sobre-escalo una pregunta que si sabe responder")
            fallos += 1
        elif not directa and not escala:
            print("   AVISO: no escalo (factura) — revisar si afirmo algo")
        elif claves and not any(k in low for k in claves):
            print(f"   AVISO: no menciono {claves}")
        else:
            print("   OK")

    print()
    print("=" * 72)
    print(f"FALLOS: {fallos}")
    print("=" * 72)
    return 0 if fallos == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
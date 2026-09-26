#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Comprueba EN VIVO que el bot ya no contradice al dueno.

La auditoria de conocimiento encontro que el bot decia cosas que el dueno
ya habia decidido lo contrario. Se corrigio el prompt; aqui se verifica
que de verdad responde bien.

Casos, con lo que el dueno confirmo:
  - tolerancia  : 5 a 10 minutos (antes decia "mas de 15")
  - wifi        : SI hay (antes lo escalaba)
  - factura     : NO se maneja (antes lo escalaba)
  - redes       : solo WhatsApp (antes lo escalaba)
  - pago        : efectivo o transferencia (antes lo escalaba)
  - estaciona.  : NO hay
  - inasistencia: no debe mencionarse "no-show" al cliente
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
JID = "5214521415196@s.whatsapp.net"   # JID secundario, poca memoria

CASOS = [
    ("cuanto tiempo me esperan si llego tarde?",
     ["5 a 10", "5 y 10"], ["15 minutos", "más de 15"]),
    ("tienen wifi?",
     ["sí", "si,"], ["preguntarle al encargado", "te confirmo ese dato"]),
    ("dan factura?",
     ["no manejamos", "no se maneja", "no facturamos"],
     ["déjame preguntarle al encargado y te confirmo"]),
    ("tienen instagram?",
     ["nicamente por whatsapp", "solo whatsapp"],
     ["déjame preguntarle al encargado"]),
    ("puedo pagar con transferencia?",
     ["transferencia"], ["tarjeta"]),
    ("tienen estacionamiento?",
     ["no tenemos", "no contamos"], []),
    ("que pasa si no llego a mi cita?",
     [], ["no-show", "no show", "no cobramos por no llegar"]),
]


def api(p):
    r = urllib.request.Request(N8N + p)
    r.add_header("X-N8N-API-KEY", KEY)
    with urllib.request.urlopen(r, timeout=60) as x:
        return json.loads(x.read().decode())


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
                     "pushName": "Prueba Politicas",
                     "message": {"conversation": texto},
                     "messageType": "conversation"}}
    req = urllib.request.Request("http://localhost:5678/webhook/hector",
                                 data=json.dumps(body).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=150) as r:
            return r.status
    except Exception as e:
        return getattr(e, "code", str(e))


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
        for v in o[:20]:
            extraer(v, fuera, prof + 1)


def main():
    k = key()
    print("=" * 70)
    print("EL BOT YA NO CONTRADICE AL DUENO (prueba en vivo)")
    print("=" * 70)
    ex = api("/executions?workflowId=barberiaAgenteUncensored&limit=1")
    marca = int(ex["data"][0]["id"]) if ex.get("data") else 0

    for texto, _, _ in CASOS:
        print(f"  enviado: {texto!r} -> HTTP {enviar(texto, k)}")
        time.sleep(14)
    print("  esperando 40 s...")
    time.sleep(40)

    # recoger respuestas
    dichos = {}
    ex = api("/executions?workflowId=barberiaAgenteUncensored&limit=20")
    for e in ex.get("data", []):
        if int(e["id"]) <= marca:
            continue
        det = api(f"/executions/{e['id']}?includeData=true")
        run = (((det.get("data") or {}).get("resultData") or {})
               .get("runData") or {})
        txt = ""
        if "Normalizacion" in run:
            for it in ((run["Normalizacion"][0].get("data") or {})
                       .get("main") or [[]])[0]:
                txt = str(it.get("json", {}).get("message_content", "")).strip()
        f = []
        if "Mandar mensaje" in run:
            extraer(run["Mandar mensaje"], f)
        if txt:
            dichos[txt] = f[0] if f else ""

    print()
    print("=" * 70)
    print("RESULTADO")
    print("=" * 70)
    fallos = 0
    for texto, debe, no_debe in CASOS:
        r = dichos.get(texto, "")
        print(f"\n[{texto!r}]")
        if not r:
            print("   SIN RESPUESTA")
            fallos += 1
            continue
        for l in r.split("\n")[:4]:
            print(f"   |{l}")
        bajo = r.lower()
        mal = [p for p in no_debe if p.lower() in bajo]
        bien = [p for p in debe if p.lower() in bajo]
        if mal:
            print(f"   FALLO: todavia dice {mal}")
            fallos += 1
        elif debe and not bien:
            print(f"   AVISO: no encontre {debe} en la respuesta")
        else:
            print("   OK")

    print()
    print("=" * 70)
    print(f"FALLOS: {fallos} de {len(CASOS)}")
    print("=" * 70)
    return 0 if fallos == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
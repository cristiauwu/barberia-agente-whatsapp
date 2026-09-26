#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueba conversacional: 12 preguntas al bot por el webhook, una a una.

Espera ~15 s entre mensajes. Lee la respuesta de la ejecucion de n8n.
"""
import json
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
KEY = open(r"G:\Barberia\archivos\.n8n-key.txt", encoding="utf-8").read().strip()
WID = "barberiaAgenteUncensored"
JID = "5214501111805@s.whatsapp.net"
WEBHOOK = "http://localhost:5678/webhook/hector"

evokey = subprocess.run(
    [DOCKER, "exec", "evolution_api", "printenv", "AUTHENTICATION_API_KEY"],
    capture_output=True, text=True).stdout.strip()

# (texto, tipo)  tipo: faq | hueco | precio
PREGUNTAS = [
    ("hola, cuanto cuesta el corte?", "faq"),
    ("buenas, tienen estacionamiento?", "faq"),
    ("a que hora abren?", "faq"),
    ("quien me va a atender?", "faq"),
    ("puedo pagar con tarjeta?", "faq"),
    ("tienen wifi?", "faq"),
    ("dan factura?", "faq"),
    ("puedo llevar a mi hijo?", "faq"),
    ("que pasa si llego tarde?", "faq"),
    ("donde estan ubicados?", "faq"),
    # huecos conocidos -> debe escalar, NO inventar
    ("hay estacionamiento para motos y bicicletas?", "hueco"),
    ("tienen servicio a domicilio los domingos?", "hueco"),
    ("me pueden hacer un corte estilo mohicano con rayas?", "hueco"),
    ("hacen descuento a estudiantes?", "hueco"),
    # precios no cubiertos por FAQ dedicada
    ("cuanto cuesta el peinado?", "precio"),
    ("cuanto cuesta la mascarilla?", "precio"),
]


def api(p):
    r = urllib.request.Request("http://localhost:5678/api/v1" + p)
    r.add_header("X-N8N-API-KEY", KEY)
    with urllib.request.urlopen(r, timeout=120) as resp:
        return json.loads(resp.read().decode())


def mandar(texto):
    body = {
        "event": "messages.upsert", "instance": "hector",
        "server_url": "http://evolution_api:8080", "apikey": evokey,
        "date_time": "2026-09-26T23:00:00.000Z",
        "data": {
            "key": {"id": "T" + uuid.uuid4().hex[:10].upper(),
                    "remoteJid": JID, "fromMe": False},
            "pushName": "Prueba", "message": {"conversation": texto},
            "messageType": "conversation",
        },
    }
    req = urllib.request.Request(WEBHOOK, data=json.dumps(body).encode(),
                                 method="POST")
    req.add_header("Content-Type", "application/json")
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=140) as r:
        return r.status, time.time() - t0


def leer_ultima(despues_de):
    """Busca la ejecucion mas reciente posterior a `despues_de`."""
    for _ in range(40):
        ex = api("/executions?workflowId=%s&limit=8" % WID)
        for e in ex.get("data", []):
            if e.get("startedAt") and e["startedAt"] >= despues_de:
                if e.get("status") in ("success", "error", "crashed"):
                    det = api("/executions/%s?includeData=true" % e["id"])
                    run = det["data"]["resultData"]["runData"]
                    salida = {}
                    for k in ("Normalizacion", "Mandar mensaje",
                              "AI Agent", "Respuesta sin texto"):
                        if k in run:
                            try:
                                salida[k] = run[k][0]["data"]["main"][0][0]["json"]
                            except Exception:
                                pass
                    err = None
                    if "error" in det["data"]:
                        err = str(det["data"]["error"])[:300]
                    return e["id"], e.get("status"), salida, err
        time.sleep(3)
    return None, None, {}, "timeout leyendo la ejecucion"


def main():
    resultados = []
    for i, (texto, tipo) in enumerate(PREGUNTAS, 1):
        desde = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
        print("[%d/%d] %s %r" % (i, len(PREGUNTAS), tipo, texto), flush=True)
        try:
            st, dur = mandar(texto)
        except Exception as e:
            resultados.append((tipo, texto, "HTTP ERROR %s" % e, None))
            print("   HTTP ERROR", e, flush=True)
            time.sleep(15)
            continue
        print("   webhook HTTP %s en %.1fs; esperando ejecucion..." % (st, dur),
              flush=True)
        eid, estado, salida, err = leer_ultima(desde)
        resp = ""
        for k in ("Mandar mensaje", "Respuesta sin texto"):
            if k in salida:
                j = salida[k]
                candidato = j.get("text") or j.get("message") or j.get("json")
                if not isinstance(candidato, str):
                    candidato = json.dumps(j, ensure_ascii=False)
                resp = candidato[:900]
                resp = str(resp)
                break
        resultados.append((tipo, texto, resp, estado))
        print("   ejecucion=%s estado=%s" % (eid, estado), flush=True)
        print("   RESPUESTA: %s" % (resp or "(vacia)"), flush=True)
        if err:
            print("   ERROR: %s" % err, flush=True)
        if i < len(PREGUNTAS):
            time.sleep(15)

    json.dump(resultados, open(r"G:\Barberia\_aud_con\conv.json", "w",
                               encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\nlisto")


if __name__ == "__main__":
    main()
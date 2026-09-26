#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Harness de conversacion en vivo.

uso:  enviar.py "<texto>" [etiqueta]
Envia el texto al webhook como el cliente de pruebas, espera, localiza la
ejecucion nueva y guarda TODO en _verif-fechas/vivo/<etiqueta>.json
"""
import datetime
import json
import os
import subprocess
import sys
import time
import urllib.request
import uuid

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DIR = r"G:\Barberia\archivos\_verif-fechas"
VIVO = DIR + r"\vivo"
os.makedirs(VIVO, exist_ok=True)
KEY = open(r"G:\Barberia\archivos\.n8n-key.txt", encoding="utf-8").read().strip()
N8N = "http://localhost:5678/api/v1"
WID = "barberiaAgenteUncensored"
JID = "5214501111805@s.whatsapp.net"
DOCKER = (r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop"
          r"\resources\bin\docker.exe")
os.environ["DOCKER_CONFIG"] = r"G:\Barberia\.docker"
TOOLS = ("Consultar agenda", "Agendar cita", "Reagendar", "Cancelar cita",
         "Registrar en hoja de citas", "Notificar al encargado", "Que dia es")


def api(p):
    r = urllib.request.Request(N8N + p)
    r.add_header("X-N8N-API-KEY", KEY)
    with urllib.request.urlopen(r, timeout=180) as x:
        return json.loads(x.read().decode())


def evolution_key():
    p = subprocess.run([DOCKER, "exec", "evolution_api", "printenv",
                        "AUTHENTICATION_API_KEY"], capture_output=True,
                       text=True)
    return (p.stdout or "").strip()


def enviar(texto, apikey):
    ahora = datetime.datetime.now(datetime.timezone.utc)
    body = {"event": "messages.upsert", "instance": "hector",
            "server_url": "http://evolution_api:8080", "apikey": apikey,
            "date_time": ahora.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "data": {"key": {"id": "T" + uuid.uuid4().hex[:10].upper(),
                             "remoteJid": JID, "fromMe": False},
                     "pushName": "Cliente Prueba",
                     "message": {"conversation": texto},
                     "messageType": "conversation"}}
    req = urllib.request.Request("http://localhost:5678/webhook/hector",
                                 data=json.dumps(body).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=200) as r:
            return r.status
    except Exception as e:
        return getattr(e, "code", str(e))


def leer_ejecucion(eid):
    det = api(f"/executions/{eid}?includeData=true")
    d = det["data"]
    rd = (d.get("resultData") or {}).get("runData") or {}
    ent = ""
    try:
        j = rd["Normalizacion"][0]["data"]["main"][0][0]["json"]
        ent = j.get("message_content") or ""
    except Exception:
        pass
    sal = ""
    try:
        sal = rd["AI Agent"][0]["data"]["main"][0][0]["json"]["output"]
    except Exception:
        pass
    enviado = None
    raw_mandar = None
    try:
        raw_mandar = rd["Mandar mensaje"][0]["data"]["main"][0][0]["json"]
        # el texto que REALMENTE se envio (ya sin espacios finales)
        enviado = raw_mandar["message"]["conversation"]
    except Exception:
        try:
            enviado = json.dumps(
                rd["Mandar mensaje"][0].get("inputOverride"),
                ensure_ascii=False)[:400]
        except Exception:
            pass
    tools = {}
    for t in TOOLS:
        if t in rd:
            try:
                tools[t] = rd[t][0]["data"]["ai_tool"][0][0]["json"]
            except Exception:
                try:
                    tools[t] = rd[t][0].get("inputOverride")
                except Exception:
                    tools[t] = "PRESENTE"
    err = None
    if d.get("status") != "success":
        ln = (d.get("resultData") or {}).get("lastNodeExecuted")
        try:
            err = json.dumps(rd[ln][0].get("error"), ensure_ascii=False)[:1500]
        except Exception:
            err = f"status={d.get('status')} lastNode={ln}"
    return {"id": eid, "status": d.get("status"),
            "startedAt": d.get("startedAt"),
            "entrada": ent, "respuesta": sal, "enviado": enviado,
            "herramientas": tools, "error": err, "nodos": list(rd.keys())}


if __name__ == "__main__":
    texto = sys.argv[1]
    etiqueta = sys.argv[2] if len(sys.argv) > 2 else (
        "caso_" + datetime.datetime.now().strftime("%H%M%S"))
    espera = int(sys.argv[3]) if len(sys.argv) > 3 else 45

    antes = api(f"/executions?workflowId={WID}&limit=1")
    marca = int(antes["data"][0]["id"]) if antes.get("data") else 0
    print(f"marca previa: {marca}")
    print(f"NOW Mexico: {datetime.datetime.now(datetime.timezone.utc).astimezone(datetime.timezone(datetime.timedelta(hours=-6)))}")
    print(f"enviando {etiqueta}: {texto!r}")
    print("HTTP:", enviar(texto, evolution_key()))
    print(f"esperando {espera} s...")
    time.sleep(espera)

    nuevas = []
    for _ in range(6):
        ex = api(f"/executions?workflowId={WID}&limit=10")
        nuevas = [e["id"] for e in ex["data"] if int(e["id"]) > marca]
        if nuevas:
            break
        time.sleep(10)

    print("ejecuciones nuevas:", nuevas)
    # solo las que corresponden a NUESTRO texto
    mias = []
    for eid in sorted(nuevas, key=int):
        r = leer_ejecucion(eid)
        if r["entrada"].strip() != texto.strip():
            continue
        mias.append(r)
    if not mias:
        print("!! ninguna ejecucion coincide con el texto enviado:")
        for eid in sorted(nuevas, key=int):
            r = leer_ejecucion(eid)
            print("   otro:", eid, repr(r["entrada"])[:80])
    salida = []
    for r in mias:
        salida.append(r)
        print("-" * 70)
        print(f"exec {r['id']} status={r['status']} startedAt={r['startedAt']}")
        print("  entrada:", repr(r["entrada"]))
        print("  respuesta:", repr(r["respuesta"])[:900])
        print("  ENVIADO:", repr(r["enviado"])[:900])
        print("  herramientas:", list(r["herramientas"].keys()))
        for t, v in r["herramientas"].items():
            print(f"    {t}: {json.dumps(v, ensure_ascii=False)[:300]}")
        if r["error"]:
            print("  ERROR:", r["error"][:600])
    json.dump(salida, open(VIVO + "\\" + etiqueta + ".json", "w",
                           encoding="utf-8"), ensure_ascii=False, indent=1)
    print("guardado:", VIVO + "\\" + etiqueta + ".json", len(salida), "coincidencias")
    if salida and len(salida) > 1:
        print("!! AVISO: mas de una ejecucion para el mismo texto")
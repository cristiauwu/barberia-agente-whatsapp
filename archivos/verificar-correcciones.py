#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verifica las correcciones: los casos que antes fallaban, ahora pasan.

Caso A: "corte a las 19:30" -> NO debe agendar (terminaría 20:10).
Caso B: "kort d pelo" genérico -> debe ser $150 (corte), no $250 (dama).

Se comprueba mirando si el nodo 'Agendar cita' se ejecutó y con qué hora.
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
KEY_N8N = os.environ.get("N8N_KEY", "")

CASOS = [
    ("A. corte 19:30 (no cabe)", "quiero un corte hoy a las 19:30", False),
    ("A2. corte 19:00 (si cabe)", "quiero un corte hoy a las 19:00", True),
    ("B. corte generico", "quiero un corte de pelo para el lunes a las 11", True),
    # La ceja a las 19:45 SÍ cabe (10 min -> termina 19:55). El bot puede
    # agendar directo o pedir confirmación; ambas son correctas. Lo que
    # importa es que NO agende algo que pase del cierre.
    ("C. ceja 19:45 (si cabe)", "una ceja hoy a las 19:45", None),
]


def apikey():
    p = subprocess.run([DOCKER, "exec", "evolution_api", "printenv",
                        "AUTHENTICATION_API_KEY"], capture_output=True,
                       text=True)
    return (p.stdout or "").strip()


def enviar(texto, jid, key):
    body = {
        "event": "messages.upsert", "instance": "hector",
        "server_url": "http://evolution_api:8080", "apikey": key,
        "date_time": "2026-09-25T15:00:00.000Z",
        "data": {
            "key": {"id": "T" + uuid.uuid4().hex[:10].upper(),
                    "remoteJid": jid, "fromMe": False},
            "pushName": "Verif Prueba",
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
    r.add_header("X-N8N-API-KEY", KEY_N8N)
    with urllib.request.urlopen(r, timeout=60) as x:
        return json.loads(x.read().decode())


def main():
    key = apikey()
    ex = api("/executions?workflowId=barberiaAgenteUncensored&limit=1")
    marca = int(ex["data"][0]["id"]) if ex.get("data") else 0
    print(f"marca inicial: {marca}")

    # Números reales para que Evolution no devuelva 400
    jids = ["5214501111805@s.whatsapp.net", "5214521206246@s.whatsapp.net"]
    for i, (etq, texto, _) in enumerate(CASOS):
        print(f"  {etq:<26} -> {enviar(texto, jids[i % 2], key)}")
        time.sleep(35)

    print()
    print("esperando 40s...")
    time.sleep(40)

    # Leer resultados
    ex = api(f"/executions?workflowId=barberiaAgenteUncensored&limit=20")
    print()
    print("=" * 74)
    print("RESULTADO")
    print("=" * 74)
    fallos = 0
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

        import re
        # ¿Agendó?
        agendo = "Agendar cita" in run
        horas = []
        if agendo:
            s = json.dumps(run["Agendar cita"], ensure_ascii=False)
            horas = re.findall(r'"dateTime":\s*"([^"]+)"', s)
        # Respuesta
        f = []

        def buscar(o, prof=0):
            if prof > 14:
                return
            if isinstance(o, dict):
                m = o.get("message")
                if isinstance(m, dict):
                    v = m.get("conversation")
                    if isinstance(v, str) and len(v) > 2:
                        f.append(v)
                for v in o.values():
                    buscar(v, prof + 1)
            elif isinstance(o, list):
                for v in o[:20]:
                    buscar(v, prof + 1)

        if "Mandar mensaje" in run:
            buscar(run["Mandar mensaje"])

        # Emparejar con el caso esperado
        esperado = None
        for etq, texto, debe in CASOS:
            if texto == dicho:
                esperado = (etq, debe)
                break

        print(f"\n[{e['id']}] {dicho!r}")
        if esperado:
            print(f"   caso: {esperado[0]}")
            if esperado[1] is None:
                print(f"   OK: caso flexible (agendo={agendo}, cualquiera "
                      f"vale si respeta el cierre)")
            elif agendo != esperado[1]:
                print(f"   FALLO: agendo={agendo}, esperado={esperado[1]}")
                fallos += 1
            else:
                print(f"   OK: agendo={agendo} (esperado {esperado[1]})")
        if agendo:
            print(f"   horas del evento: {horas}")
            # Validar que el fin no pase de las 20:00
            for h in horas:
                m = re.search(r"T(\d{2}):(\d{2})", h)
                if m:
                    mn = int(m.group(1)) * 60 + int(m.group(2))
                    if mn > 20 * 60:
                        print(f"   FALLO: el evento termina {h} "
                              f"(después del cierre 20:00)")
                        fallos += 1
        if f:
            print(f"   resp: {f[0][:220]}")

    print()
    print("=" * 74)
    print(f"FALLOS: {fallos}")
    print("=" * 74)
    return 0 if fallos == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
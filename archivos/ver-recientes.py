#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Revisa las 2 ejecuciones recientes: si son mensajes reales, que hizo el
agente."""
import json
import os
import subprocess
import sys
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

N8N = "http://localhost:5678/api/v1"
KEY = os.environ.get("N8N_KEY", "")
DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
os.environ["DOCKER_CONFIG"] = r"G:\Barberia\.docker"

HERRAMIENTAS = ("Consultar agenda", "Agendar cita", "Cancelar cita",
                "Reagendar", "Registrar en hoja de citas",
                "Notificar al encargado")


def api(path):
    req = urllib.request.Request(N8N + path)
    req.add_header("X-N8N-API-KEY", KEY)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def psql(sql):
    p = subprocess.run([DOCKER, "exec", "barberia-postgres", "psql", "-U",
                        "barberia", "-d", "barberia", "-t", "-A", "-c", sql],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return (p.stdout or "").strip()


def textos(obj, fuera, prof=0):
    if prof > 12:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("output", "text") and isinstance(v, str) and len(v) > 15:
                fuera.append(v)
            else:
                textos(v, fuera, prof + 1)
    elif isinstance(obj, list):
        for v in obj[:20]:
            textos(v, fuera, prof + 1)


def main():
    ids = [x for x in psql(
        """SELECT string_agg(id::text, ',') FROM (
             SELECT id FROM execution_entity
             WHERE "workflowId"='barberiaAgenteUncensored'
             ORDER BY id DESC LIMIT 4) s;""").split(",") if x.strip()]

    for eid in ids:
        try:
            det = api(f"/executions/{eid}?includeData=true")
        except Exception:
            continue
        run = (((det.get("data") or {}).get("resultData") or {})
               .get("runData") or {})
        print("=" * 74)
        print(f"EJECUCION {eid} | {det.get('status')}")
        print("=" * 74)
        print("  nodos:", ", ".join(run.keys())[:180])

        # Evento del payload
        if "Webhook" in run:
            txt = json.dumps(run["Webhook"], ensure_ascii=False)
            i = txt.find('"event"')
            if i >= 0:
                print("  evento:", txt[i:i+90])

        if "Normalizacion" in run:
            for it in ((run["Normalizacion"][0].get("data") or {})
                       .get("main") or [[]])[0]:
                j = it.get("json", {})
                print("  cliente:", repr(str(j.get("message_content", ""))[:110]))
                print("  from_me:", j.get("from_me"), "| tipo:", j.get("message_content_type"))

        usadas = [h for h in HERRAMIENTAS if h in run]
        print("  herramientas:", ", ".join(usadas) or "(ninguna)")

        sal = []
        if "AI Agent" in run:
            textos(run["AI Agent"], sal)
        if sal:
            print("  respuesta:", sal[0].replace("\n", " ")[:280])
        if "Mandar mensaje" in run:
            print("  -> enviado por WhatsApp")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
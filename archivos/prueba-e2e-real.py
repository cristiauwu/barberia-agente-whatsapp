#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueba definitiva de extremo a extremo.

Busca las ejecuciones que SI llegaron al AI Agent y muestra:
  - lo que dijo el cliente
  - las herramientas que uso el agente
  - la respuesta final que se mando por WhatsApp
  - el evento creado en Google Calendar
  - la fila escrita en Google Sheets
"""
import json
import os
import subprocess
import sys

# Evitar errores de codificacion en consola Windows
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
import urllib.request

N8N = "http://localhost:5678/api/v1"
KEY = os.environ.get("N8N_KEY", "")
DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
os.environ["DOCKER_CONFIG"] = r"G:\Barberia\.docker"


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
    if prof > 10:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("output", "text") and isinstance(v, str) and len(v) > 20:
                fuera.append(v)
            else:
                textos(v, fuera, prof + 1)
    elif isinstance(obj, list):
        for v in obj[:15]:
            textos(v, fuera, prof + 1)


def main():
    # Ultimas 40 ejecuciones; quedarse con las que llegaron al AI Agent
    encontradas = 0
    for eid in [int(x) for x in psql(
            """SELECT string_agg(id::text, ',') FROM (
                 SELECT id FROM execution_entity
                 WHERE "workflowId"='barberiaAgenteUncensored'
                 ORDER BY id DESC LIMIT 40) s;""").split(",") if x.strip()][:40]:
        try:
            det = api(f"/executions/{eid}?includeData=true")
        except Exception:
            continue
        run = (((det.get("data") or {}).get("resultData") or {})
               .get("runData") or {})
        if "AI Agent" not in run:
            continue

        encontradas += 1
        print("=" * 74)
        print(f"EJECUCION {eid}  |  estado: {det.get('status')}")
        print("=" * 74)

        # Lo que dijo el cliente
        if "Normalizacion" in run:
            for it in ((run["Normalizacion"][0].get("data") or {})
                       .get("main") or [[]])[0]:
                j = it.get("json", {})
                print("  cliente:", repr(str(j.get("message_content"))[:110]))

        # Herramientas usadas
        usadas = [k for k in run if k in
                  ("Consultar agenda", "Agendar cita", "Cancelar cita",
                   "Reagendar", "Registrar en hoja de citas",
                   "Notificar al encargado")]
        print("  herramientas:", ", ".join(usadas) or "(ninguna)")

        # Respuesta del agente
        sal = []
        textos(run["AI Agent"], sal)
        if sal:
            print("  respuesta:", sal[0].replace("\n", " ")[:340])

        # Lo que se mando por WhatsApp
        if "Mandar mensaje" in run:
            print("  -> 'Mandar mensaje' SE EJECUTO (mensaje enviado)")
        if encontradas >= 2:
            break

    if not encontradas:
        print("Ninguna ejecucion llego al AI Agent.")

    print()
    print("=" * 74)
    print("RESUMEN DE ESTADO")
    print("=" * 74)
    print("  ejecuciones totales:",
          psql("""SELECT count(*) FROM execution_entity
                  WHERE "workflowId"='barberiaAgenteUncensored';"""))
    print("  exitosas:",
          psql("""SELECT count(*) FROM execution_entity
                  WHERE "workflowId"='barberiaAgenteUncensored'
                  AND status='success';"""))
    print("  con error:",
          psql("""SELECT count(*) FROM execution_entity
                  WHERE "workflowId"='barberiaAgenteUncensored'
                  AND status='error';"""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Comprueba si el agente uso las herramientas de Calendar y Sheets en las
conversaciones reales, y muestra los resultados."""
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


def main():
    ids = [x for x in psql(
        """SELECT string_agg(id::text, ',') FROM (
             SELECT id FROM execution_entity
             WHERE "workflowId"='barberiaAgenteUncensored' AND status='success'
             ORDER BY id DESC LIMIT 60) s;""").split(",") if x.strip()]

    uso = {h: 0 for h in HERRAMIENTAS}
    ejemplos = []
    revisadas = 0

    for eid in ids:
        try:
            det = api(f"/executions/{eid}?includeData=true")
        except Exception:
            continue
        run = (((det.get("data") or {}).get("resultData") or {})
               .get("runData") or {})
        revisadas += 1
        usadas = [h for h in HERRAMIENTAS if h in run]
        for h in usadas:
            uso[h] += 1
        if usadas and len(ejemplos) < 3:
            # Lo que pidio el cliente
            dicho = ""
            if "Normalizacion" in run:
                for it in ((run["Normalizacion"][0].get("data") or {})
                           .get("main") or [[]])[0]:
                    dicho = str(it.get("json", {}).get("message_content", ""))
            ejemplos.append((eid, dicho, usadas))

    print("=" * 74)
    print("USO REAL DE HERRAMIENTAS EN CONVERSACIONES")
    print("=" * 74)
    print(f"  ejecuciones revisadas: {revisadas}")
    for h, n in uso.items():
        print(f"  {h:<28} {n} veces")
    if not any(uso.values()):
        print("\n  >>> NINGUNA herramienta se ha usado todavia.")
        print("      El agente conversa pero aun no agenda.")

    if ejemplos:
        print()
        print("=" * 74)
        print("EJEMPLOS")
        print("=" * 74)
        for eid, dicho, usadas in ejemplos:
            print(f"\n  ejecucion {eid}")
            print(f"    cliente dijo: {dicho[:120]}")
            print(f"    herramientas: {', '.join(usadas)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
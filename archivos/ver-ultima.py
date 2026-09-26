#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Inspecciona la ULTIMA ejecucion completa: que nodos corrieron y que dijo
el agente, para entender por que no usa las herramientas."""
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


def recolectar(obj, fuera, prof=0):
    if prof > 12:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("output", "text") and isinstance(v, str) and len(v) > 15:
                fuera.append((k, v))
            else:
                recolectar(v, fuera, prof + 1)
    elif isinstance(obj, list):
        for v in obj[:20]:
            recolectar(v, fuera, prof + 1)


def main():
    ids = [x for x in psql(
        """SELECT string_agg(id::text, ',') FROM (
             SELECT id FROM execution_entity
             WHERE "workflowId"='barberiaAgenteUncensored'
             ORDER BY id DESC LIMIT 6) s;""").split(",") if x.strip()]

    for eid in ids[:4]:
        det = api(f"/executions/{eid}?includeData=true")
        run = (((det.get("data") or {}).get("resultData") or {})
               .get("runData") or {})
        print("=" * 74)
        print(f"EJECUCION {eid} | {det.get('status')}")
        print("=" * 74)
        print("  nodos que corrieron:", ", ".join(run.keys()))

        # Entrada al agente
        if "Edit Fields" in run:
            for it in ((run["Edit Fields"][0].get("data") or {})
                       .get("main") or [[]])[0]:
                print("  mensaje al agente:",
                      repr(str(it.get("json", {}).get("chat_input", ""))[:130]))

        # Respuesta
        sal = []
        for nodo in ("AI Agent",):
            if nodo in run:
                recolectar(run[nodo], sal)
        if sal:
            print("  respuesta del agente:")
            print("   ", sal[0][1].replace("\n", " ")[:400])

        if "Mandar mensaje" in run:
            print("  -> mensaje ENVIADO al cliente")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
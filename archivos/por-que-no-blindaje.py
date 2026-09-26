#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Descubre por que el blindaje no detuvo el bucle.

Hipotesis: el campo fromMe no llega en el payload que Evolution envia para
mensajes SALIENTES, o Evolution manda otro formato (send.message).
"""
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


def main():
    ids = [x for x in psql(
        """SELECT string_agg(id::text, ',') FROM (
             SELECT id FROM execution_entity
             WHERE "workflowId"='barberiaAgenteUncensored'
             ORDER BY id DESC LIMIT 25) s;""").split(",") if x.strip()]

    print("=" * 74)
    print("QUE CAMPO fromMe LLEGA Y QUE DECIDE EL IF")
    print("=" * 74)
    for eid in ids[:12]:
        try:
            det = api(f"/executions/{eid}?includeData=true")
        except Exception:
            continue
        run = (((det.get("data") or {}).get("resultData") or {})
               .get("runData") or {})

        # Valor de from_me calculado
        fm = None
        if "Normalizacion" in run:
            for it in ((run["Normalizacion"][0].get("data") or {})
                       .get("main") or [[]])[0]:
                fm = it.get("json", {}).get("from_me")

        # Se ejecuto el IF? a donde fue?
        if_ejec = "IF - No es del bot" in run
        otros = [k for k in run.keys()
                 if k not in ("Webhook", "Normalizacion", "Switch")]

        print(f"\n  ejec {eid}: from_me={fm!r} | IF_corrio={if_ejec}")
        print(f"     nodos: {', '.join(run.keys())[:170]}")

        # Si el IF no corrio, ver la estructura de conexiones usada
        if not if_ejec and "Normalizacion" in run:
            print("     >>> El IF NO se ejecuto: revisar el cableado")
    return 0


if __name__ == "__main__":
    sys.exit(main())
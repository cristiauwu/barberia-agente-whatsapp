#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Muestra el payload CRUDO de un evento que el IF corto, para saber que
esta mandando Evolution en masa.
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
    # Buscar una ejecucion cortada (solo 3 nodos) reciente
    ids = [x for x in psql(
        """SELECT string_agg(id::text, ',') FROM (
             SELECT id FROM execution_entity
             WHERE "workflowId"='barberiaAgenteUncensored'
             ORDER BY id DESC LIMIT 30) s;""").split(",") if x.strip()]

    mostrados = 0
    for eid in ids:
        try:
            det = api(f"/executions/{eid}?includeData=true")
        except Exception:
            continue
        run = (((det.get("data") or {}).get("resultData") or {})
               .get("runData") or {})
        if "Switch" in run:
            continue  # esa si llego al agente
        if "Webhook" not in run:
            continue

        # Extraer el payload de entrada del webhook
        txt = json.dumps(run["Webhook"], ensure_ascii=False)
        print("=" * 74)
        print(f"EJECUCION {eid} (cortada por el IF)")
        print("=" * 74)
        # Buscar el cuerpo del webhook
        for marca in ("\"body\"", "\"event\"", "\"data\"", "fromMe",
                      "messageType", "remoteJid"):
            i = txt.find(marca)
            if i >= 0:
                print(f"  [{marca}] {txt[i:i+260]}")
        print()
        mostrados += 1
        if mostrados >= 3:
            break
    return 0


if __name__ == "__main__":
    sys.exit(main())
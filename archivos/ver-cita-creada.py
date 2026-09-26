#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Confirma que la cita llego a Google Calendar y a Google Sheets."""
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


def api(path):
    req = urllib.request.Request(N8N + path)
    req.add_header("X-N8N-API-KEY", KEY)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def recolectar(obj, fuera, prof=0):
    if prof > 14:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("id", "summary", "start", "end") and isinstance(v, (str, dict)):
                fuera.append((k, v))
            recolectar(v, fuera, prof + 1)
    elif isinstance(obj, list):
        for v in obj[:25]:
            recolectar(v, fuera, prof + 1)


def main():
    det = api("/executions/533?includeData=true")
    run = (((det.get("data") or {}).get("resultData") or {}).get("runData") or {})

    print("=" * 74)
    print("1) GOOGLE CALENDAR: que devolvio 'Agendar cita'")
    print("=" * 74)
    if "Agendar cita" in run:
        datos = []
        recolectar(run["Agendar cita"], datos)
        vistos = set()
        for k, v in datos:
            clave = (k, str(v)[:60])
            if clave in vistos:
                continue
            vistos.add(clave)
            if k in ("id", "summary", "start", "end"):
                print(f"  {k}: {str(v)[:130]}")
    else:
        print("  (no corrio)")

    print()
    print("=" * 74)
    print("2) GOOGLE SHEETS: que se registro")
    print("=" * 74)
    if "Registrar en hoja de citas" in run:
        datos = []
        recolectar(run["Registrar en hoja de citas"], datos)
        for k, v in datos[:14]:
            print(f"  {k}: {str(v)[:130]}")
    else:
        print("  (no corrio)")

    print()
    print("=" * 74)
    print("3) RESULTADO DE LAS HERRAMIENTAS (exito o error)")
    print("=" * 74)
    for h in ("Consultar agenda", "Agendar cita", "Registrar en hoja de citas"):
        if h not in run:
            continue
        txt = json.dumps(run[h], ensure_ascii=False)
        estado = "ERROR" if ('"error"' in txt and "error\":" not in txt[:50]) else "OK"
        # Detectar error real
        malo = any(x in txt for x in ("error\":{", "NodeApiError", "ECONNREFUSED",
                                      "401", "403", "404", "Forbidden"))
        print(f"  {h:<28} -> {'PROBLEMA' if malo else 'OK'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
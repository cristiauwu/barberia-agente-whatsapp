#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Muestra el resultado CRUDO de las herramientas para saber si de verdad
funcionaron o fallaron (mi detector anterior daba falsos positivos)."""
import json
import os
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


def resumir(obj, prof=0, ruta=""):
    """Muestra solo las claves utiles de la respuesta de la herramienta."""
    salida = []
    if prof > 10:
        return salida
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("id", "summary", "start", "end", "dateTime", "status",
                     "error", "message", "description", "code", "success"):
                salida.append(f"{ruta}/{k} = {str(v)[:120]}")
            else:
                salida += resumir(v, prof + 1, ruta + "/" + k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:4]):
            salida += resumir(v, prof + 1, f"{ruta}[{i}]")
    return salida


def main():
    det = api("/executions/533?includeData=true")
    run = (((det.get("data") or {}).get("resultData") or {}).get("runData") or {})

    for h in ("Consultar agenda", "Agendar cita", "Registrar en hoja de citas"):
        print("=" * 74)
        print("HERRAMIENTA:", h)
        print("=" * 74)
        if h not in run:
            print("  (no corrio)")
            continue
        txt = json.dumps(run[h], ensure_ascii=False)
        # Ver si hay un error explicito
        tiene_error = "NodeApiError" in txt or "ERR_" in txt or "Unauthorized" in txt
        print("  contiene error explicito:", tiene_error)
        lineas = resumir(run[h])
        for l in lineas[:12]:
            print("   ", l)
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Muestra el contenido real del item de salida del AI Agent.

El formato del runData puede variar, asi que se recorre la estructura
completa buscando el texto de respuesta.
"""
import json
import os
import subprocess
import sys
import urllib.request

N8N = "http://localhost:5678/api/v1"
KEY = os.environ.get("N8N_KEY", "")


def api(path):
    req = urllib.request.Request(N8N + path)
    req.add_header("X-N8N-API-KEY", KEY)
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode())


def buscar_textos(obj, fuera, ruta="", prof=0):
    """Recorre y recolecta strings largos (respuestas del modelo)."""
    if prof > 8:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("output", "text", "content") and isinstance(v, str) and len(v) > 25:
                fuera.append((ruta + "/" + k, v))
            else:
                buscar_textos(v, fuera, ruta + "/" + k, prof + 1)
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:12]):
            buscar_textos(v, fuera, ruta + f"[{i}]", prof + 1)


def main():
    ex = api("/executions?workflowId=barberiaAgenteUncensored&limit=8")
    mostrados = 0
    for e in ex.get("data", []):
        if e["status"] != "success":
            continue
        det = api(f"/executions/{e['id']}?includeData=true")
        rd = ((det.get("data") or {}).get("resultData") or {})
        run = rd.get("runData") or {}
        print("=" * 74)
        print("EJECUCION", e["id"])
        print("=" * 74)
        print("  nodos ejecutados:", ", ".join(run.keys()))
        # Texto de respuesta
        textos = []
        if "AI Agent" in run:
            buscar_textos(run["AI Agent"], textos, "AI Agent")
        vistos = set()
        for ruta, t in textos:
            clave = t[:60]
            if clave in vistos:
                continue
            vistos.add(clave)
            print(f"\n  >>> RESPUESTA ({ruta}):")
            print("     ", t.replace("\n", " ")[:500])
        # Herramientas
        usadas = [k for k in run if k in ("Consultar agenda", "Agendar cita",
                                          "Cancelar cita", "Reagendar",
                                          "Registrar en hoja de citas",
                                          "Notificar al encargado")]
        print("\n  herramientas:", ", ".join(usadas) or "(ninguna)")
        print()
        mostrados += 1
        if mostrados >= 3:
            break
    return 0


if __name__ == "__main__":
    sys.exit(main())
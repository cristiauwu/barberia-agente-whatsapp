#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Toolkit de consulta a la API de n8n. La clave se lee del entorno.

Uso:  uv run python ver-n8n.py workflows
      uv run python ver-n8n.py router
      uv run python ver-n8n.py libre
"""
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


def api(p):
    r = urllib.request.Request(N8N + p)
    r.add_header("X-N8N-API-KEY", KEY)
    with urllib.request.urlopen(r, timeout=60) as x:
        return json.loads(x.read().decode())


def main():
    if not KEY:
        print("falta N8N_KEY en el entorno")
        return 1
    cmd = sys.argv[1] if len(sys.argv) > 1 else "workflows"

    if cmd == "workflows":
        for w in api("/workflows?limit=20").get("data", []):
            print(f"  {w['name'][:46]:<48} active={w.get('active')}")
        return 0

    wf = api("/workflows/barberiaAgenteUncensored")

    if cmd == "router":
        sw = next(n for n in wf["nodes"] if n["name"] == "Router de comandos")
        print("=== salidas del Router de comandos ===")
        for v in sw["parameters"]["rules"]["values"]:
            for c in v["conditions"]["conditions"]:
                print(f"  {c['rightValue']}")
        op = sw["parameters"]["options"]
        print(f"\n  fallback: {op.get('fallbackOutput')} / "
              f"{op.get('renameFallbackOutput')}")
        print(f"  leftValue: "
              f"{sw['parameters']['rules']['values'][0]['conditions']['conditions'][0]['leftValue']}")
        return 0

    if cmd == "libre":
        n = next(x for x in wf["nodes"]
                 if x["name"] == "Preparar rango de fechas")
        c = n["parameters"]["jsCode"]
        print("=== LIBRE / esRango en 'Preparar rango de fechas' ===")
        for l in c.split("\n"):
            if any(k in l for k in ("LIBRE", "esRango", "hasta", "titulo")):
                s = l.strip()
                if s and not s.startswith("//"):
                    print(f"  {s[:120]}")
        print()
        n2 = next(x for x in wf["nodes"] if x["name"] == "Formatear agenda")
        c2 = n2["parameters"]["jsCode"]
        print("=== donde imprime 'Huecos' ===")
        for i, l in enumerate(c2.split("\n")):
            if "Huecos" in l or "esRango" in l:
                print(f"  linea {i}: {l.strip()[:110]}")
        return 0

    print("comandos: workflows | router | libre")
    return 1


if __name__ == "__main__":
    sys.exit(main())
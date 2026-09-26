#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compara la version ANTERIOR con la ACTUAL y muestra lo que hizo el
agente en la ejecucion 1198 (la que volvio a fallar)."""
import json, sys, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
KEY = open(r"G:\Barberia\archivos\.n8n-key.txt", encoding="utf-8").read().strip()
N8N = "http://localhost:5678/api/v1"
WID = "barberiaAgenteUncensored"
DIR = r"G:\Barberia\archivos\_verif-fechas"


def api(p):
    r = urllib.request.Request(N8N + p)
    r.add_header("X-N8N-API-KEY", KEY)
    with urllib.request.urlopen(r, timeout=180) as x:
        return json.loads(x.read().decode())


print("=" * 74)
print("VERSION ANTERIOR vs ACTUAL")
print("=" * 74)
try:
    d = api(f"/workflows/{WID}/diff?fromVersionId=ce1d5933-8575-4606-8837-4c9645da783a&toVersionId=119cce56-03b8-460d-a3f0-a0ed62604b46")
    print(json.dumps(d, ensure_ascii=False)[:6000])
except Exception as e:
    print("diff no disponible:", e)

# ---- version anterior ----
try:
    prev = api(f"/workflows/{WID}/versions/ce1d5933-8575-4606-8837-4c9645da783a")
    nodos_prev = [n["name"] for n in prev.get("nodes", [])]
    print("\nversion ce1d5933 nodos:", len(nodos_prev))
    print("tiene 'Que dia es':", "Que dia es" in nodos_prev)
except Exception as e:
    print("versions endpoint no disponible:", e)

print()
print("=" * 74)
print("EXEC 1198 — QUE HIZO EL AGENTE (la que volvio a fallar)")
print("=" * 74)
det = api("/executions/1198?includeData=true")
rd = det["data"]["resultData"]["runData"]
print("nodos ejecutados:", list(rd.keys()))
print()
ag = rd.get("AI Agent")
if ag:
    for run in ag:
        out = run.get("data", {}).get("main", [])
        print("AI Agent ejecuciones:", len(ag))
        try:
            j = out[0][0]["json"]
            print(json.dumps(j, ensure_ascii=False)[:4000])
        except Exception as e:
            print("no se pudo leer la salida:", e)
        print("--- rawAgentSteps / intermediateSteps ---")
        try:
            steps = out[0][0]["json"].get("intermediateSteps")
            print(json.dumps(steps, ensure_ascii=False)[:4000])
        except Exception:
            pass
print()
print("claves del item del AI Agent:")
try:
    j = rd["AI Agent"][0]["data"]["main"][0][0]["json"]
    print(list(j.keys()))
    for k in list(j.keys()):
        print(f"  {k}: {json.dumps(j[k], ensure_ascii=False)[:300]}")
except Exception as e:
    print(e)
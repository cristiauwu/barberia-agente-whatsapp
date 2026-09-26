#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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
print("CAUSA DE LAS 5 EJECUCIONES CON ERROR")
print("=" * 74)
for eid in ("1109", "1106", "1094", "1091", "1089"):
    det = api(f"/executions/{eid}?includeData=true")
    d = det["data"]
    print(f"\n--- exec {eid} [{d.get('startedAt')}] ---")
    rd = ((d.get("resultData") or {}).get("runData") or {})
    for nname in ("AI Agent", "OpenAI Chat Model", "Mandar mensaje"):
        if nname not in rd:
            continue
        for run in rd[nname]:
            err = run.get("error")
            if err:
                print(f"  nodo {nname}: error")
                print("   ", json.dumps(err, ensure_ascii=False)[:900])
            st = run.get("executionStatus")
            if st != "success":
                print(f"  nodo {nname}: executionStatus={st}")
    # ultimo nodo
    ln = d["resultData"].get("lastNodeExecuted")
    print("  lastNodeExecuted:", ln)
    if ln and ln in rd:
        r0 = rd[ln][0]
        if r0.get("error"):
            print("   error del ultimo nodo:",
                  json.dumps(r0["error"], ensure_ascii=False)[:1200])

print()
print("=" * 74)
print("HISTORIAL DE VERSIONES DEL WORKFLOW")
print("=" * 74)
try:
    h = api(f"/workflows/{WID}/history?limit=30")
    print(json.dumps(h, ensure_ascii=False)[:3000])
except Exception as e:
    print("history no disponible:", e)

# versiones via API publica
try:
    wf = api(f"/workflows/{WID}")
    print("\nclaves del workflow:", [k for k in wf.keys()])
    print("versionId:", wf.get("versionId"), "updatedAt:", wf.get("updatedAt"),
          "createdAt:", wf.get("createdAt"))
except Exception as e:
    print(e)
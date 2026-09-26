#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reconocimiento: estructura de una ejecucion + cuantos hay."""
import json, sys, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

KEY = open(r"G:\Barberia\archivos\.n8n-key.txt", encoding="utf-8").read().strip()
N8N = "http://localhost:5678/api/v1"
WID = "barberiaAgenteUncensored"


def api(p):
    r = urllib.request.Request(N8N + p)
    r.add_header("X-N8N-API-KEY", KEY)
    with urllib.request.urlopen(r, timeout=120) as x:
        return json.loads(x.read().decode())


ex = api(f"/executions?workflowId={WID}&limit=100")
print("total devueltas:", len(ex["data"]))
print("primera:", ex["data"][0]["id"], ex["data"][0]["status"],
      ex["data"][0].get("startedAt"), ex["data"][0].get("mode"))
print("ultima:", ex["data"][-1]["id"], ex["data"][-1]["status"],
      ex["data"][-1].get("startedAt"))

det = api(f"/executions/{ex['data'][0]['id']}?includeData=true")
d = det["data"]
print("claves de data:", list(d.keys()))
rd = d["resultData"]["runData"]
print("nodos en runData:", list(rd.keys()))
print()
print("=== Normalizacion ===")
print(json.dumps(rd.get("Normalizacion"), ensure_ascii=False)[:2500])
print()
print("=== Mandar mensaje (recortado) ===")
print(json.dumps(rd.get("Mandar mensaje"), ensure_ascii=False)[:2500])
print()
print("=== Que dia es (si existe) ===")
print(json.dumps(rd.get("Que dia es"), ensure_ascii=False)[:1500])
print()
print("=== claves resultData ===")
print(list(d["resultData"].keys()))
print("lastNodeExecuted:", d["resultData"].get("lastNodeExecuted"))
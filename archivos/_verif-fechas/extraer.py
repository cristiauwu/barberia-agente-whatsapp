#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, urllib.request, sys, os

KEY = open(r"G:\Barberia\archivos\.n8n-key.txt", encoding="utf-8").read().strip()
N8N = "http://localhost:5678/api/v1"

def api(p):
    r = urllib.request.Request(N8N + p)
    r.add_header("X-N8N-API-KEY", KEY)
    with urllib.request.urlopen(r, timeout=120) as x:
        return json.loads(x.read().decode())

wf = api("/workflows/barberiaAgenteUncensored")
with open(r"G:\Barberia\archivos\_verif-fechas\wf_agente.json", "w", encoding="utf-8") as f:
    json.dump(wf, f, ensure_ascii=False, indent=1)

print("nombre:", wf.get("name"), "activo:", wf.get("active"))
print("nodos:", len(wf["nodes"]))
for n in wf["nodes"]:
    print("  -", n["name"], "|", n["type"])
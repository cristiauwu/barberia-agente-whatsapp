#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, sys, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
KEY = open(r"G:\Barberia\archivos\.n8n-key.txt", encoding="utf-8").read().strip()
N8N = "http://localhost:5678/api/v1"


def api(p):
    r = urllib.request.Request(N8N + p)
    r.add_header("X-N8N-API-KEY", KEY)
    with urllib.request.urlopen(r, timeout=180) as x:
        return json.loads(x.read().decode())


for eid in ("1197", "1196", "1198", "1139"):
    det = api(f"/executions/{eid}?includeData=true")
    d = det["data"]
    rd = d["resultData"]["runData"]
    print("=" * 74)
    print(f"EXEC {eid} | startedAt={d.get('startedAt')} | stoppedAt={d.get('stoppedAt')} | {d.get('status')}")
    try:
        j = rd["Normalizacion"][0]["data"]["main"][0][0]["json"]
        print("  ENTRADA:", repr(j.get("message_content")))
        print("  de:", j.get("user_number"), "| nombre:", j.get("user_name"))
    except Exception as e:
        print("  entrada?", e)
    if "Que dia es" in rd:
        try:
            print("  TOOL 'Que dia es' ->",
                  json.dumps(rd["Que dia es"][0]["data"]["ai_tool"][0][0]["json"],
                             ensure_ascii=False))
        except Exception as e:
            print("  tool raw:", json.dumps(rd["Que dia es"], ensure_ascii=False)[:600])
    else:
        print("  TOOL 'Que dia es': NO se ejecuto")
    # consultar agenda?
    if "Consultar agenda" in rd:
        try:
            inp = rd["Consultar agenda"][0].get("inputOverride") or {}
            print("  Consultar agenda entrada:", json.dumps(inp, ensure_ascii=False)[:300])
        except Exception:
            pass
    ag = rd.get("AI Agent")
    if ag:
        try:
            print("  RESPUESTA:", repr(ag[0]["data"]["main"][0][0]["json"]["output"])[:800])
        except Exception as e:
            print("  respuesta?", e)
    # herramientas ejecutadas
    print("  nodos de herramienta ejecutados:",
          [k for k in rd if k in ("Consultar agenda", "Agendar cita", "Reagendar",
                                  "Cancelar cita", "Registrar en hoja de citas",
                                  "Notificar al encargado", "Que dia es")])
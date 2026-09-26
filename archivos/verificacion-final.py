#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verificacion final: estado real de las ejecuciones y respuesta del agente."""
import json
import os
import subprocess
import sys
import urllib.request

N8N = "http://localhost:5678/api/v1"
KEY = os.environ.get("N8N_KEY", "")
DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
os.environ["DOCKER_CONFIG"] = r"G:\Barberia\.docker"


def api(path):
    req = urllib.request.Request(N8N + path)
    req.add_header("X-N8N-API-KEY", KEY)
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode())


def psql(sql):
    p = subprocess.run([DOCKER, "exec", "barberia-postgres", "psql", "-U",
                        "barberia", "-d", "barberia", "-t", "-A", "-c", sql],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return (p.stdout or "").strip()


def main():
    print("=== EJECUCIONES EN LA BASE (crudo) ===")
    print(psql("""SELECT id || ' | ' || "workflowId" || ' | ' || status
                  FROM execution_entity ORDER BY id DESC LIMIT 8;"""))

    print()
    print("=== VIA API: ultimas del workflow del agente ===")
    try:
        ex = api("/executions?workflowId=barberiaAgenteUncensored&limit=6")
        for e in ex.get("data", []):
            print(f"  {e['id']} | {e['status']}")
    except Exception as e:
        print("  error:", e)

    print()
    print("=== RESPUESTA DEL AGENTE (ultima ejecucion exitosa) ===")
    # Buscar la ultima ejecucion success y mostrar el texto del AI Agent
    ids = psql("""SELECT string_agg(id::text, ',') FROM (
                    SELECT id FROM execution_entity
                    WHERE status='success' AND "workflowId"='barberiaAgenteUncensored'
                    ORDER BY id DESC LIMIT 2) s;""")
    for eid in [x for x in ids.split(",") if x.strip()]:
        try:
            det = api(f"/executions/{eid}?includeData=true")
        except Exception as ex:
            print(f"  {eid}: no se pudo leer ({ex})")
            continue
        rd = ((det.get("data") or {}).get("resultData") or {})
        run = rd.get("runData") or {}
        print(f"\n  --- ejecucion {eid} ({det.get('status')}) ---")
        # Entrada del webhook
        if "Normalizacion" in run:
            for item in (((run["Normalizacion"][0].get("data") or {})
                          .get("main") or [[]])[0]):
                j = item.get("json", {})
                print("    cliente dijo:", str(j.get("message_content"))[:90])
        # Salida del agente
        if "AI Agent" in run:
            for item in (((run["AI Agent"][0].get("data") or {})
                          .get("main") or [[]])[0]):
                j = item.get("json", {})
                out = j.get("output") or j.get("text") or ""
                print("    agente respondio:", str(out).replace("\n", " ")[:400])
        # Herramientas usadas
        usadas = [k for k in run if k in ("Consultar agenda", "Agendar cita",
                                          "Cancelar cita", "Reagendar",
                                          "Registrar en hoja de citas",
                                          "Notificar al encargado")]
        print("    herramientas usadas:", ", ".join(usadas) or "(ninguna)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Detecta si el bot responde a sus PROPIOS mensajes (fromMe=true).

Sintoma: cientos de ejecuciones, ninguna usa herramientas, y el 'cliente'
habla con el estilo del bot. Es un bucle que puede provocar ban de WhatsApp.
"""
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
DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
os.environ["DOCKER_CONFIG"] = r"G:\Barberia\.docker"


def api(path):
    req = urllib.request.Request(N8N + path)
    req.add_header("X-N8N-API-KEY", KEY)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def psql(sql):
    p = subprocess.run([DOCKER, "exec", "barberia-postgres", "psql", "-U",
                        "barberia", "-d", "barberia", "-t", "-A", "-c", sql],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return (p.stdout or "").strip()


def main():
    print("=" * 74)
    print("1) VOLUMEN DE EJECUCIONES")
    print("=" * 74)
    print(psql("""SELECT '  total: ' || count(*) FROM execution_entity
                  WHERE "workflowId"='barberiaAgenteUncensored';"""))
    print(psql("""SELECT '  ultimos 10 min: ' || count(*) FROM execution_entity
                  WHERE "workflowId"='barberiaAgenteUncensored'
                  AND "startedAt" > now() - interval '10 minutes';"""))
    print(psql("""SELECT '  primera: ' || min("startedAt")::text || ' | ultima: '
                  || max("startedAt")::text FROM execution_entity
                  WHERE "workflowId"='barberiaAgenteUncensored';"""))

    print()
    print("=" * 74)
    print("2) EL PAYLOAD TRAE fromMe? (buscar en ejecuciones recientes)")
    print("=" * 74)
    ids = [x for x in psql(
        """SELECT string_agg(id::text, ',') FROM (
             SELECT id FROM execution_entity
             WHERE "workflowId"='barberiaAgenteUncensored'
             ORDER BY id DESC LIMIT 12) s;""").split(",") if x.strip()]

    para_arriba = 0
    con_fromme = 0
    for eid in ids:
        try:
            det = api(f"/executions/{eid}?includeData=true")
        except Exception:
            continue
        run = (((det.get("data") or {}).get("resultData") or {})
               .get("runData") or {})
        # El payload crudo esta en el nodo Webhook
        if "Webhook" in run:
            txt = json.dumps(run["Webhook"], ensure_ascii=False)
            if '"fromMe":true' in txt or '"fromMe": true' in txt:
                con_fromme += 1
        if "AI Agent" in run:
            para_arriba += 1

    print(f"  ejecuciones con fromMe=true : {con_fromme}")
    print(f"  ejecuciones que usaron AI Agent: {para_arriba}")

    print()
    print("=" * 74)
    print("3) QUE TIPO DE EVENTO LLEGA (event del payload)")
    print("=" * 74)
    eventos = {}
    for eid in ids:
        try:
            det = api(f"/executions/{eid}?includeData=true")
        except Exception:
            continue
        run = (((det.get("data") or {}).get("resultData") or {})
               .get("runData") or {})
        if "Normalizacion" in run:
            for it in ((run["Normalizacion"][0].get("data") or {})
                       .get("main") or [[]])[0]:
                j = it.get("json", {})
                tipo = j.get("message_content_type", "")
                origen = "BOT" if "fromMe" in str(j) and j.get("fromMe") else "?"
                eventos[tipo] = eventos.get(tipo, 0) + 1
    print("  tipos de mensaje:", eventos or "(sin datos)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
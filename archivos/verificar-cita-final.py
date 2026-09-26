#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verificacion final: la cita llego a Calendar y a Sheets sin errores."""
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


def textos(obj, fuera, prof=0):
    if prof > 12:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("output", "text") and isinstance(v, str) and len(v) > 15:
                fuera.append(v)
            else:
                textos(v, fuera, prof + 1)
    elif isinstance(obj, list):
        for v in obj[:20]:
            textos(v, fuera, prof + 1)


def main():
    ex = api("/executions?workflowId=barberiaAgenteUncensored&limit=3")
    for e in ex.get("data", []):
        det = api(f"/executions/{e['id']}?includeData=true")
        run = (((det.get("data") or {}).get("resultData") or {})
               .get("runData") or {})
        if not run or "Webhook" not in run:
            continue
        print("=" * 74)
        print(f"EJECUCION {e['id']} | {e['status']}")
        print("=" * 74)

        # Entrada
        if "Normalizacion" in run:
            for it in ((run["Normalizacion"][0].get("data") or {})
                       .get("main") or [[]])[0]:
                j = it.get("json", {})
                print("  cliente:", repr(str(j.get("message_content", ""))[:100]))

        # Herramientas: exito o error
        for h in ("Consultar agenda", "Agendar cita", "Cancelar cita",
                  "Reagendar", "Registrar en hoja de citas"):
            if h not in run:
                continue
            t = json.dumps(run[h], ensure_ascii=False)
            malo = ("NodeApiError" in t or "Forbidden" in t
                    or '"error":{' in t)
            print(f"  {h:<28} -> {'ERROR' if malo else 'OK'}")
            if malo:
                i = t.find('"message"')
                print(f"       {t[i:i+200]}")

        # Respuesta
        sal = []
        if "AI Agent" in run:
            textos(run["AI Agent"], sal)
        if sal:
            print("  respuesta:", sal[0].replace("\n", " ")[:260])

        # Evento creado
        if "Agendar cita" in run:
            t = json.dumps(run["Agendar cita"], ensure_ascii=False)
            for marca in ('"id":"', '"htmlLink"', '"summary"'):
                i = t.find(marca)
                if i > 0:
                    print(f"  {marca} {t[i:i+120]}")
        break
    return 0


if __name__ == "__main__":
    sys.exit(main())
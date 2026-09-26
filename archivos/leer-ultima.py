#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lee la conversacion de la ultima ejecucion para ver por que no registro."""
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


def textos(o, fuera, prof=0):
    if prof > 12:
        return
    if isinstance(o, dict):
        for k, v in o.items():
            if k in ("output", "text") and isinstance(v, str) and len(v) > 15:
                fuera.append(v)
            else:
                textos(v, fuera, prof + 1)
    elif isinstance(o, list):
        for v in o[:20]:
            textos(v, fuera, prof + 1)


def main():
    ex = api("/executions?workflowId=barberiaAgenteUncensored&limit=3")
    for e in ex.get("data", []):
        det = api(f"/executions/{e['id']}?includeData=true")
        run = (((det.get("data") or {}).get("resultData") or {})
               .get("runData") or {})
        if not run or "Webhook" not in run:
            continue
        print("=" * 72)
        print(f"EJECUCION {e['id']} | {e['status']}")
        print("=" * 72)
        if "Normalizacion" in run:
            for it in ((run["Normalizacion"][0].get("data") or {})
                       .get("main") or [[]])[0]:
                j = it.get("json", {})
                print("cliente:", repr(str(j.get("message_content", ""))[:130]))
        print("herramientas:",
              [k for k in run if k in
               ("Consultar agenda", "Agendar cita", "Cancelar cita",
                "Reagendar", "Registrar en hoja de citas",
                "Notificar al encargado")] or "(ninguna)")
        if "Consultar agenda" in run:
            t = json.dumps(run["Consultar agenda"], ensure_ascii=False)
            if "NodeApiError" in t:
                i = t.find("message")
                print("  ERROR consultar:", t[i:i + 220])
        if "Registrar en hoja de citas" in run:
            it = run["Registrar en hoja de citas"][0]
            if "error" in it:
                print("  ERROR sheets:", json.dumps(it["error"],
                                                    ensure_ascii=False)[:250])
        f = []
        if "AI Agent" in run:
            textos(run["AI Agent"], f)
        if f:
            print("respuesta:", f[0].replace("\n", " ")[:300])
        break
    return 0


if __name__ == "__main__":
    sys.exit(main())
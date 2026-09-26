#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verifica las 4 pruebas del router de comandos.

Comprueba, para cada ejecucion:
  - si el remitente era operador
  - por que camino fue (router vs agente)
  - si llamo a la IA (coste de tokens) o no
  - el texto de respuesta
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


def textos(o, fuera, prof=0):
    if prof > 12:
        return
    if isinstance(o, dict):
        for k, v in o.items():
            if k in ("output", "respuesta") and isinstance(v, str) and len(v) > 5:
                fuera.append(v)
            else:
                textos(v, fuera, prof + 1)
    elif isinstance(o, list):
        for v in o[:20]:
            textos(v, fuera, prof + 1)


def main():
    ex = api("/executions?workflowId=barberiaAgenteUncensored&limit=12")
    filas = []
    for e in ex.get("data", []):
        try:
            det = api(f"/executions/{e['id']}?includeData=true")
        except Exception:
            continue
        run = (((det.get("data") or {}).get("resultData") or {})
               .get("runData") or {})
        if "¿Es operador?" not in run:
            continue
        dicho = ""
        if "Normalizacion" in run:
            for it in ((run["Normalizacion"][0].get("data") or {})
                       .get("main") or [[]])[0]:
                j = it.get("json", {})
                dicho = str(j.get("message_content", "")).strip()
                jid = str(j.get("user_number", ""))
        sal = []
        textos(run, sal)
        filas.append({
            "id": e["id"],
            "dicho": dicho,
            "jid": jid.split("@")[0],
            "uso_ia": "AI Agent" in run,
            "router": "Router de comandos" in run,
            "respondio": "Responder al operador" in run,
            "respuesta": sal[0] if sal else "",
            "nodos": list(run.keys()),
        })

    print("=" * 74)
    print(f"EJECUCIONES CON EL ROUTER: {len(filas)}")
    print("=" * 74)
    for f in filas:
        print(f"\n[{f['id']}] de {f['jid']}: {f['dicho']!r}")
        print(f"   paso por router : {f['router']}")
        print(f"   llamo a la IA   : {f['uso_ia']}  "
              f"{'(coste 0)' if not f['uso_ia'] else '(uso tokens)'}")
        print(f"   respondio       : {f['respondio']}")
        if f["respuesta"]:
            print(f"   respuesta       : {f['respuesta'][:220]}")

    print()
    print("=" * 74)
    print("VEREDICTO")
    print("=" * 74)
    if not filas:
        print("  no encontre ejecuciones del router")
        return 1
    for f in filas:
        d = f["dicho"].upper()
        if d == "COMANDOS":
            ok = f["router"] and not f["uso_ia"] and "COMANDOS" in f["respuesta"].upper()
            print(f"  {'OK  ' if ok else 'MAL '} COMANDOS del dueño "
                  f"-> menu sin usar IA")
        elif d == "HOY":
            if f["jid"] == "5215520894522":
                print(f"  {'OK  ' if f['router'] else 'MAL '} HOY del dueño "
                      f"-> router (comando pendiente)")
            else:
                ok = not f["router"] and f["uso_ia"]
                print(f"  {'OK  ' if ok else 'MAL '} HOY del CLIENTE "
                      f"-> atendido por el agente, sin ejecutar comando")
        elif d == "HOLA":
            ok = f["router"] and f["uso_ia"]
            print(f"  {'OK  ' if ok else 'MAL '} 'hola' del dueño "
                  f"-> fallback al agente")
    return 0


if __name__ == "__main__":
    sys.exit(main())
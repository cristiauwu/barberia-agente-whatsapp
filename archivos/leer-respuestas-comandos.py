#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lee las respuestas que dio el sistema a cada comando del dueño.

Para cada comando comprueba:
  - que llegó al router
  - si usó la IA (coste de tokens) o no
  - el texto exacto de la respuesta
  - si respetó el formato de WhatsApp (un asterisco, no dos)
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


def buscar_respuesta(o, fuera, prof=0):
    if prof > 14:
        return
    if isinstance(o, dict):
        if "respuesta" in o and isinstance(o["respuesta"], str) and o["respuesta"]:
            fuera.append(o["respuesta"])
        for v in o.values():
            buscar_respuesta(v, fuera, prof + 1)
    elif isinstance(o, list):
        for v in o[:25]:
            buscar_respuesta(v, fuera, prof + 1)


def main():
    ex = api("/executions?workflowId=barberiaAgenteUncensored&limit=20")
    filas = []
    for e in ex.get("data", []):
        try:
            det = api(f"/executions/{e['id']}?includeData=true")
        except Exception:
            continue
        run = (((det.get("data") or {}).get("resultData") or {})
               .get("runData") or {})
        if "Router de comandos" not in run:
            continue
        dicho = ""
        if "Normalizacion" in run:
            for it in ((run["Normalizacion"][0].get("data") or {})
                       .get("main") or [[]])[0]:
                dicho = str(it.get("json", {}).get("message_content", "")).strip()
        fuera = []
        buscar_respuesta(run, fuera)
        resp = fuera[0] if fuera else ""
        errores = []
        for nombre, datos in run.items():
            for it in (datos if isinstance(datos, list) else []):
                if isinstance(it, dict) and "error" in it:
                    errores.append(f"{nombre}: "
                                   f"{json.dumps(it['error'])[:110]}")
        filas.append({
            "id": e["id"], "dicho": dicho,
            "ia": "AI Agent" in run,
            "resp": resp,
            "nodos": [k for k in run if k not in
                      ("Webhook", "Normalizacion", "¿Es operador?",
                       "Router de comandos")],
            "err": errores,
        })

    print("=" * 76)
    print(f"RESPUESTAS DE LOS COMANDOS ({len(filas)})")
    print("=" * 76)
    for f in reversed(filas):
        print(f"\n[{f['id']}] *{f['dicho']}*")
        print(f"   usó IA: {'SÍ' if f['ia'] else 'NO (coste 0)'}")
        print(f"   pasos: {', '.join(f['nodos'][:6])}")
        if f["err"]:
            for x in f["err"]:
                print(f"   ERROR {x}")
        print(f"   ---")
        for linea in (f["resp"] or "(sin respuesta)").split("\n"):
            print(f"   {linea}")

    print()
    print("=" * 76)
    print("VEREDICTO")
    print("=" * 76)
    problemas = 0
    for f in reversed(filas):
        d = f["dicho"].upper()
        ok = bool(f["resp"]) and not f["err"]
        marca = "OK  " if ok else "MAL "
        if not ok:
            problemas += 1
        print(f"  {marca}{f['dicho']:<28} "
              f"{'respondió' if f['resp'] else 'SIN RESPUESTA'}"
              f"{' + error' if f['err'] else ''}")
        if "**" in (f["resp"] or ""):
            print("        MAL contiene ** (markdown que WhatsApp no lee)")
            problemas += 1

    print()
    print(f"problemas: {problemas}")
    return 0 if problemas == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
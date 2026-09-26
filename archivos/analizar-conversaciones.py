#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Recopila conversaciones REALES de WhatsApp para analizar el estilo del
agente antes de reescribir el prompt.

Muestra: lo que dijo el cliente, la respuesta del agente, y si uso
herramientas. Sirve para detectar problemas de tono, longitud y formato.
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


def primeros_textos(o, fuera, prof=0):
    if prof > 12:
        return
    if isinstance(o, dict):
        for k, v in o.items():
            if k in ("output",) and isinstance(v, str) and len(v) > 10:
                fuera.append(v)
            else:
                primeros_textos(v, fuera, prof + 1)
    elif isinstance(o, list):
        for v in o[:20]:
            primeros_textos(v, fuera, prof + 1)


def main():
    ex = api("/executions?workflowId=barberiaAgenteUncensored&limit=30")
    pares = []
    for e in ex.get("data", []):
        try:
            det = api(f"/executions/{e['id']}?includeData=true")
        except Exception:
            continue
        run = (((det.get("data") or {}).get("resultData") or {})
               .get("runData") or {})
        if "AI Agent" not in run:
            continue

        dicho = ""
        if "Normalizacion" in run:
            for it in ((run["Normalizacion"][0].get("data") or {})
                       .get("main") or [[]])[0]:
                dicho = str(it.get("json", {}).get("message_content", "")).strip()

        sal = []
        primeros_textos(run["AI Agent"], sal)
        respuesta = sal[0].strip() if sal else ""

        usadas = [k for k in run if k in
                  ("Consultar agenda", "Agendar cita", "Cancelar cita",
                   "Reagendar", "Registrar en hoja de citas",
                   "Notificar al encargado")]

        if dicho or respuesta:
            pares.append((e["id"], dicho, respuesta, usadas))

    print("=" * 76)
    print(f"CONVERSACIONES REALES ENCONTRADAS: {len(pares)}")
    print("=" * 76)
    for eid, dicho, resp, usadas in pares:
        print(f"\n[{eid}]")
        print(f"  CLIENTE : {dicho[:150]}")
        print(f"  AGENTE  : {resp[:400]}")
        if usadas:
            print(f"  HERRAM  : {', '.join(usadas)}")
        print(f"  largo respuesta: {len(resp)} caracteres | "
              f"lineas: {resp.count(chr(10)) + 1}")

    # Metricas para guiar la mejora
    if pares:
        largos = [len(r) for _, _, r, _ in pares if r]
        emojis = sum(1 for _, _, r, _ in pares if any(
            ord(c) > 0x2190 for c in r))
        print()
        print("=" * 76)
        print("METRICAS")
        print("=" * 76)
        print(f"  respuestas analizadas : {len(largos)}")
        print(f"  largo promedio        : {sum(largos)//max(1,len(largos))} car.")
        print(f"  largo maximo          : {max(largos) if largos else 0} car.")
        print(f"  con emoji/negrita     : {emojis} de {len(largos)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
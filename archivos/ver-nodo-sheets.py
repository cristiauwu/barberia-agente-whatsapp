#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Muestra la respuesta EXACTA del nodo de Sheets y de Calendar."""
import json
import os
import sys
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

N8N = "http://localhost:5678/api/v1"
KEY = os.environ.get("N8N_API_KEY", os.environ.get("N8N_KEY", ""))


def api(p):
    r = urllib.request.Request(N8N + p)
    r.add_header("X-N8N-API-KEY", KEY)
    with urllib.request.urlopen(r, timeout=60) as x:
        return json.loads(x.read().decode())


def main():
    det = api("/executions/566?includeData=true")
    run = (((det.get("data") or {}).get("resultData") or {}).get("runData") or {})

    for h in ("Registrar en hoja de citas",):
        print("=" * 74)
        print(h)
        print("=" * 74)
        if h not in run:
            print("  no corrio")
            continue
        intento = run[h][0]
        # Salida del nodo
        salida = ((intento.get("data") or {}).get("main") or [[]])[0]
        print(f"  items de salida: {len(salida)}")
        for it in salida[:2]:
            print("  ", json.dumps(it.get("json", {}), ensure_ascii=False)[:500])

        # Si hay error
        if "error" in intento:
            print("  ERROR:", json.dumps(intento["error"], ensure_ascii=False)[:400])

        # La configuracion usada
        params = (intento.get("source") or [])
        print("  source:", json.dumps(params, ensure_ascii=False)[:200])

    print()
    print("=" * 74)
    print("Entrada que recibio el nodo de Sheets (lo que intento escribir)")
    print("=" * 74)
    if "Registrar en hoja de citas" in run:
        it = run["Registrar en hoja de citas"][0]
        entrada = ((it.get("inputOverride") or {}).get("main") or [[]])[0]
        if entrada:
            for x in entrada[:1]:
                print(" ", json.dumps(x, ensure_ascii=False)[:600])
        else:
            print("  (sin inputOverride; ver executionData)")

    # Buscar datos de entrada del nodo AI Agent (lo que propuso el modelo)
    print()
    print("=" * 74)
    print("Argumentos que el modelo paso a la herramienta")
    print("=" * 74)
    txt = json.dumps(run.get("Registrar en hoja de citas"), ensure_ascii=False)
    for marca in ("Estatus", "Nombre", "Servicio", "Dia", "Hora",
                  "Precio_del_servicio", "Numero"):
        i = txt.find(marca)
        if i > 0:
            print(f"  {marca}: ...{txt[i:i+130]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
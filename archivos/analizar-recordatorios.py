#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analiza el workflow de recordatorios: nodos huerfanos y cableado real.

Un nodo 'suelto' puede ser:
  a) una herramienta de agente (no necesita entrada main), o
  b) un nodo realmente desconectado -> bug de verdad.
"""
import json
import os
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
os.environ["DOCKER_CONFIG"] = r"G:\Barberia\.docker"
WID = "barberiaRecordatorios"


def export(wid):
    rem = f"/tmp/{wid}-an.json"
    loc = rf"G:\Barberia\archivos\an-{wid}.json"
    subprocess.run([DOCKER, "exec", "barberia-n8n", "n8n", "export:workflow",
                    f"--id={wid}", f"--output={rem}"], capture_output=True)
    subprocess.run([DOCKER, "cp", f"barberia-n8n:{rem}", loc],
                   capture_output=True)
    d = json.load(open(loc, encoding="utf-8"))
    return d[0] if isinstance(d, list) else d


def main():
    wf = export(WID)
    nodos = wf["nodes"]
    conns = wf["connections"]

    # Quien recibe conexiones
    destino = set()
    origen = set()
    for src, ramas in conns.items():
        origen.add(src)
        for salidas in ramas.values():
            for grupo in salidas:
                for c in grupo:
                    destino.add(c["node"])

    print("=" * 74)
    print("NODOS SIN ENTRADA (nadie les manda datos)")
    print("=" * 74)
    for n in nodos:
        nombre = n["name"]
        tipo = n["type"]
        es_trigger = "Trigger" in tipo or tipo.endswith(".webhook") or \
                     "manualTrigger" in tipo
        tiene_entrada = nombre in destino
        if not tiene_entrada and not es_trigger:
            print(f"  ⚠ {nombre:<34} [{tipo.replace('n8n-nodes-base.','')}]")
    print("  (si no aparece nada, todos reciben datos)")

    print()
    print("=" * 74)
    print("NODOS SIN SALIDA (no llevan a ningun lado)")
    print("=" * 74)
    for n in nodos:
        nombre = n["name"]
        if nombre not in origen:
            print(f"  ⚠ {nombre:<34} [{n['type'].replace('n8n-nodes-base.','')}]")
    print("  (los nodos finales es normal que no tengan salida)")

    print()
    print("=" * 74)
    print("CABLEADO COMPLETO")
    print("=" * 74)
    for src, ramas in conns.items():
        for tipo, salidas in ramas.items():
            for i, grupo in enumerate(salidas):
                if not grupo:
                    print(f"  {src}  [salida {i}] -> (vacia)")
                    continue
                for c in grupo:
                    print(f"  {src}  [salida {i}] -> {c['node']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
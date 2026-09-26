#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Muestra la respuesta del agente y los errores de las ejecuciones."""
import json
import os
import subprocess
import sys

DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
os.environ["DOCKER_CONFIG"] = r"G:\Barberia\.docker"


def psql(sql):
    p = subprocess.run([DOCKER, "exec", "barberia-postgres", "psql", "-U",
                        "barberia", "-d", "barberia", "-t", "-A", "-c", sql],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return (p.stdout or "").strip()


def main():
    print("=" * 74)
    print("SALIDA DEL AGENTE (ejecuciones exitosas)")
    print("=" * 74)
    for eid in psql("SELECT string_agg(id::text, ',') FROM (SELECT id FROM execution_entity WHERE status='success' ORDER BY id DESC LIMIT 3) s;").split(","):
        eid = eid.strip()
        if not eid:
            continue
        out = psql(f"""SELECT left("data"::text, 3000) FROM execution_data
                       WHERE "executionId" = {eid};""")
        # Buscar el texto que devolvio el AI Agent
        idx = out.find("Listo")
        if idx < 0:
            idx = out.find("cuesta")
        if idx < 0:
            idx = out.find("Hola")
        print(f"\n--- ejecucion {eid} ---")
        if idx >= 0:
            print("  ", out[max(0, idx - 120):idx + 400].replace("\\n", " ")[:500])
        else:
            print("  (no encontre texto de respuesta)")

    print()
    print("=" * 74)
    print("ERRORES")
    print("=" * 74)
    for eid in psql("SELECT string_agg(id::text, ',') FROM (SELECT id FROM execution_entity WHERE status='error' ORDER BY id DESC LIMIT 2) s;").split(","):
        eid = eid.strip()
        if not eid:
            continue
        out = psql(f"""SELECT left("data"::text, 4000) FROM execution_data
                       WHERE "executionId" = {eid};""")
        print(f"\n--- ejecucion {eid} ---")
        for clave in ("message\\\":\\\"", '"message"'):
            i = out.find(clave)
            if i >= 0:
                print("  ", out[i:i + 350])
                break
        else:
            print("  (sin mensaje legible)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extrae el error legible de las ejecuciones fallidas de n8n."""
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
    # Id de las ejecuciones fallidas mas recientes
    ids = psql("""SELECT string_agg(id::text, ',') FROM (
                    SELECT id FROM execution_entity
                    WHERE status='error'
                    ORDER BY id DESC LIMIT 2) s;""")
    if not ids:
        print("No hay ejecuciones fallidas.")
        return 0

    for eid in ids.split(","):
        eid = eid.strip()
        print("=" * 74)
        print("EJECUCION", eid)
        print("=" * 74)
        # El nodo que fallo
        nodo = psql(f"""SELECT left(regexp_replace("data"::text,
                '.*"lastNodeExecuted"\\s*:\\s*"([^"]*)".*', '\\1'), 200)
                FROM execution_data WHERE "executionId" = {eid};""")
        print("  ultimo nodo:", nodo)

        # El mensaje de error dentro de resultData.error
        err = psql(f"""SELECT "data"::text FROM execution_data
                       WHERE "executionId" = {eid};""")
        try:
            # Buscar el bloque de error en el texto crudo
            idx = err.find('"error"')
            if idx >= 0:
                frag = err[idx:idx + 1500]
                print("  fragmento de error:")
                print("   ", frag[:900])
        except Exception as e:
            print("  no pude parsear:", e)
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
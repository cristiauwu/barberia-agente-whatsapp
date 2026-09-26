#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parsea execution_data correctamente para extraer el error real.

n8n guarda el JSON con referencias numericas internas; se localiza el
nodo que fallo dentro de runData y se lee su bloque de error.
"""
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
    eid = sys.argv[1] if len(sys.argv) > 1 else "15"
    raw = psql(f'SELECT "data"::text FROM execution_data WHERE "executionId"={eid};')
    try:
        d = json.loads(raw)
    except Exception as e:
        print("no parseable:", e)
        print(raw[:600])
        return 1

    # d suele ser una lista: [ {...,"resultData":...}, ... ] con referencias
    def resolver(obj, nivel=0):
        """Convierte la estructura con indices a algo legible."""
        return obj

    # Estrategia: reconstruir sustituyendo indices
    if isinstance(d, list):
        print("elementos en la raiz:", len(d))
        for i, el in enumerate(d):
            if not isinstance(el, dict):
                continue
            rd = el.get("resultData")
            if isinstance(rd, dict) and rd.get("error"):
                err = rd["error"]
                print("\n--- resultData.error ---")
                if isinstance(err, dict):
                    for k, v in err.items():
                        print(f"  {k}: {str(v)[:300]}")
                else:
                    print("  ", str(err)[:300])
            if isinstance(rd, dict) and rd.get("runData"):
                rd2 = rd["runData"]
                print("\n--- runData (nodos ejecutados) ---")
                if isinstance(rd2, dict):
                    for nombre, val in rd2.items():
                        txt = json.dumps(val, ensure_ascii=False)
                        if "error" in txt.lower():
                            print(f"\n  NODO CON ERROR: {nombre}")
                            print("   ", txt[:900])
    return 0


if __name__ == "__main__":
    sys.exit(main())
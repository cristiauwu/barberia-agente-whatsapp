#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Resuelve las referencias numericas de execution_data de n8n.

n8n serializa con 'flatted': un array donde los objetos se referencian
por indice numerico. Hay que expandirlo para leer el error real.
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


def unflatten(data):
    """Reconstruye la estructura de 'flatted' (referencias por indice)."""
    if not isinstance(data, list):
        return data
    cache = {}

    def build(i, depth=0):
        if depth > 60:
            return None
        if i in cache:
            return cache[i]
        v = data[i] if 0 <= i < len(data) else None
        if isinstance(v, dict):
            obj = {}
            cache[i] = obj
            for k, val in v.items():
                obj[k] = build(val, depth + 1) if isinstance(val, int) else val
            return obj
        if isinstance(v, list):
            lst = []
            cache[i] = lst
            for val in v:
                lst.append(build(val, depth + 1) if isinstance(val, int) else val)
            return lst
        return v

    return build(0)


def main():
    eid = sys.argv[1] if len(sys.argv) > 1 else "15"
    raw = psql(f'SELECT "data"::text FROM execution_data WHERE "executionId"={eid};')
    try:
        d = json.loads(raw)
    except Exception as e:
        print("no parseable:", e)
        return 1

    # El objeto raiz suele ser data[0] (un dict con referencias)
    raiz = d[0] if isinstance(d, list) and d and isinstance(d[0], dict) else d
    res = {}
    for k, v in (raiz.items() if isinstance(raiz, dict) else []):
        res[k] = d[v] if isinstance(v, int) and v < len(d) else v

    rd = res.get("resultData")
    if isinstance(rd, int) and rd < len(d):
        rd = d[rd]
    if isinstance(rd, int):
        rd = d[rd]

    print("=" * 74)
    print("EJECUCION", eid)
    print("=" * 74)
    if isinstance(rd, dict):
        err = rd.get("error")
        if isinstance(err, int):
            err = d[err]
        if isinstance(err, dict):
            print("\n--- ERROR ---")
            for k in ("name", "message", "description", "httpCode"):
                if k in err:
                    v = err[k]
                    if isinstance(v, int):
                        v = d[v]
                    print(f"  {k}: {str(v)[:300]}")
        last = rd.get("lastNodeExecuted")
        if isinstance(last, int):
            last = d[last]
        print("\n  ultimo nodo:", last)
    else:
        print("resultData no es dict:", type(rd))
    return 0


if __name__ == "__main__":
    sys.exit(main())
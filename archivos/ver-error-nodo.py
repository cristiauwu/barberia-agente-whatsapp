#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extrae el mensaje de error concreto del nodo 'Mandar mensaje'."""
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
    eid = psql("SELECT id FROM execution_entity WHERE status='error' ORDER BY id DESC LIMIT 1;")
    print("Ejecucion con error:", eid)
    raw = psql(f'SELECT "data"::text FROM execution_data WHERE "executionId" = {eid};')
    if not raw:
        print("sin datos")
        return 1

    # El error de nodo suele traer 'description' con el detalle real
    for marca in ('"description"', 'ECONNREFUSED', 'ENOTFOUND', 'ETIMEDOUT',
                  'statusCode', 'connect', 'not found', '404', '401'):
        i = raw.find(marca)
        if i >= 0:
            print(f"\n  [{marca}] encontrado en pos {i}:")
            print("   ", raw[max(0, i - 200):i + 400].replace("\\n", " ")[:600])

    # Intentar localizar el texto legible del error de axios/fetch
    for marca in ('getaddrinfo', 'ENOTFOUND', 'ECONNREFUSED', 'certificate',
                  'timeout', 'Invalid URL', 'connect ETIMEDOUT'):
        if marca in raw:
            print(f"\n  >>> contiene: {marca}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
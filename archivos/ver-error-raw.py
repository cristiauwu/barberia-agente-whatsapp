#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vuelca la seccion de error de execution_data de forma legible."""
import json
import os
import re
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
    eid = "15"
    raw = psql(f'SELECT "data"::text FROM execution_data WHERE "executionId"={eid};')
    print("longitud total:", len(raw))

    # El error real suele estar cerca de "description" o "httpCode"
    for marca in ("description", "httpCode", "ECONNREFUSED", "errno",
                  "code", "syscall", "address", "port"):
        for m in re.finditer(r'"%s":"?([^,"]{0,120})' % marca, raw):
            print(f"  {marca}: {m.group(1)[:120]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
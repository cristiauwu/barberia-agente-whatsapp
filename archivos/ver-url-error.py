#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extrae la URL exacta que intento llamar el nodo 'Mandar mensaje'."""
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
    for eid in ("16", "15", "12"):
        raw = psql(f'SELECT "data"::text FROM execution_data WHERE "executionId"={eid};')
        print("=" * 74)
        print("EJECUCION", eid)
        print("=" * 74)
        # URLs http(s) mencionadas
        urls = set(re.findall(r"https?://[A-Za-z0-9_.:\-]+(?:/[A-Za-z0-9_\-/]*)?", raw))
        for u in sorted(urls):
            if "n8n" in u or "evolution" in u or "8080" in u or "5678" in u:
                print("   URL:", u)
        # el valor de server_url usado
        for m in re.finditer(r"server_url[^,]{0,80}", raw):
            print("   server_url:", m.group(0)[:100])
        # mensaje de error del nodo
        m = re.search(r'"message":"([^"]{0,200})"', raw)
        if m:
            print("   message:", m.group(1)[:200])
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
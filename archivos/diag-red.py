#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Diagnostica si n8n puede alcanzar Evolution con distintos nombres.

El nodo 'Mandar mensaje' usa el campo server_url que viene en el payload
del webhook. Si Evolution anuncia 'localhost:8080', desde dentro del
contenedor de n8n eso apunta a n8n mismo -> ECONNREFUSED.
"""
import os
import subprocess
import sys

DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
os.environ["DOCKER_CONFIG"] = r"G:\Barberia\.docker"


def node_eval(container, url):
    """Ejecuta un fetch dentro del contenedor, sin problemas de comillas."""
    js = (
        "fetch('%s/')"
        ".then(r => console.log('%s -> HTTP ' + r.status))"
        ".catch(e => console.log('%s -> FALLA: ' + e.message));"
    ) % (url, url, url)
    p = subprocess.run([DOCKER, "exec", container, "node", "-e", js],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    out = (p.stdout or "").strip()
    err = (p.stderr or "").strip()
    return out or err[:200]


def main():
    print("=" * 74)
    print("DESDE EL CONTENEDOR DE N8N, A DONDE PUEDE LLEGAR")
    print("=" * 74)
    for url in ("http://localhost:8080", "http://127.0.0.1:8080",
                "http://evolution_api:8080"):
        print(f"  {node_eval('barberia-n8n', url)}")

    print()
    print("=" * 74)
    print("DESDE EL CONTENEDOR DE EVOLUTION")
    print("=" * 74)
    for url in ("http://localhost:8080", "http://barberia-n8n:5678"):
        print(f"  {node_eval('evolution_api', url)}")

    print()
    print("=" * 74)
    print("QUE ANUNCIA EVOLUTION EN SU PAYLOAD (server_url)")
    print("=" * 74)
    p = subprocess.run([DOCKER, "exec", "evolution_api", "printenv",
                        "SERVER_URL"], capture_output=True, text=True)
    print("  SERVER_URL =", (p.stdout or "").strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
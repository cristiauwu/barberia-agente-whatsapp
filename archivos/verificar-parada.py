#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Comprueba que el bucle se detuvo tras desactivar el workflow."""
import os
import subprocess
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
os.environ["DOCKER_CONFIG"] = r"G:\Barberia\.docker"


def psql(sql):
    p = subprocess.run([DOCKER, "exec", "barberia-postgres", "psql", "-U",
                        "barberia", "-d", "barberia", "-t", "-A", "-c", sql],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return (p.stdout or "").strip()


def main():
    a = psql("SELECT count(*) FROM execution_entity;")
    print("ejecuciones AHORA      :", a)
    time.sleep(30)
    b = psql("SELECT count(*) FROM execution_entity;")
    print("ejecuciones +30s       :", b)
    delta = int(b) - int(a)
    print()
    if delta == 0:
        print(">>> EL BUCLE SE DETUVO (0 ejecuciones nuevas en 30s)")
    else:
        print(f">>> AUN HAY ACTIVIDAD: {delta} ejecuciones nuevas en 30s")

    print()
    print("=== ventana de tiempo del bucle ===")
    print(psql("""SELECT '  primera: ' || min("startedAt")::text
                  || '  |  ultima: ' || max("startedAt")::text
                  FROM execution_entity
                  WHERE "workflowId"='barberiaAgenteUncensored';"""))
    print(psql("""SELECT '  ejecuciones con error: ' || count(*)
                  FROM execution_entity
                  WHERE "workflowId"='barberiaAgenteUncensored'
                  AND status='error';"""))
    print(psql("""SELECT '  ejecuciones exitosas: ' || count(*)
                  FROM execution_entity
                  WHERE "workflowId"='barberiaAgenteUncensored'
                  AND status='success';"""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
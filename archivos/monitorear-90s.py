#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Monitorea 90s para confirmar que no vuelve el bucle."""
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
    a = int(psql("SELECT count(*) FROM execution_entity;"))
    print("inicio:", a)
    for i in range(6):
        time.sleep(15)
        b = int(psql("SELECT count(*) FROM execution_entity;"))
        print(f"  +{(i+1)*15:>3}s: {b}  (nuevas: {b - a})")
    print()
    if b - a == 0:
        print(">>> SIN BUCLE: 0 ejecuciones en 90 segundos.")
        print("    El agente esta en espera, listo para recibir mensajes.")
    elif b - a <= 3:
        print(f">>> Practicamente limpio: solo {b - a} ejecuciones (esperado 0).")
    else:
        print(f">>> AUN HAY ACTIVIDAD: {b - a} ejecuciones en 90s.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
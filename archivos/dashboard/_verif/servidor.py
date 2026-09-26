#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pruebas del servidor-dashboard.py. Todo escribe a un archivo de log;
nada lee de tuberias de procesos hijos (eso cuelga en este harness)."""
from __future__ import annotations

import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

LOG = Path(r"G:\Barberia\archivos\dashboard\_verif\_salida-servidor.txt")
out = open(LOG, "w", encoding="utf-8")


def w(*a):
    print(*a)
    print(*a, file=out)
    out.flush()


UV = r"C:\Users\kimbo\.cherrystudio\bin\uv.exe"
SRV = r"G:\Barberia\archivos\dashboard\servidor-dashboard.py"
TMP = Path(r"G:\Barberia\archivos\dashboard\_verif")
LOG1 = TMP / "_srv1.out"
LOG2 = TMP / "_srv2.out"


def arrancar(puerto, log):
    f = open(log, "w", encoding="utf-8")
    return subprocess.Popen(
        [UV, "run", "python", SRV, "--puerto", str(puerto), "--intervalo", "0"],
        stdout=f, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
        errors="replace")


def pedir(url, method="GET"):
    req = urllib.request.Request(url, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            cuerpo = r.read()
            return r.status, len(cuerpo)
    except urllib.error.HTTPError as e:
        return e.code, len(e.read())
    except Exception as e:
        return "ERR", str(e)[:80]


w("=" * 72)
w("A) PUERTO OCUPADO")
w("=" * 72)
p1 = arrancar(8101, LOG1)
time.sleep(14)
w("  servidor 1 vivo?", p1.poll() is None)
p2 = arrancar(8101, LOG2)
time.sleep(14)
w("  servidor 2 termino? rc =", p2.poll())
w("  --- stdout/stderr del SEGUNDO servidor ---")
for l in LOG2.read_text(encoding="utf-8", errors="replace").splitlines():
    w("  |", l)
w("  HTTP 8101 (debe seguir el primero):", pedir("http://127.0.0.1:8101/"))
p1.terminate()
try:
    p1.wait(timeout=15)
except Exception:
    p1.kill()
time.sleep(2)

w("")
w("=" * 72)
w("B) PATH TRAVERSAL / ARCHIVOS FUERA DEL PANEL")
w("=" * 72)
p3 = arrancar(8102, LOG1)
time.sleep(14)
rutas = ["/", "/index.html", "/dashboard.html", "/dashboard.html?v=1",
         "/../.env", "/..%2f.env", "/%2e%2e/.env", "/../generar-dashboard.py",
         "/capturas/datos-escritorio-1.png", "/README.md",
         "/C:/Windows/win.ini", "/etc/passwd", "/dashboard.html/../.env",
         "//../.env", "/%2e%2e%2f.env"]
for r in rutas:
    w(f"  GET {r:38s} -> {pedir('http://127.0.0.1:8102' + r)}")
w("  HEAD / ->", pedir("http://127.0.0.1:8102/", "HEAD"))
w("  POST / ->", pedir("http://127.0.0.1:8102/", "POST"))
p3.terminate()
try:
    p3.wait(timeout=15)
except Exception:
    p3.kill()
time.sleep(2)

w("")
w("=" * 72)
w("C) --una-vez")
w("=" * 72)
L3 = TMP / "_srv3.out"
with open(L3, "w", encoding="utf-8") as f:
    r = subprocess.run([UV, "run", "python", SRV, "--una-vez"],
                       stdout=f, stderr=subprocess.STDOUT, timeout=300)
w("  rc =", r.returncode)
for l in L3.read_text(encoding="utf-8", errors="replace").splitlines()[-6:]:
    w("  |", l)

w("")
w("=" * 72)
w("D) ZONA HORARIA DEL SERVIDOR: usa hora local de Windows?")
w("=" * 72)
import datetime
w("  hora local Windows:", datetime.datetime.now().isoformat())
w("  hora UTC          :", datetime.datetime.utcnow().isoformat())
w("  -> el panel toma la fecha de POSTGRES (SET TIME ZONE), no de Python.")

out.close()
print("LOG:", LOG)
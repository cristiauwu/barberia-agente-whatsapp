#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Confirmacion acotada: dos servidores en el MISMO puerto."""
from __future__ import annotations

import subprocess
import time
import urllib.request
from pathlib import Path

UV = r"C:\Users\kimbo\.cherrystudio\bin\uv.exe"
SRV = r"G:\Barberia\archivos\dashboard\servidor-dashboard.py"
TMP = Path(r"G:\Barberia\archivos\dashboard\_verif")
LOG = TMP / "_salida-puerto.txt"
out = open(LOG, "w", encoding="utf-8")


def w(*a):
    print(*a)
    print(*a, file=out)
    out.flush()


def arrancar(puerto, log):
    f = open(log, "w", encoding="utf-8")
    return subprocess.Popen([UV, "run", "python", SRV, "--puerto", "8111",
                             "--intervalo", "0"],
                            stdout=f, stderr=subprocess.STDOUT, text=True,
                            encoding="utf-8", errors="replace")


L1, L2 = TMP / "_p1.out", TMP / "_p2.out"
w("arrancando servidor 1 en 8111...")
p1 = arrancar(8111, L1)
time.sleep(12)
w("  p1 vivo:", p1.poll() is None)
w("  p1 dijo:")
for l in L1.read_text(encoding="utf-8", errors="replace").splitlines():
    w("   |", l)

w("arrancando servidor 2 en 8111 (mismo puerto)...")
p2 = arrancar(8111, L2)
time.sleep(12)
w("  p2 termino? rc =", p2.poll(), " (None = SIGUE VIVO)")
w("  p2 dijo:")
for l in L2.read_text(encoding="utf-8", errors="replace").splitlines():
    w("   |", l)

w("")
w("  *** DIAGNOSTICO ***")
w("  allow_reuse_address = True en Windows deja que un SEGUNDO proceso")
w("  haga bind del MISMO puerto y quede vivo. El bloque 'except OSError'")
w("  que imprime 'no pude abrir el puerto' NUNCA se ejecuta.")
w("  p1 vivo:", p1.poll() is None, " p2 vivo:", p2.poll() is None)
try:
    with urllib.request.urlopen("http://127.0.0.1:8111/", timeout=8) as r:
        w("  HTTP 8111 ->", r.status, len(r.read()), "bytes")
except Exception as e:
    w("  HTTP 8111 ERR:", e)

for p in (p1, p2):
    p.terminate()
for p in (p1, p2):
    try:
        p.wait(timeout=8)
    except Exception:
        p.kill()
out.close()
print("LISTO")
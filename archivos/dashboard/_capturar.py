#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Herramienta interna de captura (no forma parte del entregable).

Sirve la carpeta del dashboard por HTTP y usa Chrome headless para capturar:
  - escritorio 1440px
  - movil real 390px (via iframe sobre HTTP, porque Chrome fuerza min 504px)

Uso:
  uv run python _capturar.py <prefijo>
"""
from __future__ import annotations

import functools
import http.server
import json
import os
import re
import socketserver
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

AQUI = Path(__file__).resolve().parent
CAPTURAS = AQUI / "capturas"
PUERTO = 8123
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


def perfil_temporal() -> str:
    return tempfile.mkdtemp(prefix="capseg_")


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def servir():
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.ThreadingTCPServer(
        ("127.0.0.1", PUERTO), functools.partial(Handler, directory=str(AQUI)))
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd


def chrome(url: str, salida: Path, ancho: int, alto: int, espera_ms: int = 2500):
    salida.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
        "--no-first-run", "--no-default-browser-check",
        "--force-device-scale-factor=1",
        "--user-data-dir=" + perfil_temporal(),
        "--virtual-time-budget=%d" % espera_ms,
        "--window-size=%d,%d" % (ancho, alto),
        "--screenshot=" + str(salida),
        url,
    ]
    r = subprocess.run(cmd, capture_output=True, timeout=180)
    return r.returncode, (r.stderr or b"").decode("utf-8", "replace")[-400:]


def escribir_movil():
    """Envoltorio con iframe de 390px: Chrome headless no baja de 504px."""
    p = AQUI / "_movil.html"
    p.write_text(
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<style>html,body{margin:0;padding:0;background:#888}"
        "iframe{width:390px;height:3400px;border:0;display:block;margin:0}"
        "</style></head><body>"
        "<iframe src='dashboard.html'></iframe></body></html>", encoding="utf-8")
    return p


def main() -> int:
    prefijo = sys.argv[1] if len(sys.argv) > 1 else "captura"
    httpd = servir()
    try:
        escribir_movil()
        resultados = []
        base = "http://127.0.0.1:%d" % PUERTO

        rc, err = chrome(base + "/dashboard.html",
                         CAPTURAS / ("%s-escritorio.png" % prefijo),
                         1440, 3000)
        resultados.append(("escritorio", rc, err))

        rc, err = chrome(base + "/_movil.html",
                         CAPTURAS / ("%s-movil.png" % prefijo),
                         504, 3500)
        resultados.append(("movil", rc, err))

        for nombre, rc, err in resultados:
            print("%s -> exit %s %s" % (nombre, rc, err[:200]))
    finally:
        httpd.shutdown()
        httpd.server_close()
        m = AQUI / "_movil.html"
        if m.exists():
            m.unlink()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Captura el dashboard en escritorio y movil para revisarlo de verdad.

Usa Chrome headless. OJO: Chrome fuerza un minimo de 504px de ancho de
ventana, asi que para capturar 390px reales se sirve el HTML por HTTP y se
mete en un iframe de 390px dentro de una ventana mas grande.
"""
import base64
import os
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

AQUI = Path(r"G:\Barberia\archivos\dashboard")
SALIDA = AQUI / "capturas"
SALIDA.mkdir(exist_ok=True)

CHROME = None
for cand in (r"C:\Program Files\Google\Chrome\Application\chrome.exe",
             r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
             os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")):
    if os.path.exists(cand):
        CHROME = cand
        break
if not CHROME:
    print("no encontre chrome.exe")
    sys.exit(2)
print(f"chrome: {CHROME}")

HTML = (AQUI / "dashboard.html").read_text(encoding="utf-8")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/marco"):
            # Marco con iframe de 390px para simular un movil real
            ancho = 390
            pagina = (
                "<!DOCTYPE html><html><head><meta charset='utf-8'>"
                "<style>html,body{margin:0;background:#111}"
                f"iframe{{width:{ancho}px;height:2600px;border:0;display:block;"
                "margin:0 auto}}</style></head><body>"
                "<iframe src='/dashboard.html'></iframe></body></html>")
            cuerpo = pagina.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(cuerpo)))
            self.end_headers()
            self.wfile.write(cuerpo)
            return
        cuerpo = HTML.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def log_message(self, *a):
        pass


srv = ThreadingHTTPServer(("127.0.0.1", 8123), Handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
time.sleep(0.5)
print("servidor local en 8123")


def capturar(url, salida, ancho, alto, esperar=2):
    args = [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
            "--hide-scrollbars", "--force-device-scale-factor=1",
            f"--window-size={ancho},{alto}",
            f"--screenshot={salida}", url]
    subprocess.run(args, capture_output=True, timeout=90)
    ok = os.path.exists(salida)
    kb = os.path.getsize(salida) // 1024 if ok else 0
    print(f"  {'OK ' if ok else 'MAL'} {os.path.basename(salida)} ({kb} KB)")
    return ok


print("\n=== capturas ===")
capturar("http://127.0.0.1:8123/dashboard.html",
         str(SALIDA / "despues-escritorio.png"), 1440, 2300)
capturar("http://127.0.0.1:8123/marco",
         str(SALIDA / "despues-movil.png"), 520, 2600)
srv.shutdown()
print(f"\ncapturas en {SALIDA}")
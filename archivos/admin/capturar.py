#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Captura el panel en escritorio y movil para revisarlo.

Chrome headless fuerza un minimo de 504px de ancho, asi que el movil real
(390px) se captura con un iframe dentro de una ventana mayor.
"""
import os
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

AQUI = r"G:\Barberia\archivos\admin"
HTML = os.path.join(AQUI, "barber-chinos-admin.html")
CAPS = os.path.join(AQUI, "capturas")
os.makedirs(CAPS, exist_ok=True)

CHROME = None
for c in (r"C:\Program Files\Google\Chrome\Application\chrome.exe",
          r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"):
    if os.path.exists(c):
        CHROME = c
        break
if not CHROME:
    print("no encontre chrome")
    sys.exit(2)

DATOS = open(HTML, encoding="utf-8").read()


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/movil"):
            ancho = 390
            p = ("<!DOCTYPE html><html><head><meta charset='utf-8'>"
                 "<style>html,body{margin:0;background:#0A0A0A}"
                 f"iframe{{width:{ancho}px;height:4200px;border:0;display:block;"
                 "margin:0 auto}}</style></head><body>"
                 "<iframe src='/panel'></iframe></body></html>")
            cuerpo = p.encode()
        else:
            cuerpo = DATOS.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def log_message(self, *a):
        pass


def main():
    srv = ThreadingHTTPServer(("127.0.0.1", 8137), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    time.sleep(0.6)
    print("  servidor en 8137")

    def cap(url, salida, ancho, alto, espera=5):
        args = [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
                "--hide-scrollbars", "--force-device-scale-factor=1",
                "--virtual-time-budget=9000",
                f"--window-size={ancho},{alto}",
                f"--screenshot={salida}", url]
        subprocess.run(args, capture_output=True, timeout=120)
        ok = os.path.exists(salida)
        kb = os.path.getsize(salida) // 1024 if ok else 0
        print(f"  {'OK ' if ok else 'MAL'} {os.path.basename(salida)} ({kb} KB)")
        return ok

    print("\n=== capturas ===")
    cap("http://127.0.0.1:8137/panel",
        os.path.join(CAPS, "escritorio.png"), 1600, 2600)
    cap("http://127.0.0.1:8137/movil",
        os.path.join(CAPS, "movil.png"), 520, 4200)
    srv.shutdown()
    print(f"\n  en {CAPS}")


if __name__ == "__main__":
    main()
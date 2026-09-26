#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
servidor-dashboard.py - Sirve el panel de la barberia en la red local (Wi-Fi).

QUE HACE
    1. Regenera `dashboard.html` desde Postgres (una vez, al arrancar).
    2. Levanta un servidor HTTP de solo lectura que sirve ese HTML.
    3. Regenera el HTML cada N segundos, para que el dueno vea datos frescos
       sin hacer nada.

POR QUE ASI
    Gratis, local y sin cuentas. No usa tuneles ni servicios publicos:
    la base de datos NUNCA sale de este equipo. El celular del dueno solo
    necesita estar en la misma red Wi-Fi que esta PC.

USO
    uv run python G:\\Barberia\\archivos\\dashboard\\servidor-dashboard.py
    uv run python ...\\servidor-dashboard.py --puerto 8099 --intervalo 120
    uv run python ...\\servidor-dashboard.py --una-vez      (solo genera y sale)

Cuando arranca, imprime las URLs. Abrelas desde el celular conectado al mismo
Wi-Fi. Si no carga, casi siempre es el Firewall de Windows bloqueando el puerto
(ver README.md de esta carpeta).
"""

from __future__ import annotations

import argparse
import http.server
import socket
import socketserver
import subprocess
import sys
import threading
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
GENERADOR = AQUI / "generar-dashboard.py"
HTML = AQUI / "dashboard.html"
PUERTO_DEFECTO = 8099
INTERVALO_DEFECTO = 120


def ip_local() -> str:
    """IP de esta PC en la red local (la que ve el celular)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))          # no envia nada, solo elige la ruta
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def regenerar(silencioso: bool = False) -> bool:
    r = subprocess.run([sys.executable, str(GENERADOR)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("  ! El generador fallo (exit %s):" % r.returncode)
        print("    " + (r.stderr or r.stdout).strip().replace("\n", "\n    "))
        return False
    if not silencioso:
        for linea in r.stdout.strip().splitlines():
            print("  " + linea)
    return True


class Manejador(http.server.SimpleHTTPRequestHandler):
    """Sirve SOLO dashboard.html en la raiz. Nada mas del disco."""

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(AQUI), **kw)

    def _solo_panel(self) -> bool:
        return self.path.split("?")[0] in ("/", "/index.html", "/dashboard.html")

    def do_GET(self):
        if self._solo_panel():
            self.path = "/dashboard.html"
            return super().do_GET()
        self.send_error(404, "Solo existe /dashboard.html")

    def do_HEAD(self):
        if self._solo_panel():
            self.path = "/dashboard.html"
            return super().do_HEAD()
        self.send_error(404, "Solo existe /dashboard.html")

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, must-revalidate")
        super().end_headers()

    def log_message(self, fmt, *args):
        pass          # consola limpia


def bucle_regeneracion(intervalo: int, parar: threading.Event):
    while not parar.wait(intervalo):
        print("  [%s] Regenerando el panel..." % time.strftime("%H:%M:%S"))
        regenerar(silencioso=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="Servidor local del panel de la barberia.")
    ap.add_argument("--puerto", type=int, default=PUERTO_DEFECTO)
    ap.add_argument("--intervalo", type=int, default=INTERVALO_DEFECTO,
                    help="Segundos entre regeneraciones (0 = no regenerar)")
    ap.add_argument("--una-vez", action="store_true",
                    help="Solo genera el HTML y termina (no levanta el servidor)")
    args = ap.parse_args()

    print("Generando el panel desde Postgres...")
    if not regenerar() and not HTML.exists():
        print("ERROR: no hay dashboard.html y el generador fallo. Aborto.")
        return 2
    if args.una_vez:
        return 0

    ip = ip_local()
    parar = threading.Event()
    if args.intervalo > 0:
        hilo = threading.Thread(target=bucle_regeneracion,
                                args=(args.intervalo, parar), daemon=True)
        hilo.start()

    socketserver.TCPServer.allow_reuse_address = True
    try:
        servidor = socketserver.ThreadingTCPServer(("0.0.0.0", args.puerto), Manejador)
    except OSError as e:
        print("ERROR: no pude abrir el puerto %d (%s)." % (args.puerto, e))
        print("Prueba con otro puerto: --puerto 8100")
        return 3

    print("")
    print("  Panel de '%s' listo." % "Barber Chinos")
    print("")
    print("  En ESTA computadora:  http://localhost:%d" % args.puerto)
    print("  En el CELULAR:        http://%s:%d" % (ip, args.puerto))
    if args.intervalo > 0:
        print("  Se regenera cada %d segundos." % args.intervalo)
    print("")
    print("  El celular debe estar en la MISMA red Wi-Fi que esta PC.")
    print("  Para detener: Ctrl + C")
    print("")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nDetenido.")
    finally:
        parar.set()
        servidor.shutdown()
        servidor.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
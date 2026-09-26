#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Aisla que elemento causa los bloques de color en la captura.

Estrategia: generar 4 variantes del HTML, cada una con una pieza
desactivada, capturarlas y comparar el tamano del archivo. La variante que
"arregla" la captura delata al culpable.

Tambien pregunta al navegador QUE elemento ocupa el centro de la pantalla,
usando --dump-dom sobre una pagina que inserta el resultado en el DOM.
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
ORIGEN = os.path.join(AQUI, "barber-chinos-admin.html")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BASE = open(ORIGEN, encoding="utf-8").read()

VARIANTES = {}

# 1) sin grain
v = BASE.replace("body::after{", "body::after{display:none!important;")
VARIANTES["sin-grain"] = v

# 2) sin preloader
v = BASE.replace("#preloader{", "#preloader{display:none!important;")
VARIANTES["sin-preloader"] = v

# 3) sin cursor (los dos circulos)
v = BASE.replace(".cursor,.cursor-seguidor{",
                 ".cursor,.cursor-seguidor{display:none!important;")
VARIANTES["sin-cursor"] = v

# 4) sin las animaciones de aparicion (que todo sea visible)
v = BASE.replace("[data-animar]{opacity:0;", "[data-animar]{opacity:1;")
VARIANTES["sin-anim"] = v

# 5) todo junto
v = BASE
v = v.replace("body::after{", "body::after{display:none!important;")
v = v.replace("#preloader{", "#preloader{display:none!important;")
v = v.replace(".cursor,.cursor-seguidor{",
              ".cursor,.cursor-seguidor{display:none!important;")
v = v.replace("[data-animar]{opacity:0;", "[data-animar]{opacity:1;")
VARIANTES["todo"] = v


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        nombre = self.path.strip("/").split("?")[0] or "todo"
        cuerpo = VARIANTES.get(nombre, BASE).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def log_message(self, *a):
        pass


def main():
    srv = ThreadingHTTPServer(("127.0.0.1", 8141), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    time.sleep(0.5)

    salida = os.path.join(AQUI, "capturas", "diag")
    os.makedirs(salida, exist_ok=True)

    print("=" * 62)
    print("AISLAMIENTO: que variante renderiza bien?")
    print("=" * 62)
    for nombre in VARIANTES:
        ruta = os.path.join(salida, f"{nombre}.png")
        subprocess.run([CHROME, "--headless=new", "--disable-gpu",
                        "--no-sandbox", "--hide-scrollbars",
                        "--virtual-time-budget=12000",
                        "--window-size=1280,900",
                        f"--screenshot={ruta}",
                        f"http://127.0.0.1:8141/{nombre}?sinpre"],
                       capture_output=True, timeout=150)
        kb = os.path.getsize(ruta) // 1024 if os.path.exists(ruta) else 0
        print(f"  {nombre:16} -> {kb} KB")

    srv.shutdown()
    print()
    print("  La variante con menos KB suele ser la que renderiza texto")
    print("  (los bloques de color comprimen muy bien y pesan poco).")
    print(f"  capturas en {salida}")


if __name__ == "__main__":
    main()
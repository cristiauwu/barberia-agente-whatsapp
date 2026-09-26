#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Diagnostica 3 problemas vistos en la captura, con datos.

  1. Una barra cobre en la parte superior que no deberia estar.
  2. Los dos botones del pie del sidebar aparecen estirados a todo el ancho.
  3. Las tarjetas KPI faltantes (la captura las pilla a medio animar).

Este script hace dos cosas:
  A. Cuenta etiquetas abiertas y cerradas en el HTML generado: un desbalance
     rompe la estructura del DOM y explica que elementos se salgan de sitio.
  B. Pregunta al navegador QUE elemento ocupa varios puntos de la pantalla,
     e imprime los resultados. Es la forma directa de saber que pinta la
     barra de arriba y que son los botones estirados.
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
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

D = open(HTML, encoding="utf-8").read()

# ---------------------------------------------------------------- A
print("=" * 66)
print("A. BALANCE DE ETIQUETAS EN EL HTML GENERADO")
print("=" * 66)
for et in ("div", "section", "article", "table", "tbody", "tr", "td",
           "aside", "main", "nav", "button", "p", "h1", "h2", "h3",
           "span", "ul", "li", "svg"):
    abre = D.count("<" + et + " ") + D.count("<" + et + ">")
    cierra = D.count("</" + et + ">")
    if abre != cierra:
        print(f"  DESBALANCE  <{et}> abre {abre} / cierra {cierra}"
              f"  -> diferencia {abre - cierra}")
print("  (solo se listan los desbalanceados)")

# ---------------------------------------------------------------- B
SONDA = """<!DOCTYPE html><html><head><meta charset="utf-8">
<style>html,body{margin:0;height:100%}iframe{width:1280px;height:900px;border:0}
#r{position:fixed;right:0;bottom:0;background:#fff;color:#000;font:12px monospace;
padding:6px;z-index:99999;white-space:pre;max-width:600px}</style></head><body>
<iframe id="f" src="/panel?sinpre"></iframe><pre id="r"></pre>
<script>
window.addEventListener("load", function(){
  setTimeout(function(){
    var d;
    try { d = document.getElementById("f").contentDocument; }
    catch(e){ document.getElementById("r").textContent = "no acceso: " + e; return; }
    var puntos = [[640,12],[640,30],[640,60],[200,455],[900,455],
                  [340,455],[640,760],[130,120],[640,449]];
    var out = [];
    puntos.forEach(function(p){
      var el = d.elementFromPoint(p[0], p[1]);
      if(!el){ out.push(p + " -> (nada)"); return; }
      var r = el.getBoundingClientRect();
      out.push(p[0] + "," + p[1] + " -> " + el.tagName.toLowerCase() +
        "." + (el.className || "(sin clase)").toString().slice(0,42) +
        "  w=" + Math.round(r.width) + " h=" + Math.round(r.height) +
        " x=" + Math.round(r.left));
    });
    var barra = d.querySelector(".barra");
    var pie = d.querySelector(".pie-acciones");
    var raiz = getComputedStyle(d.documentElement);
    out.push("");
    out.push(".barra  w=" + (barra ? Math.round(barra.getBoundingClientRect().width) : "?"));
    out.push(".pie-acciones w=" + (pie ? Math.round(pie.getBoundingClientRect().width) : "?"));
    out.push("--sidebar = " + raiz.getPropertyValue("--sidebar"));
    out.push("hojas CSS = " + d.styleSheets.length +
             " reglas = " + (d.styleSheets[0] ? d.styleSheets[0].cssRules.length : "?"));
    out.push("body::after opacity = " +
      getComputedStyle(d.body, "::after").opacity);
    document.getElementById("r").textContent = out.join("\\n");
  }, 2500);
});
</script></body></html>"""


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        c = (SONDA if self.path.startswith("/sonda") else D).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(c)))
        self.end_headers()
        self.wfile.write(c)

    def log_message(self, *a):
        pass


def main():
    srv = ThreadingHTTPServer(("127.0.0.1", 8143), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    time.sleep(0.5)

    print()
    print("=" * 66)
    print("B. QUE ELEMENTO PINTA CADA PUNTO DE LA PANTALLA")
    print("=" * 66)
    ruta = os.path.join(AQUI, "capturas", "sonda.html")
    p = subprocess.run([CHROME, "--headless=new", "--disable-gpu",
                        "--no-sandbox", "--virtual-time-budget=15000",
                        "--dump-dom", "http://127.0.0.1:8143/sonda"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=180)
    dom = p.stdout or ""
    # extraer el contenido del <pre id="r">
    import re
    m = re.search(r'<pre id="r">(.*?)</pre>', dom, re.S)
    if m:
        for l in m.group(1).split("\n"):
            print("  " + l.replace("&lt;", "<").replace("&gt;", ">")
                  .replace("&amp;", "&"))
    else:
        print("  no pude leer la sonda")
        print("  (primeros 300 del DOM):", dom[:300])
    srv.shutdown()


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Por que el grafico sigue vacio? Responde con datos, no supuestos.

Hace dos comprobaciones independientes:
  A. Lee el marcado del grafico en el HTML generado (sin navegador).
  B. Pregunta al navegador la altura calculada de las barras y si el JS
     llego a ejecutarse.
"""
import os
import re
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

# ------------------------------------------------------------------ A
print("=" * 68)
print("A. EL MARCADO DEL GRAFICO EN EL HTML")
print("=" * 68)
print(f"  class='col'   : {D.count(chr(99) + chr(108) + chr(97) + chr(115) + chr(115) + chr(61) + chr(39) + chr(99) + chr(111) + chr(108) + chr(39))}")
print(f"  barra-col     : {D.count('barra-col')}")
print(f"  data-alto     : {D.count('data-alto')}")
i = D.find("class='grafica'")
if i < 0:
    i = D.find('class="grafica"')
print(f"  posicion de .grafica: {i}")
if i > 0:
    print("  --- primeros 520 caracteres del grafico ---")
    print("  " + D[i:i + 520].replace("\n", "\n  "))
else:
    print("  NO se encontro el contenedor .grafica")
j = D.find("function crecer(")
print()
print(f"  la funcion crecer() esta en el HTML: {j > 0}")
print(f"  crecerPendientes esta en el HTML: {'crecerPendientes' in D}")
k = D.find("crecerPendientes")
if k > 0:
    print("  --- como se llama crecerPendientes ---")
    for m in re.finditer(r"crecerPendientes\(\)", D):
        ctx = D[max(0, m.start() - 70):m.start() + 25]
        print("    ..." + ctx.replace("\n", " ")[-90:])

# ------------------------------------------------------------------ B
SONDA = """<!DOCTYPE html><html><head><meta charset="utf-8">
<style>html,body{margin:0}iframe{width:1280px;height:900px;border:0;display:block}
#r{position:fixed;right:0;bottom:0;background:#fff;color:#000;font:11px monospace;
padding:8px;z-index:99999;white-space:pre;max-width:880px;max-height:60vh;overflow:auto}
</style></head><body>
<iframe id="f" src="/panel?sinpre&sinanim"></iframe><pre id="r"></pre>
<script>
window.addEventListener("load", function(){
  setTimeout(function(){
    var out = [];
    var w = document.getElementById("f").contentWindow;
    var d = w.document;
    try{
      out.push("=== EL GRAFICO ===");
      var g = d.querySelector(".grafica");
      out.push("existe .grafica: " + !!g);
      if(g){
        out.push(".grafica alto = " + Math.round(g.getBoundingClientRect().height));
        var cols = g.querySelectorAll(".col");
        out.push(".col encontrados = " + cols.length);
        var bcs = g.querySelectorAll(".barra-col");
        out.push(".barra-col encontrados = " + bcs.length);
        if(cols.length){
          out.push("primer .col data-alto = " + cols[0].dataset.alto);
          out.push("primer .col alto = " +
            Math.round(cols[0].getBoundingClientRect().height));
        }
        if(bcs.length){
          out.push("primer .barra-col alto(rect) = " +
            Math.round(bcs[0].getBoundingClientRect().height));
          out.push("primer .barra-col style.height = '" +
            bcs[0].style.height + "'");
          out.push("primer .barra-col computed height = " +
            w.getComputedStyle(bcs[0]).height);
          out.push("primer .barra-col computed width = " +
            w.getComputedStyle(bcs[0]).width);
          var p = bcs[0].parentNode;
          out.push("padre del .barra-col = " + p.className);
          out.push("padre display=" + w.getComputedStyle(p).display +
            " align-items=" + w.getComputedStyle(p).alignItems +
            " alto=" + Math.round(p.getBoundingClientRect().height));
        }
      }
      out.push("");
      out.push("=== ESTADO DEL JS ===");
      out.push("hay errores? (window.onerror) = " + (w.__err || "sin registrar"));
      var cards = d.querySelectorAll(".card-grafica,.card");
      var conBarras = 0, crecidas = 0;
      cards.forEach(function(c){
        if(c.querySelector(".col,.srv-barra,.hora-barra")){
          conBarras++;
          if(c.dataset.crecida === "1") crecidas++;
        }
      });
      out.push("cajas con barras = " + conBarras + "  marcadas crecidas = " + crecidas);
      out.push("");
      out.push("=== VISTA ACTIVA ===");
      var v = d.querySelector(".vista.activa");
      out.push("clave = " + (v ? v.dataset.vistaPanel : "ninguna"));
      out.push("contiene la grafica = " +
        (v && v.contains(g) ? "SI" : "NO"));
    }catch(e){ out.push("ERROR en la sonda: " + e.message); }
    document.getElementById("r").textContent = out.join("\\n");
  }, 4500);
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
    srv = ThreadingHTTPServer(("127.0.0.1", 8149), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    time.sleep(0.5)
    print()
    print("=" * 68)
    print("B. LO QUE DICE EL NAVEGADOR")
    print("=" * 68)
    p = subprocess.run([CHROME, "--headless=new", "--disable-gpu",
                        "--no-sandbox", "--virtual-time-budget=14000",
                        "--dump-dom", "http://127.0.0.1:8149/sonda"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=200)
    m = re.search(r'<pre id="r">(.*?)</pre>', p.stdout or "", re.S)
    if m:
        for l in m.group(1).split("\n"):
            print("  " + l.replace("&lt;", "<").replace("&gt;", ">")
                  .replace("&amp;", "&").replace("&quot;", '"'))
    else:
        print("  no pude leer la sonda")
    srv.shutdown()


if __name__ == "__main__":
    main()
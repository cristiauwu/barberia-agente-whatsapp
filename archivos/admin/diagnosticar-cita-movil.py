#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Por que se cortan los nombres de las citas en movil?

Mide, dentro de un iframe de 390px reales:
  - el ancho calculado de cada columna del grid .cita
  - el white-space, overflow y text-overflow efectivos de .cita-nombre
  - cuanto mide el texto del nombre y cuanto su caja

Asi el arreglo sale de numeros, no de suposiciones.
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

SONDA = """<!DOCTYPE html><html><head><meta charset="utf-8">
<style>html,body{margin:0;background:#000}iframe{width:390px;height:1200px;
border:0;display:block}
#r{position:fixed;right:0;top:0;background:#fff;color:#000;font:11px monospace;
padding:8px;z-index:99999;white-space:pre;max-height:100vh;overflow:auto;
max-width:640px}</style></head><body>
<iframe id="f" src="/panel?sinpre&sinanim"></iframe><pre id="r"></pre>
<script>
window.addEventListener("load", function(){
  setTimeout(function(){
    var w = document.getElementById("f").contentWindow;
    var d = w.document;
    var out = [];
    try{
      var cita = d.querySelector(".cita");
      out.push("=== .cita ===");
      var cs = w.getComputedStyle(cita);
      out.push("ancho = " + Math.round(cita.getBoundingClientRect().width));
      out.push("grid-template-columns = " + cs.gridTemplateColumns);
      out.push("gap = " + cs.columnGap);
      out.push("padding = " + cs.padding);
      out.push("");
      out.push("=== HIJOS DEL .cita ===");
      Array.prototype.forEach.call(cita.children, function(h){
        var r = h.getBoundingClientRect();
        var s = w.getComputedStyle(h);
        out.push("  " + h.className + " | x=" + Math.round(r.left) +
          " w=" + Math.round(r.width) + " h=" + Math.round(r.height) +
          " gc=" + s.gridColumn + " gr=" + s.gridRow);
      });
      out.push("");
      var n = cita.querySelector(".cita-nombre");
      var info = cita.querySelector(".cita-info");
      out.push("=== .cita-info ===");
      out.push("ancho = " + Math.round(info.getBoundingClientRect().width));
      out.push("min-width = " + w.getComputedStyle(info).minWidth);
      out.push("");
      out.push("=== .cita-nombre ===");
      var ns = w.getComputedStyle(n);
      out.push("white-space = " + ns.whiteSpace);
      out.push("overflow = " + ns.overflow);
      out.push("text-overflow = " + ns.textOverflow);
      out.push("ancho caja = " + Math.round(n.getBoundingClientRect().width));
      out.push("alto caja = " + Math.round(n.getBoundingClientRect().height));
      out.push("scrollWidth = " + n.scrollWidth);
      out.push("texto = '" + n.textContent + "'");
      out.push("");
      out.push("=== A QUE MEDIA QUERY CORRESPONDE ===");
      out.push("ancho del iframe = " + d.documentElement.clientWidth);
      out.push("max-width:820px aplica = " +
        (d.documentElement.clientWidth <= 820));
    }catch(e){ out.push("ERROR: " + e.message); }
    document.getElementById("r").textContent = out.join("\\n");
  }, 3000);
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
    srv = ThreadingHTTPServer(("127.0.0.1", 8151), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    time.sleep(0.5)
    p = subprocess.run([CHROME, "--headless=new", "--disable-gpu",
                        "--no-sandbox", "--virtual-time-budget=12000",
                        "--window-size=1000,1300", "--dump-dom",
                        "http://127.0.0.1:8151/sonda"],
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
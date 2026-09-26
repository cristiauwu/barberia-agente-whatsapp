#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quien comprime la cita en movil? Mide la cadena de padres completa.

Dato ya conocido: .cita mide 234px cuando deberia medir ~308px, y su
columna central (1fr) se queda en 38px. Aqui se recorre la cadena de
padres desde .cita hasta main imprimiendo el ancho de cada uno, para ver
donde se pierde el ancho.
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
<style>html,body{margin:0;background:#000}iframe{width:390px;height:900px;
border:0;display:block}
#r{position:fixed;right:0;top:0;background:#fff;color:#000;font:11px monospace;
padding:8px;z-index:99999;white-space:pre;max-height:100vh;overflow:auto}
</style></head><body>
<iframe id="f" src="/panel?sinpre&sinanim"></iframe><pre id="r"></pre>
<script>
window.addEventListener("load", function(){
  setTimeout(function(){
    var w = document.getElementById("f").contentWindow, d = w.document;
    var out = [];
    try{
      var n = d.querySelector(".cita");
      out.push("=== CADENA DE PADRES DE .cita ===");
      var el = n;
      while(el && el.tagName !== "HTML"){
        var r = el.getBoundingClientRect();
        var s = w.getComputedStyle(el);
        out.push("  " + el.tagName.toLowerCase() +
          "." + (el.className || "-").toString().slice(0,26).padEnd(26) +
          " w=" + String(Math.round(r.width)).padStart(5) +
          " pad=" + s.paddingLeft + "/" + s.paddingRight +
          " maxw=" + s.maxWidth +
          " disp=" + s.display);
        el = el.parentElement;
      }
      out.push("");
      out.push("=== LA PILL Y EL BOTON (columnas 3) ===");
      var p = n.querySelector(".pill");
      var m = n.querySelector(".mas");
      if(p) out.push("  pill w=" + Math.round(p.getBoundingClientRect().width));
      if(m) out.push("  mas  w=" + Math.round(m.getBoundingClientRect().width));
      out.push("");
      out.push("=== CUANTO CABE DE TEXTO ===");
      var nn = n.querySelector(".cita-nombre");
      out.push("  .cita-nombre ancho=" + Math.round(nn.getBoundingClientRect().width));
      out.push("  su texto mide=" + nn.scrollWidth + "px de ancho natural");
      out.push("  le falta=" + (nn.scrollWidth - Math.round(nn.getBoundingClientRect().width)) + "px");
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
    srv = ThreadingHTTPServer(("127.0.0.1", 8153), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    time.sleep(0.5)
    p = subprocess.run([CHROME, "--headless=new", "--disable-gpu",
                        "--no-sandbox", "--virtual-time-budget=12000",
                        "--window-size=1000,1000", "--dump-dom",
                        "http://127.0.0.1:8153/sonda"],
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
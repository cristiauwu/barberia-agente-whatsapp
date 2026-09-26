#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Captura las 6 vistas del panel y comprueba que ninguna sale vacia.

Para cada vista: captura, mide cuantos elementos visibles tiene y cuanto
pesa la imagen. Una vista vacia da una captura muy liviana y sin texto.
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
CAPS = os.path.join(AQUI, "capturas", "vistas")
os.makedirs(CAPS, exist_ok=True)
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
D = open(HTML, encoding="utf-8").read()

VISTAS = ["dashboard", "agenda", "clientes", "servicios", "reportes",
          "config"]

SONDA = """<!DOCTYPE html><html><head><meta charset="utf-8">
<style>html,body{margin:0;background:#000}iframe{width:1200px;height:1500px;
border:0;display:block}
#r{position:fixed;right:0;top:0;background:#fff;color:#000;font:11px monospace;
padding:8px;z-index:99999;white-space:pre}</style></head><body>
<iframe id="f" src="/panel?sinpre&sinanim&vista=__V__"></iframe><pre id="r"></pre>
<script>
window.addEventListener("load", function(){
  setTimeout(function(){
    var w = document.getElementById("f").contentWindow, d = w.document;
    var out = [];
    try{
      var v = d.querySelector(".vista.activa");
      out.push("vista activa = " + (v ? v.dataset.vistaPanel : "NINGUNA"));
      var n = d.querySelector(".nav-item.activo");
      out.push("nav activo = " + (n ? n.dataset.vista : "NINGUNO"));
      out.push("elementos visibles = " + v.querySelectorAll("*").length);
      out.push("con data-animar = " + v.querySelectorAll("[data-animar]").length);
      var invis = 0;
      v.querySelectorAll("[data-animar]").forEach(function(e){
        if(parseFloat(w.getComputedStyle(e).opacity) < 0.5) invis++;
      });
      out.push("aun invisibles = " + invis);
      var alto = v.getBoundingClientRect().height;
      out.push("alto de la vista = " + Math.round(alto) + "px");
      out.push("tiene KPI = " + v.querySelectorAll(".kpi").length);
      out.push("tiene .card = " + v.querySelectorAll(".card").length);
      out.push("tiene barras = " +
        v.querySelectorAll(".barra-col,.srv-barra i,.hora-barra i").length);
      var texto = (v.innerText || "").length;
      out.push("caracteres de texto = " + texto);
    }catch(e){ out.push("ERROR: " + e.message); }
    document.getElementById("r").textContent = out.join("\\n");
  }, 3200);
});
</script></body></html>"""


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/sonda"):
            v = (re.search(r"vista=(\w+)", self.path) or [None, "dashboard"])[1]
            c = SONDA.replace("__V__", v).encode()
        else:
            c = D.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(c)))
        self.end_headers()
        self.wfile.write(c)

    def log_message(self, *a):
        pass


def main():
    srv = ThreadingHTTPServer(("127.0.0.1", 8155), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    time.sleep(0.5)

    print("=" * 70)
    print("LAS 6 VISTAS DEL PANEL")
    print("=" * 70)
    fallos = 0
    for v in VISTAS:
        print(f"\n--- {v} ---")
        p = subprocess.run([CHROME, "--headless=new", "--disable-gpu",
                            "--no-sandbox", "--virtual-time-budget=10000",
                            "--window-size=1400,1600", "--dump-dom",
                            f"http://127.0.0.1:8155/sonda?vista={v}"],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=200)
        m = re.search(r'<pre id="r">(.*?)</pre>', p.stdout or "", re.S)
        if m:
            info = {}
            for l in m.group(1).split("\n"):
                l = (l.replace("&lt;", "<").replace("&gt;", ">")
                     .replace("&amp;", "&"))
                if " = " in l:
                    k, val = l.split(" = ", 1)
                    info[k.strip()] = val.strip()
            activa = info.get("vista activa", "?")
            invis = int(info.get("aun invisibles", "0") or 0)
            texto = int(info.get("caracteres de texto", "0") or 0)
            alto = info.get("alto de la vista", "?")
            print(f"  vista activa: {activa}  (pedida: {v})")
            print(f"  texto: {texto} caracteres   alto: {alto}")
            print(f"  KPI {info.get('tiene KPI')}  cards "
                  f"{info.get('tiene .card')}  barras "
                  f"{info.get('tiene barras')}")
            if activa != v:
                print(f"  FALLO: no cambio a la vista {v}")
                fallos += 1
            if texto < 80:
                print("  FALLO: la vista casi no tiene texto")
                fallos += 1
            if invis > 0:
                print(f"  AVISO: {invis} elementos siguen invisibles")
        else:
            print("  FALLO: no pude leer la sonda")
            fallos += 1

        # captura de la vista
        salida = os.path.join(CAPS, f"{v}.png")
        subprocess.run([CHROME, "--headless=new", "--disable-gpu",
                        "--no-sandbox", "--hide-scrollbars",
                        "--virtual-time-budget=9000",
                        "--window-size=1400,1500",
                        f"--screenshot={salida}",
                        f"http://127.0.0.1:8155/panel?sinpre&sinanim&vista={v}"],
                       capture_output=True, timeout=200)
        kb = os.path.getsize(salida) // 1024 if os.path.exists(salida) else 0
        print(f"  captura: {kb} KB")

    srv.shutdown()
    print()
    print("=" * 70)
    print(f"FALLOS: {fallos}")
    print("=" * 70)
    return 0 if fallos == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
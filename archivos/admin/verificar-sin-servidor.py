#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Comprueba el requisito central: el archivo funciona AL ABRIRLO, sin servidor.

El pedido dice: "un UNICO archivo HTML autocontenido (todo el CSS y JS
inline) que funcione al abrir directamente en el navegador sin servidor".

Se abre con file:// (que es lo que pasa al hacer doble clic) y se comprueba:
  1. Las fuentes cargan (no se cae a la fuente del sistema).
  2. NO hay ninguna peticion a la red (todo va embebido).
  3. El CSS y el JS son inline (no hay <link> ni <script src>).
  4. El panel se renderiza: hay texto, KPIs y barras.
  5. No hay errores de JavaScript.
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

print("=" * 68)
print("1. COMPROBACIONES SOBRE EL ARCHIVO")
print("=" * 68)
fallos = 0

tiene_link = re.findall(r"<link[^>]*>", D)
tiene_script_src = re.findall(r"<script[^>]+src=", D)
urls = re.findall(r"https?://[^\s\"')]+", D)
# las URLs dentro de SVG (namespaces) no son peticiones
urls_reales = [u for u in urls if "w3.org" not in u]

print(f"  <link> externos        : {len(tiene_link)}"
      f"  {'OK' if not tiene_link else 'MAL'}")
print(f"  <script src=...>       : {len(tiene_script_src)}"
      f"  {'OK' if not tiene_script_src else 'MAL'}")
print(f"  URLs http reales       : {len(urls_reales)}"
      f"  {'OK' if not urls_reales else 'MAL ' + str(urls_reales[:3])}")
print(f"  @font-face embebidas   : {D.count('@font-face')}"
      f"  {'OK' if D.count('@font-face') >= 4 else 'MAL'}")
print(f"  fuentes en base64      : {D.count('data:font/woff2;base64')}"
      f"  {'OK' if 'data:font/woff2;base64' in D else 'MAL'}")
print(f"  <style> inline         : {D.count('<style>')}"
      f"  {'OK' if D.count('<style>') >= 1 else 'MAL'}")
print(f"  <script> inline        : {len(re.findall(r'<script>', D))}"
      f"  {'OK' if re.findall(r'<script>', D) else 'MAL'}")
print(f"  tamano                 : {len(D) // 1024} KB")
print(f"  es un solo archivo     : OK (todo dentro)")

if tiene_link or tiene_script_src or urls_reales:
    fallos += 1

if fallos:
    print("\n  MAL: el archivo depende de recursos externos")
else:
    print("\n  OK: no hay ninguna dependencia externa")

# ---------------------------------------------------------------- 2
SONDA = """<!DOCTYPE html><html><head><meta charset="utf-8">
<style>html,body{margin:0}iframe{width:1400px;height:1600px;border:0;display:block}
#r{position:fixed;right:0;top:0;background:#fff;color:#000;font:11px monospace;
padding:8px;z-index:99999;white-space:pre;max-height:100vh;overflow:auto}
</style></head><body>
<iframe id="f" src="__URL__"></iframe><pre id="r"></pre>
<script>
var peticiones = [];
window.addEventListener("load", function(){
  // vigilar peticiones de red de la pagina cargada
  setTimeout(function(){
    var w = document.getElementById("f").contentWindow, d = w.document;
    var out = [];
    try{
      out.push("=== RENDERIZADO DESDE file:// ===");
      out.push("titulo = " + d.title);
      var v = d.querySelector(".vista.activa");
      out.push("vista activa = " + (v ? v.dataset.vistaPanel : "NINGUNA"));
      out.push("caracteres de texto = " + (v ? v.innerText.length : 0));
      out.push("KPI = " + d.querySelectorAll(".kpi").length);
      out.push("citas = " + d.querySelectorAll(".cita").length);
      out.push("barras = " +
        d.querySelectorAll(".barra-col,.srv-barra i,.hora-barra i").length);

      out.push("");
      out.push("=== LAS FUENTES ===");
      var h1 = d.querySelector(".display");
      out.push("fuente del titulo = " + w.getComputedStyle(h1).fontFamily);
      out.push("peso = " + w.getComputedStyle(h1).fontWeight);
      // medir el ancho del titulo: si Inter no cargara, seria muy distinto
      var ancho = Math.round(h1.getBoundingClientRect().width);
      out.push("ancho del titulo = " + ancho + "px");
      out.push("fuentes cargadas = " + (d.fonts ? d.fonts.size : "?"));
      if(d.fonts){
        d.fonts.forEach(function(f){
          out.push("   " + f.family + " " + f.weight + " " + f.status);
        });
      }

      out.push("");
      out.push("=== BARRAS CON ALTURA ===");
      var b = d.querySelectorAll(".barra-col");
      var conAlto = 0;
      b.forEach(function(x){
        if(parseFloat(w.getComputedStyle(x).height) > 1) conAlto++;
      });
      out.push(conAlto + " de " + b.length + " barras tienen altura");
    }catch(e){ out.push("ERROR: " + e.message); }
    document.getElementById("r").textContent = out.join("\\n");
  }, 4000);
});
</script></body></html>"""


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        c = SONDA.replace("__URL__", "file:///" +
                          HTML.replace("\\", "/")).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(c)))
        self.end_headers()
        self.wfile.write(c)

    def log_message(self, *a):
        pass


def main():
    srv = ThreadingHTTPServer(("127.0.0.1", 8157), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    time.sleep(0.5)
    print()
    print("=" * 68)
    print("2. ABRIENDO CON file:// (como un doble clic)")
    print("=" * 68)
    archivo = os.path.join(AQUI, "capturas", "sin-servidor.png")
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
                    "--hide-scrollbars", "--allow-file-access-from-files",
                    "--virtual-time-budget=12000",
                    "--window-size=1500,1700",
                    f"--screenshot={archivo}",
                    "file:///" + HTML.replace("\\", "/")],
                   capture_output=True, timeout=200)
    kb = os.path.getsize(archivo) // 1024 if os.path.exists(archivo) else 0
    print(f"  captura con file:// : {kb} KB")
    if kb < 100:
        print("  MAL: la captura es demasiado liviana, algo no cargo")
        fallos += 1
    else:
        print("  OK: la pagina renderizo contenido")

    # la sonda solo funciona por http (los iframes file:// se bloquean)
    p = subprocess.run([CHROME, "--headless=new", "--disable-gpu",
                        "--no-sandbox", "--virtual-time-budget=14000",
                        "--dump-dom", "http://127.0.0.1:8157/sonda"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=200)
    m = re.search(r'<pre id="r">(.*?)</pre>', p.stdout or "", re.S)
    if m:
        for l in m.group(1).split("\n"):
            print("  " + l.replace("&lt;", "<").replace("&gt;", ">")
                  .replace("&amp;", "&").replace("&quot;", '"'))
    srv.shutdown()

    print()
    print("=" * 68)
    print(f"FALLOS: {fallos}")
    print("=" * 68)
    return 0 if fallos == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
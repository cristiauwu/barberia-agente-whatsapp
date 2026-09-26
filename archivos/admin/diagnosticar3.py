#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Averigua POR QUE .barra mide 1270px en vez de 260px.

La sonda anterior dijo:
    .barra        w=1270     (deberia ser 260)
    .pie-acciones w=1241
    --sidebar = 260px        (la variable SI esta bien)

Es decir: la variable existe pero el ancho no se aplica. Este script
pregunta al navegador POR QUE:

  1. El ancho calculado de .barra (getComputedStyle) y su offsetWidth.
  2. TODAS las reglas CSS que coinciden con .barra, en orden, para ver cual
     gana y de donde sale el 1270.
  3. El texto literal de la regla .barra en el archivo generado.
  4. Si #preloader sigue interceptando los clics.
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

# ---------------------------------------------------------------- 3
print("=" * 66)
print("3. LA REGLA .barra EN EL ARCHIVO GENERADO")
print("=" * 66)
for m in re.finditer(r"(?m)^\s*\.barra[^{]*\{[^}]*\}", D):
    txt = m.group(0)
    print("  " + txt.replace("\n", " ")[:160])
print()
# la variable
for m in re.finditer(r"--sidebar\s*:\s*[^;]+;", D):
    print(f"  variable encontrada: {m.group(0)}")
print()
# comprobar que el bloque :root esta entero
i = D.find(":root{")
if i >= 0:
    j = D.find("}", i)
    print(f"  bloque :root empieza en {i}, cierra en {j}")
    print(f"  contiene --sidebar: {'--sidebar' in D[i:j]}")
print()
# medir cuantas reglas CSS hay y donde empieza el estilo propio
print(f"  total caracteres del archivo: {len(D)}")
k = D.find("/* =====================================================================\n   TOKENS")
print(f"  el CSS propio empieza en: {k}")

SONDA = """<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
html,body{margin:0;height:100%}
iframe{width:1280px;height:900px;border:0;display:block}
#r{position:fixed;right:0;bottom:0;background:#fff;color:#000;
 font:11px monospace;padding:8px;z-index:99999;white-space:pre;
 max-width:900px;max-height:50vh;overflow:auto}
</style></head><body>
<iframe id="f" src="/panel?sinpre"></iframe><pre id="r"></pre>
<script>
window.addEventListener("load", function(){
  setTimeout(function(){
    var d = document.getElementById("f").contentDocument;
    var out = [];
    var b = d.querySelector(".barra");
    var cs = d.defaultView.getComputedStyle(b);
    out.push("=== .barra ===");
    out.push("tag=" + b.tagName + " class=" + b.className);
    out.push("computed width = " + cs.width);
    out.push("computed position = " + cs.position);
    out.push("offsetWidth = " + b.offsetWidth);
    out.push("rect = " + JSON.stringify(b.getBoundingClientRect().toJSON()));
    out.push("--sidebar en .barra = " +
      d.defaultView.getComputedStyle(b).getPropertyValue("--sidebar"));
    out.push("");
    out.push("=== REGLAS QUE COINCIDEN CON .barra ===");
    var hojas = d.styleSheets;
    for(var h = 0; h < hojas.length; h++){
      var reglas;
      try { reglas = hojas[h].cssRules; } catch(e){ continue; }
      for(var i = 0; i < reglas.length; i++){
        var reg = reglas[i];
        if(reg.type === 1){
          var sel = reg.selectorText || "";
          if(sel.indexOf(".barra") >= 0 && sel.indexOf(".barra-") < 0 &&
             sel.indexOf(".barra ') < 0){
            var w = reg.style.getPropertyValue("width");
            if(w || sel === ".barra"){
              out.push(sel + "  { width:" + (w || "-") + " }");
            }
          }
        } else if(reg.type === 4){
          try{
            for(var k = 0; k < reg.cssRules.length; k++){
              var r2 = reg.cssRules[k];
              var s2 = r2.selectorText || "";
              if(s2.indexOf(".barra") >= 0){
                var w2 = r2.style.getPropertyValue("width");
                if(w2) out.push("[@media " + reg.conditionText + "] " +
                  s2 + " { width:" + w2 + " }");
              }
            }
          }catch(e){}
        }
      }
    }
    out.push("");
    out.push("=== OTROS ANCHOS ===");
    [".app","main",".contenido",".pie-acciones",".accion",".nav"].forEach(
      function(s){
        var e = d.querySelector(s);
        if(e) out.push(s + " = " + Math.round(e.getBoundingClientRect().width));
      });
    out.push("viewport ancho = " + d.documentElement.clientWidth);
    out.push("");
    var p = d.getElementById("preloader");
    if(p){
      var pc = d.defaultView.getComputedStyle(p);
      out.push("=== #preloader ===");
      out.push("class = '" + p.className + "'  transform=" + pc.transform);
      out.push("opacity=" + pc.opacity + " pointer-events=" + pc.pointerEvents +
               " visibility=" + pc.visibility);
      out.push("rect.top = " + Math.round(p.getBoundingClientRect().top));
    }
    document.getElementById("r").textContent = out.join("\\n");
  }, 6000);
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
    srv = ThreadingHTTPServer(("127.0.0.1", 8145), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    time.sleep(0.5)
    print()
    print("=" * 66)
    print("1 y 2. QUE DICE EL NAVEGADOR")
    print("=" * 66)
    p = subprocess.run([CHROME, "--headless=new", "--disable-gpu",
                        "--no-sandbox", "--virtual-time-budget=20000",
                        "--dump-dom", "http://127.0.0.1:8145/sonda"],
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
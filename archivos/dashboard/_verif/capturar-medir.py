#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Captura y MIDE el panel con un viewport FIEL (landscape real).

Problema que resuelve: `@media (orientation:portrait)` del panel cambia la
rejilla. Una ventana alta (1440x7000) es "portrait" y NO representa el
escritorio real. Aqui:
  - el escritorio se mide en un iframe de 1440x900 (landscape, 4 columnas)
  - las capturas de pagina completa se hacen por TROZOS, desplazando el
    scroll DENTRO del iframe (contentWindow.scrollTo), asi el layout es el
    del escritorio real en cada trozo.

Rutas:
  /                -> dashboard.html crudo
  /marco390?y=N    -> iframe 390x844 (movil real), scroll interno a N
  /marco768?y=N    -> iframe 768x1024
  /marco1440?y=N   -> iframe 1440x900
  /medir390|768|1440 -> iframe del tamano + JS que imprime mediciones
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

AQUI = Path(r"G:\Barberia\archivos\dashboard")
SALIDA = AQUI / "capturas" / "verificacion"
SALIDA.mkdir(parents=True, exist_ok=True)

CHROME = None
for cand in (r"C:\Program Files\Google\Chrome\Application\chrome.exe",
             r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
             os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")):
    if os.path.exists(cand):
        CHROME = cand
        break
if not CHROME:
    print("no encontre chrome.exe"); sys.exit(2)

ap = argparse.ArgumentParser()
ap.add_argument("--etiqueta", default="datos")
ap.add_argument("--solo-medir", action="store_true")
ap.add_argument("--solo-capturar", action="store_true")
args = ap.parse_args()

HTML = (AQUI / "dashboard.html").read_text(encoding="utf-8")

MEDIR_JS = r"""
<script>
window.addEventListener('load', function(){
  setTimeout(function(){
    var out = [];
    function push(s){ out.push(s); }
    var f = document.getElementById('f');
    var d, w;
    try { d = f.contentDocument; w = f.contentWindow; }
    catch(e){ document.getElementById('res').textContent =
                'NO_SE_PUDO_LEER_IFRAME: '+e; return; }
    var de = d.documentElement;
    var ancho = w.innerWidth;
    push('ANCHO_VIEWPORT='+ancho+' ALTO_VIEWPORT='+w.innerHeight);
    push('ORIENTACION='+(w.innerHeight>ancho?'portrait':'landscape'));
    push('DOC_scrollWidth='+de.scrollWidth+' clientWidth='+de.clientWidth
         +' SCROLL_LATERAL='+(de.scrollWidth>de.clientWidth+1));
    var desb = [], fuera = [];
    var todos = d.querySelectorAll('*');
    for (var i=0;i<todos.length;i++){
      var el = todos[i];
      var r = el.getBoundingClientRect();
      if (el.scrollWidth > el.clientWidth + 1 && el.clientWidth > 0){
        desb.push('OVERFLOW:'+el.tagName+'.'+(el.className||'')
                  +' scroll='+el.scrollWidth+' client='+el.clientWidth
                  +' txt="'+(el.textContent||'').trim().slice(0,38)+'"');
      }
      if (r.right > ancho + 1 && r.width > 0){
        fuera.push('FUERA:'+el.tagName+'.'+(el.className||'')
                   +' right='+r.right.toFixed(1)+' ancho='+r.width.toFixed(1)
                   +' txt="'+(el.textContent||'').trim().slice(0,38)+'"');
      }
    }
    push('N_OVERFLOW_INTERNO='+desb.length);
    for (var i=0;i<Math.min(desb.length,60);i++) push('  '+desb[i]);
    push('N_FUERA_VIEWPORT='+fuera.length);
    for (var i=0;i<Math.min(fuera.length,60);i++) push('  '+fuera[i]);
    var kk = d.querySelectorAll('.kpi');
    push('N_KPIS='+kk.length+' COLS_VISIBLES='+
      (kk.length? Math.round((kk[0].getBoundingClientRect().left - 0)/1)>=0? '' : '' : ''));
    var porFila = {};
    for (var i=0;i<kk.length;i++){
      var rk = kk[i].getBoundingClientRect();
      var top = Math.round(rk.top);
      porFila[top] = (porFila[top]||0)+1;
    }
    var filas=[];
    for (var t in porFila) filas.push(porFila[t]);
    push('KPIS_POR_FILA='+filas.join(','));
    for (var i=0;i<kk.length;i++){
      var v = kk[i].querySelector('.kpi-v');
      var rv = v.getBoundingClientRect();
      var rk2 = kk[i].getBoundingClientRect();
      push('KPI'+i+' "'+kk[i].querySelector('.kpi-t').textContent
           +'"="'+v.textContent+'" kpiAncho='+rk2.width.toFixed(1)
           +' valorAncho='+rv.width.toFixed(1)
           +' RECORTA_VALOR='+(v.scrollWidth>v.clientWidth+1)
           +' kpiDesborda='+(kk[i].scrollWidth>kk[i].clientWidth+1));
    }
    var cols = d.querySelectorAll('.tendencia .col');
    var alturas = [];
    for (var i=0;i<cols.length;i++){
      var b = cols[i].querySelector('.barra-v');
      alturas.push(b.style.height);
    }
    push('N_BARRAS='+cols.length);
    push('ALTURAS='+alturas.join(','));
    var tbs = d.querySelectorAll('table');
    push('N_TABLAS='+tbs.length);
    for (var i=0;i<tbs.length;i++){
      var t = tbs[i];
      var r = t.getBoundingClientRect();
      push('TABLA'+i+' filas='+t.querySelectorAll('tbody tr').length
           +' ancho='+r.width.toFixed(1)+' desborda='
           +(t.scrollWidth>t.clientWidth+1));
    }
    var cort = [];
    var cand = d.querySelectorAll('td,.kpi-v,.fila-cab .val,.leyenda>span,.eje span,.chip,.pill,.kpi-t');
    for (var i=0;i<cand.length;i++){
      var el = cand[i];
      if (el.scrollWidth > el.clientWidth + 1 && el.clientWidth > 0){
        cort.push('RECORTADO '+el.tagName+'.'+(el.className||'')+' "'
                  +el.textContent.trim().slice(0,44)+'"');
      }
    }
    push('N_RECORTADOS='+cort.length);
    for (var i=0;i<Math.min(cort.length,30);i++) push('  '+cort[i]);
    push('ALTURA_DOC='+de.scrollHeight);
    document.getElementById('res').textContent = out.join('\n');
  }, 2200);
});
</script>
"""


def marco(ancho, alto, y, medir):
    res = ("<pre id='res' style='color:#0f0;font:12px monospace;"
           "white-space:pre-wrap;max-width:900px'></pre>") if medir else ""
    js = MEDIR_JS if medir else (
        "<script>window.addEventListener('load',function(){setTimeout(function(){"
        "document.getElementById('f').contentWindow.scrollTo(0,%d);},600);});</script>" % y)
    h = ("<!DOCTYPE html><html><head><meta charset='utf-8'>"
         "<style>html,body{margin:0;background:#111}"
         "iframe{width:%dpx;height:%dpx;border:0;display:block;margin:0 auto}"
         "</style></head><body>"
         "<iframe id='f' src='/dashboard.html'></iframe>%s%s</body></html>"
         % (ancho, alto, res, js))
    return h.encode()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        p, _, q = self.path.partition("?")
        qs = dict(kv.split("=") for kv in q.split("&") if "=" in kv)
        y = int(qs.get("y", "0"))
        if p == "/marco390":
            cuerpo = marco(390, 844, y, False)
        elif p == "/marco768":
            cuerpo = marco(768, 1024, y, False)
        elif p == "/marco1440":
            cuerpo = marco(1440, 900, y, False)
        elif p == "/medir390":
            cuerpo = marco(390, 844, 0, True)
        elif p == "/medir768":
            cuerpo = marco(768, 1024, 0, True)
        elif p == "/medir1440":
            cuerpo = marco(1440, 900, 0, True)
        else:
            cuerpo = HTML.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def log_message(self, *a):
        pass


srv = ThreadingHTTPServer(("127.0.0.1", 8125), Handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
time.sleep(0.4)


def capturar(nombre, url, ancho, alto):
    salida = str(SALIDA / nombre)
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
                    "--hide-scrollbars", "--force-device-scale-factor=1",
                    "--virtual-time-budget=6000",
                    f"--window-size={ancho},{alto}", f"--screenshot={salida}", url],
                   capture_output=True, timeout=120)
    ok = os.path.exists(salida)
    kb = os.path.getsize(salida) // 1024 if ok else 0
    print(f"  {'OK ' if ok else 'MAL'} {nombre} ({kb} KB)")
    return ok


def medir(nombre, url):
    r = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
                        "--virtual-time-budget=9000", "--dump-dom", url],
                       capture_output=True, timeout=120)
    dom = r.stdout.decode("utf-8", "replace")
    m = re.search(r"<pre id=\"res\"[^>]*>(.*?)</pre>", dom, re.S)
    txt = m.group(1) if m else "(no se encontro #res)"
    for a, b in (("&lt;", "<"), ("&gt;", ">"), ("&amp;", "&"), ("&quot;", '"')):
        txt = txt.replace(a, b)
    (SALIDA / nombre).write_text(txt, encoding="utf-8")
    print(f"  medicion -> {nombre}")
    return txt


et = args.etiqueta
if not args.solo_capturar:
    print(f"=== mediciones [{et}] ===")
    for ancho, nom in ((390, "movil"), (768, "tablet"), (1440, "escritorio")):
        txt = medir(f"medicion-{et}-{nom}.txt", f"http://127.0.0.1:8125/medir{ancho}")
        for l in txt.splitlines()[:12]:
            print("   " + l)

if not args.solo_medir:
    print(f"=== capturas [{et}] (trozos con viewport fiel) ===")
    # desktop 1440x900 landscape, 7 trozos
    for i in range(7):
        capturar(f"{et}-escritorio-{i+1}.png",
                 f"http://127.0.0.1:8125/marco1440?y={i*820}", 1440, 900)
    # movil 390x844 dentro de ventana mas ancha (Chrome fuerza >=504)
    for i in range(11):
        capturar(f"{et}-movil-{i+1}.png",
                 f"http://127.0.0.1:8125/marco390?y={i*820}", 520, 844)
    # tablet
    for i in range(5):
        capturar(f"{et}-tablet-{i+1}.png",
                 f"http://127.0.0.1:8125/marco768?y={i*1000}", 800, 1024)

srv.shutdown()
print(f"\nsalida en {SALIDA}")
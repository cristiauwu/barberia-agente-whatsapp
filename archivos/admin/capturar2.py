#!/usr/bin/env python3
"""Captura el panel: escritorio, movil, una vista interna y tema claro."""
import os, subprocess, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
AQUI=r"G:\Barberia\archivos\admin"
CAPS=os.path.join(AQUI,"capturas")
os.makedirs(CAPS,exist_ok=True)
CHROME=r"C:\Program Files\Google\Chrome\Application\chrome.exe"
D=open(os.path.join(AQUI,"barber-chinos-admin.html"),encoding="utf-8").read()
class H(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/movil"):
            p=("<!DOCTYPE html><html><head><meta charset='utf-8'><style>html,body{margin:0;background:#0A0A0A}"
               "iframe{width:390px;height:5200px;border:0;display:block;margin:0 auto}</style></head><body>"
               "<iframe src='/panel?sinpre&sinanim'></iframe></body></html>")
            c=p.encode()
        else: c=D.encode()
        self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8")
        self.send_header("Content-Length",str(len(c))); self.end_headers(); self.wfile.write(c)
    def log_message(self,*a): pass
srv=ThreadingHTTPServer(("127.0.0.1",8147),H)
threading.Thread(target=srv.serve_forever,daemon=True).start()
time.sleep(0.6)
def cap(url,sal,an,al,ms=6000):
    subprocess.run([CHROME,"--headless=new","--disable-gpu","--no-sandbox",
      "--hide-scrollbars","--force-device-scale-factor=1",
      f"--virtual-time-budget={ms}",
      f"--window-size={an},{al}",f"--screenshot={sal}",url],capture_output=True,timeout=180)
    ok=os.path.exists(sal)
    print(f"  {'OK ' if ok else 'MAL'} {os.path.basename(sal)} ({os.path.getsize(sal)//1024 if ok else 0} KB)")
print("=== capturas ===")
cap("http://127.0.0.1:8147/panel?sinpre&sinanim",os.path.join(CAPS,"escritorio.png"),1600,2400)
cap("http://127.0.0.1:8147/movil",os.path.join(CAPS,"movil.png"),520,5200)
srv.shutdown()
print("listo")
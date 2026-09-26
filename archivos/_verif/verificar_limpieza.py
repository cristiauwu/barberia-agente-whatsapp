# -*- coding: utf-8 -*-
import json,sys,io,subprocess
sys.path.insert(0,r"G:\Barberia\archivos\_verif")
from harness import api
import cal
if not getattr(sys.stdout,"_vutf8",False):
    sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace"); sys.stdout._vutf8=True
DOCKER=r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
def psql(s):
    r=subprocess.run([DOCKER,"exec","barberia-postgres","psql","-U","barberia","-d","barberia","-t","-A","-F","|","-c",s],capture_output=True,text=True,encoding="utf-8",errors="replace")
    return ((r.stdout or "")+(r.stderr or "")).strip()
print("=== workflows (no deben quedar temporales) ===")
for w in api("/workflows?limit=100")["data"]:
    print("  ",w["id"],w["name"],"activo" if w.get("active") else "")
print("=== memoria ===")
print(psql("SELECT session_id,count(*) FROM n8n_chat_histories GROUP BY 1 ORDER BY 2 DESC;"))
print("=== CRM ===")
print(psql("SELECT jid,nombre,visitas,etiqueta FROM barber_clientes;"))
print("=== citas pg ===")
print(psql("SELECT id,nombre,inicio,estado FROM barber_citas;"))
print("=== calendario: ¿sigue el evento de prueba? ===")
r=cal.listar()
ids=[e["id"] for e in r.get("eventos",[])]
print("  total eventos:",len(ids))
print("  evento Doble Reserva presente:", "mvhhjisn6bk4efd7fnqlm0ghls" in ids)
print("=== escalaciones/pausas/bloqueos ===")
print(psql("SELECT count(*) FROM barber_escalaciones;"),psql("SELECT count(*) FROM barber_pausas;"),psql("SELECT count(*) FROM barber_bloqueos;"))
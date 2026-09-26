# -*- coding: utf-8 -*-
"""Limpieza de artefactos de prueba: evento, fila de hoja, memoria y CRM."""
import json, urllib.request, urllib.error, uuid, time, sys, io, subprocess
sys.path.insert(0, r"G:\Barberia\archivos\_verif")
import cal
if not getattr(sys.stdout,"_vutf8",False):
    sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace"); sys.stdout._vutf8=True
N8N="http://localhost:5678/api/v1"
KEY=open(r"G:\Barberia\archivos\.n8n-key.txt").read().strip()
DOC="1lvSVFWU2ApvK7p5BsFHI68Icur46P6hI8o8r9ozhBfk"; SHEET=941506024
CRED={"googleSheetsOAuth2Api":{"id":"lGEYmmJh1FvqzQi9","name":"Google Sheets account"}}
DOCKER=r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
def psql(s):
    r=subprocess.run([DOCKER,"exec","barberia-postgres","psql","-U","barberia","-d","barberia","-t","-A","-F","|","-c",s],capture_output=True,text=True,encoding="utf-8",errors="replace")
    return ((r.stdout or "")+(r.stderr or "")).strip()
def api(method,path,body=None):
    data=json.dumps(body).encode() if body is not None else None
    req=urllib.request.Request(N8N+path,data=data,method=method)
    req.add_header("X-N8N-API-KEY",KEY); req.add_header("Content-Type","application/json")
    try:
        with urllib.request.urlopen(req,timeout=90) as r: return r.status,json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e: return e.code,e.read().decode()[:300]
    except Exception as e: return None,str(e)

EVENTO="mvhhjisn6bk4efd7fnqlm0ghls"   # Corte desvanecido o tijera — Doble Reserva
print("=== 1) borrar evento del calendario ===")
print(cal.borrar(EVENTO))

print("=== 2) borrar fila de la hoja ===")
NOMBRE="__verif_delrow"
RUTA="verifdel"+uuid.uuid4().hex[:8]
def limpia_wf():
    st,l=api("GET","/workflows?limit=100")
    for w in (l.get("data",[]) if st==200 else []):
        if w["name"]==NOMBRE:
            if w.get("active"): api("POST",f"/workflows/{w['id']}/deactivate",{}); time.sleep(1)
            api("DELETE",f"/workflows/{w['id']}")
wf={"name":NOMBRE,"nodes":[
 {"parameters":{"httpMethod":"POST","path":RUTA,"responseMode":"lastNode","options":{}},
  "type":"n8n-nodes-base.webhook","typeVersion":2,"position":[0,0],"id":str(uuid.uuid4()),"name":"Webhook","webhookId":str(uuid.uuid4())},
 {"parameters":{"operation":"delete","documentId":{"__rl":True,"value":DOC,"mode":"list","cachedResultName":"Citas barbería"},
   "sheetName":{"__rl":True,"value":SHEET,"mode":"list","cachedResultName":"Hoja 1"},
   "toDelete":"rows","startIndex":8,"numberToDelete":1,"options":{}},
  "type":"n8n-nodes-base.googleSheets","typeVersion":4.6,"position":[220,0],"id":str(uuid.uuid4()),"name":"Borrar fila","credentials":CRED},
 {"parameters":{"jsCode":"return [{json:{ok:true,n:$input.all().length}}];"},
  "type":"n8n-nodes-base.code","typeVersion":2,"position":[440,0],"id":str(uuid.uuid4()),"name":"Ok"},
],"connections":{"Webhook":{"main":[[{"node":"Borrar fila","type":"main","index":0}]]},
 "Borrar fila":{"main":[[{"node":"Ok","type":"main","index":0}]]}},"settings":{"executionOrder":"v1"}}
limpia_wf()
st,c=api("POST","/workflows",wf)
if st in (200,201):
    wid=c["id"]; api("POST",f"/workflows/{wid}/activate",{})
    sal=None
    for i in range(8):
        time.sleep(3)
        try:
            req=urllib.request.Request(f"http://localhost:5678/webhook/{RUTA}",data=b"{}",method="POST")
            req.add_header("Content-Type","application/json")
            with urllib.request.urlopen(req,timeout=120) as r: sal=json.loads(r.read().decode()); break
        except Exception as e: sal="err:"+str(e)[:90]
    print("  resultado:",sal)
    time.sleep(2)
    try: api("POST",f"/workflows/{wid}/deactivate",{})
    except Exception: pass
    api("DELETE",f"/workflows/{wid}")
else:
    print("  no pude crear workflow:",st,c)

print("=== 3) restaurar memoria de 1805 (quitar filas nuevas, id>1100) ===")
print("  actual:",psql("SELECT count(*),max(id) FROM n8n_chat_histories WHERE session_id='5214501111805@s.whatsapp.net';"))
print("  borradas:",psql("DELETE FROM n8n_chat_histories WHERE session_id='5214501111805@s.whatsapp.net' AND id>1100;"))
print("  ahora:",psql("SELECT count(*),max(id) FROM n8n_chat_histories WHERE session_id='5214501111805@s.whatsapp.net';"))
print("=== 4) restaurar nombre del CRM ===")
print(psql("UPDATE barber_clientes SET nombre='Cliente Prueba', servicio_habitual='Corte desvanecido o tijera', etiqueta='frecuente', visitas=5, ultima_visita='2026-09-25 16:29:43.933448' WHERE jid='5214501111805@s.whatsapp.net';"))
print(psql("SELECT jid,nombre,visitas,servicio_habitual,etiqueta FROM barber_clientes;"))
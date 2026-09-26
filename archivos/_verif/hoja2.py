# -*- coding: utf-8 -*-
"""Verificar estado de la hoja de citas (solo lectura)."""
import json, urllib.request, urllib.error, uuid, time, sys, io
if not getattr(sys.stdout,"_vutf8",False):
    sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace"); sys.stdout._vutf8=True
N8N="http://localhost:5678/api/v1"
KEY=open(r"G:\Barberia\archivos\.n8n-key.txt").read().strip()
DOC="1lvSVFWU2ApvK7p5BsFHI68Icur46P6hI8o8r9ozhBfk"
SHEET="941506024"
CRED={"googleSheetsOAuth2Api":{"id":"lGEYmmJh1FvqzQi9","name":"Google Sheets account"}}
NOMBRE="__verif_hoja_tmp"
def api(method,path,body=None):
    data=json.dumps(body).encode() if body is not None else None
    req=urllib.request.Request(N8N+path,data=data,method=method)
    req.add_header("X-N8N-API-KEY",KEY); req.add_header("Content-Type","application/json")
    try:
        with urllib.request.urlopen(req,timeout=90) as r:
            return r.status,json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code,e.read().decode()[:400]
    except Exception as e:
        return None,str(e)
RUTA="verifhoja"+uuid.uuid4().hex[:8]
def limpiar():
    st,l=api("GET","/workflows?limit=100")
    for w in (l.get("data",[]) if st==200 else []):
        if w["name"]==NOMBRE:
            if w.get("active"): api("POST",f"/workflows/{w['id']}/deactivate",{}); time.sleep(1)
            api("DELETE",f"/workflows/{w['id']}")
wf={"name":NOMBRE,"nodes":[
  {"parameters":{"httpMethod":"POST","path":RUTA,"responseMode":"lastNode","options":{}},
   "type":"n8n-nodes-base.webhook","typeVersion":2,"position":[0,0],"id":str(uuid.uuid4()),
   "name":"Webhook","webhookId":str(uuid.uuid4())},
  {"parameters":{"operation":"read","documentId":{"__rl":True,"value":DOC,"mode":"list","cachedResultName":"Citas barbería"},
    "sheetName":{"__rl":True,"value":SHEET,"mode":"list","cachedResultName":"Hoja 1"},"options":{}},
   "type":"n8n-nodes-base.googleSheets","typeVersion":4.6,"position":[220,0],"id":str(uuid.uuid4()),
   "name":"Leer hoja","credentials":CRED},
  {"parameters":{"jsCode":"const filas=$input.all().map(i=>i.json);return [{json:{total:filas.length,filas}}];"},
   "type":"n8n-nodes-base.code","typeVersion":2,"position":[440,0],"id":str(uuid.uuid4()),"name":"Resumir"},
 ],
 "connections":{"Webhook":{"main":[[{"node":"Leer hoja","type":"main","index":0}]]},
                "Leer hoja":{"main":[[{"node":"Resumir","type":"main","index":0}]]}},
 "settings":{"executionOrder":"v1"}}
limpiar()
st,c=api("POST","/workflows",wf)
wid=c["id"]; api("POST",f"/workflows/{wid}/activate",{})
salida=None
for i in range(8):
    time.sleep(3)
    try:
        req=urllib.request.Request(f"http://localhost:5678/webhook/{RUTA}",data=b"{}",method="POST")
        req.add_header("Content-Type","application/json")
        with urllib.request.urlopen(req,timeout=120) as r:
            salida=json.loads(r.read().decode()); break
    except Exception as e:
        salida="err:"+str(e)[:100]
print(json.dumps(salida,ensure_ascii=False,indent=1)[:4000])
time.sleep(2)
try: api("POST",f"/workflows/{wid}/deactivate",{}); time.sleep(1)
except Exception: pass
api("DELETE",f"/workflows/{wid}")
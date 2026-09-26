# -*- coding: utf-8 -*-
"""Leer la hoja de citas y borrar filas de prueba."""
import json, urllib.request, urllib.error, uuid, time, sys, io
if not getattr(sys.stdout,"_vutf8",False):
    sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace"); sys.stdout._vutf8=True
N8N="http://localhost:5678/api/v1"
KEY=open(r"G:\Barberia\archivos\.n8n-key.txt").read().strip()
DOC="1lvSVFWU2ApvK7p5BsFHI68Icur46P6hI8o8r9ozhBfk"
SHEET="941506024"
CRED={"googleSheetsOAuth2Api":{"id":"","name":""}}
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
# descubrir credencial de sheets desde el workflow del agente
st,wf=api("GET","/workflows/barberiaAgenteUncensored")
for n in wf["nodes"]:
    if "googleSheets" in n["type"] or n.get("credentials",{}).get("googleSheetsOAuth2Api"):
        print("creds sheets en nodo",n["name"],":",json.dumps(n.get("credentials"),ensure_ascii=False))
    if "googleCalendar" in n["type"]:
        print("creds cal en nodo",n["name"],":",json.dumps(n.get("credentials"),ensure_ascii=False))
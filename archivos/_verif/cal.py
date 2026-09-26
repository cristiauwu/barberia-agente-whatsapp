# -*- coding: utf-8 -*-
"""Herramienta de calendario aislada (workflow temporal propio, no toca el agente)."""
import json, urllib.request, urllib.error, uuid, time, sys, io
if not getattr(sys.stdout,"_vutf8",False):
    sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace"); sys.stdout._vutf8=True

N8N="http://localhost:5678/api/v1"
KEY=open(r"G:\Barberia\archivos\.n8n-key.txt").read().strip()
CAL="b5e08030160a7cead790f900fafd3728792af6d2eac8a22b1dedb7844c09143c@group.calendar.google.com"
CRED={"googleCalendarOAuth2Api":{"id":"I6TpcTTP1cn1tviR","name":"Google Calendar account"}}
NOMBRE="_verif-cal-tmp"

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

RUTA="verifcal"+uuid.uuid4().hex[:8]

def build():
    return {
  "name":NOMBRE,
  "nodes":[
   {"parameters":{"httpMethod":"POST","path":RUTA,"responseMode":"lastNode","options":{}},
    "type":"n8n-nodes-base.webhook","typeVersion":2,"position":[0,0],
    "id":str(uuid.uuid4()),"name":"Webhook","webhookId":str(uuid.uuid4())},
   {"parameters":{"rules":{"values":[
      {"conditions":{"options":{"caseSensitive":True,"typeValidation":"loose","version":2},
       "conditions":[{"id":str(uuid.uuid4()),"leftValue":"={{ $json.body.modo }}",
        "rightValue":"delete","operator":{"type":"string","operation":"equals"}}],
       "combinator":"and"},"renameOutput":True,"outputKey":"Borrar"}]},
     "options":{"fallbackOutput":"extra","renameFallbackOutput":"Listar"}},
    "type":"n8n-nodes-base.switch","typeVersion":3.2,"position":[220,0],
    "id":str(uuid.uuid4()),"name":"Modo"},
   # rama listar (fallback)
   {"parameters":{"operation":"getAll","calendar":{"__rl":True,"value":CAL,"mode":"list","cachedResultName":"BARBER"},
     "returnAll":True,"options":{"singleEvents":True},"timeMin":"={{ $json.body.desde }}","timeMax":"={{ $json.body.hasta }}"},
    "type":"n8n-nodes-base.googleCalendar","typeVersion":1.3,"position":[460,-120],
    "id":str(uuid.uuid4()),"name":"Listar","credentials":CRED},
   {"parameters":{"jsCode":"return [{json:{eventos:$input.all().map(i=>i.json).filter(e=>e&&e.summary).map(e=>({id:e.id,summary:e.summary,start:e.start&&(e.start.dateTime||e.start.date),end:e.end&&(e.end.dateTime||e.end.date),description:(e.description||'').slice(0,120)}))}}];"},
    "type":"n8n-nodes-base.code","typeVersion":2,"position":[680,-120],
    "id":str(uuid.uuid4()),"name":"Resumir"},
   # rama borrar
   {"parameters":{"operation":"delete","calendar":{"__rl":True,"value":CAL,"mode":"list","cachedResultName":"BARBER"},
     "eventId":"={{ $json.body.id }}"},
    "type":"n8n-nodes-base.googleCalendar","typeVersion":1.3,"position":[460,120],
    "id":str(uuid.uuid4()),"name":"Borrar","credentials":CRED},
   {"parameters":{"assignments":{"assignments":[{"id":str(uuid.uuid4()),"name":"borrado",
      "value":"={{ $json.id }}","type":"string"}]},"options":{}},
    "type":"n8n-nodes-base.set","typeVersion":3.4,"position":[680,120],
    "id":str(uuid.uuid4()),"name":"Confirmar"},
  ],
  "connections":{
    "Webhook":{"main":[[{"node":"Modo","type":"main","index":0}]]},
    "Modo":{"main":[[{"node":"Borrar","type":"main","index":0}],[{"node":"Listar","type":"main","index":0}]]},
    "Listar":{"main":[[{"node":"Resumir","type":"main","index":0}]]},
    "Borrar":{"main":[[{"node":"Confirmar","type":"main","index":0}]]},
  },
  "settings":{"executionOrder":"v1"}}

def limpiar_wf():
    st,l=api("GET","/workflows?limit=100")
    for w in (l.get("data",[]) if st==200 else []):
        if w["name"]==NOMBRE:
            if w.get("active"): api("POST",f"/workflows/{w['id']}/deactivate",{}); time.sleep(1)
            api("DELETE",f"/workflows/{w['id']}")

def instalar():
    limpiar_wf()
    st,c=api("POST","/workflows",build())
    if st not in (200,201): raise RuntimeError(f"no pude crear: {st} {c}")
    wid=c["id"]
    api("POST",f"/workflows/{wid}/activate",{})
    return wid

def llamar(payload,reintentos=8):
    last=None
    for i in range(reintentos):
        time.sleep(3)
        try:
            req=urllib.request.Request(f"http://localhost:5678/webhook/{RUTA}",
                data=json.dumps(payload).encode(),method="POST")
            req.add_header("Content-Type","application/json")
            with urllib.request.urlopen(req,timeout=120) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            last=str(e)[:120]
    raise RuntimeError("webhook no respondio: "+str(last))

def listar(desde=None,hasta=None):
    wid=instalar()
    try:
        return llamar({"modo":"list","desde":desde,"hasta":hasta})
    finally:
        time.sleep(2)
        try: api("POST",f"/workflows/{wid}/deactivate",{}); time.sleep(1)
        except Exception: pass
        api("DELETE",f"/workflows/{wid}")

def borrar(eid):
    wid=instalar()
    try:
        return llamar({"modo":"delete","id":eid})
    finally:
        time.sleep(2)
        try: api("POST",f"/workflows/{wid}/deactivate",{}); time.sleep(1)
        except Exception: pass
        api("DELETE",f"/workflows/{wid}")

if __name__=="__main__":
    accion=sys.argv[1] if len(sys.argv)>1 else "list"
    if accion=="list":
        r=listar(sys.argv[2] if len(sys.argv)>2 else None, sys.argv[3] if len(sys.argv)>3 else None)
        print(json.dumps(r,ensure_ascii=False,indent=1))
    elif accion=="delete":
        print(json.dumps(borrar(sys.argv[2]),ensure_ascii=False))
    elif accion=="clean":
        limpiar_wf(); print("workflow temporal eliminado")
import json, urllib.request, subprocess, sys, io, uuid, time, datetime
if not getattr(sys.stdout,"_vutf8",False):
    sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace")
    sys.stdout._vutf8=True

N8NKEY=open(r"G:\Barberia\archivos\.n8n-key.txt").read().strip()
WF="barberiaAgenteUncensored"
DOCKER=r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
EVOKEY=subprocess.run([DOCKER,"exec","evolution_api","printenv","AUTHENTICATION_API_KEY"],
                      capture_output=True,text=True).stdout.strip()

def api(p):
    r=urllib.request.Request("http://localhost:5678/api/v1"+p)
    r.add_header("X-N8N-API-KEY",N8NKEY)
    return json.loads(urllib.request.urlopen(r,timeout=90).read().decode())

def psql(s):
    r=subprocess.run([DOCKER,"exec","barberia-postgres","psql","-U","barberia","-d","barberia",
                      "-t","-A","-F","|","-c",s],capture_output=True,text=True,encoding="utf-8",errors="replace")
    return ((r.stdout or "")+(r.stderr or "")).strip()

def enviar(jid,texto,wait=200,pushName="Prueba Verif"):
    """Devuelve dict con exec_id, status, respuesta, nodos."""
    antes=set(e["id"] for e in api(f"/executions?workflowId={WF}&limit=30")["data"])
    body={"event":"messages.upsert","instance":"hector",
      "server_url":"http://evolution_api:8080","apikey":EVOKEY,
      "date_time":"2026-09-25T23:00:00.000Z",
      "data":{"key":{"id":"T"+uuid.uuid4().hex[:10].upper(),"remoteJid":jid,"fromMe":False},
        "pushName":pushName,"message":{"conversation":texto},
        "messageType":"conversation"}}
    req=urllib.request.Request("http://localhost:5678/webhook/hector",
        data=json.dumps(body).encode(),method="POST")
    req.add_header("Content-Type","application/json")
    http=""
    try:
        r=urllib.request.urlopen(req,timeout=wait); http=str(r.status)
    except Exception as e:
        http="ERR:"+repr(e)
    t0=time.time()
    nuevo=None
    while time.time()-t0<wait:
        try:
            data=api(f"/executions?workflowId={WF}&limit=30")["data"]
        except Exception:
            time.sleep(2); continue
        for e in data:
            if e["id"] not in antes:
                if e["status"] in ("success","error","crashed","failed"):
                    nuevo=e; break
        if nuevo: break
        time.sleep(2)
    if not nuevo:
        return {"http":http,"error":"sin ejecucion nueva"}
    eid=nuevo["id"]
    det=api(f"/executions/{eid}?includeData=true")
    run=det["data"]["resultData"]["runData"]
    def nodo(n):
        d=run.get(n)
        if not d: return None
        try:
            return d[0]["data"]["main"][0][0]["json"]
        except Exception:
            return None
    out={"http":http,"exec_id":eid,"status":nuevo["status"]}
    mm=nodo("Mandar mensaje")
    out["respuesta"]=mm.get("message",{}).get("conversation") if mm else None
    ag=nodo("AI Agent")
    out["agente"]=ag.get("output") if ag else None
    out["nodos"]=list(run.keys())
    err=det["data"].get("resultData",{}).get("error")
    out["error_msg"]=err
    return out

if __name__=="__main__":
    print("JIDs y memoria actual:")
    print(psql("SELECT session_id,count(*) FROM n8n_chat_histories GROUP BY 1 ORDER BY 2 DESC;"))
    print("EVOKEY len",len(EVOKEY))
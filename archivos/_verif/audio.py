import sys,io,json,time,uuid,urllib.request
sys.path.insert(0,r"G:\Barberia\archivos\_verif")
from harness import api, WF, EVOKEY
if not getattr(sys.stdout,"_vutf8",False):
    sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace"); sys.stdout._vutf8=True
JID="5214501111805@s.whatsapp.net"
antes=set(e["id"] for e in api(f"/executions?workflowId={WF}&limit=30")["data"])
body={"event":"messages.upsert","instance":"hector","server_url":"http://evolution_api:8080","apikey":EVOKEY,
  "date_time":"2026-09-25T23:00:00.000Z",
  "data":{"key":{"id":"T"+uuid.uuid4().hex[:10].upper(),"remoteJid":JID,"fromMe":False},
    "pushName":"Prueba Audio",
    "message":{"audioMessage":{"url":"https://fake.local/a.ogg","mimetype":"audio/ogg; codecs=opus","ptt":True,"seconds":5}},
    "messageType":"audioMessage"}}
req=urllib.request.Request("http://localhost:5678/webhook/hector",data=json.dumps(body).encode(),method="POST")
req.add_header("Content-Type","application/json")
try:
    r=urllib.request.urlopen(req,timeout=120); print("HTTP",r.status)
except Exception as e:
    print("HTTP err",repr(e))
time.sleep(8)
nuevo=None
for e in api(f"/executions?workflowId={WF}&limit=30")["data"]:
    if e["id"] not in antes and e["status"]=="success": nuevo=e; break
if not nuevo: print("sin ejecucion"); sys.exit()
print("exec",nuevo["id"],nuevo["status"])
det=api(f"/executions/{nuevo['id']}?includeData=true")
run=det["data"]["resultData"]["runData"]
print("nodos:",list(run.keys()))
for n in ["Normalizacion","Aviso solo texto","Mandar mensaje"]:
    v=run.get(n)
    if not v: print(f"  [{n}] NO EJECUTADO"); continue
    s=json.dumps(v,ensure_ascii=False)
    print(f"  [{n}] {s[:500]}")
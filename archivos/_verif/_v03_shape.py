import json, urllib.request, sys, io
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace")
KEY=open(r"G:\Barberia\archivos\.n8n-key.txt").read().strip()
def api(p):
    r=urllib.request.Request("http://localhost:5678/api/v1"+p)
    r.add_header("X-N8N-API-KEY",KEY)
    return json.loads(urllib.request.urlopen(r,timeout=60).read().decode())

WF="barberiaAgenteUncensored"
ex=api(f"/executions?workflowId={WF}&limit=2")
eid=ex["data"][0]["id"]
det=api(f"/executions/{eid}?includeData=true")
run=det["data"]["resultData"]["runData"]
print("EXEC",eid)
for node in ["Mandar mensaje","AI Agent","IF - Respuesta no vacia","Switch","Postgres Chat Memory"]:
    d=run.get(node)
    if not d: continue
    txt=json.dumps(d,ensure_ascii=False)
    print("=== ",node," (len",len(txt),") ===")
    print(txt[:2500])
    print()
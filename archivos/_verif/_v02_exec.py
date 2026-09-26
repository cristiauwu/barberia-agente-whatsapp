import json, urllib.request
KEY=open(r"G:\Barberia\archivos\.n8n-key.txt").read().strip()
def api(p):
    r=urllib.request.Request("http://localhost:5678/api/v1"+p)
    r.add_header("X-N8N-API-KEY",KEY)
    return json.loads(urllib.request.urlopen(r,timeout=60).read().decode())

WF="barberiaAgenteUncensored"
ex=api(f"/executions?workflowId={WF}&limit=5")
print("total devuelto:",len(ex["data"]))
for e in ex["data"]:
    print(e["id"],e["status"],e.get("startedAt"))
if ex["data"]:
    eid=ex["data"][0]["id"]
    det=api(f"/executions/{eid}?includeData=true")
    run=det["data"]["resultData"]["runData"]
    print("--- NODOS ---")
    for k in run: print(" ",k)
    print("--- Normalizacion ---")
    print(json.dumps(run.get("Normalizacion",{}),ensure_ascii=False)[:1500])
    print("--- Mandar mensaje ---")
    print(json.dumps(run.get("Mandar mensaje",{}),ensure_ascii=False)[:2000])
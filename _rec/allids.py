import json, urllib.request, sys, time
sys.stdout.reconfigure(encoding="utf-8")
KEY = open(r"G:\Barberia\archivos\.n8n-key.txt", encoding="utf-8").read().strip()

def api(p):
    r = urllib.request.Request("http://localhost:5678/api/v1" + p)
    r.add_header("X-N8N-API-KEY", KEY)
    return json.loads(urllib.request.urlopen(r, timeout=180).read().decode())

# enumerate ALL executions of the recordatorios workflow
allids = []
cursor = None
while True:
    p = "/executions?workflowId=barberiaRecordatorios&limit=250"
    if cursor: p += f"&lastId={cursor}"
    res = api(p)
    data = res.get("data", [])
    if not data: break
    allids += [e["id"] for e in data]
    cursor = data[-1]["id"]
    if len(data) < 250: break
print("TOTAL executions enumerated:", len(allids))
print("ids:", allids)

# Also check the OTHER workflows for history
for wid in ("5zd5go4TFKqIsgdT", "barberiaAgenteUncensored"):
    res = api(f"/executions?workflowId={wid}&limit=5")
    print(f"--- {wid}: {len(res.get('data',[]))} recent")
    for e in res.get("data", []):
        print("   ", e["id"], e["status"], e.get("startedAt"))

json.dump(allids, open(r"G:\Barberia\_rec\all_ids.json","w"), indent=1)
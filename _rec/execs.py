import json, urllib.request, sys, os
sys.stdout.reconfigure(encoding="utf-8")
KEY = open(r"G:\Barberia\archivos\.n8n-key.txt", encoding="utf-8").read().strip()

def api(p):
    r = urllib.request.Request("http://localhost:5678/api/v1" + p)
    r.add_header("X-N8N-API-KEY", KEY)
    return json.loads(urllib.request.urlopen(r, timeout=120).read().decode())

lst = api("/executions?workflowId=barberiaRecordatorios&limit=100")
print("total returned:", len(lst["data"]))
rows = []
for e in lst["data"]:
    d = api(f"/executions/{e['id']}?includeData=false")
    x = d.get("data", d)
    rows.append({
        "id": x["id"], "status": x["status"], "started": x.get("startedAt"),
        "stopped": x.get("stoppedAt"), "waitTill": x.get("waitTill"),
        "finished": x.get("finished"), "mode": x.get("mode"),
    })
rows.sort(key=lambda r: int(r["id"]))
from collections import Counter
print("STATUS COUNTS:", Counter(r["status"] for r in rows))
print()
print(f"{'id':>6} {'status':<10} {'startedAt':<26} {'waitTill':<26} {'stoppedAt':<26}")
for r in rows:
    print(f"{r['id']:>6} {r['status']:<10} {str(r['started']):<26} {str(r['waitTill']):<26} {str(r['stopped']):<26}")
json.dump(rows, open(r"G:\Barberia\_rec\exec_meta.json","w",encoding="utf-8"), indent=1)
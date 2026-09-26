import json, urllib.request, io, collections

KEY = open(r"G:\Barberia\archivos\.n8n-key.txt").read().strip()
BASE = "http://localhost:5678/api/v1"
out = io.StringIO()

def api(p):
    r = urllib.request.Request(BASE + p)
    r.add_header("X-N8N-API-KEY", KEY)
    with urllib.request.urlopen(r, timeout=90) as x:
        return json.loads(x.read().decode())

ex = api("/executions?limit=250")
data = ex.get("data", [])
out.write(f"total devueltas: {len(data)}  nextCursor={'si' if ex.get('nextCursor') else 'no'}\n")
cnt = collections.Counter()
status = collections.Counter()
for e in data:
    cnt[e.get("workflowId")] += 1
    status[(e.get("workflowId"), e.get("status"))] += 1
out.write("\npor workflow:\n")
for k, v in cnt.items():
    out.write(f"  {k}: {v}\n")
out.write("\npor workflow+status:\n")
for k, v in status.items():
    out.write(f"  {k}: {v}\n")

# ultimas 15 ejecuciones con detalle
out.write("\n=== ultimas 15 ejecuciones ===\n")
for e in data[:15]:
    out.write(f"  {e.get('id')} wf={e.get('workflowId')} status={e.get('status')} started={e.get('startedAt')} mode={e.get('mode')}\n")

open(r"G:\Barberia\archivos\_tg\03-ejecuciones.txt", "w", encoding="utf-8").write(out.getvalue())
print("OK")
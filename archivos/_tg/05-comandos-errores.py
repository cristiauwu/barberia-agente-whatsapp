import json, urllib.request, io

KEY = open(r"G:\Barberia\archivos\.n8n-key.txt").read().strip()
BASE = "http://localhost:5678/api/v1"
out = io.StringIO()

def api(p):
    r = urllib.request.Request(BASE + p)
    r.add_header("X-N8N-API-KEY", KEY)
    with urllib.request.urlopen(r, timeout=90) as x:
        return json.loads(x.read().decode())

w = api("/workflows/barberiaAgenteUncensored")
for n in w["nodes"]:
    if n["name"] == "Router de comandos":
        keys = [v.get("outputKey") for v in n["parameters"]["rules"]["values"]]
        out.write(f"Router de comandos: {len(keys)} salidas -> {keys}\n")
        out.write("fallback: " + json.dumps(n["parameters"].get("options"), ensure_ascii=False) + "\n")

# errores de barberia Recordatorios
out.write("\n=== ejecuciones barberiaRecordatorios ===\n")
ex = api("/executions?limit=250")
for e in ex["data"]:
    if e.get("workflowId") != "barberiaRecordatorios":
        continue
    det = api(f"/executions/{e['id']}?includeData=true")
    rd = ((det.get("data") or {}).get("resultData") or {})
    err = rd.get("error") or {}
    last = rd.get("lastNodeExecuted")
    out.write(f"  id={e['id']} status={e['status']} started={e.get('startedAt')} last={last} err={str(err.get('message'))[:200]}\n")

# errores recientes del agente
out.write("\n=== errores recientes barberiaAgenteUncensored ===\n")
c = 0
for e in ex["data"]:
    if e.get("workflowId") != "barberiaAgenteUncensored" or e.get("status") != "error":
        continue
    det = api(f"/executions/{e['id']}?includeData=true")
    rd = ((det.get("data") or {}).get("resultData") or {})
    err = rd.get("error") or {}
    out.write(f"  id={e['id']} started={e.get('startedAt')} last={rd.get('lastNodeExecuted')} err={str(err.get('message'))[:250]}\n")
    c += 1
    if c >= 7:
        break

open(r"G:\Barberia\archivos\_tg\05-comandos-errores.txt", "w", encoding="utf-8").write(out.getvalue())
print("OK")
import json, urllib.request, sys
sys.stdout.reconfigure(encoding="utf-8")
KEY = open(r"G:\Barberia\archivos\.n8n-key.txt", encoding="utf-8").read().strip()

def api(p):
    r = urllib.request.Request("http://localhost:5678/api/v1" + p)
    r.add_header("X-N8N-API-KEY", KEY)
    return json.loads(urllib.request.urlopen(r, timeout=120).read().decode())

def full(eid):
    d = api(f"/executions/{eid}?includeData=true")
    return d.get("data", d)

for eid in [861]:
    x = full(eid)
    rd = x.get("resultData") or {}
    print("="*100)
    print(f"EXEC {eid} status={x.get('status')} waitTill={x.get('waitTill')} started={x.get('startedAt')} stopped={x.get('stoppedAt')}")
    print("  lastNodeExecuted:", rd.get("lastNodeExecuted"))
    run = rd.get("runData") or {}
    for name in ["ESPERAR A 1 H", "RECORDATORIO 1 H"]:
        if name in run:
            for r in run[name]:
                print(f"  --- {name}: status={r.get('executionStatus')} startTime={r.get('startTime')} executionTime={r.get('executionTime')}")
                print("      input :", json.dumps((r.get("data") or {}).get("main",[[[]]])[0], ensure_ascii=False)[:800])
                print("      output:", json.dumps((r.get("inputData") or {}), ensure_ascii=False)[:200])
                if r.get("error"): print("      error:", json.dumps(r["error"], ensure_ascii=False)[:500])
    # print all runData outputs for the last few nodes
    print("  --- FULL runData order ---")
    for name, arr in run.items():
        for r in arr:
            print(f"    {name}: {r.get('executionStatus')}")
    json.dump(x, open(rf"G:\Barberia\_rec\ex{eid}_full.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
import json, urllib.request, sys, re
sys.stdout.reconfigure(encoding="utf-8")
KEY = open(r"G:\Barberia\archivos\.n8n-key.txt", encoding="utf-8").read().strip()

def api(p):
    r = urllib.request.Request("http://localhost:5678/api/v1" + p)
    r.add_header("X-N8N-API-KEY", KEY)
    return json.loads(urllib.request.urlopen(r, timeout=180).read().decode())

# workflow static data
w = api("/workflows/barberiaRecordatorios")
print("=== workflow staticData ===")
print(json.dumps(w.get("staticData"), ensure_ascii=False, indent=1))

ids = json.load(open(r"G:\Barberia\_rec\all_ids.json"))
print(f"\n=== scanning {len(ids)} executions for errors ===")
PATTERNS = ["Missing columns", "does not have permission", "Forbidden", "ENOTFOUND",
            "invalid_grant", "Execution ID", "waitTill", "Cannot read", "duplicate key"]
summary = []
for eid in ids:
    d = api(f"/executions/{eid}?includeData=true")
    x = d.get("data", d)
    rd = x.get("resultData") or {}
    run = rd.get("runData") or {}
    errs = []
    if rd.get("error"):
        e = rd["error"]
        errs.append({"node": (e.get("node") or {}).get("name"), "msg": e.get("message"),
                     "desc": e.get("description"), "http": e.get("httpCode"),
                     "cause": (e.get("cause") or {}).get("message") if isinstance(e.get("cause"), dict) else str(e.get("cause"))})
    for name, arr in run.items():
        for r in arr:
            if r.get("executionStatus") == "error" and r.get("error"):
                e = r["error"]
                errs.append({"node": name, "msg": e.get("message"), "desc": e.get("description"),
                             "http": e.get("httpCode")})
    nodes = list(run.keys())
    summary.append({"id": eid, "status": x.get("status"), "waitTill": x.get("waitTill"),
                    "last": rd.get("lastNodeExecuted"), "nodes": nodes, "errors": errs,
                    "stopped": x.get("stoppedAt"), "started": x.get("startedAt")})
    print(f"--- {eid} status={x.get('status')} last={rd.get('lastNodeExecuted')}")
    for e in errs:
        print(f"      ERR node={e['node']} msg={e['msg']!r} desc={e['desc']!r} http={e['http']} cause={e.get('cause')!r}")

json.dump(summary, open(r"G:\Barberia\_rec\exec_summary.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)

print("\n=== PATTERN SEARCH across all execution JSON ===")
blob = json.dumps(summary, ensure_ascii=False)
for p in PATTERNS:
    print(f"  {p!r}: {'FOUND' if p.lower() in blob.lower() else 'not found'}")
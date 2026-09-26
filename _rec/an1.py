import json, sys
sys.stdout.reconfigure(encoding="utf-8")

def load(p):
    return json.load(open(p, encoding="utf-8"))

def summarize(eid):
    d = load(rf"G:\Barberia\_rec\ex{eid}.json")["data"]
    print("="*90)
    print(f"EXEC {eid}  status={d['status']} mode={d['mode']} started={d.get('startedAt')} stopped={d.get('stoppedAt')}")
    rd = d.get("resultData") or {}
    err = rd.get("error")
    if err:
        print("  ERROR node:", (err.get("node") or {}).get("name"))
        print("  ERROR msg :", repr(err.get("message"))[:600])
        print("  ERROR desc:", repr(err.get("description"))[:600])
        print("  ERROR http:", err.get("httpCode"))
        print("  stack:", (err.get("stack") or "")[:400].replace("\n"," | "))
    run = rd.get("runData") or {}
    print("  nodes executed:", list(run.keys()))
    for name, arr in run.items():
        for r in arr:
            st = r.get("executionStatus")
            if st != "success":
                e2 = r.get("error") or {}
                print(f"   !! {name}: {st} -> {repr(e2.get('message'))[:300]}")
    lr = rd.get("lastNodeExecuted")
    print("  lastNodeExecuted:", lr)
    if rd.get("waitTill"):
        print("  waitTill:", rd["waitTill"])

for eid in [1195, 1194, 1192]:
    summarize(eid)
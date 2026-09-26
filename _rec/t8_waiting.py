import sys, json, time
sys.path.insert(0, r"G:\Barberia\_rec")
import tb

print("=== EJECUCIONES EN 'waiting' AHORA ===")
waiting = []
for e in tb.execs(limit=100):
    m = tb.exec_meta(e["id"])
    if m.get("status") == "waiting":
        waiting.append(m)
waiting.sort(key=lambda x: int(x["id"]))
print(f"total waiting: {len(waiting)}")
for m in waiting:
    x = tb.exec_full(m["id"])
    rd = x.get("resultData") or {}
    run = rd.get("runData") or {}
    last = rd.get("lastNodeExecuted")
    rid = None
    for r in (run.get("Google Sheets Trigger") or []):
        for it in (r.get("data") or {}).get("main", [[]])[0]:
            rid = (it.get("json") or {}).get("ID")
    if rid is None:
        for name in ("Code",):
            for r in (run.get(name) or []):
                for it in (r.get("data") or {}).get("main", [[]])[0]:
                    rid = (it.get("json") or {}).get("ID")
    print(f"  exec {m['id']:>5} waitTill={m.get('waitTill')} last={last:<16} rowID={rid}")

print("\n=== los 5 que estaban en waiting ANTES de mi prueba ===")
for eid in ["1171", "1075", "747", "756", "820", "829", "835", "847", "852"]:
    m = tb.exec_meta(eid)
    print(f"  exec {eid:>5}: status={m.get('status')} waitTill={m.get('waitTill')}")
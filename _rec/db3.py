import sys, json
sys.path.insert(0, r"G:\Barberia\_rec")
import tb

for eid in ("1171", "1298"):
    x = tb.exec_full(eid)
    ed = (x.get("data") or {}).get("executionData") or {}
    stack = ed.get("nodeExecutionStack") or []
    print("="*100)
    print(f"exec {eid} status={x.get('status')} waitTill={x.get('waitTill')}")
    print(f"  nodeExecutionStack ({len(stack)} entradas):")
    for s in stack:
        n = s.get("node") or {}
        mains = (s.get("data") or {}).get("main")
        run = (((s.get("data") or {}).get("main") or [[]])[0] or [])
        print(f"    - {n.get('name')!r:45} items={len(run)}")
    print("  waitingExecution:", json.dumps(ed.get("waitingExecution"), ensure_ascii=False)[:300])
    print("  waitingExecutionSource:", json.dumps(ed.get("waitingExecutionSource"), ensure_ascii=False)[:300])
    rd = x.get("resultData") or {}
    print("  runData nodes:", list((rd.get("runData") or {}).keys()))
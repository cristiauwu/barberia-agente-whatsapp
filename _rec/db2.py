import sys, json
sys.path.insert(0, r"G:\Barberia\_rec")
import tb

for eid in ("1300", "1298", "1171"):
    x = tb.exec_full(eid)
    rd = x.get("resultData") or {}
    run = rd.get("runData") or {}
    print("="*100)
    print(f"exec {eid} last={rd.get('lastNodeExecuted')}")
    for name in ("Registrar cliente (CRM)", "Registrar cita (Postgres)"):
        arr = run.get(name)
        if not arr:
            print(f"  {name}: NO ejecutado")
            continue
        for r in arr:
            print(f"  {name}: status={r.get('executionStatus')}")
            out = (r.get("data") or {}).get("main")
            print("     out:", json.dumps(out, ensure_ascii=False)[:500])
            if r.get("error"):
                print("     ERROR:", json.dumps(r["error"], ensure_ascii=False)[:700])
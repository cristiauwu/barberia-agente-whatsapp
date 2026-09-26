import json, sys
sys.stdout.reconfigure(encoding="utf-8")
x = json.load(open(r"G:\Barberia\_rec\ex861_full.json", encoding="utf-8"))
rd = x.get("resultData") or {}
run = rd.get("runData") or {}
for name in ["Append or update row in sheet", "IF - Toca recordatorio 24 h",
             "IF - Toca recordatorio 1 h", "ESPERAR A 1 H", "RECORDATORIO 1 H"]:
    if name not in run: 
        print(f"[{name}] NOT in runData"); continue
    for i, r in enumerate(run[name]):
        print("="*90)
        print(f"{name} [{i}] status={r.get('executionStatus')}")
        print("  waitTill:", r.get("waitTill"))
        print("  OUTPUT data:", json.dumps((r.get("data") or {}).get("main"), ensure_ascii=False)[:1500])
        print("  INPUT data :", json.dumps((r.get("inputData") or {}).get("main"), ensure_ascii=False)[:1500])
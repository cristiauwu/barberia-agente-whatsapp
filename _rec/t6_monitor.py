import sys, json, time
sys.path.insert(0, r"G:\Barberia\_rec")
import tb

MI_ID = "verif-rec-wait-24h"
antes = set(json.load(open(r"G:\Barberia\_rec\antes_ids.json")))
print("vigilando durante ~7 min. Ejecuciones previas:", len(antes))
vistos = {}
t0 = time.time()
while time.time() - t0 < 420:
    for e in tb.execs(limit=60):
        eid = e["id"]
        if eid in antes:
            continue
        m = tb.exec_meta(eid)
        x = tb.exec_full(eid)
        rd = x.get("resultData") or {}
        run = rd.get("runData") or {}
        trig = run.get("Google Sheets Trigger") or []
        rid = None
        for r in trig:
            for it in (r.get("data") or {}).get("main", [[]])[0]:
                rid = (it.get("json") or {}).get("ID")
        last = rd.get("lastNodeExecuted")
        st = m.get("status")
        key = (eid, st, last, rid)
        if vistos.get(eid) != key:
            vistos[eid] = key
            marca = "  <<< MI FILA" if rid == MI_ID else ""
            print(f"[{time.strftime('%H:%M:%S')}] exec {eid} status={st} last={last} rowID={rid}{marca}")
            if rid == MI_ID or eid == "1298":
                for name in ("ESPERAR A 24 H", "RECORDATORIO 24 H", "ESPERAR A 1 H", "RECORDATORIO 1 H"):
                    for r in (run.get(name) or []):
                        print(f"        {name}: {r.get('executionStatus')}")
                        out = (r.get("data") or {}).get("main")
                        if out and any(out):
                            print("           out:", json.dumps(out, ensure_ascii=False)[:700])
                json.dump(x, open(rf"G:\Barberia\_rec\watch_{eid}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    time.sleep(20)
print("\nfin de la vigilancia")
print(json.dumps({k: list(v) for k, v in vistos.items()}, ensure_ascii=False, indent=1))
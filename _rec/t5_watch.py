import sys, json, time
sys.path.insert(0, r"G:\Barberia\_rec")
import tb

WID = "barberiaRecordatorios"
files = ["G:\\Barberia\\_rec\\antes_ids.json", "G:\\Barberia\\_rec\\antes_ids2.json"]
antes = set()
for f in files:
    try:
        antes |= set(json.load(open(f)))
    except Exception:
        pass
print("ids previos conocidos:", len(antes))

print("\nVigilando aparicion de la ejecucion del trigger...")
nueva = None
t0 = time.time()
while time.time() - t0 < 200:
    act = tb.execs(limit=60)
    nuevas = [e for e in act if e["id"] not in antes]
    if nuevas:
        nuevas.sort(key=lambda e: int(e["id"]))
        nueva = nuevas[0]
        break
    time.sleep(10)

print("elapsed: %.0fs" % (time.time() - t0))
if not nueva:
    print("NO aparecio ejecucion nueva en 200s")
    sys.exit(1)
eid = nueva["id"]
print("NUEVA EJECUCION:", eid, nueva.get("status"))
json.dump({"eid": eid}, open(r"G:\Barberia\_rec\wait_test_eid.json", "w"))

# caracterizar
x = tb.exec_full(eid)
rd = x.get("resultData") or {}
run = rd.get("runData") or {}
print("  status:", x.get("status"), "waitTill:", x.get("waitTill"))
print("  last:", rd.get("lastNodeExecuted"))
print("  nodos:", list(run.keys()))
trig = run.get("Google Sheets Trigger") or []
for r in trig:
    for it in (r.get("data") or {}).get("main", [[]])[0]:
        print("  fila:", json.dumps(it.get("json"), ensure_ascii=False))
code = run.get("Code") or []
for r in code:
    for it in (r.get("data") or {}).get("main", [[]])[0]:
        j = it.get("json") or {}
        print("  Code:", json.dumps({k: j.get(k) for k in ("ID","recordatorio24ISO","recordatorio1ISO","mandar24","mandar1")}, ensure_ascii=False))
for wn in ("ESPERAR A 24 H", "ESPERAR A 1 H"):
    for r in (run.get(wn) or []):
        print(f"  {wn}: {r.get('executionStatus')} waitTill={r.get('waitTill')}")

# ??? ya salio del Wait?
if x.get("status") == "waiting":
    print("\n  >> SIGUE EN 'waiting'. Esperando a que se reanude (3 min)...")
    t0 = time.time()
    while time.time() - t0 < 260:
        m = tb.exec_meta(eid)
        if m.get("status") != "waiting":
            print("  >> CAMBIO a:", m.get("status"))
            break
        time.sleep(15)
    m = tb.exec_meta(eid)
    print("  estado final:", m.get("status"), "finished:", m.get("finished"))

print("\n=== DETALLE FINAL ===")
x = tb.exec_full(eid)
rd = x.get("resultData") or {}
run = rd.get("runData") or {}
print("status:", x.get("status"), "last:", rd.get("lastNodeExecuted"))
for name in ("ESPERAR A 24 H", "RECORDATORIO 24 H", "IF - Toca recordatorio 1 h", "ESPERAR A 1 H"):
    for r in (run.get(name) or []):
        print(f"--- {name}: {r.get('executionStatus')}")
        out = (r.get("data") or {}).get("main")
        if out:
            print("    out:", json.dumps(out, ensure_ascii=False)[:900])
        if r.get("error"):
            print("    ERROR:", json.dumps(r["error"], ensure_ascii=False)[:600])
json.dump(x, open(rf"G:\Barberia\_rec\wait_test_{eid}.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
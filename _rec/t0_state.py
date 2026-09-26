import sys, json, time
sys.path.insert(0, r"G:\Barberia\_rec")
import tb

w = tb.api("GET", "/workflows/barberiaRecordatorios")[1]
print("=== staticData ===", json.dumps(w.get("staticData"), ensure_ascii=False))

print("\n=== ejecuciones recientes ===")
for e in sorted(tb.execs(limit=15), key=lambda x: int(x["id"])):
    m = tb.exec_meta(e["id"])
    print(f"  {e['id']:>5} {str(m.get('status')):<9} started={m.get('startedAt')} waitTill={m.get('waitTill')}")

print("\n=== HOJA ===")
rows = tb.parse_csv(tb.read_sheet())
for i, r in enumerate(rows, 1):
    print(f"  {i}: {r}")
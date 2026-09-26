import sys, json
sys.path.insert(0, r"G:\Barberia\_rec")
import tb

st, w = tb.api("GET", "/workflows/barberiaRecordatorios")
print("HTTP", st)
json.dump(w, open(r"G:\Barberia\_rec\W2_BACKUP_original.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("backup guardado,", len(w["nodes"]), "nodos")
for n in w["nodes"]:
    if n["name"] in ("ESPERAR A 24 H", "ESPERAR A 1 H"):
        print(f"  ORIGINAL {n['name']}: {json.dumps(n['parameters'], ensure_ascii=False)}")
print("  settings:", json.dumps(w.get("settings"), ensure_ascii=False))
print("  staticData:", json.dumps(w.get("staticData"), ensure_ascii=False))
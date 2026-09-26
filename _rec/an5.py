import json, sys, urllib.request
sys.stdout.reconfigure(encoding="utf-8")
KEY = open(r"G:\Barberia\archivos\.n8n-key.txt", encoding="utf-8").read().strip()

wf = json.load(open(r"G:\Barberia\_rec\wf.json", encoding="utf-8"))
print("=== RAW connections (exact) ===")
for src, v in wf["connections"].items():
    for ctype, outs in v.items():
        for i, targets in enumerate(outs):
            names = [t["node"] for t in targets]
            print(f"  {src!r} [{ctype}] out#{i} -> {names}")

print()
print("=== NODES reachable from Switch's Cancelado/Actualizado outputs ===")
sw = wf["connections"]["Switch"]["main"]
for i, targets in enumerate(sw):
    print(f"  Switch out#{i} -> {[t['node'] for t in targets]}")

print()
print("=== IF - Es cita agendada outputs ===")
for i, targets in enumerate(wf["connections"]["IF - Es cita agendada"]["main"]):
    etiqueta = "TRUE(agendado)" if i == 0 else "FALSE"
    print(f"  out#{i} {etiqueta} -> {[t['node'] for t in targets]}")

# --- agent workflow: what does it write to the sheet? ---
def api(p):
    r = urllib.request.Request("http://localhost:5678/api/v1" + p)
    r.add_header("X-N8N-API-KEY", KEY)
    return json.loads(urllib.request.urlopen(r, timeout=120).read().decode())

ag = api("/workflows/barberiaAgenteUncensored")
print(f"\n=== AGENTE: {len(ag['nodes'])} nodos ===")
for n in ag["nodes"]:
    if "googleSheets" in n["type"] or "Sheets" in n["type"]:
        p = n.get("parameters", {})
        print("-"*80)
        print(f"NODO {n['name']!r} type={n['type']} tv={n['typeVersion']}")
        print("  operation:", p.get("operation"))
        cols = p.get("columns") or {}
        print("  mappingMode:", cols.get("mappingMode"))
        print("  matchingColumns:", cols.get("matchingColumns"))
        print("  value keys:", list((cols.get("value") or {}).keys()))
        print("  schema ids:", [s.get("id") for s in (cols.get("schema") or [])])
        print("  documentId:", json.dumps(p.get("documentId"), ensure_ascii=False)[:200])
        print("  sheetName:", json.dumps(p.get("sheetName"), ensure_ascii=False)[:200])
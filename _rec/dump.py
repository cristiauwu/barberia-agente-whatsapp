import json, io, sys
sys.stdout.reconfigure(encoding="utf-8")
wf = json.load(open(r"G:\Barberia\_rec\wf.json", encoding="utf-8"))
out = io.StringIO()
def p(*a):
    print(*a, file=out)

p("="*90)
p("WORKFLOW:", wf["name"], "| active:", wf["active"], "| id:", wf["id"])
p("settings:", json.dumps(wf.get("settings"), ensure_ascii=False))
p("nodeCount:", len(wf["nodes"]))
p("="*90)
for n in wf["nodes"]:
    p("-"*90)
    p(f"NODE: {n['name']}  type={n['type']} tv={n['typeVersion']} disabled={n.get('disabled')}")
    p(f"  pos={n.get('position')}  credentials={json.dumps(n.get('credentials'), ensure_ascii=False)}")
    p("  params:")
    p(json.dumps(n.get("parameters"), indent=2, ensure_ascii=False))
p("="*90)
p("CONNECTIONS:")
p(json.dumps(wf["connections"], indent=2, ensure_ascii=False))
open(r"G:\Barberia\_rec\dump.txt","w",encoding="utf-8").write(out.getvalue())
print("WROTE", len(out.getvalue()))
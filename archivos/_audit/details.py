import json, os, io, re
base = r"G:\Barberia\archivos\_audit"
out = io.StringIO()
def W(*a): print(*a, file=out)
wf = json.load(open(os.path.join(base,"barberiaAgenteUncensored.json"),encoding="utf-8"))
nodes = {n["name"]: n for n in wf["nodes"]}

ag = nodes["AI Agent"]
sm = ag["parameters"]["options"]["systemMessage"]
W("SYSTEM MESSAGE (AI Agent) — chars:", len(sm), " approx tokens (chars/4):", round(len(sm)/4))
W("="*80)
W(sm)
W("="*80)
W("AI Agent full options keys:", list(ag["parameters"].get("options",{}).keys()))
W("AI Agent promptType:", ag["parameters"].get("promptType"))
W("AI Agent text:", ag["parameters"].get("text"))
W("AI Agent typeVersion:", ag.get("typeVersion"))
W("AI Agent ALL node-level keys:", {k:v for k,v in ag.items() if k not in ("parameters","position","id","name","type","typeVersion")})

W("#"*90)
W("MODEL NODE (OpenAI Chat Model) full params:")
W(json.dumps(nodes["OpenAI Chat Model"]["parameters"], ensure_ascii=False, indent=1))

W("#"*90)
W("MEMORY NODE (Postgres Chat Memory) full params:")
W(json.dumps(nodes["Postgres Chat Memory"], ensure_ascii=False, indent=1))

W("#"*90)
W("TOOLS — toolDescription + fromAi descriptions + parameter names")
for n in wf["nodes"]:
    t = n["type"]
    if "Tool" in t or t.endswith(".toolHttpRequest"):
        p = n["parameters"]
        W("-"*80)
        W(f"NODE NAME: {n['name']!r}  type={t}")
        W(f"  descriptionType: {p.get('descriptionType','(none)')}")
        W(f"  toolDescription: {p.get('toolDescription','(NONE)')!r}")
        W(f"  toolName/name override: {p.get('name','(none)')}")
        s = json.dumps(p, ensure_ascii=False)
        fas = re.findall(r"\$fromAI\((\s*'[^']*'|\s*\"[^\"]*\")\s*,\s*(`[^`]*`|'[^']*'|\"[^\"]*\"|'')", s)
        for name_,desc in fas:
            W(f"    fromAi param {name_.strip()} -> desc={desc.strip()}")

W("#"*90)
W("SWITCH fallback (Router de comandos + Switch wf1)")
for nm in ["Switch","Router de comandos"]:
    W(nm, "options:", json.dumps(nodes[nm]["parameters"]["options"], ensure_ascii=False))
    W("   rules count:", len(nodes[nm]["parameters"]["rules"]["values"]))
    for i,r in enumerate(nodes[nm]["parameters"]["rules"]["values"]):
        outs = r.get("outputKey") or r.get("renameOutput")
        W(f"   [{i}] outputKey={outs!r}")

W("#"*90)
W("NOTES / notesInFlow in wf1")
for n in wf["nodes"]:
    if n.get("notes"):
        W(f"  {n['name']!r} notesInFlow={n.get('notesInFlow')}: {n['notes'][:200]!r}")

wfr = json.load(open(os.path.join(base,"barberiaRecordatorios.json"),encoding="utf-8"))
nr = {n["name"]: n for n in wfr["nodes"]}
W("#"*90)
W("WF2 'Code' node full jsCode:")
W(nr["Code"]["parameters"]["jsCode"])
W("#"*90)
W("WF2 Webhook/trigger + Switch fallback:")
W("Switch options:", json.dumps(nr["Switch"]["parameters"]["options"], ensure_ascii=False))
W("Code1 jsCode:", nr["Code1"]["parameters"]["jsCode"])
W("QUITAR RECORDATORIO params:", json.dumps(nr["QUITAR RECORDATORIO"]["parameters"], ensure_ascii=False))
W("Wait nodes:", json.dumps({k:{kk:vv for kk,vv in nr[k]["parameters"].items()} for k in ["ESPERAR A 24 H","ESPERAR A 1 H"]}, ensure_ascii=False))
open(os.path.join(base,"details.txt"),"w",encoding="utf-8").write(out.getvalue())
print("ok", len(out.getvalue()))

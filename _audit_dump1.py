import json, os, re

OUT = r"G:\Barberia\_audit"
res = []
def w(*a):
    res.append(" ".join(str(x) for x in a))

def get_full(wfname, node):
    wf = json.load(open(os.path.join(OUT, wfname), encoding="utf-8"))
    for n in wf["nodes"]:
        if n["name"] == node:
            return n
    return None

wf_agent = "wf_Barberia_-_Agente_de_citas_(Uncensored_AI).json"
wf_rec = "wf_Barberia_-_Recordatorios_de_cita.json"

# ---- 1. AI Agent full parameters ----
wf = json.load(open(os.path.join(OUT, wf_agent), encoding="utf-8"))
for n in wf["nodes"]:
    if n["name"] == "AI Agent":
        w("############ AI AGENT PARAMETERS ############")
        w(json.dumps(n["parameters"], ensure_ascii=False, indent=1))
        w()
    if n["name"] == "OpenAI Chat Model":
        w("############ OpenAI Chat Model PARAMETERS ############")
        w(json.dumps(n["parameters"], ensure_ascii=False, indent=1))
        w()

# ---- 2. all Code nodes text ----
for fn in (wf_agent, wf_rec):
    wf = json.load(open(os.path.join(OUT, fn), encoding="utf-8"))
    for n in wf["nodes"]:
        if n["type"] == "n8n-nodes-base.code":
            w("#"*80)
            w(f"CODE NODE [{fn}] :: {n['name']}")
            w("#"*80)
            for k, v in n["parameters"].items():
                w(f"-- param {k}:")
                w(v if isinstance(v, str) else json.dumps(v, ensure_ascii=False, indent=1))
            w()

open(r"G:\Barberia\_audit\_dump1.txt", "w", encoding="utf-8").write("\n".join(res))
print("len", len("\n".join(res)))
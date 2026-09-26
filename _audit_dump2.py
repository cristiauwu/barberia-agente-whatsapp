import json, os, re

OUT = r"G:\Barberia\_audit"
wf_agent = os.path.join(OUT, "wf_Barberia_-_Agente_de_citas_(Uncensored_AI).json")
wf_rec = os.path.join(OUT, "wf_Barberia_-_Recordatorios_de_cita.json")
res = []
def w(*a):
    res.append(" ".join(str(x) for x in a))

wf = json.load(open(wf_agent, encoding="utf-8"))
for n in wf["nodes"]:
    if n["name"] == "AI Agent":
        sm = n["parameters"]["options"]["systemMessage"]
        w("### FULL systemMessage  (len=%d)" % len(sm))
        w(sm)
        w()

open(r"G:\Barberia\_audit\SYSTEM_PROMPT_FULL.txt", "w", encoding="utf-8").write("\n".join(res))

# All remaining non-code node params (short) and node names with types
res2 = []
def w2(*a):
    res2.append(" ".join(str(x) for x in a))
for fn in (wf_agent, wf_rec):
    wf = json.load(open(fn, encoding="utf-8"))
    w2("="*80)
    w2("WF:", wf.get("name"))
    w2("="*80)
    for n in wf["nodes"]:
        if n["type"] in ("n8n-nodes-base.code",):
            continue
        s = json.dumps(n["parameters"], ensure_ascii=False)
        w2(f"--- [{n['name']}] {n['type']} (len={len(s)})")
        w2(s[:2500])
        w2("")
open(r"G:\Barberia\_audit\NODE_PARAMS.txt", "w", encoding="utf-8").write("\n".join(res2))

# analysis of prompt
sm = open(r"G:\Barberia\_audit\SYSTEM_PROMPT_FULL.txt", encoding="utf-8").read()
res3 = []
def w3(*a):
    res3.append(" ".join(str(x) for x in a))
w3("len systemMessage:", len(sm))
w3("count '**' :", sm.count("**"))
w3("count single-asterisk pairs (approx):", len(re.findall(r"(?<!\*)\*(?!\*)[^*\n]{1,80}\*(?!\*)", sm)))
w3("count '━':", sm.count("━"))
w3("count '╔':", sm.count("╔"))
w3("count '┏':", sm.count("┏"))
w3("count '─':", sm.count("─"))
w3("mentions Paco:", "Paco" in sm)
w3("mentions Chino:", "Chino" in sm)
w3("mentions Pinzón:", "Pinzón" in sm)
w3("mentions barbers Juan/Carlos/Miguel:", [x for x in ["Juan","Carlos","Miguel"] if x in sm])
w3("mentions Esteban:", "Esteban" in sm)
w3("mentions totalVisits:", "totalVisits" in sm)
w3("mentions 2h recordatorio:", "2 h" in sm or "2h" in sm)
w3("mentions 24h:", "24" in sm)
w3("mentions negrita:", "negrita" in sm.lower())
open(r"G:\Barberia\_audit\_prompt_analysis.txt","w",encoding="utf-8").write("\n".join(res3))
print("\n".join(res3))
import json, os, io, re
base=r"G:\Barberia\archivos\_audit"
out=[]
def W(*a): s=" ".join(str(x) for x in a); out.append(s)
w1=json.load(open(os.path.join(base,"barberiaAgenteUncensored_v2.json"),encoding="utf-8"))
w1o=json.load(open(os.path.join(base,"barberiaAgenteUncensored.json"),encoding="utf-8"))
w2=json.load(open(os.path.join(base,"barberiaRecordatorios_v2.json"),encoding="utf-8"))
w2o=json.load(open(os.path.join(base,"barberiaRecordatorios.json"),encoding="utf-8"))
def n(nm,wf): return {x["name"]:x for x in wf["nodes"]}[nm]
W("### MODEL NODE v2:"); W(json.dumps(n("OpenAI Chat Model",w1)["parameters"],ensure_ascii=False,indent=1))
W("### MODEL NODE v2 node keys:", sorted(n("OpenAI Chat Model",w1).keys()))
W("### MEMORY v2:"); W(json.dumps(n("Postgres Chat Memory",w1),ensure_ascii=False,indent=1))
W("### AI AGENT v2 options keys:", list(n("AI Agent",w1)["parameters"].get("options",{}).keys()))
W("### AI Agent v2 node keys:", sorted(n("AI Agent",w1).keys()))
sm=n("AI Agent",w1)["parameters"]["options"]["systemMessage"]
W("### systemMessage len:", len(sm))
# diff node sets
def diff(a,b,label):
    na={x["name"] for x in a["nodes"]}; nb={x["name"] for x in b["nodes"]}
    W(f"### {label}: nodes added:", sorted(nb-na), "removed:", sorted(na-nb))
    for nm in sorted(na&nb):
        ja=json.dumps(n(nm,a),ensure_ascii=False,sort_keys=True); jb=json.dumps(n(nm,b),ensure_ascii=False,sort_keys=True)
        if ja!=jb: W(f"    CHANGED: {nm}")
diff(w1o,w1,"WF1 old->new"); diff(w2o,w2,"WF2 old->new")
# WF2 details fresh
W("### WF2 Switch options:", json.dumps(n("Switch",w2)["parameters"]["options"],ensure_ascii=False))
W("### WF2 Code1:", json.dumps(n("Code1",w2)["parameters"],ensure_ascii=False))
W("### WF2 Google Sheets Trigger params:", json.dumps(n("Google Sheets Trigger",w2)["parameters"],ensure_ascii=False)[:800])
W("### WF2 n8n node creds:", json.dumps(n("QUITAR RECORDATORIO",w2).get("credentials"),ensure_ascii=False))
W("### WF2 n8n node params:", json.dumps(n("QUITAR RECORDATORIO",w2)["parameters"],ensure_ascii=False))
W("### WF2 wait nodes:", json.dumps({x: n(x,w2)["parameters"] for x in ["ESPERAR A 24 H","ESPERAR A 1 H"]},ensure_ascii=False))
# connections v2 for wf1 - check for unconnected outputs / dangling
W("### WF1 v2 connection sources:", sorted(w1["connections"].keys()))
W("### WF1 nodes with no outgoing AND no incoming (except triggers):")
ins=set()
for s,c in w1["connections"].items():
    for t,br in c.items():
        for b in br:
            for x in (b or []): ins.add(x["node"])
for x in w1["nodes"]:
    if x["name"] not in w1["connections"] and x["name"] not in ins:
        W("    isolated:", x["name"], x["type"])
W("### WF2 same:")
ins=set()
for s,c in w2["connections"].items():
    for t,br in c.items():
        for b in br:
            for x in (b or []): ins.add(x["node"])
for x in w2["nodes"]:
    if x["name"] not in w2["connections"] and x["name"] not in ins:
        W("    isolated:", x["name"], x["type"])
W("### WF2 Switch branches -> targets:")
for bi,br in enumerate(w2["connections"]["Switch"]["main"]):
    W("    main[%d] ->"%bi, [t["node"] for t in (br or [])])
W("### WF1 Switch (wf1) branches -> targets:")
for bi,br in enumerate(w1["connections"]["Switch"]["main"]):
    W("    main[%d] ->"%bi, [t["node"] for t in (br or [])])
W("### WF1 'IF - Cliente pausado' outputs:", w1["connections"].get("IF - Cliente pausado"))
W("### WF1 Router fallback 'No es comando' index:")
rr=n("Router de comandos",w1)["parameters"]["rules"]["values"]
W("   rules:",len(rr))
for bi,br in enumerate(w1["connections"]["Router de comandos"]["main"]):
    W("    main[%d] ->"%bi, [t["node"] for t in (br or [])])
open(os.path.join(base,"final.txt"),"w",encoding="utf-8").write("\n".join(out))
print("ok")

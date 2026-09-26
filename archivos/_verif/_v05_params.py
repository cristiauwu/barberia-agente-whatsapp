import json,sys,io
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace")
wf=json.load(open(r"G:\Barberia\archivos\_verif\wf_agente.json",encoding="utf-8"))
nodes={n["name"]:n for n in wf["nodes"]}
def p(n):
    print("="*30,n,"="*30)
    print(json.dumps(nodes[n].get("parameters",{}),ensure_ascii=False,indent=1)[:6000])
p("Postgres Chat Memory")
p("OpenAI Chat Model")
p("Webhook")
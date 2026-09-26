import json, urllib.request, sys, io
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace")
KEY=open(r"G:\Barberia\archivos\.n8n-key.txt").read().strip()
def api(p):
    r=urllib.request.Request("http://localhost:5678/api/v1"+p)
    r.add_header("X-N8N-API-KEY",KEY)
    return json.loads(urllib.request.urlopen(r,timeout=60).read().decode())
wf=api("/workflows/barberiaAgenteUncensored")
open(r"G:\Barberia\archivos\_verif\wf_agente.json","w",encoding="utf-8").write(json.dumps(wf,ensure_ascii=False,indent=1))
nodes=wf["nodes"]
print("total nodos:",len(nodes))
for n in nodes:
    print(f"- {n['name']} :: {n['type']} v{n.get('typeVersion')}")
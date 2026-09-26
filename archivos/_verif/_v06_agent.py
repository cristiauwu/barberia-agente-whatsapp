import json,sys,io
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace")
wf=json.load(open(r"G:\Barberia\archivos\_verif\wf_agente.json",encoding="utf-8"))
nodes={n["name"]:n for n in wf["nodes"]}
a=nodes["AI Agent"]["parameters"]
print("AGENT KEYS:",list(a.keys()))
print(a.get("text","") if isinstance(a.get("text"),str) else "")
print("--- systemMessage ---")
print(a.get("options",{}).get("systemMessage","<none>"))
print("--- promptType/messages ---")
print(json.dumps({k:v for k,v in a.items() if k not in ("text",)},ensure_ascii=False)[:3000])
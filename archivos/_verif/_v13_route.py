import json,sys,io,re
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace")
wf=json.load(open(r"G:\Barberia\archivos\_verif\wf_agente.json",encoding="utf-8"))
nodes={n["name"]:n for n in wf["nodes"]}
sm=nodes["AI Agent"]["parameters"]["options"]["systemMessage"]
print("systemMessage len",len(sm))
for term in ["no-show","no show","noshow","factura","factur","audio","foto","imagen","video"]:
    print(f"  {term!r}: {sm.lower().count(term.lower())}")
print("=== Switch ===")
print(json.dumps(nodes["Switch"]["parameters"],ensure_ascii=False,indent=1)[:3000])
print("=== Edit Fields ===")
print(json.dumps(nodes["Edit Fields"]["parameters"],ensure_ascii=False,indent=1)[:1500])
print("=== Edit Fields2 ===")
print(json.dumps(nodes["Edit Fields2"]["parameters"],ensure_ascii=False,indent=1)[:1500])
print("=== Normalizacion ===")
print(json.dumps(nodes["Normalizacion"]["parameters"],ensure_ascii=False,indent=1)[:2500])
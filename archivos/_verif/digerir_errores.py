import sys,io,json
sys.path.insert(0,r"G:\Barberia\archivos\_verif")
from harness import api, WF
if not getattr(sys.stdout,"_vutf8",False):
    sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace"); sys.stdout._vutf8=True

for eid in [1089,1091,1094,1106,1109]:
    det=api(f"/executions/{eid}?includeData=true")
    run=det["data"]["resultData"]["runData"]
    print("="*30,"EXEC",eid,"="*30)
    print("nodos:",list(run.keys()))
    for n in ["Normalizacion","AI Agent","IF - Respuesta no vacia","Mandar mensaje"]:
        v=run.get(n)
        if not v: print(f"  [{n}] NO EJECUTADO"); continue
        try:
            j=v[0]["data"]["main"][0]
        except Exception:
            j=None
        if n=="Normalizacion":
            print("  ENTRADA:",json.dumps(j[0]["json"].get("message_content"),ensure_ascii=False) if j else None,
                  "| de:",json.dumps(j[0]["json"].get("user_number")) if j else None)
        elif n=="AI Agent":
            o=j[0]["json"] if j else None
            print("  AI Agent output:",json.dumps(o.get("output"),ensure_ascii=False) if o else "SIN ITEMS")
            md=v[0].get("metadata",{})
            print("  meta:",json.dumps(md,ensure_ascii=False)[:400])
        elif n=="IF - Respuesta no vacia":
            print("  IF ramas: true=",len(j[0]) if j else 0,"items ; false=",len(j[1]) if j and len(j)>1 else 0)
            print("  IF json:",json.dumps(j[0][0]["json"],ensure_ascii=False) if j and j[0] else None)
        else:
            print("  Mandar mensaje:",json.dumps(v,ensure_ascii=False)[:700])
    print()
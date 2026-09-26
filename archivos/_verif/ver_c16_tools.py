import sys,io,json
sys.path.insert(0,r"G:\Barberia\archivos\_verif")
from harness import api, WF
if not getattr(sys.stdout,"_vutf8",False):
    sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace"); sys.stdout._vutf8=True
for eid in [1170,1174]:
    det=api(f"/executions/{eid}?includeData=true")
    run=det["data"]["resultData"]["runData"]
    print("="*25,"EXEC",eid,"="*25)
    print("nodos:",list(run.keys()))
    for k,v in run.items():
        if k.startswith(("Agendar","Registrar","Consultar")):
            s=json.dumps(v,ensure_ascii=False)
            print(f"  [{k}] len={len(s)}")
            print("   ",s[:900])
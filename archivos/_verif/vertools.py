import sys,io,json
sys.path.insert(0,r"G:\Barberia\archivos\_verif")
from harness import api, WF
if not getattr(sys.stdout,"_vutf8",False):
    sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace"); sys.stdout._vutf8=True

def dump(eid, nodos=None):
    det=api(f"/executions/{eid}?includeData=true")
    run=det["data"]["resultData"]["runData"]
    print("EXEC",eid)
    for k,v in run.items():
        if nodos and k not in nodos: continue
        if not k.lower().startswith(("consultar","agendar","cancelar","reagendar","registrar","notificar")):
            continue
        print("="*25,k,"="*25)
        s=json.dumps(v,ensure_ascii=False)
        print(s[:1200])

for eid in sys.argv[1:]:
    dump(eid)
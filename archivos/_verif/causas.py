import sys,io,json
sys.path.insert(0,r"G:\Barberia\archivos\_verif")
from harness import api, WF
if not getattr(sys.stdout,"_vutf8",False):
    sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace"); sys.stdout._vutf8=True

def causa(eid,wid):
    try:
        det=api(f"/executions/{eid}?includeData=true")
    except Exception as e:
        return "no pude leer: "+repr(e)
    d=det["data"]
    rd=d.get("resultData") or {}
    err=rd.get("error")
    out=[]
    if err:
        out.append("error.msg="+str(err.get("message"))[:300])
        out.append("error.node="+str((err.get("node") or {}).get("name")))
        out.append("error.desc="+str(err.get("description"))[:300])
    run=rd.get("runData") or {}
    las=None
    for k,v in run.items():
        try:
            st=v[0].get("executionStatus")
        except Exception:
            st=None
        if st and st!="success":
            las=(k,st)
            em=v[0].get("error")
            out.append(f"NODO FALLA={k} status={st} err={json.dumps(em,ensure_ascii=False)[:400] if em else None}")
    if not err and not las:
        out.append("sin error explicito; nodos:"+",".join(run.keys()))
    return " | ".join(out)

print("########## AGENTE ##########")
for eid in [1109,1106,1094,1091,1089]:
    print(f"--- exec {eid} ---")
    print(" ",causa(eid,WF))
print()
print("########## RECORDATORIOS ##########")
for eid in [733,732,731,722,720,703,687,680,611,596]:
    print(f"--- exec {eid} ---")
    print(" ",causa(eid,"barberiaRecordatorios"))
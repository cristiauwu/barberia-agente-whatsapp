import sys,io,json
sys.path.insert(0,r"G:\Barberia\archivos\_verif")
from harness import api, WF
if not getattr(sys.stdout,"_vutf8",False):
    sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace"); sys.stdout._vutf8=True
# ejecuciones posteriores al fix 21:39:50Z  (id >= 1110 aprox)
ex=api(f"/executions?workflowId={WF}&limit=90")["data"]
print("id | status | usa 'Respuesta sin texto'? | texto vacio a Mandar?")
vacios=0; fallback=0; n=0
for e in ex:
    if int(e["id"])<1110: continue
    det=api(f"/executions/{e['id']}?includeData=true")
    rd=det["data"].get("resultData") or {}
    run=rd.get("runData") or {}
    n+=1
    if "Respuesta sin texto" in run: fallback+=1
    mm=run.get("Mandar mensaje")
    vac=""
    if mm:
        try:
            t=mm[0]["data"]["main"][0][0]["json"]["message"]["conversation"]
            if not t or not t.strip(): vac="VACIO"; vacios+=1
        except Exception: pass
    if e["status"]!="success" or vac:
        print(" ",e["id"],e["status"],"fallback" if "Respuesta sin texto" in run else "-",vac)
print()
print(f"ejecuciones post-fix examinadas: {n}")
print(f"usaron respaldo 'Respuesta sin texto': {fallback}")
print(f"envios con texto vacio: {vacios}")
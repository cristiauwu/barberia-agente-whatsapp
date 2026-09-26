import sys,io,json
sys.path.insert(0,r"G:\Barberia\archivos\_verif")
from harness import api, WF
if not getattr(sys.stdout,"_vutf8",False):
    sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace"); sys.stdout._vutf8=True

for wid,nombre in [(WF,"AGENTE"),("barberiaRecordatorios","RECORDATORIOS"),("5zd5go4TFKqIsgdT","VIGILANCIA")]:
    try:
        ex=api(f"/executions?workflowId={wid}&limit=50")
    except Exception as e:
        print(nombre,"ERR",e); continue
    d=ex["data"]
    print(f"=== {nombre} ({wid}): {len(d)} ejecuciones ===")
    from collections import Counter
    print("  estados:",dict(Counter(e["status"] for e in d)))
    for e in d:
        if e["status"]!="success":
            print("  !!",e["id"],e["status"],e.get("startedAt"),e.get("stoppedAt"))
    print("  rango:",d[-1]["startedAt"] if d else None,"->",d[0]["startedAt"] if d else None)
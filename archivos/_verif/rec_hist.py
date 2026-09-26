import sys,io,json
sys.path.insert(0,r"G:\Barberia\archivos\_verif")
from harness import api
if not getattr(sys.stdout,"_vutf8",False):
    sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace"); sys.stdout._vutf8=True
wf=api("/workflows/barberiaRecordatorios")
print("Recordatorios updatedAt:",wf.get("updatedAt"),"createdAt:",wf.get("createdAt"),"activo:",wf.get("active"))
h=api("/workflows/barberiaRecordatorios/history?limit=10")
for v in h["data"]:
    print("  ver:",v["createdAt"],"|",v["name"],"|",(v.get("description") or "")[:90])
print()
ex=api("/executions?workflowId=barberiaRecordatorios&limit=24")["data"]
print("ultimas:",len(ex))
for e in ex[:12]:
    print("  ",e["id"],e["status"],e.get("startedAt"))
print("errores mas recientes:")
for e in ex:
    if e["status"]=="error":
        print("  ",e["id"],e.get("startedAt")); break
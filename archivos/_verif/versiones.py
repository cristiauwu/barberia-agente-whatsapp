import sys,io,json
sys.path.insert(0,r"G:\Barberia\archivos\_verif")
from harness import api, WF
if not getattr(sys.stdout,"_vutf8",False):
    sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace"); sys.stdout._vutf8=True
wf=api(f"/workflows/{WF}")
print("workflow createdAt:",wf.get("createdAt"),"updatedAt:",wf.get("updatedAt"))
print("active:",wf.get("active"),"versionId:",wf.get("versionId"))
print()
try:
    h=api(f"/workflows/{WF}/history?limit=20")
    print("HISTORIAL:",json.dumps(h,ensure_ascii=False)[:1500])
except Exception as e:
    print("history err",e)
print()
try:
    ex=api(f"/workflows/{WF}/executions?limit=1")
    print(ex)
except Exception as e:
    pass
# publicacion
try:
    pub=api(f"/workflows/{WF}?includeData=true")
except Exception as e:
    pass
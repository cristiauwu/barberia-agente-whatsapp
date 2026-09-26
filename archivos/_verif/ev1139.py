import sys,io,json,datetime
sys.path.insert(0,r"G:\Barberia\archivos\_verif")
from harness import api, WF
if not getattr(sys.stdout,"_vutf8",False):
    sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace"); sys.stdout._vutf8=True
det=api(f"/executions/1139?includeData=true")
d=det["data"]
print("exec 1139 startedAt:",d.get("startedAt"),"stoppedAt:",d.get("stoppedAt"),"status:",d.get("status"))
run=d["resultData"]["runData"]
print("user_number:",run["Normalizacion"][0]["data"]["main"][0][0]["json"]["user_number"])
print("user_name:",run["Normalizacion"][0]["data"]["main"][0][0]["json"]["user_name"])
print("nodos:",list(run.keys()))
for k,v in run.items():
    if k.lower().startswith(("consultar",)):
        s=json.dumps(v,ensure_ascii=False)
        import re
        for m in re.finditer(r'"(?:After|Before)":\s*"[^"]*"',s): print("  ARG",m.group(0))
        for m in re.finditer(r'"dateTime":\s*"20[^"]*"',s): print("  DT",m.group(0))
wf=api(f"/workflows/{WF}")
print("workflow updatedAt:",wf.get("updatedAt"))
h=api(f"/workflows/{WF}/history?limit=3")
for x in h["data"]: print("  version:",x["createdAt"],x["name"])
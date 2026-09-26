import sys,io,json,re
sys.path.insert(0,r"G:\Barberia\archivos\_verif")
from harness import api
if not getattr(sys.stdout,"_vutf8",False):
    sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace"); sys.stdout._vutf8=True

eid=sys.argv[1]
det=api(f"/executions/{eid}?includeData=true")
run=det["data"]["resultData"]["runData"]
for k,v in run.items():
    s=json.dumps(v,ensure_ascii=False)
    if "After" in s or "Before" in s or "intermediateSteps" in s or "tool_calls" in s:
        print("### nodo",k,"len",len(s))
        for m in re.finditer(r'"(?:After|Before)":\s*"[^"]*"',s):
            print("   ARG:",m.group(0))
        for m in re.finditer(r'"name":\s*"(Consultar agenda|Agendar cita|Registrar en hoja de citas|Notificar al encargado|Reagendar|Cancelar cita)"',s):
            print("   TOOL:",m.group(0))
        for m in re.finditer(r'"(?:Start|End)":\s*"20[^"]*"',s):
            print("   DT:",m.group(0))
        for m in re.finditer(r'"summary":\s*"[^"]*"',s):
            print("   EV:",m.group(0)[:140])
import sys,io,json
sys.path.insert(0,r"G:\Barberia\archivos\_verif")
from harness import api, WF
if not getattr(sys.stdout,"_vutf8",False):
    sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace"); sys.stdout._vutf8=True
ex=api(f"/executions?workflowId={WF}&limit=90")["data"]
for e in ex:
    if int(e["id"])<1110: continue
    det=api(f"/executions/{e['id']}?includeData=true")
    run=(det["data"].get("resultData") or {}).get("runData") or {}
    if "Respuesta sin texto" not in run: continue
    ent=""
    try: ent=run["Normalizacion"][0]["data"]["main"][0][0]["json"]["message_content"]
    except Exception: pass
    ag=""
    try: ag=run["AI Agent"][0]["data"]["main"][0][0]["json"].get("output")
    except Exception: pass
    txt=""
    try: txt=run["Mandar mensaje"][0]["data"]["main"][0][0]["json"]["message"]["conversation"]
    except Exception: pass
    print(f"--- exec {e['id']} entrada={ent!r}")
    print(f"    AI Agent output={ag!r}")
    print(f"    enviado={txt!r}")
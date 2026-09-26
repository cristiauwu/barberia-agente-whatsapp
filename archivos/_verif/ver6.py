import sys,io,json
sys.path.insert(0,r"G:\Barberia\archivos\_verif")
from harness import api, WF
if not getattr(sys.stdout,"_vutf8",False):
    sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace"); sys.stdout._vutf8=True
for eid in [1169,1164,1139,1132,1129,1100]:
    det=api(f"/executions/{eid}?includeData=true")
    run=det["data"]["resultData"]["runData"]
    try: txt=run["Mandar mensaje"][0]["data"]["main"][0][0]["json"]["message"]["conversation"]
    except Exception: txt=None
    try: ent=run["Normalizacion"][0]["data"]["main"][0][0]["json"]["message_content"]
    except Exception: ent=None
    print("="*28,"EXEC",eid,"="*28)
    print("ENTRADA:",json.dumps(ent,ensure_ascii=False))
    print("TEXTO CRUDO:")
    print(repr(txt))
    print()
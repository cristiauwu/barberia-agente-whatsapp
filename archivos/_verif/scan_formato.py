import sys,io,json,re
sys.path.insert(0,r"G:\Barberia\archivos\_verif")
from harness import api, WF
if not getattr(sys.stdout,"_vutf8",False):
    sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace"); sys.stdout._utf8=True
    sys.stdout._vutf8=True
# tras el fix (22:00 UTC en adelante). Ventana amplia: ultimas 90 ejecuciones
ex=api(f"/executions?workflowId={WF}&limit=90")["data"]
print("ejecuciones:",len(ex))
malos={}
tot=0
for e in ex:
    det=api(f"/executions/{e['id']}?includeData=true")
    rd=det["data"].get("resultData") or {}
    run=rd.get("runData") or {}
    mm=run.get("Mandar mensaje")
    if not mm: continue
    try: js=mm[0]["data"]["main"][0][0]["json"]
    except Exception: continue
    txt=js.get("message",{}).get("conversation")
    if not txt: continue
    tot+=1
    pr=[]
    if "**" in txt: pr.append("dbl**")
    for i,l in enumerate(txt.split("\n")):
        if l!=l.rstrip(): pr.append("trailWS@%d"%i); break
    for i,l in enumerate(txt.split("\n")):
        if l!=l.lstrip() and l.strip(): pr.append("indent@%d"%i); break
    if len(txt.split("\n"))>10: pr.append(">10lineas(%d)"%len(txt.split("\n")))
    if len(txt)>620: pr.append(">620char(%d)"%len(txt))
    if re.search(r'[╔╗╚╝┏┓┗┛━─═]',txt): pr.append("marco")
    em=re.findall(r'[\U0001F300-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F]',txt)
    if len(em)>1: pr.append("emoji=%d"%len(em))
    if pr: malos[e["id"]]=pr
print("respuestas examinadas:",tot)
print("con posibles problemas:",len(malos))
for k,v in malos.items(): print("  exec",k,v)
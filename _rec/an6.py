import json,urllib.request,sys
sys.stdout.reconfigure(encoding="utf-8")
KEY=open(r"G:\Barberia\archivos\.n8n-key.txt",encoding="utf-8").read().strip()
r=urllib.request.Request("http://localhost:5678/api/v1/workflows/barberiaAgenteUncensored")
r.add_header("X-N8N-API-KEY",KEY)
ag=json.loads(urllib.request.urlopen(r,timeout=120).read().decode())
for n in ag["nodes"]:
    nm=n["name"].lower(); ty=n["type"]
    if any(k in nm for k in ("hoja","sheet","cancel","reagend","reprogram","calendar")) or "Sheet" in ty or "Calendar" in ty:
        p=n.get("parameters",{})
        print(f"{n['name']!r:<42} {ty:<45} op={p.get('operation')}")

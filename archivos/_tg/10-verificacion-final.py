import json, urllib.request, io

KEY = open(r"G:\Barberia\archivos\.n8n-key.txt").read().strip()
BASE = "http://localhost:5678/api/v1"
out = io.StringIO()

def api(p):
    r = urllib.request.Request(BASE + p)
    r.add_header("X-N8N-API-KEY", KEY)
    with urllib.request.urlopen(r, timeout=60) as x:
        return json.loads(x.read().decode())

lst = api("/workflows?limit=50")["data"]
out.write("=== VERIFICACION FINAL: workflows tras la evaluacion ===\n")
for w in lst:
    out.write(f"  {w['id']}\t{w['name']}\tactive={w.get('active')}\n")
out.write(f"\ntotal workflows: {len(lst)}\n")
out.write("barberiaAlertas existe? " + str(any("barberiaAlertas" in w["name"] for w in lst)) + "\n")

tg = 0
for w in lst:
    d = api("/workflows/" + w["id"])
    for n in d["nodes"]:
        if "telegram" in n["type"].lower():
            tg += 1
            out.write(f"  NODO TELEGRAM: {w['name']} / {n['name']}\n")
out.write(f"nodos telegram totales: {tg}\n")

creds = api("/credentials?limit=100")["data"]
out.write(f"\ncredenciales: {len(creds)}\n")
out.write("telegramApi existe? " + str(any(c["type"] == "telegramApi" for c in creds)) + "\n")

open(r"G:\Barberia\archivos\_tg\10-verificacion-final.txt", "w", encoding="utf-8").write(out.getvalue())
print("OK")
import json, urllib.request, urllib.error

KEY = open(r"G:\Barberia\archivos\.n8n-key.txt").read().strip()
BASE = "http://localhost:5678/api/v1"
lines = []

def api(p):
    r = urllib.request.Request(BASE + p)
    r.add_header("X-N8N-API-KEY", KEY)
    try:
        with urllib.request.urlopen(r, timeout=60) as x:
            return json.loads(x.read().decode())
    except urllib.error.HTTPError as e:
        lines.append(f"HTTPError {e.code} on {p}: {e.read().decode()[:300]}")
        return None

lst = api("/workflows?limit=50")
lines.append("=== WORKFLOWS ===")
ids = []
if lst:
    for w in lst.get("data", []):
        ids.append(w["id"])
        lines.append(f"{w['id']}\t{w['name']}\tactive={w.get('active')}")

for wid in ids:
    w = api("/workflows/" + wid)
    if not w:
        continue
    lines.append(f"\n=== {wid} | {w.get('name')} | active={w.get('active')} | nodes={len(w.get('nodes', []))} ===")
    for n in w.get("nodes", []):
        lines.append(f"  - {n['name']}  [{n['type']}]  disabled={n.get('disabled')}")

lines.append("\n=== CREDENCIALES ===")
c = api("/credentials?limit=100")
if c:
    for x in c.get("data", []):
        lines.append(f"{x['id']}\t{x['name']}\t{x['type']}")

open(r"G:\Barberia\archivos\_tg\01-inspeccion.txt", "w", encoding="utf-8").write("\n".join(lines))
print("OK")
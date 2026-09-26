import json, urllib.request, io

KEY = open(r"G:\Barberia\archivos\.n8n-key.txt").read().strip()
BASE = "http://localhost:5678/api/v1"
out = io.StringIO()

def api(p):
    r = urllib.request.Request(BASE + p)
    r.add_header("X-N8N-API-KEY", KEY)
    with urllib.request.urlopen(r, timeout=90) as x:
        return json.loads(x.read().decode())

w = api("/workflows/barberiaAgenteUncensored")
want = ["Preparar rango de fechas", "Leer agenda del rango", "Formatear agenda",
        "Responder al operador", "Consultar agenda", "Leer estado del sistema", "Formatear estado"]
for n in w["nodes"]:
    if n["name"] in want:
        out.write(f"\n=== {n['name']} [{n['type']}] v{n.get('typeVersion')} creds={json.dumps(n.get('credentials'))} ===\n")
        out.write(json.dumps(n.get("parameters"), ensure_ascii=False, indent=2)[:6000] + "\n")

out.write("\n=== credencial Evolution (estructura) ===\n")
for c in api("/credentials?limit=100")["data"]:
    out.write(f"{c['id']} | {c['name']} | {c['type']}\n")

open(r"G:\Barberia\archivos\_tg\09-reutilizar.txt", "w", encoding="utf-8").write(out.getvalue())
print("OK")
import json, urllib.request, io

KEY = open(r"G:\Barberia\archivos\.n8n-key.txt").read().strip()
BASE = "http://localhost:5678/api/v1"
out = io.StringIO()

def api(p):
    r = urllib.request.Request(BASE + p)
    r.add_header("X-N8N-API-KEY", KEY)
    with urllib.request.urlopen(r, timeout=90) as x:
        return json.loads(x.read().decode())

def dump(wid, names):
    w = api("/workflows/" + wid)
    out.write(f"\n########## {wid} / {w.get('name')} (active={w.get('active')}) ##########\n")
    out.write("--- connections (resumen) ---\n")
    for src, conn in (w.get("connections") or {}).items():
        outs = []
        for k, v in conn.items():
            for arr in v:
                outs.append(f"{k}->" + ",".join(x["node"] for x in arr))
        out.write(f"  {src}: {'; '.join(outs)}\n")
    for n in w["nodes"]:
        if n["name"] in names or (names == ["*"]):
            out.write(f"\n=== NODO: {n['name']} [{n['type']}] disabled={n.get('disabled')} ===\n")
            out.write(json.dumps(n.get("parameters"), ensure_ascii=False, indent=2)[:4000] + "\n")

dump("barberiaRecordatorios", ["Notificar cita nueva al encargado", "IF - Es cita agendada", "Code", "Switch"])
dump("5zd5go4TFKqIsgdT", ["Avisar al dueño", "IF - Hay citas pasadas", "Buscar citas pasadas"])
dump("barberiaAgenteUncensored", ["Notificar al encargado", "¿Es operador?", "Router de comandos", "IF - No es del bot"])

open(r"G:\Barberia\archivos\_tg\04-nodos.txt", "w", encoding="utf-8").write(out.getvalue())
print("OK")
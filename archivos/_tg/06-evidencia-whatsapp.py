import json, urllib.request, io, subprocess

KEY = open(r"G:\Barberia\archivos\.n8n-key.txt").read().strip()
BASE = "http://localhost:5678/api/v1"
DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
out = io.StringIO()

def api(p):
    r = urllib.request.Request(BASE + p)
    r.add_header("X-N8N-API-KEY", KEY)
    with urllib.request.urlopen(r, timeout=90) as x:
        return json.loads(x.read().decode())

# API key de Evolution
p = subprocess.run([DOCKER, "exec", "evolution_api", "printenv", "AUTHENTICATION_API_KEY"],
                   capture_output=True, text=True)
APIKEY = (p.stdout or "").strip()
out.write(f"Evolution AUTHENTICATION_API_KEY presente: {bool(APIKEY)} (len={len(APIKEY)})\n")

def evo(path, method="GET", body=None):
    url = "http://localhost:8080" + path
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("apikey", APIKEY)
    r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=30) as x:
            return json.loads(x.read().decode())
    except Exception as e:
        return {"__error__": str(e)}

inst = evo("/instance/fetchInstances")
out.write("\n=== instancias Evolution ===\n")
out.write(json.dumps(inst, ensure_ascii=False)[:2000] + "\n")

# Evidencia real: ejecucion 838 (cita agendada) -> se ejecuto el aviso?
for eid in [838, 800]:
    det = api(f"/executions/{eid}?includeData=true")
    rd = (((det.get("data") or {}).get("resultData") or {}).get("runData") or {})
    out.write(f"\n=== ejecucion {eid} -> nodos ejecutados ===\n")
    for name, runs in rd.items():
        out.write(f"  - {name}\n")
    node = rd.get("Notificar cita nueva al encargado")
    if node:
        out.write("  >> Aviso ejecutado. Salida:\n")
        out.write(json.dumps(node[0].get("data", {}).get("main", []), ensure_ascii=False)[:1500] + "\n")

# Ultimo aviso real (buscar en ejecuciones la salida del nodo de aviso)
out.write("\n=== buscar ultima ejecucion con aviso enviado ===\n")
ex = api("/executions?limit=60")
found = 0
for e in ex["data"]:
    if e.get("workflowId") != "barberiaRecordatorios":
        continue
    det = api(f"/executions/{e['id']}?includeData=true")
    rd = (((det.get("data") or {}).get("resultData") or {}).get("runData") or {})
    node = rd.get("Notificar cita nueva al encargado")
    if node:
        out.write(f"  ejecucion {e['id']} ({e.get('startedAt')}) SI ejecuto el aviso\n")
        out.write("   salida: " + json.dumps(node[0].get("data", {}).get("main", []), ensure_ascii=False)[:800] + "\n")
        found += 1
        if found >= 3:
            break
if not found:
    out.write("  (no se encontro en las ultimas 60 ejecuciones)\n")

open(r"G:\Barberia\archivos\_tg\06-evidencia-whatsapp.txt", "w", encoding="utf-8").write(out.getvalue())
print("OK")
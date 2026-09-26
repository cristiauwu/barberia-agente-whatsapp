import json, urllib.request, io, subprocess, collections

KEY = open(r"G:\Barberia\archivos\.n8n-key.txt").read().strip()
BASE = "http://localhost:5678/api/v1"
DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
out = io.StringIO()

def api(p):
    r = urllib.request.Request(BASE + p)
    r.add_header("X-N8N-API-KEY", KEY)
    with urllib.request.urlopen(r, timeout=90) as x:
        return json.loads(x.read().decode())

# 1) Telegram reachability from host and from n8n container
out.write("=== CONECTIVIDAD api.telegram.org ===\n")
try:
    r = urllib.request.Request("https://api.telegram.org/")
    with urllib.request.urlopen(r, timeout=15) as x:
        out.write(f"host -> HTTP {x.status} body={x.read().decode()[:200]}\n")
except Exception as e:
    out.write(f"host -> ERROR {e}\n")

p = subprocess.run([DOCKER, "exec", "barberia-n8n", "wget", "-q", "-O", "-", "--timeout=15",
                    "https://api.telegram.org/"], capture_output=True, text=True, timeout=60)
out.write(f"n8n container -> rc={p.returncode} out={p.stdout[:200]!r} err={p.stderr[:200]!r}\n")

# getMe sin token (debe dar 401, confirma que el endpoint responde)
try:
    r = urllib.request.Request("https://api.telegram.org/bot000/getMe")
    with urllib.request.urlopen(r, timeout=15) as x:
        out.write(f"getMe fake -> {x.read().decode()[:300]}\n")
except Exception as e:
    body = getattr(e, "read", lambda: b"")()
    out.write(f"getMe fake -> {e} body={body[:300]!r}\n")

# 2) version de n8n y nodo Telegram disponible
p = subprocess.run([DOCKER, "exec", "barberia-n8n", "n8n", "--version"], capture_output=True, text=True, timeout=90)
out.write(f"\nn8n version: rc={p.returncode} out={p.stdout.strip()} err={p.stderr.strip()[:200]}\n")

p = subprocess.run([DOCKER, "exec", "barberia-n8n", "sh", "-c",
                    "ls /usr/local/lib/node_modules/n8n/node_modules | grep -i telegram || true"],
                   capture_output=True, text=True, timeout=60)
out.write(f"nodo telegram: out={p.stdout.strip()!r} err={p.stderr.strip()[:200]!r}\n")

# 3) Volumen de mensajes al dueno en Evolution
APIKEY = subprocess.run([DOCKER, "exec", "evolution_api", "printenv", "AUTHENTICATION_API_KEY"],
                        capture_output=True, text=True).stdout.strip()
def evo(path, method="GET", body=None):
    url = "http://localhost:8080" + path
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("apikey", APIKEY); r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=40) as x:
            return json.loads(x.read().decode())
    except Exception as e:
        return {"__error__": str(e)}

out.write("\n=== conteo de mensajes (Evolution) ===\n")
for jid in ["5214521206246@s.whatsapp.net", "524521206246@s.whatsapp.net", "5214501111805@s.whatsapp.net"]:
    msgs = evo(f"/chat/findMessages/hector", "POST", {"where": {"key": {"remoteJid": jid}}, "limit": 500})
    recs = []
    if isinstance(msgs, dict):
        recs = (((msgs.get("messages") or {}).get("records")) or msgs.get("records") or [])
    out.write(f"{jid}: {len(recs)} mensajes recuperados  err={msgs.get('__error__')}\n")

open(r"G:\Barberia\archivos\_tg\07-viabilidad.txt", "w", encoding="utf-8").write(out.getvalue())
print("OK")
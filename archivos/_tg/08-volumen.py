import json, urllib.request, io, subprocess, collections, datetime

DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
APIKEY = subprocess.run([DOCKER, "exec", "evolution_api", "printenv", "AUTHENTICATION_API_KEY"],
                        capture_output=True, text=True).stdout.strip()
out = io.StringIO()

def evo(path, method="GET", body=None):
    url = "http://localhost:8080" + path
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("apikey", APIKEY); r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=60) as x:
            return json.loads(x.read().decode())
    except Exception as e:
        return {"__error__": str(e)}

# Telegram node package present in n8n image?
p = subprocess.run([DOCKER, "exec", "barberia-n8n", "sh", "-c",
    "find / -maxdepth 8 -type d -name 'n8n-nodes-base' 2>/dev/null | head -3"], capture_output=True, text=True, timeout=120)
out.write("find n8n-nodes-base: " + p.stdout.strip() + "\n")
p = subprocess.run([DOCKER, "exec", "barberia-n8n", "sh", "-c",
    "ls $(find / -maxdepth 8 -type d -name 'n8n-nodes-base' | head -1)/dist/nodes 2>/dev/null | grep -i -E 'telegram|httpRequest' "],
    capture_output=True, text=True, timeout=120)
out.write("nodos disponibles: " + repr(p.stdout.strip()) + " err=" + repr(p.stderr.strip()[:200]) + "\n")

# Volumen real de avisos: mensajes fromMe al owner
out.write("\n=== mensajes fromMe (bot->dueno) por dia ===\n")
dia = collections.Counter()
horas = collections.Counter()
for jid, label in [("5214521206246@s.whatsapp.net", "dueno-aliases")]:
    for page in range(1, 4):
        msgs = evo(f"/chat/findMessages/hector", "POST",
                   {"where": {"key": {"remoteJid": jid}}, "limit": 200, "page": page})
        recs = (((msgs.get("messages") or {}).get("records")) or []) if isinstance(msgs, dict) else []
        if not recs:
            break
        for m in recs:
            ts = m.get("messageTimestamp")
            fm = (m.get("key") or {}).get("fromMe")
            txt = (((m.get("message") or {}).get("conversation")) or "")
            if not ts:
                continue
            d = datetime.datetime.utcfromtimestamp(int(ts)).strftime("%Y-%m-%d")
            dia[(d, bool(fm))] += 1
            if fm:
                horas[datetime.datetime.utcfromtimestamp(int(ts)).strftime("%H")] += 1
out.write("fecha | fromMe(bool) | count\n")
for k in sorted(dia):
    out.write(f"  {k[0]}  fromMe={k[1]}  {dia[k]}\n")
out.write("\nmensajes del bot por hora UTC:\n")
for h in sorted(horas):
    out.write(f"  {h}h  {'#'*horas[h]} ({horas[h]})\n")

open(r"G:\Barberia\archivos\_tg\08-volumen.txt", "w", encoding="utf-8").write(out.getvalue())
print("OK")
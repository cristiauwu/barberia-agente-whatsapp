# -*- coding: utf-8 -*-
import io, json, sys, time, urllib.request, uuid
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

N8N = "http://localhost:5678/api/v1"
WID = "barberiaAgenteUncensored"
JID = "5214501111805@s.whatsapp.net"
KEY = open(r"G:\Barberia\archivos\.n8n-key.txt", encoding="utf-8").read().strip()
buf=[]
def w(*a):
    s=" ".join(str(x) for x in a); buf.append(s); print(s)

def api(p):
    r = urllib.request.Request(N8N + p); r.add_header("X-N8N-API-KEY", KEY)
    with urllib.request.urlopen(r, timeout=120) as x:
        return json.loads(x.read().decode())

base = api("/executions?workflowId=%s&limit=3" % WID)
ultimo = int(base["data"][0]["id"])
w("Ejecucion base: %s  (estados: %s)" % (ultimo, [ (e['id'], e.get('status')) for e in base['data']]))

APIKEY_FALSA = "CLAVE_FALSA_DE_ATACANTE_1234567890"
TEXTO = "cual es el precio del corte?"
body = {"event": "messages.upsert", "instance": "hector",
        "server_url": "http://evolution_api:8080", "apikey": APIKEY_FALSA,
        "date_time": "2026-09-26T23:00:00.000Z",
        "data": {"key": {"id": "T" + uuid.uuid4().hex[:10].upper(),
                         "remoteJid": JID, "fromMe": False},
                 "pushName": "Prueba Auditoria",
                 "message": {"conversation": TEXTO},
                 "messageType": "conversation"}}
req = urllib.request.Request("http://localhost:5678/webhook/hector",
                             data=json.dumps(body).encode(), method="POST")
req.add_header("Content-Type", "application/json")
with urllib.request.urlopen(req, timeout=180) as r:
    w("POST con apikey FALSA -> HTTP %s %s" % (r.status, r.read()[:200].decode()))

for intento in range(12):
    time.sleep(6)
    ex = api("/executions?workflowId=%s&limit=6" % WID)
    nuevas = [e for e in ex.get("data", []) if int(e["id"]) > ultimo]
    w("  t+%2ds -> ejecuciones nuevas: %s" % ((intento+1)*6, [(e['id'], e.get('status')) for e in nuevas]))
    if nuevas:
        for e in nuevas:
            det = api("/executions/%s?includeData=true" % e["id"])
            try:
                run = det["data"]["resultData"]["runData"]
            except Exception as ex2:
                w("      (sin runData: %r)" % (ex2,)); continue
            if "Normalizacion" in run:
                nm = run["Normalizacion"][0]["data"]["main"][0][0]["json"]
                w("      Normalizacion.instance_apikey = %r" % nm.get("instance_apikey"))
                w("      Normalizacion.instance_server_url = %r" % nm.get("instance_server_url"))
                w("      Normalizacion.instance_name = %r" % nm.get("instance_name"))
            if "Mandar mensaje" in run:
                out = run["Mandar mensaje"][0]["data"]["main"][0][0]["json"]
                w("      Mandar mensaje -> %s" % json.dumps(out, ensure_ascii=False)[:400])
            if "Aviso solo texto" in run:
                w("      Aviso solo texto presente")
        break

io.open(r"G:\Barberia\_audit\_sec_webhook_auth2.txt","w",encoding="utf-8").write("\n".join(buf))
print("\n[escrito]")
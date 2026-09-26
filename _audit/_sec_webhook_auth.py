# -*- coding: utf-8 -*-
"""Verifica si el webhook valida el 'apikey' del cuerpo.
Se envia un apikey FALSO. Si el workflow arranca igual, no hay validacion.
NO se usa el numero del dueno. JID de pruebas."""
import json, os, re, subprocess, sys, time, urllib.request, uuid
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DOCKER = (r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop"
          r"\resources\bin\docker.exe")
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

base = api("/executions?workflowId=%s&limit=1" % WID)
ultimo = int(base["data"][0]["id"]) if base.get("data") else 0
w("Ejecucion base: %s" % ultimo)

w("\n" + "#" * 84)
w("# PRUEBA DE CONTROL DE ACCESO EN EL WEBHOOK")
w("# Se manda apikey=FALSA. Si el workflow se ejecuta -> el webhook NO autentica.")
w("#" * 84)

TEXTO = "cual es el precio del corte?"
APikeyFalsa = "CLAVE_FALSA_DE_ATACANTE_1234567890"
body = {"event": "messages.upsert", "instance": "hector",
        "server_url": "http://evolution_api:8080", "apikey": APikeyFalsa,
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
    w("  POST webhook con apikey FALSA -> HTTP %s  %s" % (r.status, r.read()[:200].decode()))

time.sleep(8)
ex = api("/executions?workflowId=%s&limit=5" % WID)
nuevas = [e for e in ex.get("data", []) if int(e["id"]) > ultimo]
w("  Ejecuciones creadas DESPUES del intento: %d" % len(nuevas))
for e in nuevas:
    w("     id=%s status=%s" % (e["id"], e.get("status")))

# ¿a donde se envio el mensaje? Deberia ser el numero de Evolution, no el del atacante
for e in nuevas:
    det = api("/executions/%s?includeData=true" % e["id"])
    run = det["data"]["resultData"]["runData"]
    if "Normalizacion" in run:
        nm = run["Normalizacion"][0]["data"]["main"][0][0]["json"]
        w("  Normalizacion.instance_apikey = %r" % nm.get("instance_apikey"))
        w("  Normalizacion.instance_server_url = %r" % nm.get("instance_server_url"))
    if "Mandar mensaje" in run:
        nm = run["Mandar mensaje"][0]["data"]["main"][0][0]["json"]
        w("  Destino del envio (Mandar mensaje) = %s" % json.dumps(nm, ensure_ascii=False)[:500])

w("\n  >> Si instance_apikey == '%s', el sistema USO la clave que le dio el" % APikeyFalsa)
w("     atacante. Eso significa que el webhook no autentica al emisor y que el")
w("     atacante controla hacia donde y con que clave n8n habla con Evolution.")

io.open(r"G:\Barberia\_audit\_sec_webhook_auth.txt","w",encoding="utf-8").write("\n".join(buf))
print("\n[escrito]")
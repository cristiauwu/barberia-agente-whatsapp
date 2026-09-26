# -*- coding: utf-8 -*-
"""Prueba aislada: ¿el webhook valida el apikey del cuerpo?
Usa un MARCADOR UNICO en el texto para localizar exactamente esa ejecucion."""
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

MARCA = "ZQ" + uuid.uuid4().hex[:8].upper()
APikeyFalsa = "CLAVE_FALSA_ATACANTE_" + MARCA
TEXTO = "que precio tiene el corte? (marca %s)" % MARCA

w("MARCADOR DE ESTA PRUEBA: %s" % MARCA)
base = api("/executions?workflowId=%s&limit=3" % WID)
ultimo = int(base["data"][0]["id"])
w("Ejecucion base: %s" % ultimo)

body = {"event": "messages.upsert", "instance": "hector",
        "server_url": "http://evolution_api:8080", "apikey": APikeyFalsa,
        "date_time": "2026-09-26T23:00:00.000Z",
        "data": {"key": {"id": "T" + uuid.uuid4().hex[:10].upper(),
                         "remoteJid": JID, "fromMe": False},
                 "pushName": "Auditoria " + MARCA,
                 "message": {"conversation": TEXTO},
                 "messageType": "conversation"}}
req = urllib.request.Request("http://localhost:5678/webhook/hector",
                             data=json.dumps(body).encode(), method="POST")
req.add_header("Content-Type", "application/json")
with urllib.request.urlopen(req, timeout=180) as r:
    w("POST con apikey FALSA -> HTTP %s %s" % (r.status, r.read()[:200].decode()))

encontrada = None
for intento in range(20):
    time.sleep(6)
    ex = api("/executions?workflowId=%s&limit=12" % WID)
    for e in ex.get("data", []):
        if int(e["id"]) <= ultimo:
            continue
        try:
            det = api("/executions/%s?includeData=true" % e["id"])
            run = det["data"]["resultData"]["runData"]
        except Exception:
            continue
        # localizar por el marcador en el TRIGGER o Normalizacion
        blob = json.dumps(run, ensure_ascii=False)
        if MARCA in blob:
            encontrada = (e["id"], run)
            break
    if encontrada:
        break

w("\n" + "=" * 84)
if not encontrada:
    w("!! No se encontro ninguna ejecucion con el marcador %s" % MARCA)
    w("   (el webhook pudo haber rechazado, o el workflow tardo mas)")
else:
    eid, run = encontrada
    w("EJECUCION ENCONTRADA: %s" % eid)
    w("=" * 84)
    if "Normalizacion" in run:
        nm = run["Normalizacion"][0]["data"]["main"][0][0]["json"]
        w("  Normalizacion.instance_apikey      = %r" % nm.get("instance_apikey"))
        w("  Normalizacion.instance_server_url  = %r" % nm.get("instance_server_url"))
        w("  Normalizacion.instance_name        = %r" % nm.get("instance_name"))
        w("  Normalizacion.user_number          = %r" % nm.get("user_number"))
        w("  Normalizacion.user_name            = %r" % nm.get("user_name"))
        w("")
        w("  >> apikey ENVIADA POR EL ATACANTE  = %r" % APikeyFalsa)
        if nm.get("instance_apikey") == APikeyFalsa:
            w("  >>> RESULTADO: el sistema ACEPTO y USO la clave del atacante. NO HAY VALIDACION.")
        else:
            w("  >>> RESULTADO: el sistema IGNORO la clave del atacante (uso otra).")
            w("      La clave efectiva fue: %r" % nm.get("instance_apikey"))
    if "Mandar mensaje" in run:
        out = run["Mandar mensaje"][0]["data"]["main"][0][0]["json"]
        w("  Envio final (Mandar mensaje): %s" % json.dumps(out, ensure_ascii=False)[:600])

io.open(r"G:\Barberia\_audit\_sec_webhook_aislado.txt","w",encoding="utf-8").write("\n".join(buf))
print("\n[escrito]")
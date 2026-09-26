import json, urllib.request, subprocess, sys, io, uuid, time
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace")
DOCKER=r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
KEY=subprocess.run([DOCKER,"exec","evolution_api","printenv","AUTHENTICATION_API_KEY"],capture_output=True,text=True).stdout.strip()
print("evolution key len:",len(KEY))

def enviar(jid,texto):
    body={"event":"messages.upsert","instance":"hector",
      "server_url":"http://evolution_api:8080","apikey":KEY,
      "date_time":"2026-09-25T23:00:00.000Z",
      "data":{"key":{"id":"T"+uuid.uuid4().hex[:10].upper(),"remoteJid":jid,"fromMe":False},
        "pushName":"Prueba Verif","message":{"conversation":texto},
        "messageType":"conversation"}}
    req=urllib.request.Request("http://localhost:5678/webhook/hector",
        data=json.dumps(body).encode(),method="POST")
    req.add_header("Content-Type","application/json")
    try:
        r=urllib.request.urlopen(req,timeout=180)
        return ("HTTP "+str(r.status), r.read().decode()[:300])
    except Exception as e:
        return ("ERR",repr(e))

for jid in ["5214501111805@s.whatsapp.net","5214501119999@s.whatsapp.net"]:
    print(jid, enviar(jid,"?") if False else "")
print("sin envio aun")
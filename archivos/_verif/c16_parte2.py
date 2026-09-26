import sys,io,json,time
sys.path.insert(0,r"G:\Barberia\archivos\_verif")
from harness import enviar
import cal
if not getattr(sys.stdout,"_vutf8",False):
    sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace"); sys.stdout._vutf8=True
JID="5214501111805@s.whatsapp.net"
# nueva conversacion (memoria borrada) para simular OTRO cliente que pide la misma hora
import subprocess
DOCKER=r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
subprocess.run([DOCKER,"exec","barberia-postgres","psql","-U","barberia","-d","barberia","-c",
  f"DELETE FROM n8n_chat_histories WHERE session_id='{JID}';"],capture_output=True,text=True)
print("memoria borrada para simular segundo cliente")

r1=enviar(JID,"hola",pushName="Otro Cliente")
print(">>> hola ->",r1.get("respuesta"))
time.sleep(14)
r2=enviar(JID,"quiero un corte mañana a la 1 de la tarde",pushName="Otro Cliente")
print("\n>>> peticion misma hora ->",r2.get("respuesta"))
print("    exec",r2.get("exec_id"),r2.get("status"))
time.sleep(3)
print("\n--- CALENDARIO 2026-09-26 tras la 2a peticion ---")
ev=cal.listar("2026-09-26T00:00:00-06:00","2026-09-26T23:59:59-06:00")
print(json.dumps(ev,ensure_ascii=False,indent=1))
json.dump({"r2":r2.get("respuesta"),"exec":r2.get("exec_id"),"cal":ev},
  open(r"G:\Barberia\archivos\_verif\c16b.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
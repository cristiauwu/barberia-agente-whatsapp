import sys,io,json,time
sys.path.insert(0,r"G:\Barberia\archivos\_verif")
from harness import enviar
if not getattr(sys.stdout,"_vutf8",False):
    sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace"); sys.stdout._vutf8=True
JID="5214501111805@s.whatsapp.net"
r=enviar(JID,"quiero ver mis citas",pushName="Doble Reserva")
print("EXEC",r.get("exec_id"),r.get("status"))
print("ENTRADA:",json.dumps(r.get("entrada"),ensure_ascii=False))
print("RESPUESTA:")
print(r.get("respuesta"))
json.dump(r,open(r"G:\Barberia\archivos\_verif\vermiscitas.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
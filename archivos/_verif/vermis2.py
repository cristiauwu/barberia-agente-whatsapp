import sys,io,json,time
sys.path.insert(0,r"G:\Barberia\archivos\_verif")
from harness import enviar
if not getattr(sys.stdout,"_vutf8",False):
    sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace"); sys.stdout._vutf8=True
JID="5214501111805@s.whatsapp.net"
out={}
r=enviar(JID,"quiero una ceja el lunes 5 de octubre a las 11 de la mañana",pushName="Doble Reserva")
print(">>> reserva2:",r.get("respuesta"),"| exec",r.get("exec_id"),r.get("status"))
out["reserva2"]={"resp":r.get("respuesta"),"exec":r.get("exec_id")}
time.sleep(15)
r2=enviar(JID,"ver mis citas",pushName="Doble Reserva")
print("\n>>> LISTADO:")
print(r2.get("respuesta"))
out["listado"]={"resp":r2.get("respuesta"),"exec":r2.get("exec_id")}
json.dump(out,open(r"G:\Barberia\archivos\_verif\vermis2.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
import sys,io,json,time
sys.path.insert(0,r"G:\Barberia\archivos\_verif")
from harness import enviar
if not getattr(sys.stdout,"_vutf8",False):
    sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace"); sys.stdout._vutf8=True
txt="Quiero informacion sobre sus servicios y precios disponibles. "*34+"gracias"
print("longitud enviada:",len(txt))
r=enviar("5214501111805@s.whatsapp.net",txt,pushName="Cliente Prueba")
print("exec",r.get("exec_id"),r.get("status"))
print("respuesta:",r.get("respuesta"))
json.dump({"len":len(txt),"resp":r.get("respuesta"),"exec":r.get("exec_id"),"status":r.get("status")},
  open(r"G:\Barberia\archivos\_verif\c12b.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
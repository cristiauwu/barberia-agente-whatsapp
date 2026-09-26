import sys,io,json,time
sys.path.insert(0,r"G:\Barberia\archivos\_verif")
from harness import enviar, psql
import cal
if not getattr(sys.stdout,"_vutf8",False):
    sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace"); sys.stdout._vutf8=True

JID="5214501111805@s.whatsapp.net"
res={}
def paso(tag,txt,**kw):
    print(f"\n>>> [{tag}] {txt[:110]!r}")
    r=enviar(JID,txt,**kw)
    print("<<< RESP:",r.get("respuesta"))
    print("<<< exec",r.get("exec_id"),r.get("status"))
    res[tag]={"enviado":txt,"resp":r.get("respuesta"),"exec":r.get("exec_id"),"status":r.get("status")}
    return r

paso("C16-prev","cuales son los servicios y precios", pushName="Doble Reserva")
time.sleep(13)
paso("C16-1","quiero un corte mañana a la 1 de la tarde", pushName="Doble Reserva")
time.sleep(15)

print("\n--- CALENDARIO 2026-09-26 ---")
ev=cal.listar("2026-09-26T00:00:00-06:00","2026-09-26T23:59:59-06:00")
print(json.dumps(ev,ensure_ascii=False,indent=1))
res["C16-cal"]=ev
json.dump(res,open(r"G:\Barberia\archivos\_verif\c16.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
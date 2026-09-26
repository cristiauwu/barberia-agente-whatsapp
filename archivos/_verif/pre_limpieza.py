import sys,io,json
sys.path.insert(0,r"G:\Barberia\archivos\_verif")
from harness import psql
import cal
if not getattr(sys.stdout,"_vutf8",False):
    sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace"); sys.stdout._utf8=False; sys.stdout._vutf8=True
print("=== esquema barber_clientes ===")
print(psql("\\d barber_clientes"))
print("=== auditoria reciente ===")
print(psql("SELECT * FROM barber_auditoria ORDER BY 1 DESC LIMIT 10;")[:2000])
print("=== eventos del calendario AHORA ===")
r=cal.listar()
for e in r.get("eventos",[]):
    print(" ",e["id"],"|",e["summary"],"|",e["start"])
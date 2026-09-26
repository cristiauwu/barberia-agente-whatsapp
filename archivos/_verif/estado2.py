import sys,io,json
sys.path.insert(0,r"G:\Barberia\archivos\_verif")
from harness import psql
if not getattr(sys.stdout,"_vutf8",False):
    sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace"); sys.stdout._vutf8=True
print(psql("\\d barber_citas"))
print("=== citas ===")
print(psql("SELECT * FROM barber_citas;"))
print("=== nombres en backup de memoria ===")
bk=json.load(open(r"G:\Barberia\archivos\_verif\bk_memoria_1805.json",encoding="utf-8"))
import re
nombres=set()
for r in bk:
    m=r["message"]
    c=m.get("content") if isinstance(m,dict) else None
    if c:
        for mm in re.finditer(r'Cliente:\s*([^\n(]+)',c): nombres.add(mm.group(1).strip())
print(nombres)
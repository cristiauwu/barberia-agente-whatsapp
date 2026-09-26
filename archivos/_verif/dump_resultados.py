import sys,io,json
if not getattr(sys.stdout,"_vutf8",False):
    sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace"); sys.stdout._vutf8=True
res=json.load(open(r"G:\Barberia\archivos\_verif\resultados.json",encoding="utf-8"))
for cid,r in res.items():
    print("@@@",cid,"| exec",r.get("exec_id"),"| status",r.get("status"))
    print("ENV:",repr(r.get("enviado")))
    print("RESP:")
    print(r.get("respuesta"))
    print()
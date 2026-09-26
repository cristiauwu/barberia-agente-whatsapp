import json,sys,io
if not getattr(sys.stdout,"_vutf8",False):
    sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace"); sys.stdout._vutf8=True
wf=json.load(open(r"G:\Barberia\archivos\_verif\wf_agente.json",encoding="utf-8"))
conns=wf["connections"]
print("=== Quien apunta a 'Mandar mensaje' ===")
for src,outs in conns.items():
    for oi,arr in enumerate(outs.get("main") or []):
        for c in (arr or []):
            if c["node"]=="Mandar mensaje":
                print(f"  {src} (salida {oi}) -> Mandar mensaje")
print()
print("=== Salidas de 'AI Agent' ===")
print(json.dumps(conns.get("AI Agent"),ensure_ascii=False,indent=1))
print("=== Salidas de 'IF - Respuesta no vacia' ===")
print(json.dumps(conns.get("IF - Respuesta no vacia"),ensure_ascii=False,indent=1))
print("=== Salidas de 'Respuesta sin texto' ===")
print(json.dumps(conns.get("Respuesta sin texto"),ensure_ascii=False,indent=1))
print("=== Salidas de 'Aviso solo texto' ===")
print(json.dumps(conns.get("Aviso solo texto"),ensure_ascii=False,indent=1))
print("=== onError de nodos clave ===")
for n in wf["nodes"]:
    if n.get("onError") or n.get("retryOnFail"):
        print(f"  {n['name']}: onError={n.get('onError')} retry={n.get('retryOnFail')} maxTries={n.get('maxTries')}")
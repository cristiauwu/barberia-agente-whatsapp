import json,sys,io
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace")
wf=json.load(open(r"G:\Barberia\archivos\_verif\wf_agente.json",encoding="utf-8"))
nodes={n["name"]:n for n in wf["nodes"]}
for n in ["Mandar mensaje","Responder al operador","Notificar al encargado","IF - Respuesta no vacia","Respuesta sin texto","Aviso solo texto","Consultar agenda","Agendar cita","Registrar en hoja de citas"]:
    nd=nodes[n]
    print("="*20,n,"="*20)
    print("onError:",nd.get("onError"),"retry:",nd.get("retryOnFail"),"alwaysOutput:",nd.get("alwaysOutputData"))
    print(json.dumps(nd.get("parameters",{}),ensure_ascii=False)[:1800])
    print()
import json, os, io
base=r"G:\Barberia\archivos\_audit"
wf=json.load(open(os.path.join(base,"barberiaAgenteUncensored.json"),encoding="utf-8"))
out=[]
def W(*a): s=" ".join(str(x) for x in a); out.append(s); print(s[:2000])
W("updatedAt:", wf.get("updatedAt"), "createdAt:", wf.get("createdAt"), "versionCounter:", wf.get("versionCounter"))
for n in wf["nodes"]:
    if n["name"] in ("Mandar mensaje","Responder al operador","Notificar al encargado","Registrar en hoja de citas","Consultar agenda","Agendar cita","Cancelar cita","Reagendar","Get Audio","Get Image","Crear bloqueo en calendario","Leer agenda del rango"):
        W("-", n["name"], "| node keys:", sorted(n.keys()))
        W("   retryOnFail:", n.get("retryOnFail"), "maxTries:", n.get("maxTries"), "waitBetweenTries:", n.get("waitBetweenTries"))
        W("   params keys:", sorted(n.get("parameters",{}).keys()))
open(os.path.join(base,"retry.txt"),"w",encoding="utf-8").write("\n".join(out))

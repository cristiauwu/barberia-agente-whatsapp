import json, os, io, re
base = r"G:\Barberia\archivos\_audit"
out = io.StringIO()
def W(*a): print(*a, file=out)
wf = json.load(open(os.path.join(base,"barberiaAgenteUncensored.json"),encoding="utf-8"))
nodes = {n["name"]: n for n in wf["nodes"]}
# Normalizacion full
W("NORMALIZACION full params:")
W(json.dumps(nodes["Normalizacion"]["parameters"], ensure_ascii=False, indent=1))
W("="*90)
W("Notificar al encargado FULL:")
W(json.dumps(nodes["Notificar al encargado"], ensure_ascii=False, indent=1))
W("="*90)
W("Registrar en hoja de citas FULL:")
W(json.dumps(nodes["Registrar en hoja de citas"], ensure_ascii=False, indent=1))
W("="*90)
W("Mandar mensaje FULL:"); W(json.dumps(nodes["Mandar mensaje"], ensure_ascii=False, indent=1))
W("="*90)
W("Webhook FULL:"); W(json.dumps(nodes["Webhook"], ensure_ascii=False, indent=1))
W("="*90)
W("Workflow-level: meta/tags/staticData/description:")
for k in ["description","meta","tags","staticData","triggerCount","versionId","activeVersionId","isArchived","nodeGroups","sourceWorkflowId"]:
    W(" ", k, "=", json.dumps(wf.get(k), ensure_ascii=False)[:500])
W("="*90)
wf2 = json.load(open(os.path.join(base,"barberiaRecordatorios.json"),encoding="utf-8"))
for k in ["description","meta","tags","staticData","triggerCount"]:
    W(" WF2", k, "=", json.dumps(wf2.get(k), ensure_ascii=False)[:500])
open(os.path.join(base,"details2.txt"),"w",encoding="utf-8").write(out.getvalue())
print("ok")

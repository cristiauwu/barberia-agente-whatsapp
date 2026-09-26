import sys, json
sys.path.insert(0, r"G:\Barberia\_aud_con")
from _db import q

cols, rows = q("SELECT id, categoria, origen, prioridad, activo, pregunta, "
               "respuesta, sinonimos FROM barber_conocimiento ORDER BY id")
data = [dict(zip(cols, r)) for r in rows]
with open(r"G:\Barberia\_aud_con\faqs.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=1)

print("total:", len(data))
for d in data:
    print("#%-3d [%s/%s] p=%d act=%s" % (d["id"], d["categoria"], d["origen"],
                                          d["prioridad"], d["activo"]))
    print("   P:", d["pregunta"])
    print("   R:", d["respuesta"])
    print("   S:", d["sinonimos"])
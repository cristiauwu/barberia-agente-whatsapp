import sys, re, json
sys.path.insert(0, r"G:\Barberia\_aud_con")
from _db import q

cols, rows = q("SELECT id, categoria, origen, prioridad, activo, pregunta, "
               "respuesta FROM barber_conocimiento ORDER BY id")
data = [dict(zip(cols, r)) for r in rows]

# tabla resumen de 58
tab = ["| id | categoría | origen | pregunta |",
       "|---|---|---|---|"]
for d in data:
    tab.append("| %d | %s | **%s** | %s |" % (
        d["id"], d["categoria"], d["origen"], d["pregunta"]))

# propuestas detalladas
prop = []
for d in data:
    if d["origen"] == "propuesta":
        prop.append("### #%d — %s\n\n**Respuesta actual:**\n> %s\n\n"
                    "**Pregunta para el dueño:** ¿esto es correcto?\n" %
                    (d["id"], d["pregunta"], d["respuesta"]))

open(r"G:\Barberia\_aud_con\tabla58.md", "w", encoding="utf-8").write(
    "\n".join(tab))
open(r"G:\Barberia\_aud_con\propuestas.md", "w", encoding="utf-8").write(
    "\n".join(prop))
print(len(data), "filas |", len(prop), "propuestas")
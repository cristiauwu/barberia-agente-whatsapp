import sys, json
sys.path.insert(0, r"G:\Barberia\_aud_con")
from _db import q

cols, rows = q("SELECT id, origen, categoria, prioridad, activo, "
               "pregunta, respuesta, sinonimos FROM barber_conocimiento ORDER BY id")
data = [dict(zip(cols, r)) for r in rows]

out = []
for d in data:
    out.append("#%-3d [%s/%s] p=%d act=%s" % (d["id"], d["categoria"],
               d["origen"], d["prioridad"], d["activo"]))
    out.append("  P: " + d["pregunta"])
    out.append("  R: " + d["respuesta"])
    out.append("  S: " + d["sinonimos"])
    out.append("")
open(r"G:\Barberia\_aud_con\faqs.txt", "w", encoding="utf-8").write("\n".join(out))

# duplicados por solapamiento de palabras de la pregunta
import unicodedata, re
def norm(s):
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return set(re.findall(r"[a-z]+", s))

pares = []
for i in range(len(data)):
    for j in range(i + 1, len(data)):
        a, b = norm(data[i]["pregunta"]), norm(data[j]["pregunta"])
        if not a or not b:
            continue
        jac = len(a & b) / len(a | b)
        if jac >= 0.5:
            pares.append((round(jac, 2), data[i]["id"], data[j]["id"],
                          data[i]["pregunta"], data[j]["pregunta"]))
o2 = ["== PREGUNTAS CON ALTO SOLAPAMIENTO (Jaccard >= 0.5) =="]
for p in sorted(pares, reverse=True):
    o2.append(str(p))
o2.append("")
o2.append("== SINONIMOS DUPLICADOS DENTRO DE LA MISMA FILA ==")
for d in data:
    ws = d["sinonimos"].split()
    dup = sorted({w for w in ws if ws.count(w) > 1})
    if dup:
        o2.append("#%d %s" % (d["id"], dup))
o2.append("")
o2.append("== SINONIMOS VACIOS ==")
for d in data:
    if not d["sinonimos"].strip():
        o2.append("#%d %s" % (d["id"], d["pregunta"]))
open(r"G:\Barberia\_aud_con\dups.txt", "w", encoding="utf-8").write("\n".join(o2))
print("escrito")
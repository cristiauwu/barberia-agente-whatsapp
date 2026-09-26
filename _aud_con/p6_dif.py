import sys, re, json, unicodedata
sys.path.insert(0, r"G:\Barberia\_aud_con")
from _db import q

def norm(s):
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()

cols, rows = q("SELECT id, origen, categoria, prioridad, activo, pregunta, "
               "respuesta, sinonimos FROM barber_conocimiento ORDER BY id")
data = [dict(zip(cols, r)) for r in rows]

bloque = open(r"G:\Barberia\_aud_con\bloque_prompt.txt", encoding="utf-8").read()
lineas = [l for l in bloque.split("\n") if l.strip().startswith("- **")]

# parse "- **PREGUNTA** RESPUESTA"
prompt_items = []
for l in lineas:
    m = re.match(r"^-\s+\*\*(.+?)\*\*\s*(.*)$", l.strip(), re.S)
    if m:
        prompt_items.append((m.group(1).strip(), m.group(2).strip()))
    else:
        prompt_items.append((l.strip(), ""))

print("DB filas: %d | prompt items: %d" % (len(data), len(prompt_items)))
print()

db_by_norm = {}
for d in data:
    db_by_norm.setdefault(norm(d["pregunta"]), []).append(d)

out = []
out.append("== A)¿QUE ESTA EN EL PROMPT Y NO EN LA BASE? ==")
solo_prompt = []
matched_db = set()
for i, (p, r) in enumerate(prompt_items, 1):
    np = norm(p)
    if np in db_by_norm:
        matched_db.add(np)
        continue
    # buscar por solapamiento
    best = None
    wp = set(np.split())
    for d in data:
        wd = set(norm(d["pregunta"]).split())
        if not wp or not wd:
            continue
        j = len(wp & wd) / len(wp | wd)
        if best is None or j > best[0]:
            best = (j, d)
    solo_prompt.append((i, p, r, best))
    out.append("[prompt #%d] %r" % (i, p))
    out.append("    respuesta prompt: %r" % r)
    if best and best[0] > 0.4:
        out.append("    parecida en BD #%d %r (jaccard %.2f)" % (best[1]["id"], best[1]["pregunta"], best[0]))
        if norm(best[1]["respuesta"]) != norm(r):
            out.append("    >>> RESPUESTA DISTINTA")
            out.append("        BD   : %r" % best[1]["respuesta"])
            out.append("        PROMPT: %r" % r)
    out.append("")

out.append("")
out.append("== B) ¿QUE ESTA EN LA BASE Y NO EN EL PROMPT? ==")
solo_db = [d for d in data if norm(d["pregunta"]) not in matched_db]
for d in solo_db:
    out.append("#%-3d [%s] %s" % (d["id"], d["origen"], d["pregunta"]))
    out.append("      R: %s" % d["respuesta"])
out.append("")

out.append("== C) COINCIDEN EN TEXTO PERO DIFIERE LA RESPUESTA ==")
for i, (p, r) in enumerate(prompt_items, 1):
    np = norm(p)
    if np in db_by_norm:
        d = db_by_norm[np][0]
        if norm(d["respuesta"]) != norm(r):
            out.append("#%d %s" % (d["id"], d["pregunta"]))
            out.append("   BD    : %r" % d["respuesta"])
            out.append("   PROMPT: %r" % r)
            out.append("")

out.append("== D) RESUMEN ==")
out.append("filas BD: %d" % len(data))
out.append("items prompt: %d" % len(prompt_items))
out.append("en prompt y en BD (texto igual): %d" % len(matched_db))
out.append("solo en el prompt: %d" % len(solo_prompt))
out.append("solo en la BD: %d" % len(solo_db))

txt = "\n".join(out)
open(r"G:\Barberia\_aud_con\dif_prompt.txt", "w", encoding="utf-8").write(txt)
print(txt)
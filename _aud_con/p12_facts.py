import sys, json, re, unicodedata
sys.path.insert(0, r"G:\Barberia\_aud_con")
from _db import q, buscar

out = []

def norm(s):
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s)

sm = open(r"G:\Barberia\_aud_con\prompt_vivo.txt", encoding="utf-8").read()
bloque = open(r"G:\Barberia\_aud_con\bloque_prompt.txt", encoding="utf-8").read()
sin_bloque = sm.replace(bloque, "")
nsm, nbloque = norm(sm), norm(bloque)

out.append("== ¿EL DATO SIGUE EN EL PROMPT FUERA DEL BLOQUE DE FAQs? ==")
DATOS = [
    ("direccion Calle Pinzón #574", r"pinz[oó]n\s*#?\s*574"),
    ("telefono 452-281-8144", r"452[\s-]?281[\s-]?8144"),
    ("horario 10:00 a 20:00", r"10:00.{0,12}20:00"),
    ("domingo cerrado", r"domingo"),
    ("precio corte $150", r"\$?150"),
    ("precio barba $100", r"\$?100"),
    ("precio ceja $30", r"\$?30"),
    ("precio dama $250", r"\$?250"),
    ("precio peinado $300", r"\$?300"),
    ("precio mascarilla $50", r"\$?50"),
    ("duracion 40 min corte", r"40\s*min"),
    ("depilacion", r"depilaci"),
    ("mascarilla", r"mascarilla"),
    ("planchado", r"planchado"),
]
for nombre, pat in DATOS:
    en_bloque = bool(re.search(pat, nbloque))
    fuera = bool(re.search(pat, norm(sin_bloque)))
    out.append("  %-32s bloque=%-5s FUERA-del-bloque=%-5s %s"
               % (nombre, en_bloque, fuera,
                  "OK" if fuera else ">>> NO ESTA EN EL PROMPT"))

out.append("")
out.append("== LITERAL: lineas del prompt que contradicen la BD ==")
for pid in [3, 5, 20, 30, 31, 34, 40, 48, 51, 213, 214, 215]:
    _, r = q("SELECT pregunta, respuesta FROM barber_conocimiento WHERE id=%s", (pid,))
    if not r:
        out.append("#%d NO ESTA EN LA BD (fila borrada)" % pid)
        continue
    preg = r[0][0]
    for l in bloque.split("\n"):
        if l.strip().startswith("- **") and norm(preg) in norm(l):
            out.append("#%d" % pid)
            out.append("  PROMPT: " + l.strip())
            break

out.append("")
out.append("== LA FAQ QUE EL DUENO MANDO BORRAR SIGUE EN EL PROMPT ==")
for l in bloque.split("\n"):
    if re.search(r"no llego|no[- ]?show|cobran", l, re.I):
        out.append("  " + l.strip())

out.append("")
out.append("== CONFIRMAR QUE LA FILA 41 FUE BORRADA ==")
out.append(str(q("SELECT id,pregunta FROM barber_conocimiento WHERE id=41")[1]))

txt = "\n".join(out)
open(r"G:\Barberia\_aud_con\prompt_facts.txt", "w", encoding="utf-8").write(txt)
print(txt)
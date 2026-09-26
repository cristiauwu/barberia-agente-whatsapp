import sys, re, unicodedata
sys.path.insert(0, r"G:\Barberia\_aud_con")

def norm(s):
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s)

# ¿El ARCHIVO del repo tiene la linea de no-show?
ruta = r"G:\Barberia\prompt-sistema-agente-barberia.txt"
txt = open(ruta, encoding="utf-8").read()
out = ["== ARCHIVO DEL REPO: prompt-sistema-agente-barberia.txt =="]
out.append("caracteres: %d" % len(txt))
for l in txt.split("\n"):
    if re.search(r"no[- ]?show|no llego|cobran si", l, re.I):
        out.append("  ENCONTRADA: " + l.strip()[:120])
out.append("  (si no hay lineas arriba, el archivo NO tiene esa FAQ)")

# workflow vivo
vivo = open(r"G:\Barberia\_aud_con\prompt_vivo.txt", encoding="utf-8").read()
out.append("")
out.append("== PROMPT VIVO (n8n) ==")
out.append("caracteres: %d" % len(vivo))
for l in vivo.split("\n"):
    if re.search(r"no[- ]?show|no llego|cobran si", l, re.I):
        out.append("  ENCONTRADA: " + l.strip()[:120])

# id 41 confirmado: contar entradas del seed
sql = open(r"G:\Barberia\archivos\conocimiento-barberia.sql", encoding="utf-8").read()
i = sql.find("VALUES")
bloque = sql[i:sql.find("ON CONFLICT")]
entradas = re.findall(r"^\('(.+?)',$", bloque, re.M)
out.append("")
out.append("== SEED del SQL: entradas en orden ==")
out.append("total entradas: %d" % len(entradas))
for n, e in enumerate(entradas, 1):
    if n in (40, 41, 42):
        out.append("  entrada #%d -> %s" % (n, e[:70]))

txt2 = "\n".join(out)
open(r"G:\Barberia\_aud_con\verif.txt", "w", encoding="utf-8").write(txt2)
print(txt2)
import sys, re, json
sys.path.insert(0, r"G:\Barberia\_aud_con")

sm = open(r"G:\Barberia\_aud_con\prompt_vivo.txt", encoding="utf-8").read()
out = []

out.append("== ¿DONDE APARECEN LOS PRECIOS Y DURACIONES EN EL PROMPT? ==")
for kw in ["150", "250", "300", "100", "50", "30", "mascarilla", "peinado",
           "planchado", "depilaci", "tarjeta", "transferencia", "efectivo",
           "wifi", "factura", "5 a 10", "15 minutos", "redes"]:
    hits = [m.start() for m in re.finditer(re.escape(kw), sm, re.I)]
    secciones = sorted({sm.rfind("\n# ", 0, h) for h in hits})
    titulos = []
    for s in secciones:
        linea = sm[s:s + 60].split("\n")[1] if s >= 0 else "?"
        titulos.append(linea.strip()[:50])
    out.append("  %-14s apariciones=%-3d secciones=%s" % (kw, len(hits), titulos[:6]))

out.append("")
out.append("== SECCIONES (titulos) DEL PROMPT ==")
for m in re.finditer(r"^# .*$", sm, re.M):
    out.append("  " + m.group(0)[:90])

out.append("")
out.append("== ¿EL PROMPT DICE 'NO INVENTES'? ==")
for m in re.finditer(r"[^\n]*(invent|no supongas|nunca inventes)[^\n]*", sm, re.I):
    out.append("  " + m.group(0).strip()[:160])

txt = "\n".join(out)
open(r"G:\Barberia\_aud_con\prompt_sec.txt", "w", encoding="utf-8").write(txt)
print(txt)
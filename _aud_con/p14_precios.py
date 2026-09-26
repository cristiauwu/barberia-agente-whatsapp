import sys, re
sys.path.insert(0, r"G:\Barberia\_aud_con")
from _db import q, buscar

cats = q("SELECT clave, nombre, precio, duracion_min FROM barber_servicios ORDER BY clave")[1]
cat = {r[0]: (r[1], str(int(r[2])), r[3]) for r in cats}

out = []
out.append("== CATALOGO REAL barber_servicios ==")
for k, v in sorted(cat.items()):
    out.append("  %-12s %-28s $%-5s %s min" % (k, v[0], v[1], v[2]))

FORMULAS = [
    "cuanto cuesta el {}", "cuanto cuesta la {}", "cuanto vale el {}",
    "precio del {}", "precio de la {}", "cuanto sale el {}",
    "q precio tiene el {}", "cuanto es el {}", "cuanto me cobran por el {}",
]
TERMINOS = {
    "corte": "corte", "barba": "barba", "ceja": "ceja",
    "mascarilla": "mascarilla", "dama": "corte de dama",
    "planchado": "planchado", "peinado": "peinado",
    "depilacion": "depilacion",
}

out.append("")
out.append("== PRECIO: ¿la respuesta de la FAQ TOP trae el precio del catalogo? ==")
mal = []
for clave in sorted(TERMINOS):
    termino = TERMINOS[clave]
    precio_real = cat[clave][1]
    for f in FORMULAS:
        texto = f.format(termino)
        filas, err = buscar(texto, 3)
        if not filas:
            out.append("  VACIO %-42r -> SIN RESULTADO" % texto)
            continue
        top = filas[0]
        _, rr = q("SELECT respuesta FROM barber_conocimiento WHERE id=%s",
                  (top["id"],))
        resp = rr[0][0]
        cifras = re.findall(r"\$?(\d{2,4})", resp)
        correcto = precio_real in cifras
        if not correcto:
            mal.append((texto, clave, precio_real, top["pregunta"], resp))
        out.append("  %s %-42r -> %-46s cifras=%s real=$%s"
                   % ("OK  " if correcto else "MAL ", texto,
                      top["pregunta"][:44], cifras, precio_real))

out.append("")
out.append("== FALLOS DE PRECIO ==")
for m in mal:
    out.append("  q=%r" % m[0])
    out.append("     servicio=%s  precio_real=$%s" % (m[1], m[2]))
    out.append("     FAQ devuelta: %s" % m[3])
    out.append("     respuesta   : %r" % m[4])
out.append("  TOTAL fallos: %d de %d" % (len(mal), len(FORMULAS) * len(TERMINOS)))

out.append("")
out.append("== ¿HAY FAQ DE PRECIO DEDICADA POR SERVICIO? ==")
for clave in sorted(TERMINOS):
    clave_busq = {"dama": "dama", "depilacion": "depilaci"}.get(clave, clave)
    _, r = q("SELECT id, pregunta FROM barber_conocimiento "
             "WHERE pregunta ILIKE '%%cuesta%%' AND pregunta ILIKE %s",
             ("%" + clave_busq + "%",))
    out.append("  %-12s -> %s" % (clave, r[0][1] if r else "NINGUNA FAQ DE PRECIO"))

txt = "\n".join(out)
open(r"G:\Barberia\_aud_con\precios.txt", "w", encoding="utf-8").write(txt)
print("fallos:", len(mal))
print(txt)
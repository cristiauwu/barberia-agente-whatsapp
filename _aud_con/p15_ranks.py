import sys
sys.path.insert(0, r"G:\Barberia\_aud_con")
from _db import q, buscar

out = []
for t in ["cuanto cuesta el peinado", "cuanto cuesta la mascarilla",
          "cuanto cuesta el planchado", "cuanto cuesta el corte",
          "cuanto cuesta el peinado express", "precio peinado"]:
    filas, err = buscar(t, 5)
    out.append("q=%r" % t)
    for i, f in enumerate(filas, 1):
        _, r = q("SELECT left(respuesta,70), prioridad FROM barber_conocimiento WHERE id=%s",
                 (f["id"],))
        out.append("   %d. #%-4s rank=%.4f prio=%s %-46s" % (
            i, f["id"], f["rank"], r[0][1], f["pregunta"][:46]))
        out.append("        %r" % r[0][0])
    if not filas:
        out.append("   SIN RESULTADO")
    out.append("")

print("\n".join(out))
open(r"G:\Barberia\_aud_con\ranks.txt", "w", encoding="utf-8").write("\n".join(out))
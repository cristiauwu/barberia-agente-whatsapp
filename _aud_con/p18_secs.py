import sys, re
sys.path.insert(0, r"G:\Barberia\_aud_con")

sm = open(r"G:\Barberia\_aud_con\prompt_vivo.txt", encoding="utf-8").read()

def seccion(titulo):
    i = sm.find("# " + titulo)
    if i < 0:
        return "(no encontrada)"
    k = sm.find("\n# ", i + 5)
    return sm[i:k if k > 0 else len(sm)]

out = []
for t in ["CATÁLOGO DE SERVICIOS", "REGLAS DE PRECIOS Y DURACIÓN",
          "DATOS DEL NEGOCIO", "HORARIO DE ATENCIÓN",
          "PROCESO D — CONSULTAS, PRECIOS Y FUERA DE ALCANCE",
          "LÍMITES Y PROTECCIONES"]:
    out.append("=" * 72)
    out.append(seccion(t))
    out.append("")

txt = "\n".join(out)
open(r"G:\Barberia\_aud_con\prompt_secciones.txt", "w", encoding="utf-8").write(txt)
print(txt)
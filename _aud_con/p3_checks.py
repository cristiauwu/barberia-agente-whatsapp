import sys, json
sys.path.insert(0, r"G:\Barberia\_aud_con")
from _db import q

cols, rows = q("SELECT id, origen, categoria, prioridad, activo, "
               "pregunta, respuesta, sinonimos, creado_en, actualizado_en "
               "FROM barber_conocimiento ORDER BY id")
data = [dict(zip(cols, r)) for r in rows]

print("== HUECOS DE ID ==")
ids = [d["id"] for d in data]
print("ids:", ids)
faltan = [i for i in range(min(ids), max(ids) + 1) if i not in ids]
print("faltan:", faltan)

print("\n== BUSCAR 'no llego' / 'no show' ==")
print(q("SELECT id,pregunta FROM barber_conocimiento WHERE "
        "pregunta ILIKE '%llego%' OR pregunta ILIKE '%no show%' "
        "OR sinonimos ILIKE '%no show%'")[1])

print("\n== PROPUESTAS ==")
for d in data:
    if d["origen"] == "propuesta":
        print("#%d %s" % (d["id"], d["pregunta"]))

print("\n== FECHAS DE CREACION (agrupado) ==")
for r in q("SELECT date_trunc('minute',creado_en) c, count(*), "
           "min(id), max(id) FROM barber_conocimiento GROUP BY 1 ORDER BY 1")[1]:
    print(r)

print("\n== ACTUALIZACIONES DISTINTAS ==")
for r in q("SELECT date_trunc('minute',actualizado_en) a, count(*), min(id), max(id) "
           "FROM barber_conocimiento GROUP BY 1 ORDER BY 1")[1]:
    print(r)

print("\n== DUPLICADOS EXACTOS DE RESPUESTA ==")
for r in q("SELECT md5(respuesta) h, count(*), string_agg(id::text,','), "
           "left(min(respuesta),70) FROM barber_conocimiento "
           "GROUP BY 1 HAVING count(*)>1 ORDER BY 2 DESC")[1]:
    print(r)

print("\n== PREGUNTAS MUY PARECIDAS ==")
for r in q("""
  SELECT a.id, b.id, a.pregunta, b.pregunta,
         round(similarity(a.pregunta,b.pregunta)::numeric,3) s
  FROM barber_conocimiento a JOIN barber_conocimiento b ON a.id<b.id
  WHERE similarity(a.pregunta,b.pregunta) > 0.35
  ORDER BY s DESC""")[1]:
    print(r)

print("\n== SINONIMOS VACIOS ==")
print(q("SELECT id,pregunta FROM barber_conocimiento "
        "WHERE trim(sinonimos)='' ")[1])

print("\n== SINONIMOS DUPLICADOS DENTRO DE LA MISMA FILA ==")
for r in q("""SELECT id, sinonimos FROM barber_conocimiento""")[1]:
    ws = r[1].split()
    dup = sorted({w for w in ws if ws.count(w) > 1})
    if dup:
        print(r[0], dup)

print("\n== PREGUNTA != RESPUESTA NUMEROS ==")
import re
for d in data:
    nums_par = re.findall(r"\$?\s?(\d{2,4})", d["respuesta"])
    print("#%-3d %s" % (d["id"], d["respuesta"][:95].encode("ascii","replace").decode()))
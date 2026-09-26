import re
sql = open(r"G:\Barberia\archivos\conocimiento-barberia.sql", encoding="utf-8").read()
i = sql.find("VALUES")
j = sql.find("ON CONFLICT", i)
bloque = sql[i:j]
# cada entrada empieza con ('¿  o  (' y termina con la linea que acaba en ,
entradas = re.findall(r"^\('(.*?)',$", bloque, re.M)
print("entradas con ^('...',$ :", len(entradas))
# alternativa: contar las lineas que empiezan con "(" y contienen comilla tras 1 char
ini = [l for l in bloque.split("\n") if re.match(r"^\('", l)]
print("lineas que empiezan con (' :", len(ini))
print("total lineas del bloque:", len(bloque.split(chr(10))))
print("--- primeras 3 ---")
for l in ini[:3]:
    print(repr(l[:80]))
print("--- ultimas 3 ---")
for l in ini[-3:]:
    print(repr(l[:80]))
# ¿aparece la pregunta del no-show en el seed?
print("--- ¿'no llego' en el seed? ---")
for l in bloque.split("\n"):
    if "no llego" in l.lower() or "no-show" in l.lower():
        print(repr(l[:100]))
print("(vacio = no esta en el seed)")
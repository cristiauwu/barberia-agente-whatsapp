# -*- coding: utf-8 -*-
"""Extrae la logica de control de acceso (Comprobar operador) y trozos del prompt."""
import json, io, sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

doc = json.load(io.open(r"G:\Barberia\BarberiaAgenteFLUJO-1-UNCENSORED.json", encoding="utf-8"))
out = []
def w(*a):
    s = " ".join(str(x) for x in a); out.append(s); print(s)

for n in doc["nodes"]:
    nm = n.get("name", "")
    if nm in ("Comprobar operador", "Leer operadores", "¿Es operador?",
              "IF - No es del bot", "Leer pausa", "Calcular pausa",
              "IF - Cliente pausado", "Router de comandos", "Normalizacion"):
        w("\n" + "=" * 90)
        w("### NODO: %s   (%s)" % (nm, n.get("type")))
        w("=" * 90)
        p = n.get("parameters") or {}
        for k, v in p.items():
            if k in ("jsCode", "code"):
                w("-- %s --\n%s" % (k, v))
            else:
                w("-- %s -- %s" % (k, json.dumps(v, ensure_ascii=False)[:1500]))

# condiciones del IF
for n in doc["nodes"]:
    if n.get("name") in ("Comprobar operador", "¿Es operador?", "IF - No es del bot", "IF - Cliente pausado"):
        w("\n### condiciones de %s: %s" % (n["name"], json.dumps(n.get("parameters", {}).get("conditions"), ensure_ascii=False)[:2000]))

io.open(r"G:\Barberia\_audit\_sec_router.txt", "w", encoding="utf-8").write("\n".join(out))
print("\n[escrito]")
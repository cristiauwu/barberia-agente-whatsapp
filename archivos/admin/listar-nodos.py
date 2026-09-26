import json, sys
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
d=json.load(open(r"G:\Barberia\archivos\admin\INVENTARIO.json",encoding="utf-8"))
CORTO={"n8n-nodes-base.":"","@n8n/n8n-nodes-langchain.":"LC."}
def c(t):
    for k,v in CORTO.items():
        if t.startswith(k): return v+t[len(k):]
    return t
for w in d["workflows"]:
    print("="*74)
    print(f"{w['nombre']}  ({w['n_nodos']} nodos)")
    print("="*74)
    for n in w["nodos"]:
        cr=", ".join(n["credenciales"]) if n["credenciales"] else ""
        print(f"  {n['nombre'][:42]:<42} {c(n['tipo']):<34}{cr[:26]}")
    print()
    print("  --- CONEXIONES ---")
    for x in w["conexiones"]:
        et = "" if x["tipo"]=="main" else f" [{x['tipo']}]"
        s = f" (salida {x['salida']})" if x["salida"] else ""
        print(f"  {x['de'][:36]:<36} -> {x['a'][:36]:<36}{et}{s}")
    print()
import json, os, re

OUT = r"G:\Barberia\_audit"
res = []
def w(*a):
    res.append(" ".join(str(x) for x in a))

# Router de comandos full outputs
wf = json.load(open(os.path.join(OUT, "wf_Barberia_-_Agente_de_citas_(Uncensored_AI).json"), encoding="utf-8"))
for n in wf["nodes"]:
    if n["name"] == "Router de comandos":
        w("### ROUTER DE COMANDOS ###")
        w(json.dumps(n["parameters"], ensure_ascii=False, indent=1))
        w()

# where is barber_clientes referenced?
for fn in os.listdir(OUT):
    if not fn.startswith("wf_"): continue
    raw = open(os.path.join(OUT, fn), encoding="utf-8").read()
    w("#"*70)
    w("FILE", fn)
    for m in re.finditer(r"barber_clientes", raw):
        w("   ...", raw[max(0, m.start()-260):m.start()+260].replace("\\n", " ").replace("\n"," "))
    w("INSERT INTO barber_clientes occurrences:", len(re.findall(r"INSERT\s+INTO\s+barber_clientes", raw, re.I)))
    w("INSERT INTO any table:", re.findall(r"INSERT\s+INTO\s+(\w+)", raw, re.I))
    w("UPDATE any table:", re.findall(r"UPDATE\s+(\w+)", raw, re.I))
    w("barber_citas occurrences:", len(re.findall(r"barber_citas", raw)))
    w("barber_ tables referenced:", sorted(set(re.findall(r"barber_[a-z_]+", raw))))

open(r"G:\Barberia\_audit\_router_clientes.txt","w",encoding="utf-8").write("\n".join(res))
print("ok")
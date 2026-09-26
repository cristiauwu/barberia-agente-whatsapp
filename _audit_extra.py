import json, os, re, glob
OUT = r"G:\Barberia\_audit"
buf=[]
def w(*a): buf.append(" ".join(str(x) for x in a))

def allnodes():
    for fn in glob.glob(os.path.join(OUT, "wf_*.json")):
        wf = json.load(open(fn, encoding="utf-8"))
        for n in wf["nodes"]:
            yield wf["name"], n

w("### RETRY / ERROR HANDLING")
for wfn, n in allnodes():
    rf = n.get("retryOnFail"); cw = n.get("continueOnFail"); ooe = n.get("onError")
    if rf or cw or ooe:
        w(f"  [{wfn}] {n['name']}: retryOnFail={rf} continueOnFail={cw} onError={ooe}")
w("  (si no aparece nada, ningún nodo tiene retry/onError configurado)")

w("\n### NODOS CON onError / retry (parametros)")
for wfn, n in allnodes():
    s = json.dumps(n, ensure_ascii=False)
    for pat in ["retryOnFail", "onError", "continueOnFail"]:
        if pat in s:
            w(f"  [{wfn}] {n['name']}: {pat} presente")

w("\n### NOMBRES BARBERO / ESTEBAN / GALERIA / IMAGEN")
pats = ["Esteban", "Aguilera", "galer", "imageUrl", "imagen", "Imagen", "barbero", "barber", "Juan", "Carlos", "Miguel"]
for pat in pats:
    hits = []
    for fn in glob.glob(os.path.join(OUT, "wf_*.json")):
        raw = open(fn, encoding="utf-8").read()
        c = len(re.findall(re.escape(pat), raw, re.I))
        if c: hits.append(f"{os.path.basename(fn)}={c}")
    w(f"  {pat}: {hits}")

# credentials / provider hints
w("\n### CREDENCIALES REFERENCIADAS (solo metadatos)")
for fn in glob.glob(os.path.join(OUT, "wf_*.json")):
    wf = json.load(open(fn, encoding="utf-8"))
    creds = {}
    for n in wf["nodes"]:
        for k, v in (n.get("credentials") or {}).items():
            creds.setdefault(k, set()).add(str(v.get("name")))
    w(f"  {wf['name']}: { {k: sorted(v) for k, v in creds.items()} }")

open(os.path.join(OUT,"_extra.txt"),"w",encoding="utf-8").write("\n".join(buf))
print("WROTE")
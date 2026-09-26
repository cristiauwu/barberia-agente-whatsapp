import json,sys,io,re
if not getattr(sys.stdout,"_vutf8",False):
    sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace"); sys.stdout._vutf8=True
res=json.load(open(r"G:\Barberia\archivos\_verif\resultados.json",encoding="utf-8"))
print(f"{'ID':6} {'LINES':>5} {'CHARS':>5} {'dbl**':>6} {'trailWS':>8} {'indent':>7} {'emoji>1':>8}")
for cid,r in res.items():
    t=r.get("respuesta") or ""
    lineas=t.split("\n")
    dbl=t.count("**")
    trail=[i for i,l in enumerate(lineas) if l!=l.rstrip()]
    # trailing space or tab
    indent=[i for i,l in enumerate(lineas) if l!=l.lstrip() and l.strip()]
    emojis=re.findall(r'[\U0001F300-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F]',t)
    print(f"{cid:6} {len(lineas):5} {len(t):5} {dbl:6} {len(trail):8} {len(indent):7} {len(emojis):8}")
print()
print("=== DETALLE de lineas con espacios finales / doble asterisco / sangria ===")
for cid,r in res.items():
    t=r.get("respuesta") or ""
    for i,l in enumerate(t.split("\n")):
        flags=[]
        if l!=l.rstrip(): flags.append("TRAILWS")
        if "**" in l: flags.append("DBL**")
        if l!=l.lstrip() and l.strip(): flags.append("INDENT")
        if flags: print(f"  [{cid}] linea {i}: {flags} -> {l!r}")
print()
print("=== Respuestas >10 lineas ===")
for cid,r in res.items():
    t=r.get("respuesta") or ""
    n=len(t.split("\n"))
    if n>10: print(f"  {cid}: {n} lineas")
print()
print("=== Respuestas que contienen terminos prohibidos ===")
for cid,r in res.items():
    t=(r.get("respuesta") or "").lower()
    for term in ["no-show","no show","factura","factur","escuché tu audio","escuché el audio","vi tu foto","error","detalle técnico","sistema"]:
        if term in t: print(f"  [{cid}] contiene {term!r}")
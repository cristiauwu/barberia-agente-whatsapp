import os, re
root = r"G:\Barberia"
pats = ["Esteban", "Aguilera", "Paco", "Chino", "Barber Chinos", "Barbería Pinzón", "Pinzón"]
buf=[]
for dirpath, dirs, files in os.walk(root):
    dirs[:] = [d for d in dirs if d not in (".docker","node_modules",".git")]
    for fn in files:
        if not fn.lower().endswith((".md",".txt",".json",".py",".js",".csv",".yml",".env",".sql")): continue
        p = os.path.join(dirpath, fn)
        try: raw = open(p, encoding="utf-8", errors="replace").read()
        except Exception: continue
        h = {k: len(re.findall(re.escape(k), raw, re.I)) for k in pats}
        h = {k:v for k,v in h.items() if v}
        if h: buf.append(f"{p}: {h}")
open(r"G:\Barberia\_audit\_names.txt","w",encoding="utf-8").write("\n".join(buf))
print("WROTE")
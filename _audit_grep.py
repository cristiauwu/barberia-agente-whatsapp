import os, re, json
root = r"G:\Barberia"
pats = ["scheduleTrigger", "interactive", "revenue", "totalRevenue", "avgTicket", "TXN-", "APT-",
        "Metricas_Diarias", "Transacciones", "INSERT INTO barber_clientes", "listMessage", "buttons"]
buf=[]
for dirpath, dirs, files in os.walk(root):
    dirs[:] = [d for d in dirs if d not in (".docker","node_modules",".git","_audit")]
    for fn in files:
        p = os.path.join(dirpath, fn)
        if fn.startswith("_"): continue
        if not fn.lower().endswith((".md",".txt",".json",".py",".js",".csv",".yml",".env")): continue
        try:
            raw = open(p, encoding="utf-8", errors="replace").read()
        except Exception: continue
        hits = {k: len(re.findall(re.escape(k), raw, re.I)) for k in pats}
        hits = {k:v for k,v in hits.items() if v}
        if hits:
            buf.append(f"{p}\n    {hits}")
open(r"G:\Barberia\_audit\_grep_all.txt","w",encoding="utf-8").write("\n".join(buf))
print("WROTE")
import json, os, re

OUT = r"G:\Barberia\_audit"
res = []
def w(*a):
    res.append(" ".join(str(x) for x in a))

for fn in os.listdir(OUT):
    if not fn.startswith("wf_"): continue
    wf = json.load(open(os.path.join(OUT, fn), encoding="utf-8"))
    w("="*90)
    w("WORKFLOW:", wf.get("name"), "| nodes:", len(wf.get("nodes", [])))
    w("="*90)
    for n in wf["nodes"]:
        t = n["type"]
        w(f"[{n['name']}]  type={t}  disabled={n.get('disabled')}")
    w("")

# Now dump full text of all node parameters, searching for key patterns
PATTERNS = {
 "ASTERISK_2": r"\*\*",
 "BOX_HEAVY": "━",
 "BOX_DOUBLE": "╔",
 "BOX_LIGHT": "┏",
 "SEPARATOR_DASH": "───",
 "clientes_table": "barber_clientes",
 "scheduleTrigger": "scheduleTrigger",
 "cron": "cron",
 "ingreso": "(?i)ingreso",
 "revenue": "(?i)revenue",
 "metric": "(?i)m[eé]tric",
}

for fn in os.listdir(OUT):
    if not fn.startswith("wf_"): continue
    raw = open(os.path.join(OUT, fn), encoding="utf-8").read()
    w("#"*90)
    w("PATTERN SCAN:", fn)
    for k, p in PATTERNS.items():
        hits = re.findall(p, raw)
        w(f"  {k}: {len(hits)}")

open(r"G:\Barberia\_audit\_nodes.txt", "w", encoding="utf-8").write("\n".join(res))
print("done")
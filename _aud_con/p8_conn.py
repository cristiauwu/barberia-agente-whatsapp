import json
wf = json.load(open(r"G:\Barberia\_aud_con\wf_agente.json", encoding="utf-8"))
print("== CONEXIONES POR NODO (todas las salidas y tipos) ==")
for src, c in wf["connections"].items():
    for ctype, outs in c.items():
        for out in outs or []:
            for link in out or []:
                if link.get("node") == "AI Agent" or ctype != "main":
                    print("%-32s --%s--> %s" % (src, ctype, link["node"]))

print()
print("== TODAS las conexiones ai_* ==")
for src, c in wf["connections"].items():
    for ctype in c:
        if ctype.startswith("ai_"):
            print(" ", src, ctype, "->", [l["node"] for o in c[ctype] for l in (o or [])])

print()
print("== nodos que mencionan postgres/conocimiento ==")
for n in wf["nodes"]:
    blob = json.dumps(n, ensure_ascii=False)
    if "conocimiento" in blob.lower():
        print(n["name"], n["type"])
        print(blob[:800])
        print()
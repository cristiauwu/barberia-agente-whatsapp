import json, re
wf = json.load(open(r"G:\Barberia\_aud_con\wf_agente.json", encoding="utf-8"))

print("== NODOS ==")
for n in wf["nodes"]:
    print("%-38s %-46s v%s" % (n["name"], n["type"], n.get("typeVersion")))

print("\n== CONEXIONES DESDE AI Agent ==")
print(json.dumps(wf["connections"].get("AI Agent"), ensure_ascii=False, indent=1))

print("\n== NODOS QUE USAN EL TOOL ai_tool ==")
ai = []
for src, c in wf["connections"].items():
    for out in c.get("main", []):
        for link in out or []:
            if link.get("type") == "ai_tool":
                ai.append((src, link["node"]))
print(ai)

print("\n== TODOS LOS NODOS CON typeVersion / tool ==")
for n in wf["nodes"]:
    if n["type"].startswith("@n8n/n8n-nodes-langchain"):
        print(n["name"], "|", n["type"], "|", json.dumps(n.get("parameters", {}), ensure_ascii=False)[:600])
        print()
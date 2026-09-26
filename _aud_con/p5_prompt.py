import sys, json, os, urllib.request, urllib.error
sys.path.insert(0, r"G:\Barberia\_aud_con")

KEY = open(r"G:\Barberia\archivos\.n8n-key.txt", encoding="utf-8").read().strip()
BASE = "http://localhost:5678/api/v1"
WID = "barberiaAgenteUncensored"

def api(p):
    r = urllib.request.Request(BASE + p)
    r.add_header("X-N8N-API-KEY", KEY)
    with urllib.request.urlopen(r, timeout=90) as resp:
        return json.loads(resp.read().decode())

wf = api("/workflows/" + WID)
json.dump(wf, open(r"G:\Barberia\_aud_con\wf_agente.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

print("workflow:", wf.get("name"), "active:", wf.get("active"),
      "updatedAt:", wf.get("updatedAt"))
print("nodos:", len(wf["nodes"]))

for n in wf["nodes"]:
    if n["type"].endswith("agent") or "Agent" in n.get("name", ""):
        print("NODO:", n["name"], n["type"], "v", n.get("typeVersion"))

ag = next(x for x in wf["nodes"] if x["name"] == "AI Agent")
sm = ag["parameters"]["options"]["systemMessage"]
if sm.startswith("="):
    sm = sm[1:]
open(r"G:\Barberia\_aud_con\prompt_vivo.txt", "w", encoding="utf-8").write(sm)
print("systemMessage chars:", len(sm))

i = sm.find("PREGUNTAS FRECUENTES")
print("indice 'PREGUNTAS FRECUENTES':", i)
j = sm.rfind("\n# ", 0, i)
print("inicio bloque (rfind '\\n# '):", j)
k = sm.find("\n# ", i + 10)
print("fin bloque:", k)
bloque = sm[j + 1:k] if j >= 0 else sm[i:k]
open(r"G:\Barberia\_aud_con\bloque_prompt.txt", "w", encoding="utf-8").write(bloque)
print("bloque chars:", len(bloque))
lineas = [l for l in bloque.split("\n") if l.strip().startswith("- **")]
print("lineas '- **':", len(lineas))
lineas2 = [l for l in bloque.split("\n") if l.strip().startswith("-")]
print("lineas '-':", len(lineas2))
print("--- primeras 15 lineas del bloque ---")
for l in bloque.split("\n")[:18]:
    print(repr(l[:150]))
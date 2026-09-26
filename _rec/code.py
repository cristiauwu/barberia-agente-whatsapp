import json, sys
sys.stdout.reconfigure(encoding="utf-8")
wf = json.load(open(r"G:\Barberia\_rec\wf.json", encoding="utf-8"))
for n in wf["nodes"]:
    if n["name"] in ("Code", "Code1"):
        print("#"*20, n["name"])
        print(n["parameters"].get("jsCode"))
        print()
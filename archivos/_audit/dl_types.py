import json, urllib.request, os
base = r"G:\Barberia\archivos\_audit"
try:
    with urllib.request.urlopen("http://localhost:5678/types/nodes.json", timeout=120) as x:
        data = x.read().decode("utf-8")
    open(os.path.join(base,"nodes.json"),"w",encoding="utf-8").write(data)
    print("nodes.json bytes:", len(data))
except Exception as e:
    print("ERR", type(e).__name__, e)

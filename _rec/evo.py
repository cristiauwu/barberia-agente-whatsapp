import json, urllib.request, sys
sys.stdout.reconfigure(encoding="utf-8")
KEY = None
for line in open(r"G:\Barberia\.env.evolution", encoding="utf-8", errors="replace"):
    if line.strip().startswith("AUTHENTICATION_API_KEY"):
        KEY = line.split("=", 1)[1].strip()
        break
print("keylen:", len(KEY) if KEY else None)
for path in ("/instance/connectionState/hector", "/instance/fetchInstances"):
    for base in ("http://localhost:8080",):
        try:
            r = urllib.request.Request(base + path)
            r.add_header("apikey", KEY)
            with urllib.request.urlopen(r, timeout=30) as resp:
                print(path, "->", resp.status, resp.read().decode()[:500])
        except Exception as e:
            print(path, "ERROR:", str(e)[:300])
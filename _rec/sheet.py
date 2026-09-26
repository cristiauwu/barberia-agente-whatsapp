import json, urllib.request, sys
sys.stdout.reconfigure(encoding="utf-8")
GID = "941506024"
SHEET = "1lvSVFWU2ApvK7p5BsFHI68Icur46P6hI8o8r9ozhBfk"
url = f"https://docs.google.com/spreadsheets/d/{SHEET}/gviz/tq?tqx=out:csv&gid={GID}"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
raw = urllib.request.urlopen(req, timeout=60).read().decode("utf-8")
print("=== LIVE SHEET (gviz csv) ===")
print(raw)
open(r"G:\Barberia\_rec\sheet_live.csv", "w", encoding="utf-8").write(raw)
print("bytes:", len(raw))
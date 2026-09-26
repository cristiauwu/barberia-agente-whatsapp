import json,sys
sys.stdout.reconfigure(encoding="utf-8")
d=json.load(open(r"G:\Barberia\_rec\ex1195.json",encoding="utf-8"))
print(list(d.keys()))
print(json.dumps({k:(type(v).__name__) for k,v in d.items()},indent=1))
print(json.dumps(d,indent=1,ensure_ascii=False)[:3000])

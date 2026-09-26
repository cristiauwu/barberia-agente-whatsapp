import json, os, re, glob
OUT = r"G:\Barberia\_audit"
buf=[]
def w(*a): buf.append(" ".join(str(x) for x in a))
for fn in glob.glob(os.path.join(OUT,"wf_*.json")):
    wf = json.load(open(fn,encoding="utf-8"))
    w("="*80); w(wf.get("name")); w("="*80)
    for n in wf["nodes"]:
        s = json.dumps(n["parameters"], ensure_ascii=False)
        if n["type"]=="n8n-nodes-base.postgres":
            q = n["parameters"].get("query","")
            verbo = re.match(r"\s*(\w+)", q)
            w(f"[{n['name']}] VERBO={verbo.group(1).upper() if verbo else '?'}")
            w("   " + q.replace("\n"," ")[:600])
        if n["type"] in ("n8n-nodes-base.googleSheets","n8n-nodes-base.googleSheetsTool"):
            w(f"[{n['name']}] operation={n['parameters'].get('operation')} sheet={n['parameters'].get('sheetName')} doc={n['parameters'].get('documentId')}")
        if n["type"]=="n8n-nodes-base.googleSheetsTrigger":
            w(f"[{n['name']}] event={n['parameters'].get('event')} pollTimes={n['parameters'].get('pollTimes')} sheet={n['parameters'].get('sheetName')}")
        if "schedule" in n["type"].lower() or n["type"].endswith("scheduleTrigger"):
            w(f"[{n['name']}] TIPO SCHEDULE {n['type']}")
open(os.path.join(OUT,"_sql.txt"),"w",encoding="utf-8").write("\n".join(buf))
print("WROTE")
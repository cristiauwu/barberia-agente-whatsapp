import json, os, io, sys
base = r"G:\Barberia\archivos\_audit"
out = io.StringIO()
def W(*a): print(*a, file=out)
for name in ["barberiaAgenteUncensored","barberiaRecordatorios"]:
    wf = json.load(open(os.path.join(base,name+".json"),encoding="utf-8"))
    W("="*100)
    W("WORKFLOW:", wf["name"], "| id:", wf["id"], "| active:", wf.get("active"))
    W("settings:", json.dumps(wf.get("settings",{}),ensure_ascii=False))
    W("nodes:", len(wf["nodes"]))
    for i,n in enumerate(wf["nodes"]):
        W("-"*90)
        W(f"[{i}] name={n.get('name')!r} type={n.get('type')} v={n.get('typeVersion')} pos={n.get('position')} disabled={n.get('disabled')}")
        for k in ["onError","retryOnFail","maxTries","waitBetweenTries","alwaysOutputData","executeOnce","notesInFlow","notes","continueOnFail"]:
            if k in n: W("     ", k, "=", n[k])
        W("     credentials:", json.dumps(n["credentials"],ensure_ascii=False) if n.get("credentials") else "NONE")
        p = n.get("parameters",{})
        s = json.dumps(p, ensure_ascii=False)
        if len(s) > 6000: s = s[:6000] + " ...[TRUNCATED total=%d]" % len(s)
        W("     params:", s)
open(os.path.join(base,"dump.txt"),"w",encoding="utf-8").write(out.getvalue())
print("written", len(out.getvalue()))

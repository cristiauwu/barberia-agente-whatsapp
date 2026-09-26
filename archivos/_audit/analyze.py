import json, os, io, re
base = r"G:\Barberia\archivos\_audit"
out = io.StringIO()
def W(*a): print(*a, file=out)

wfs = {}
for name in ["barberiaAgenteUncensored","barberiaRecordatorios"]:
    wfs[name] = json.load(open(os.path.join(base,name+".json"),encoding="utf-8"))

# ---- connections ----
for name,wf in wfs.items():
    W("#"*100); W("CONNECTIONS:", name)
    for src, conn in wf["connections"].items():
        for ctype, branches in conn.items():
            for bi, br in enumerate(branches):
                if not br: continue
                tgts = [f"{t['node']}[{t.get('type','main')}:{t.get('index',0)}]" for t in br]
                W(f"  {src!r} --{ctype}[{bi}]--> {tgts}")

# ---- trigger / error trigger check ----
W("#"*100); W("TRIGGERS & ERROR HANDLING SCAN")
for name,wf in wfs.items():
    W("--", name)
    for n in wf["nodes"]:
        t = n["type"]
        if "trigger" in t.lower() or "webhook" in t.lower():
            W("  TRIGGER:", n["name"], t)
    errs = [n["name"] for n in wf["nodes"] if n["type"]=="n8n-nodes-base.errorTrigger"]
    W("  errorTrigger nodes:", errs or "NONE")
    s = wf.get("settings",{})
    W("  settings.errorWorkflow:", s.get("errorWorkflow","NONE"))
    for n in wf["nodes"]:
        keys = [k for k in ("onError","retryOnFail","maxTries","waitBetweenTries","alwaysOutputData","continueOnFail") if k in n]
        if keys:
            W(f"   {n['name']!r}: " + ", ".join(f"{k}={n[k]}" for k in keys))

# ---- all http / external nodes ----
W("#"*100); W("EXTERNAL CALL NODES")
for name,wf in wfs.items():
    W("--", name)
    for n in wf["nodes"]:
        t = n["type"]
        if any(x in t for x in ["httpRequest","googleCalendar","googleSheets","postgres","openAi","n8n-nodes-base.n8n","evolution",".n8n"]):
            p = n.get("parameters",{})
            W(f"  {n['name']!r} type={t} url={p.get('url','-')}")
            W(f"      auth={p.get('authentication','-')} cred={json.dumps(n.get('credentials',{}),ensure_ascii=False)}")

# ---- secrets scan ----
W("#"*100); W("SECRET SCAN")
pat = re.compile(r"(sk-[A-Za-z0-9_\-]{10,}|Bearer\s+[A-Za-z0-9_\-\.]{15,}|eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}|api[_-]?key|apikey|Authorization|token)", re.I)
for name,wf in wfs.items():
    W("--", name)
    for n in wf["nodes"]:
        s = json.dumps(n, ensure_ascii=False)
        for m in set(pat.findall(s)):
            pass
        hits = pat.findall(s)
        # find literal-looking secrets in parameter VALUES (not expressions)
        def walk(o, path=""):
            if isinstance(o, dict):
                for k,v in o.items(): walk(v, path+"/"+str(k))
            elif isinstance(o, list):
                for i,v in enumerate(o): walk(v, path+f"[{i}]")
            elif isinstance(o, str):
                if o.startswith("="): return  # expression
                if len(o) >= 24 and re.fullmatch(r"[A-Za-z0-9_\-\.\+=/]{24,}", o):
                    W(f"   LONG LITERAL in {n['name']!r} at {path}: {o[:60]}...")
                if re.search(r"(sk-[A-Za-z0-9]{10,}|Bearer\s+\S{15,})", o):
                    W(f"   TOKEN-LIKE in {n['name']!r} at {path}: {o[:80]}")
        walk(n.get("parameters",{}), "params")
    # credentials referenced
    used = {}
    for n in wf["nodes"]:
        for ct, c in (n.get("credentials") or {}).items():
            used.setdefault(ct+"|"+c.get("name","?"), []).append(n["name"])
    W("  credentials used:")
    for k,v in sorted(used.items()):
        W(f"    {k}  ->  {len(v)} nodes")

# ---- positions overlap ----
W("#"*100); W("POSITIONS")
for name,wf in wfs.items():
    W("--", name)
    seen = {}
    for n in wf["nodes"]:
        p = tuple(n.get("position") or [])
        seen.setdefault(p, []).append(n["name"])
    dup = {k:v for k,v in seen.items() if len(v)>1}
    W("  exact duplicate positions:", json.dumps(dup, ensure_ascii=False) if dup else "none")
    xs = [p[0] for p in seen]; ys=[p[1] for p in seen]
    W(f"  x range {min(xs)}..{max(xs)}  y range {min(ys)}..{max(ys)}")

# ---- generic names ----
W("#"*100); W("GENERIC NODE NAMES")
gen = re.compile(r"^(Code\d*|Edit Fields\d*|Set\d*|Switch\d*|IF\d*|HTTP Request\d*|Merge\d*|NoOp\d*|Wait\d*|Filter\d*|Postgres\d*)$")
for name,wf in wfs.items():
    W("--", name, [n["name"] for n in wf["nodes"] if gen.match(n["name"])])
open(os.path.join(base,"analysis.txt"),"w",encoding="utf-8").write(out.getvalue())
print("ok", len(out.getvalue()))

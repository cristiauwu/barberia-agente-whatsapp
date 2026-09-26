import json, urllib.request, sys
sys.stdout.reconfigure(encoding="utf-8")
KEY = open(r"G:\Barberia\archivos\.n8n-key.txt", encoding="utf-8").read().strip()

def api(p):
    r = urllib.request.Request("http://localhost:5678/api/v1" + p)
    r.add_header("X-N8N-API-KEY", KEY)
    return json.loads(urllib.request.urlopen(r, timeout=120).read().decode())

for eid in [1171, 1075, 747, 1135, 861, 800, 838, 599]:
    d = api(f"/executions/{eid}?includeData=true")
    x = d.get("data", d)
    rd = (x.get("resultData") or {}) if "resultData" in x else ((x.get("data") or {}).get("resultData") or {})
    run = rd.get("runData") or {}
    print("="*100)
    print(f"EXEC {eid} status={x.get('status')} waitTill={x.get('waitTill')} finished={x.get('finished')}")
    print("  nodes:", list(run.keys()))
    trig = run.get("Google Sheets Trigger")
    if trig:
        for r in trig:
            js = (r.get("data") or {}).get("main", [[[]]])[0]
            for it in js:
                print("  TRIGGER item:", json.dumps(it.get("json"), ensure_ascii=False)[:400])
    code = run.get("Code")
    if code:
        for r in code:
            js = (r.get("data") or {}).get("main", [[[]]])[0]
            for it in js:
                j = it.get("json") or {}
                keep = {k: j.get(k) for k in ("ID","Estatus","Nombre","Día ","Hora","Numero celular",
                        "fechaISO","recordatorio24ISO","recordatorio1ISO","mandar24","mandar1","fechaLegible")}
                print("  CODE out:", json.dumps(keep, ensure_ascii=False))
    sw = run.get("Switch")
    if sw:
        for r in sw:
            mains = (r.get("data") or {}).get("main") or []
            print(f"  SWITCH outputs non-empty: {[i for i,m in enumerate(mains) if m]}")
    for wn in ("ESPERAR A 24 H", "ESPERAR A 1 H"):
        w = run.get(wn)
        if w:
            for r in w:
                print(f"  {wn}: status={r.get('executionStatus')} waitTill={r.get('waitTill')} startTime={r.get('startTime')}")
    print("  lastNodeExecuted:", rd.get("lastNodeExecuted"))
    if rd.get("error"):
        print("  ERROR:", json.dumps(rd["error"], ensure_ascii=False)[:500])
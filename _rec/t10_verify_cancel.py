import sys, json, time
sys.path.insert(0, r"G:\Barberia\_rec")
import tb

print("=== Objetivos de cancelacion, con autenticacion ===")
for eid in ("1300", "1298"):
    x = tb.exec_meta(eid)
    print(f"  exec {eid}: status={x.get('status')} waitTill={x.get('waitTill')} finished={x.get('finished')}")

print("\n=== Detalle de las ejecuciones de cancelacion ===")
for eid in ("1322", "1325", "1329", "1331"):
    x = tb.exec_full(eid)
    rd = x.get("resultData") or {}
    run = rd.get("runData") or {}
    print("-"*90)
    print(f"exec {eid}: status={x.get('status')} last={rd.get('lastNodeExecuted')}")
    t = run.get("Google Sheets Trigger") or []
    for r in t:
        for it in (r.get("data") or {}).get("main", [[]])[0]:
            j = it.get("json") or {}
            print("   fila:", json.dumps({k: j.get(k) for k in ("ID","Estatus","Nombre","Execution ID")}, ensure_ascii=False))
    co = run.get("Code") or []
    for r in co:
        for it in (r.get("data") or {}).get("main", [[]])[0]:
            j = it.get("json") or {}
            print("   Code Estatus:", j.get("Estatus"))
    iff = run.get("IF - Es cita agendada") or []
    for r in iff:
        mains = (r.get("data") or {}).get("main") or []
        print(f"   IF - Es cita agendada -> salidas con datos: {[i for i,m in enumerate(mains) if m]}")
    print("   nodos ejecutados:", list(run.keys()))
    if "Switch" in run:
        sw = run["Switch"]
        mains = (sw[0].get("data") or {}).get("main") or []
        print(f"   Switch -> salidas con datos: {[i for i,m in enumerate(mains) if m]}")
    else:
        print("   Switch NO se ejecuto")

print("\n=== ¿Existen todavia los objetivos? ===")
for eid in ("1300", "1298", "1171", "1075"):
    x = tb.exec_meta(eid)
    print(f"  exec {eid}: status={x.get('status')} waitTill={x.get('waitTill')}")
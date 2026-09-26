import sys, json
sys.path.insert(0, r"G:\Barberia\_rec")
import tb

print(f"{'exec':>6} {'status':<9} {'waitTill':<26} {'CRM':^5} {'CITA':^5} {'WAIT':^5} {'last'}")
rows = []
for e in tb.execs(limit=100):
    m = tb.exec_meta(e["id"])
    if m.get("status") not in ("waiting", "success", "error", "canceled"):
        continue
    x = tb.exec_full(e["id"])
    rd = x.get("resultData") or {}
    run = rd.get("runData") or {}
    crm = "SI" if "Registrar cliente (CRM)" in run else "no"
    cita = "SI" if "Registrar cita (Postgres)" in run else "no"
    wait = "SI" if any(k.startswith("ESPERAR") for k in run) else "no"
    last = rd.get("lastNodeExecuted")
    rows.append((m["id"], m.get("status"), m.get("waitTill"), crm, cita, wait, last))
    print(f"{m['id']:>6} {str(m.get('status')):<9} {str(m.get('waitTill')):<26} {crm:^5} {cita:^5} {wait:^5} {last}")

print()
w = [r for r in rows if r[5] == "SI"]
print(f"Ejecuciones que entraron a un Wait: {len(w)}")
print(f"  ...de esas, SIN 'Registrar cita (Postgres)': {sum(1 for r in w if r[4]=='no')}")
print(f"  ...de esas, SIN 'Registrar cliente (CRM)'  : {sum(1 for r in w if r[3]=='no')}")
nw = [r for r in rows if r[5] == "no"]
print(f"Ejecuciones que NO entraron a un Wait: {len(nw)}")
print(f"  ...de esas, SIN 'Registrar cita (Postgres)': {sum(1 for r in nw if r[4]=='no')}")
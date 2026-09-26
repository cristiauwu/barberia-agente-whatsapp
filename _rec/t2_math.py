#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verifica los calculos del nodo Code (recordatorio24ISO / recordatorio1ISO)
contra Python puro, y los waitTill reales de las ejecuciones en espera."""
import json, sys
from datetime import datetime, timedelta, timezone
sys.stdout.reconfigure(encoding="utf-8")

MX = timezone(timedelta(hours=-6))  # America/Mexico_City, UTC-06:00 fijo

def calcula(dia, hora):
    """Reproduce el nodo Code."""
    tp = hora.split(":")
    while len(tp) < 3:
        tp.append("00")
    hh, mm, ss = [(p if len(p) > 1 else "0" + p) for p in tp]
    y, mo, d = dia.strip().split("-")
    cita = datetime(int(y), int(mo), int(d), int(hh), int(mm), int(ss), tzinfo=MX)
    r24 = cita - timedelta(days=1)
    r1 = cita - timedelta(hours=1)
    return cita, r24, r1

print("="*100)
print("A) CALCULO DEL NODO Code — casos calculados con Python")
print("="*100)
casos = [
    ("2026-09-28", "15:00:00", "01:00"),
    ("2026-09-29", "11:00:00", "17:00"),
    ("2026-09-27", "15:00:00", "21:00"),
    ("2026-10-01", "16:00:00", "22:00"),
    ("2026-09-28", "14:20:00", "20:20"),
    ("2026-09-25", "16:00:00", "22:00"),
    ("2026-09-26", "13:00:00", "19:00"),
    ("2026-09-30", "15:00:00", "21:00"),
    ("2026-09-25", "10:00:00", "16:00"),
    ("2026-09-25", "15:00:00", "21:00"),
]
for dia, hora, esperado_fechaISO in casos:
    cita, r24, r1 = calcula(dia, hora)
    f = cita.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    a = r24.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    b = r1.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    ok = "OK " if f == esperado_fechaISO else "!! "
    print(f"{ok} {dia} {hora} CDMX -> citaISO={f}  rec24ISO={a}  rec1ISO={b}")

print()
print("="*100)
print("B) waitTill REAL de cada ejecucion en espera vs. lo que el nodo Code debio calcular")
print("="*100)
sys.path.insert(0, r"G:\Barberia\_rec")
import tb

waiting = []
for e in tb.execs(limit=100):
    m = tb.exec_meta(e["id"])
    if m.get("status") == "waiting":
        waiting.append(m)
waiting.sort(key=lambda x: int(x["id"]))

for m in waiting:
    eid = m["id"]
    x = tb.exec_full(eid)
    rd = x.get("resultData") or {}
    run = rd.get("runData") or {}
    trig = run.get("Google Sheets Trigger") or []
    items = (trig[0].get("data") or {}).get("main", [[]])[0] if trig else []
    codigo = run.get("Code") or []
    cout = (codigo[0].get("data") or {}).get("main", [[[]]])[0] if codigo else []
    esperado = run.get("ESPERAR A 24 H") or run.get("ESPERAR A 1 H")
    nombre_wait = "ESPERAR A 24 H" if run.get("ESPERAR A 24 H") else "ESPERAR A 1 H"
    print("-"*100)
    print(f"EXEC {eid}  status={m.get('status')}  waitTill={m.get('waitTill')}  nodo={nombre_wait}")
    for it in items:
        j = it.get("json") or {}
        dia, hora = j.get("Día ") or j.get("Día"), j.get("Hora")
        if not dia or not hora:
            print("   (item sin fecha/hora):", json.dumps(j, ensure_ascii=False)[:200]); continue
        cita, r24, r1 = calcula(str(dia), str(hora))
        f = cita.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        a = r24.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        b = r1.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        prods = [c.get("json", {}) for c in cout]
        p = next((p for p in prods if p.get("ID") == j.get("ID")), {})
        print(f"   ID={j.get('ID')} {dia} {hora} -> py: cita={f} rec24={a} rec1={b}")
        print(f"        Code dice: cita={p.get('fechaISO')} rec24={p.get('recordatorio24ISO')} rec1={p.get('recordatorio1ISO')} mandar24={p.get('mandar24')} mandar1={p.get('mandar1')}")
        for etq, py, js in (("fecha", f, p.get("fechaISO")), ("rec24", a, p.get("recordatorio24ISO")), ("rec1", b, p.get("recordatorio1ISO"))):
            print(f"        {'COINCIDE' if py == js else 'DISCREPA'} en {etq}")
    if esperado:
        wt = (esperado[0] or {}).get("waitTill")
        print(f"   nodo {nombre_wait} waitTill(item)={wt}  |  waitTill(ejecucion)={m.get('waitTill')}")
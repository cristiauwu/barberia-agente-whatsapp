#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueba de UPSERT / idempotencia del CRM.

Usa una cita en el PASADO para que mandar24 y mandar1 sean false: el flujo
no entra a ningun Wait y por tanto 'Registrar cita (Postgres)' SI se ejecuta.
Inserta la MISMA fila (mismo ID) DOS veces y cuenta.
"""
import sys, json, time, subprocess
sys.path.insert(0, r"G:\Barberia\_rec")
import tb

DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\dockerdesktop\resources\bin\docker.exe".replace("dockerdesktop", "DockerDesktop")
ID = "verif-rec-t2"
JID = "5214501111805@s.whatsapp.net"


def sql(q):
    p = subprocess.run([DOCKER, "exec", "-i", "barberia-postgres", "psql",
                        "-U", "barberia", "-d", "barberia", "-f", "-"],
                       input=q.encode("utf-8"), capture_output=True)
    return p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def cuenta():
    o, e = sql(f"""
\\pset pager off
select count(*) as citas from barber_citas where id = '{ID}';
select visitas, etiqueta from barber_clientes where jid = '{JID}';
""")
    return o


print("=== ESTADO INICIAL ===")
print(cuenta())

fila = {
    "ID": ID, "Estatus": "agendado", "Nombre": "Verif Upsert",
    "Servicio": "Ceja", "Precio del servicio": "30",
    "Día ": "2026-09-20", "Hora": "15:00:00",
    "Numero celular": "5214501111805", "Execution ID": "",
}

for vuelta in (1, 2):
    print("="*90)
    print(f"INSERCION #{vuelta} de la MISMA fila (ID={ID}, cita en el pasado)")
    print("="*90)
    antes = {e["id"] for e in tb.execs(limit=100)}
    r = tb.append_row(fila)
    print("  append:", "ok" if r.get("ok") else r)

    eid = None
    t0 = time.time()
    while time.time() - t0 < 220:
        nn = [e for e in tb.execs(limit=80) if e["id"] not in antes]
        if nn:
            nn.sort(key=lambda e: int(e["id"]))
            eid = nn[0]["id"]
            break
        time.sleep(10)
    time.sleep(15)
    print(f"  ejecucion del trigger: {eid}")

    if eid:
        x = tb.exec_full(eid)
        rd = x.get("resultData") or {}
        run = rd.get("runData") or {}
        print(f"  status={x.get('status')} last={rd.get('lastNodeExecuted')}")
        print(f"  nodos: {list(run.keys())}")
        for name in ("Registrar cliente (CRM)", "Registrar cita (Postgres)"):
            for rr in (run.get(name) or []):
                print(f"    {name}: status={rr.get('executionStatus')} out="
                      f"{json.dumps((rr.get('data') or {}).get('main'), ensure_ascii=False)[:300]}")
                if rr.get("error"):
                    print("      ERROR:", json.dumps(rr["error"], ensure_ascii=False)[:600])

    print(cuenta())
    time.sleep(5)

print("="*90)
print("=== DETALLE FINAL barber_citas ===")
o, e = sql(f"""
\\pset pager off
select id, jid, nombre, servicio, precio, inicio, fin, estado, actualizado_en
from barber_citas where id = '{ID}';
""")
print(o); print(e)
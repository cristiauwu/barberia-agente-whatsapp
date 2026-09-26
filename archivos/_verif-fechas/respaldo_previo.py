#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Respaldo previo a las pruebas: memoria del JID de pruebas + calendario."""
import json
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"G:\Barberia\archivos\_verif")
DIR = r"G:\Barberia\archivos\_verif-fechas"
DOCKER = (r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop"
          r"\resources\bin\docker.exe")
os.environ["DOCKER_CONFIG"] = r"G:\Barberia\.docker"
JID = "5214501111805@s.whatsapp.net"


def psql(s):
    r = subprocess.run([DOCKER, "exec", "barberia-postgres", "psql", "-U",
                        "barberia", "-d", "barberia", "-t", "-A", "-F", "\t",
                        "-c", s], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return ((r.stdout or "") + (r.stderr or "")).strip()


print("=" * 70)
print("MEMORIA DEL JID DE PRUEBAS:", JID)
print("=" * 70)
filas = psql(f"SELECT id, session_id, message::text FROM n8n_chat_histories "
             f"WHERE session_id='{JID}' ORDER BY id;")
mem = []
for ln in filas.split("\n"):
    if not ln.strip():
        continue
    partes = ln.split("\t", 2)
    if len(partes) < 3:
        continue
    mem.append({"id": int(partes[0]), "session_id": partes[1],
                "message": json.loads(partes[2])})
json.dump(mem, open(DIR + r"\respaldo_memoria_1805.json", "w",
                    encoding="utf-8"), ensure_ascii=False, indent=1)
print("filas de memoria respaldadas:", len(mem))
if mem:
    print("  ids:", mem[0]["id"], "->", mem[-1]["id"])
    print("  ultimo mensaje:", json.dumps(mem[-1]["message"],
                                           ensure_ascii=False)[:400])

# --- otros JIDs presentes, para saber que no tocaremos ---
print("\nsesiones de memoria existentes:")
print(psql("SELECT session_id, count(*) FROM n8n_chat_histories "
           "GROUP BY session_id ORDER BY 2 DESC;"))

# --- Postgres: tablas del negocio ---
print("\n" + "=" * 70)
print("TABLAS barber_*")
print("=" * 70)
print(psql("SELECT table_name FROM information_schema.tables "
           "WHERE table_schema='public' ORDER BY 1;"))
for t in ("barber_citas", "barber_clientes", "barber_pausas"):
    print(f"\n-- {t} --")
    print(psql(f"SELECT count(*) FROM {t};"))

# --- calendario ---
print("\n" + "=" * 70)
print("CALENDARIO (via workflow temporal)")
print("=" * 70)
import cal  # noqa: E402

r = cal.listar("2026-09-01T00:00:00-06:00", "2027-03-01T23:59:59-06:00")
print("crudo:", json.dumps(r, ensure_ascii=False)[:400])
if isinstance(r, list):
    ev = (r[0] or {}).get("json", {}).get("eventos", []) if r else []
elif isinstance(r, dict):
    ev = (r.get("json") or {}).get("eventos") or r.get("eventos") or []
else:
    ev = []
json.dump(ev, open(DIR + r"\respaldo_calendario.json", "w",
                   encoding="utf-8"), ensure_ascii=False, indent=1)
print("eventos encontrados:", len(ev))
for e in ev:
    print(f"  {e['id']} | {e['start']} .. {e['end']} | {e['summary']}")
cal.limpiar_wf()
print("\nworkflow temporal eliminado")
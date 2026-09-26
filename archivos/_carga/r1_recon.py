#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reconocimiento: estructura del workflow, Wait, memoria, esquema, constraint."""
import json
import sys

sys.path.insert(0, r"G:\Barberia\archivos\_carga")
import lib

lib.init()
print("n8n key len =", len(lib.ENV["N8NKEY"]))
print("evolution key len =", len(lib.ENV["EVOKEY"]))

lib.h("1) WORKFLOWS")
st, d = lib.api("/workflows?limit=250")
print("status", st)
for w in (d or {}).get("data", []):
    print("  id=%-28s active=%-5s nodes=%-4d name=%s" % (
        w["id"], w.get("active"), len(w.get("nodes", [])), w["name"]))

lib.h("2) NODOS DEL AGENTE")
st, wf = lib.api("/workflows/" + lib.WF_AGENTE)
print("status", st)
nodos = wf.get("nodes", [])
print("total nodos:", len(nodos))
for n in nodos:
    print("  %-38s %-46s tv=%s" % (n["name"][:38], n["type"], n.get("typeVersion")))

lib.h("3) NODOS WAIT")
for n in nodos:
    if "wait" in n["type"].lower() or "Wait" in n["name"]:
        print("  %s -> %s" % (n["name"], json.dumps(n.get("parameters", {}), ensure_ascii=False)[:400]))

lib.h("4) NODOS DE MEMORIA")
for n in nodos:
    if "memory" in n["type"].lower() or "Memory" in n["name"]:
        print("  %s -> %s" % (n["name"], json.dumps(n.get("parameters", {}), ensure_ascii=False)[:600]))

lib.h("5) NODO AI AGENT (prompt / config)")
for n in nodos:
    if n["type"].endswith(".agent"):
        p = n.get("parameters", {})
        print("  nombre:", n["name"])
        print("  parametros:", json.dumps({k: (v if not isinstance(v, str) or len(v) < 200 else v[:200] + "...(%d)" % len(v)) for k, v in p.items()}, ensure_ascii=False)[:1500])

lib.h("6) ESQUEMA POSTGRES")
rc, out, err = lib.psql("""SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema='public' AND table_name LIKE 'barber%'
ORDER BY table_name, ordinal_position;""")
for ln in out.splitlines():
    print(" ", ln)
if err.strip():
    print("STDERR:", err[:1500])

lib.h("7) CONSTRAINT EXCLUDE")
rc, out, err = lib.psql("""SELECT conname, pg_get_constraintdef(oid)
FROM pg_constraint WHERE contype='x' AND conrelid::regclass::text LIKE 'barber%';""")
print("rc=", rc)
print(out or "(sin salida)")
if err.strip():
    print("STDERR:", err[:1500])

lib.h("8) INDICES Y TRIGGERS DE barber_citas")
rc, out, err = lib.psql("""SELECT indexname, indexdef FROM pg_indexes
WHERE tablename LIKE 'barber%' ORDER BY tablename, indexname;""")
print(out or "(sin salida)")
if err.strip():
    print("STDERR:", err[:1500])

lib.h("9) TABLAS n8n (chat_histories)")
rc, out, err = lib.psql("""SELECT table_schema, table_name FROM information_schema.tables
WHERE table_name LIKE '%chat%' OR table_name LIKE '%execution%' ORDER BY 1,2;""")
print(out or "(sin salida)")
if err.strip():
    print("STDERR:", err[:800])

lib.h("10) ESTRUCTURA n8n_chat_histories")
rc, out, err = lib.psql("""SELECT column_name, data_type FROM information_schema.columns
WHERE table_name='n8n_chat_histories' ORDER BY ordinal_position;""")
print(out or "(sin salida)")
if err.strip():
    print("STDERR:", err[:800])
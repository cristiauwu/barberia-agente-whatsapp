#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Baseline: conteos, config de hoja/calendario, operadores, recursos."""
import json
import sys

sys.path.insert(0, r"G:\Barberia\archivos\_carga")
import lib
lib.init()

lib.h("1) OPERADORES")
for r in lib.q("SELECT jid, nombre, rol, activo FROM barber_operadores ORDER BY rol, jid;"):
    print("  ", r)

lib.h("2) PAUSAS ACTIVAS")
rc, out, err = lib.psql("SELECT jid, hasta, motivo FROM barber_pausas WHERE hasta > now();")
print(out or "(ninguna)")
print("err:", err.strip()[:300] or "-")

lib.h("3) CONTEO TABLAS BARBER")
for t in ("barber_citas", "barber_clientes", "barber_pausas", "barber_bloqueos",
          "barber_auditoria", "barber_escalaciones", "barber_lista_espera", "barber_servicios"):
    try:
        print("  %-24s %s" % (t, lib.scal("SELECT count(*) FROM %s;" % t)))
    except Exception as e:
        print("  %-24s ERROR %s" % (t, str(e)[:150]))

lib.h("4) CITAS (detalle)")
for r in lib.q("SELECT id, jid, nombre, servicio, inicio, fin, estado FROM barber_citas ORDER BY inicio;"):
    print("  ", r)

lib.h("5) CLIENTES (detalle)")
for r in lib.q("SELECT jid, nombre, visitas FROM barber_clientes ORDER BY jid;"):
    print("  ", r)

lib.h("6) n8n_chat_histories")
print("  filas totales:", lib.scal("SELECT count(*) FROM n8n_chat_histories;"))
print("  sesiones distintas:", lib.scal("SELECT count(DISTINCT session_id) FROM n8n_chat_histories;"))
for r in lib.q("SELECT session_id, count(*) FROM n8n_chat_histories GROUP BY session_id ORDER BY 2 DESC;"):
    print("   ", r)
print("  tamano tabla:", lib.scal("SELECT pg_size_pretty(pg_total_relation_size('n8n_chat_histories'));"))

lib.h("7) EJECUCIONES n8n (execution_entity)")
for r in lib.q("""SELECT "workflowId", count(*) FROM execution_entity GROUP BY 1 ORDER BY 2 DESC;"""):
    print("  ", r)
print("  total:", lib.scal("SELECT count(*) FROM execution_entity;"))
print("  tamano execution_data:", lib.scal("SELECT pg_size_pretty(COALESCE(pg_total_relation_size('execution_data'),0));"))
print("  tamano execution_entity:", lib.scal("SELECT pg_size_pretty(pg_total_relation_size('execution_entity'));"))
print("  tamano DB:", lib.scal("SELECT pg_size_pretty(pg_database_size('barberia'));"))

lib.h("8) CONEXIONES pg_stat_activity")
for r in lib.q("""SELECT datname, usename, state, count(*) FROM pg_stat_activity
GROUP BY 1,2,3 ORDER BY 4 DESC;"""):
    print("  ", r)
print("  MAX_CONNECTIONS:", lib.scal("SELECT setting FROM pg_settings WHERE name='max_connections';"))
print("  total conexiones:", lib.scal("SELECT count(*) FROM pg_stat_activity;"))

lib.h("9) CONFIG HOJA DE CALCULO (workflow recordatorios)")
st, wf = lib.api("/workflows/" + lib.WF_RECORDATORIOS)
for n in wf.get("nodes", []):
    if "googleSheets" in n["type"]:
        p = n.get("parameters", {})
        doc = p.get("documentId") or p.get("sheetId")
        print("  %-34s type=%s" % (n["name"], n["type"]))
        print("     doc=", json.dumps(doc, ensure_ascii=False)[:300] if doc else None)
        print("     sheet=", json.dumps(p.get("sheetName"), ensure_ascii=False)[:200])
        if n["type"].endswith("Trigger"):
            print("     poll=", json.dumps({k: v for k, v in p.items() if "poll" in k.lower() or "event" in k.lower()}, ensure_ascii=False)[:400])

lib.h("10) CONFIG CALENDARIO (nodos googleCalendar del agente)")
st, wf2 = lib.api("/workflows/" + lib.WF_AGENTE)
for n in wf2.get("nodes", []):
    if "googleCalendar" in n["type"]:
        p = n.get("parameters", {})
        cal = p.get("calendar") or p.get("calendarId")
        print("  %-34s" % n["name"])
        print("     calendar=", json.dumps(cal, ensure_ascii=False)[:250])
        print("     op=", p.get("operation"), "start=", json.dumps(p.get("start"), ensure_ascii=False)[:120])

lib.h("11) RECURSOS (docker stats)")
for k, v in lib.docker_stats().items():
    print("  %-22s %s" % (k, v))

lib.h("12) PRUNE de n8n")
st, d = lib.api("/executions?limit=1")
print("  filtro por defecto (Devuelve solo ejecuciones guardadas):", json.dumps(d, ensure_ascii=False)[:200] if st == 200 else st)

lib.h("13) GOOGLE SHEET: filas actuales (via googleSheetsTool del agente no se puede) - uso la API de n8n para listar credenciales")
st, d = lib.api("/credentials?limit=50")
if st == 200:
    for c in d.get("data", []):
        print("   cred id=%s name=%s type=%s" % (c.get("id"), c.get("name"), c.get("type")))
else:
    print("  ", st, str(d)[:200])
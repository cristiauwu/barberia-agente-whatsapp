#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Respaldo ANTES de las pruebas. Guarda dumps en _carga/backup/."""
import json
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, r"G:\Barberia\archivos\_carga")
import lib
lib.init()

BK = r"G:\Barberia\archivos\_carga\backup"
os.makedirs(BK, exist_ok=True)

lib.h("RESPALDO")

# 1) n8n_chat_histories completo, en formato INSERT reproducible
rc, out, err = lib.docker3("exec", lib.PG_CONTAINER, "psql", "-U", "barberia",
                          "-d", "barberia", "-A", "-t", "-c",
                          "COPY (SELECT id, session_id, message::text FROM n8n_chat_histories ORDER BY id) TO STDOUT;")
with open(os.path.join(BK, "chat_histories.tsv"), "w", encoding="utf-8") as f:
    f.write(out)
print("  chat_histories.tsv filas:", len([l for l in out.splitlines() if l.strip()]), "rc=", rc)
if err.strip():
    print("  STDERR:", err[:300])

# copia de seguridad binaria real de la tabla (dentro del contenedor -> al host)
rc, out, err = lib.docker3("exec", lib.PG_CONTAINER, "sh", "-c",
                          "pg_dump -U barberia -d barberia -t n8n_chat_histories --data-only --column-inserts > /tmp/bk_chat.sql")
print("  pg_dump chat rc=", rc, err[:200])
rc, out, err = lib.docker3("cp", "%s:/tmp/bk_chat.sql" % lib.PG_CONTAINER,
                          os.path.join(BK, "chat_histories.sql"))
print("  docker cp rc=", rc, err[:200])

# 2) barber_citas / barber_clientes / barber_pausas / barber_bloqueos
for t in ("barber_citas", "barber_clientes", "barber_pausas", "barber_bloqueos"):
    rc, out, err = lib.docker3("exec", lib.PG_CONTAINER, "sh", "-c",
                              "pg_dump -U barberia -d barberia -t %s --data-only --column-inserts > /tmp/bk_%s.sql" % (t, t))
    rc, out, err = lib.docker3("cp", "%s:/tmp/bk_%s.sql" % (lib.PG_CONTAINER, t),
                              os.path.join(BK, "bd_%s.sql" % t))
    print("  respaldo %-18s rc=%s" % (t, rc))

# 3) estado en JSON
estado = {
    "tomado_en": datetime.now().astimezone().isoformat(),
    "chat_histories_filas": lib.scal("SELECT count(*) FROM n8n_chat_histories;"),
    "chat_histories_sesiones": json.loads("{}"),
    "barber_citas": lib.q("SELECT id, jid, servicio, inicio, estado FROM barber_citas ORDER BY id;"),
    "barber_clientes": lib.q("SELECT jid, nombre, visitas FROM barber_clientes ORDER BY jid;"),
    "barber_pausas": lib.q("SELECT jid, hasta, motivo FROM barber_pausas;"),
    "barber_bloqueos": lib.q("SELECT id, inicio, fin, motivo FROM barber_bloqueos;"),
    "ejecuciones": lib.scal("SELECT count(*) FROM execution_entity;"),
    "ejecuciones_agente": lib.scal(
        "SELECT count(*) FROM execution_entity WHERE \"workflowId\"='barberiaAgenteUncensored';"),
    "conexiones_pg": lib.scal("SELECT count(*) FROM pg_stat_activity;"),
    "docker_stats": lib.docker_stats(),
    "sesiones": lib.q("SELECT session_id, count(*) FROM n8n_chat_histories GROUP BY 1 ORDER BY 2 DESC;"),
}
with open(os.path.join(BK, "estado_antes.json"), "w", encoding="utf-8") as f:
    json.dump(estado, f, ensure_ascii=False, indent=2)
print("\n  estado guardado en estado_antes.json")
print("  filas chat_histories:", estado["chat_histories_filas"])
print("  ejecuciones:", estado["ejecuciones"])
print("  conexiones pg:", estado["conexiones_pg"])
print("  docker stats:", json.dumps(estado["docker_stats"], ensure_ascii=False))
print("\n  archivos en backup/:", os.listdir(BK))

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Helper de acceso a Postgres para la auditoria de conocimiento."""
import json
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import psycopg

ENV = {}
for line in open(r"G:\Barberia\.env", encoding="utf-8"):
    line = line.strip()
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        ENV[k] = v

DSN = ("host=127.0.0.1 port=5432 dbname=%s user=%s password=%s"
       % (ENV["POSTGRES_DB"], ENV["POSTGRES_USER"], ENV["POSTGRES_PASSWORD"]))


def conn():
    return psycopg.connect(DSN, connect_timeout=10)


def q(sql, params=None):
    """Devuelve (columnas, filas)."""
    with conn() as c:
        with c.cursor() as cur:
            cur.execute(sql, params)
            cols = [d.name for d in cur.description] if cur.description else []
            rows = cur.fetchall() if cur.description else []
    return cols, rows


def buscar(texto, limite=3):
    """Llama a la funcion de busqueda. Devuelve lista de dicts."""
    try:
        cols, rows = q(
            "SELECT id, pregunta, categoria, origen, rank, coincidencias "
            "FROM public.barber_buscar_conocimiento(%s, %s)", (texto, limite))
        return [dict(zip(cols, r)) for r in rows], None
    except Exception as e:
        return [], "%s: %s" % (type(e).__name__, e)


def dump(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=1, default=str))
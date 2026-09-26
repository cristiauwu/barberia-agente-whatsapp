#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Aplica al Postgres LOCAL la constraint anti-solape que solo estaba en Supabase.

HALLAZGO: la restriccion `barber_citas_no_solape` existe en Supabase pero
NO en el Postgres local. Y el local es el que n8n escribe de verdad y el
que alimenta el panel. Es decir: la proteccion contra dobles reservas
estaba en la base equivocada.

Se aplica la MISMA definicion que ya funciona en Supabase:

    ALTER TABLE barber_citas ADD CONSTRAINT barber_citas_no_solape
      EXCLUDE USING gist (tstzrange(inicio, fin) WITH &&)
      WHERE (estado IN ('agendado','confirmado'));

Necesita la extension `btree_gist` (para poder mezclar igualdad y rango en
un mismo indice). Es gratuita y viene con Postgres.

IMPORTANTE: una restriccion EXCLUDE protege las filas que YA existen; si
hubiera solapes previos, el ALTER fallaria. Por eso primero se comprueba y
se informa, sin borrar nada.
"""
import os
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DOCKER = (r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop"
          r"\resources\bin\docker.exe")
os.environ["DOCKER_CONFIG"] = r"G:\Barberia\.docker"


def sql(consulta):
    p = subprocess.run([DOCKER, "exec", "barberia-postgres", "psql",
                        "-U", "barberia", "-d", "barberia", "-t", "-A",
                        "-c", consulta], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=180)
    return (p.stdout or "").strip(), (p.stderr or "").strip()


def main():
    print("=" * 68)
    print("APLICAR LA CONSTRAINT ANTI-SOLAPE AL POSTGRES LOCAL")
    print("=" * 68)

    # --- 1. estado previo ---------------------------------------------
    o, _ = sql("SELECT count(*) FROM pg_constraint "
               "WHERE conname='barber_citas_no_solape';")
    if o == "1":
        print("  la constraint YA existe. No toco nada.")
        return 0
    print("  la constraint no existe: se va a crear")

    # --- 2. ¿hay solapes previos? --------------------------------------
    o, _ = sql("""
        SELECT count(*) FROM (
          SELECT a.id, b.id
            FROM barber_citas a JOIN barber_citas b
              ON a.id < b.id
             AND tstzrange(a.inicio,a.fin) && tstzrange(b.inicio,b.fin)
           WHERE a.estado IN ('agendado','confirmado')
             AND b.estado IN ('agendado','confirmado')
             AND a.inicio IS NOT NULL AND a.fin IS NOT NULL
             AND b.inicio IS NOT NULL AND b.fin IS NOT NULL
        ) x;""")
    print(f"  solapes actuales en la tabla: {o}")
    if o not in ("0", ""):
        print(f"  ATENCION: hay {o} solapes. La constraint fallaria al crearse.")
        print("  No se aplica nada. Hay que resolverlos primero.")
        return 1

    # --- 3. la extension -----------------------------------------------
    o, e = sql("CREATE EXTENSION IF NOT EXISTS btree_gist;")
    if e and "ERROR" in e:
        print(f"  MAL al crear la extension: {e[:150]}")
        return 1
    print("  extension btree_gist: lista")

    # --- 4. la constraint ----------------------------------------------
    o, e = sql("""
        ALTER TABLE barber_citas ADD CONSTRAINT barber_citas_no_solape
          EXCLUDE USING gist (tstzrange(inicio, fin) WITH &&)
          WHERE (estado IN ('agendado','confirmado'));""")
    if e and "ERROR" in e:
        print(f"  MAL al crear la constraint: {e[:200]}")
        return 1
    print("  constraint creada")

    # --- 5. verificacion -----------------------------------------------
    print()
    print("=" * 68)
    print("VERIFICACION")
    print("=" * 68)
    o, _ = sql("SELECT pg_get_constraintdef(oid) FROM pg_constraint "
               "WHERE conname='barber_citas_no_solape';")
    print(f"  definicion: {o[:120]}")

    # prueba real: intentar meter dos citas solapadas
    sql("CREATE TEMP TABLE _prueba (LIKE barber_citas INCLUDING ALL);")
    sql("ALTER TABLE _prueba ADD CONSTRAINT p EXCLUDE USING gist "
        "(tstzrange(inicio, fin) WITH &&) "
        "WHERE (estado IN ('agendado','confirmado'));")
    sql("INSERT INTO _prueba (id,servicio,inicio,fin,estado) VALUES "
        "('p1','Corte', now()+interval '1 day', "
        " now()+interval '1 day 40 min','agendado');")
    o, e = sql("INSERT INTO _prueba (id,servicio,inicio,fin,estado) VALUES "
               "('p2','Barba', now()+interval '1 day 20 min', "
               " now()+interval '1 day 50 min','agendado');")
    if e and ("23P01" in e or "conflicting" in e or "exclusion" in e.lower()):
        print("  OK  la base RECHAZA un solape (era el objetivo)")
        print("     SQLSTATE 23P01 capturado")
    else:
        print(f"  MAL no rechazo el solape: {e[:150]}")

    # y que SI acepte una cita pegada pero sin solapar
    sql("DELETE FROM _prueba;")
    sql("INSERT INTO _prueba (id,servicio,inicio,fin,estado) VALUES "
        "('p1','Corte', now()+interval '1 day', "
        " now()+interval '1 day 40 min','agendado');")
    o, e = sql("INSERT INTO _prueba (id,servicio,inicio,fin,estado) VALUES "
               "('p3','Ceja', now()+interval '1 day 40 min', "
               " now()+interval '1 day 50 min','agendado');")
    if e and "ERROR" in e:
        print(f"  MAL rechazo dos citas adyacentes (no deberia): {e[:120]}")
    else:
        print("  OK  acepta dos citas pegadas sin solapar")

    sql("DROP TABLE IF EXISTS _prueba;")
    print()
    print("  (tabla de prueba borrada; barber_citas sin tocar)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
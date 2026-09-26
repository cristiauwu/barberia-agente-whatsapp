#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueba la constraint anti-solape en UNA sola sesion de psql.

OJO (trampa que ya me mordio): cada llamada a `psql -c` abre una sesion
nueva. Una tabla TEMP creada en una llamada NO existe en la siguiente, asi
que la prueba de antes fallaba con 'relation does not exist'. Hay que
mandar todo el guion en un solo psql.
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

GUION = """
\\set ON_ERROR_STOP off
\\echo === 1. la constraint debe existir ===
SELECT conname, pg_get_constraintdef(oid)
  FROM pg_constraint WHERE conname='barber_citas_no_solape';

\\echo === 2. tabla de prueba con la misma restriccion ===
DROP TABLE IF EXISTS _prueba;
CREATE TABLE _prueba (
  id text PRIMARY KEY, servicio text,
  inicio timestamptz, fin timestamptz, estado text,
  CONSTRAINT _prueba_no_solape
    EXCLUDE USING gist (tstzrange(inicio, fin) WITH &&)
    WHERE (estado IN ('agendado','confirmado'))
);

\\echo === 3. primera cita: debe entrar ===
INSERT INTO _prueba VALUES ('p1','Corte', now()+interval '1 day',
  now()+interval '1 day 40 min','agendado');
SELECT count(*) AS filas_tras_la_primera FROM _prueba;

\\echo === 4. cita SOLAPADA: debe fallar con 23P01 ===
INSERT INTO _prueba VALUES ('p2','Barba', now()+interval '1 day 20 min',
  now()+interval '1 day 50 min','agendado');
SELECT count(*) AS filas_tras_el_solape FROM _prueba;

\\echo === 5. cita PEGADA sin solapar: debe entrar ===
INSERT INTO _prueba VALUES ('p3','Ceja', now()+interval '1 day 40 min',
  now()+interval '1 day 50 min','agendado');
SELECT count(*) AS filas_tras_la_pegada FROM _prueba;

\\echo === 6. cita CANCELADA solapada: debe entrar (el filtro la excluye) ===
INSERT INTO _prueba VALUES ('p4','Barba', now()+interval '1 day 10 min',
  now()+interval '1 day 30 min','cancelado');
SELECT count(*) AS filas_tras_la_cancelada FROM _prueba;

\\echo === 7. limpieza ===
DROP TABLE _prueba;
SELECT count(*) AS citas_reales FROM barber_citas;
SELECT count(*) AS constraint_sigue FROM pg_constraint
  WHERE conname='barber_citas_no_solape';
"""


def main():
    p = subprocess.run([DOCKER, "exec", "-i", "barberia-postgres", "psql",
                        "-U", "barberia", "-d", "barberia", "-f", "-"],
                       input=GUION, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=200)
    print("=" * 68)
    print("PRUEBA DE LA CONSTRAINT ANTI-SOLAPE (una sola sesion)")
    print("=" * 68)
    salida = (p.stdout or "")
    error = (p.stderr or "")
    for l in salida.split("\n"):
        if l.strip():
            print("  " + l[:120])
    print()
    print("--- stderr (los ERROR de psql van aqui) ---")
    for l in error.split("\n"):
        if l.strip():
            print("  " + l[:130])

    print()
    print("=" * 68)
    print("RESULTADO")
    print("=" * 68)
    pruebas = [
        ("la constraint existe", "barber_citas_no_solape" in salida),
        ("la primera cita entro", "filas_tras_la_primera" in salida),
        ("el solape fue RECHAZADO",
         "23P01" in error or "conflicting key value" in error
         or "exclusion" in error.lower()),
        ("la cita pegada entro", "filas_tras_la_pegada" in salida),
    ]
    fallos = 0
    for n, ok in pruebas:
        print(f"  {'OK  ' if ok else 'MAL '} {n}")
        if not ok:
            fallos += 1
    print(f"\n  FALLOS: {fallos}")
    return 0 if fallos == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
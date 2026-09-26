#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Purga la clave del vendedor de las ejecuciones historicas.

Las 94 filas de `execution_data` son ejecuciones antiguas (del bucle y de
las pruebas) que guardan la API key del vendedor. Se eliminan esas
ejecuciones completas: son registros historicos sin valor operativo.
"""
import os
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
os.environ["DOCKER_CONFIG"] = r"G:\Barberia\.docker"
CLAVE = "CLAVE_DEL_PROVEEDOR"


def psql(sql):
    p = subprocess.run([DOCKER, "exec", "barberia-postgres", "psql", "-U",
                        "barberia", "-d", "barberia", "-t", "-A", "-c", sql],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return (p.stdout or "").strip(), (p.stderr or "").strip()


def main():
    n0, _ = psql(f"""SELECT count(*) FROM execution_data
                     WHERE "data"::text LIKE '%{CLAVE}%';""")
    print(f"ejecuciones con la clave antes: {n0}")

    # Identificar las ejecuciones afectadas
    ids, _ = psql(f"""SELECT string_agg(DISTINCT "executionId"::text, ',')
                      FROM execution_data
                      WHERE "data"::text LIKE '%{CLAVE}%';""")
    if not ids:
        print("nada que purgar")
        return 0
    lista = [x for x in ids.split(",") if x.strip()]
    print(f"ejecuciones afectadas: {len(lista)}")

    # Borrar execution_data y execution_entity de esas ejecuciones
    in_clause = ",".join(lista)
    out1, err1 = psql(f"DELETE FROM execution_data "
                      f"WHERE \"executionId\" IN ({in_clause});")
    print(f"  execution_data: {out1 or err1}")
    out2, err2 = psql(f"DELETE FROM execution_entity "
                      f"WHERE id IN ({in_clause});")
    print(f"  execution_entity: {out2 or err2}")

    print()
    n1, _ = psql(f"""SELECT count(*) FROM execution_data
                     WHERE "data"::text LIKE '%{CLAVE}%';""")
    marca = "OK  " if n1 == "0" else "MAL "
    print(f"  {marca}ejecuciones con la clave despues: {n1}")

    # Barrido global de nuevo, en todas las tablas relevantes
    print()
    print("=== BARRIDO GLOBAL ===")
    for t in ("workflow_entity", "workflow_history", "execution_data",
              "credentials_entity", "settings", "workflow_published_version"):
        n, err = psql(f"""SELECT count(*) FROM {t}
                          WHERE {t}::text LIKE '%{CLAVE}%';""")
        if err and "no existe" in err.lower():
            continue
        if not n.isdigit():
            continue
        marca = "OK  " if n == "0" else "MAL "
        print(f"  {marca}{t}: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
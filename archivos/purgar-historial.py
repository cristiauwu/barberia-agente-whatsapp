#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Purga el historial de versiones que guarda la clave del vendedor.

n8n guarda una copia de cada version del workflow en `workflow_history`.
Tras limpiar los nodos y el pinData, quedan 32 versiones antiguas que aun
contienen la API key del vendedor en texto plano. Hay que borrarlas.

Se conservan las versiones MAS RECIENTES (las ya limpias) y se eliminan
solo las que contienen la clave. Se hace por SQL directo porque la API
publica de n8n no expone el borrado del historial.
"""
import json
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
WIDS = ["barberiaAgenteUncensored", "barberiaRecordatorios"]


def psql(sql, sola_una=True):
    p = subprocess.run([DOCKER, "exec", "barberia-postgres", "psql", "-U",
                        "barberia", "-d", "barberia", "-t", "-A", "-c", sql],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return (p.stdout or "").strip(), (p.stderr or "").strip()


def main():
    print("=" * 70)
    print("ESTADO ANTES")
    print("=" * 70)
    for wid in WIDS:
        tot, _ = psql(f"""SELECT count(*) FROM workflow_history
                          WHERE "workflowId"='{wid}';""")
        con, _ = psql(f"""SELECT count(*) FROM workflow_history
                          WHERE "workflowId"='{wid}'
                          AND nodes::text LIKE '%{CLAVE}%';""")
        print(f"  {wid}: {tot} versiones, {con} con la clave")

    print()
    print("=" * 70)
    print("PURGANDO (solo las versiones con la clave)")
    print("=" * 70)
    for wid in WIDS:
        out, err = psql(f"""DELETE FROM workflow_history
                            WHERE "workflowId"='{wid}'
                            AND nodes::text LIKE '%{CLAVE}%';""")
        print(f"  {wid}: {out or err}")

    print()
    print("=" * 70)
    print("ESTADO DESPUES")
    print("=" * 70)
    ok = True
    for wid in WIDS:
        tot, _ = psql(f"""SELECT count(*) FROM workflow_history
                          WHERE "workflowId"='{wid}';""")
        con, _ = psql(f"""SELECT count(*) FROM workflow_history
                          WHERE "workflowId"='{wid}'
                          AND nodes::text LIKE '%{CLAVE}%';""")
        marca = "OK  " if con == "0" else "MAL "
        if con != "0":
            ok = False
        print(f"  {marca}{wid}: {tot} versiones, {con} con la clave")

    # Comprobacion global: la clave no debe quedar en ninguna tabla de n8n
    print()
    print("=" * 70)
    print("BARRIDO FINAL: la clave en TODA la base de n8n")
    print("=" * 70)
    tablas, _ = psql("""SELECT string_agg(table_name, ',')
                        FROM information_schema.columns
                        WHERE table_schema='public'
                        AND data_type IN ('text','json','jsonb')
                        GROUP BY table_schema;""")
    encontrados = []
    for t in [x.strip() for x in tablas.split(",") if x.strip()]:
        cols, _ = psql(f"""SELECT string_agg(column_name, ',')
                           FROM information_schema.columns
                           WHERE table_schema='public' AND table_name='{t}'
                           AND data_type IN ('text','json','jsonb');""")
        if not cols:
            continue
        cond = " OR ".join([f'"{c}"::text LIKE \'%{CLAVE}%\'' for c in
                            [x.strip() for x in cols.split(",") if x.strip()]])
        n, err = psql(f"SELECT count(*) FROM {t} WHERE {cond};")
        if err or not n.isdigit():
            continue
        if int(n) > 0:
            encontrados.append((t, n))
    if encontrados:
        print("  La clave AUN aparece en:")
        for t, n in encontrados:
            print(f"    - {t}: {n} filas")
    else:
        print("  OK  la clave ya no aparece en ninguna tabla")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
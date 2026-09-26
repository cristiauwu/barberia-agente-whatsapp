#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Confirma el estado del esquema creado en Supabase."""
import os
import subprocess
import sys


def _leer_password_supabase() -> str:
    """Lee la password de Supabase sin tenerla escrita en el codigo.

    Orden: variable de entorno -> archivos locales -> error claro.
    Esos archivos estan en .gitignore, asi que la clave nunca se publica.
    """
    import os
    v = os.environ.get("SUPABASE_PASSWORD")
    if v:
        return v.strip()
    for ruta in (r"G:\Barberia\archivos\.supabase-pass.txt",
                 r"G:\Barberia\archivos\.supabase-conn.txt"):
        try:
            with open(ruta, encoding="utf-8") as f:
                lineas = [x.strip() for x in f if x.strip()]
        except OSError:
            continue
        for l in lineas:
            # en el archivo de conexion la password va en la 4a linea
            if l.startswith("password="):
                return l.split("=", 1)[1].strip()
        if len(lineas) >= 4:
            return lineas[3]
    raise SystemExit(
        "Falta la password de Supabase.\n"
        "Ponla en la variable SUPABASE_PASSWORD o crea el archivo\n"
        "  G:\\Barberia\\archivos\\.supabase-pass.txt\n"
        "con una sola linea que contenga la password."
    )


try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DOCKER = (r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop"
          r"\resources\bin\docker.exe")
os.environ["DOCKER_CONFIG"] = r"G:\Barberia\.docker"
PWD = _leer_password_supabase()

with open(r"G:\Barberia\archivos\.supabase-conn.txt", encoding="utf-8") as f:
    L = [x.strip() for x in f if x.strip()]
HOST, PUERTO, USUARIO = L[0], L[1], L[2]


def q(sql):
    p = subprocess.run(
        [DOCKER, "exec", "-e", f"PGPASSWORD={PWD}", "-e", "PGSSLMODE=require",
         "barberia-postgres", "psql", "-h", HOST, "-p", PUERTO,
         "-U", USUARIO, "-d", "postgres", "-t", "-A", "-c", sql],
        capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=120)
    return (p.stdout or "").strip()


def main():
    print("=" * 68)
    print("SUPABASE — ESTADO CONFIRMADO")
    print("=" * 68)
    print(f"  {USUARIO}@{HOST}:{PUERTO}")
    print()
    tablas = q("SELECT string_agg(table_name, ', ' ORDER BY table_name) "
               "FROM information_schema.tables WHERE table_schema='public';")
    n_tab = len([t for t in tablas.split(",") if t.strip()])
    print(f"  tablas ({n_tab}):")
    for t in tablas.split(", "):
        print(f"    - {t}")
    print()
    print(f"  servicios              {q('SELECT count(*) FROM barber_servicios;')}")
    print(f"  FAQs                   {q('SELECT count(*) FROM barber_conocimiento;')}")
    print(f"  operadores             {q('SELECT count(*) FROM barber_operadores;')}")
    print()
    ok1 = q("SELECT count(*) FROM pg_constraint "
            "WHERE conname='barber_citas_no_solape';") == "1"
    ok2 = q("SELECT count(*) FROM pg_matviews "
            "WHERE matviewname='barber_metricas_diarias';") == "1"
    ok3 = q("SELECT count(*) FROM pg_proc "
            "WHERE proname='barber_buscar';") == "1"
    print(f"  constraint anti-solape {'OK' if ok1 else 'FALTA'}")
    print(f"  vista de metricas      {'OK' if ok2 else 'FALTA'}")
    print(f"  funcion buscar         {'OK' if ok3 else 'FALTA'}")
    print()
    print("=== busqueda de conocimiento en Supabase ===")
    for x in ("a que hora abren", "cuanto cuesta el corte",
              "donde estan ubicados", "puedo cancelar"):
        sql = ("SELECT pregunta FROM barber_buscar('"
               + x.replace("'", "''") + "', 1);")
        r = q(sql)
        print(f"  {x!r:26} -> {r[:56] or '(sin resultados)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
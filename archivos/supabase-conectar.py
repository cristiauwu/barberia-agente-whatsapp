#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conecta a Supabase Postgres desde el contenedor local.

Se usa el cliente psql que ya existe en `barberia-postgres` para salir a
internet y hablar con Supabase. Las credenciales se pasan como variables de
entorno de Docker (`PGPASSWORD`), NUNCA en la línea de conexión, para no
tener que escapar los caracteres especiales de la contraseña.

Se usa `PGSSLMODE=require` porque Supabase exige SSL.
"""
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

HOST = "db.zucgrcyzofelmiorvxhb.supabase.co"
PORT = "5432"
USER = "postgres"
DB = "postgres"
# La contraseña termina en @@ (doble arroba): se pasa como variable de
# entorno para no tener que escaparla dentro de una URL.
PWD = _leer_password_supabase()


def psql(sql, timeout=60):
    """Ejecuta SQL en Supabase. Devuelve (stdout, stderr) por separado."""
    args = [DOCKER, "exec",
            "-e", f"PGPASSWORD={PWD}",
            "-e", "PGSSLMODE=require",
            "-e", "PGCONNECT_TIMEOUT=20",
            "barberia-postgres",
            "psql", "-h", HOST, "-p", PORT, "-U", USER, "-d", DB,
            "-t", "-A", "-F", " | ", "-c", sql]
    try:
        p = subprocess.run(args, capture_output=True, text=True,
                           encoding="utf-8", errors="replace",
                           timeout=timeout)
    except subprocess.TimeoutExpired:
        return "", "TIMEOUT"
    return (p.stdout or "").strip(), (p.stderr or "").strip()


def main():
    print("=" * 72)
    print("CONEXION A SUPABASE")
    print("=" * 72)
    print(f"  host: {HOST}")
    print(f"  user: {USER}")
    print(f"  base: {DB}")
    print(f"  password: {'*' * len(PWD)} ({len(PWD)} caracteres)")
    print()

    out, err = psql("SELECT 1;")
    if err and "ERROR" in err.upper():
        print("  FALLO DE CONEXION:")
        for l in err.split("\n")[:6]:
            print(f"    {l}")
        return 1
    if not out:
        print("  FALLO: sin respuesta")
        print("  stderr:", err[:300])
        return 1
    print(f"  OK  conectado (SELECT 1 -> {out})")

    print()
    print("=== version del servidor ===")
    out, _ = psql("SELECT version();")
    print(" ", out[:110])

    print()
    print("=== privilegios: puedo crear tablas? ===")
    out, _ = psql("SELECT current_user, "
                  "has_database_privilege(current_user, 'public', 'CREATE') "
                  "AS puede_crear;")
    print(" ", out)

    print()
    print("=== extensiones ya instaladas ===")
    out, _ = psql("SELECT string_agg(extname, ', ' ORDER BY extname) "
                  "FROM pg_extension;")
    print(" ", out)

    print()
    print("=== extensiones DISPONIBLES que nos interesan ===")
    for ext in ("btree_gist", "unaccent", "pg_trgm", "vector", "pgcrypto"):
        out, _ = psql(f"SELECT count(*) FROM pg_available_extensions "
                      f"WHERE name = '{ext}';")
        marca = "SI" if out == "1" else "no"
        print(f"  {ext:<14} {marca}")

    print()
    print("=== tablas que ya existen en public ===")
    out, _ = psql("SELECT count(*) FROM information_schema.tables "
                  "WHERE table_schema = 'public';")
    print(f"  total: {out}")
    out, _ = psql("SELECT coalesce(string_agg(table_name, ', '), '(ninguna)') "
                  "FROM information_schema.tables "
                  "WHERE table_schema = 'public' LIMIT 30;")
    print(f"  {out[:300]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
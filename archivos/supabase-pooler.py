#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conecta a Supabase por el POOLER, que sí tiene IPv4.

PROBLEMA:
  El host directo `db.<ref>.supabase.co` ahora resuelve SOLO a IPv6.
  El contenedor `barberia-postgres` no tiene IPv6 (solo loopback), así que
  la conexión directa falla con "Network unreachable".
  Comprobado: `getent hosts` devuelve solo la dirección IPv6, y dentro del
  contenedor `ip -6 route` está vacío.

SOLUCIÓN: usar el Connection Pooler de Supabase (Supavisor), que tiene
direcciones IPv4. Formato:
    host: aws-0-<region>.pooler.supabase.com
    puerto: 5432 (session mode) o 6543 (transaction mode)
    usuario: postgres.<project-ref>    <- OJO: lleva el ref pegado

Este script PRUEBA cada región hasta encontrar la correcta.
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

REF = "zucgrcyzofelmiorvxhb"
PWD = _leer_password_supabase()

REGIONES = ["us-east-1", "us-west-1", "us-east-2", "us-west-2",
            "ca-central-1", "eu-central-1", "eu-west-1", "eu-west-2",
            "eu-west-3", "ap-southeast-1", "ap-southeast-2",
            "ap-northeast-1", "ap-northeast-2", "sa-east-1",
            "ap-south-1", "eu-north-1"]


def probar(host, puerto, usuario, timeout=20):
    """Devuelve (ok, mensaje)."""
    args = [DOCKER, "exec",
            "-e", f"PGPASSWORD={PWD}",
            "-e", "PGSSLMODE=require",
            "-e", f"PGCONNECT_TIMEOUT={timeout}",
            "barberia-postgres",
            "psql", "-h", host, "-p", str(puerto), "-U", usuario,
            "-d", "postgres", "-t", "-A", "-c", "SELECT 1;"]
    try:
        p = subprocess.run(args, capture_output=True, text=True,
                           encoding="utf-8", errors="replace",
                           timeout=timeout + 15)
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT"
    out = (p.stdout or "").strip()
    err = (p.stderr or "").strip()
    if out == "1":
        return True, "1"
    return False, err[:100]


def main():
    print("=" * 72)
    print("BUSCANDO LA REGION DEL POOLER DE SUPABASE")
    print("=" * 72)
    print(f"  ref del proyecto: {REF}")
    print(f"  usuario del pooler: postgres.{REF}")
    print()

    encontrada = None
    for pref in ("aws-0", "aws-1"):
        for reg in REGIONES:
            host = f"{pref}-{reg}.pooler.supabase.com"
            ok, msg = probar(host, 5432, f"postgres.{REF}")
            if ok:
                print(f"  OK  {host}  (puerto 5432, session mode)")
                encontrada = (host, 5432)
                break
            elif "password" in msg.lower() or "authentication" in msg.lower():
                # Llegó al servidor pero la contraseña/usuario falla
                print(f"  ~~  {host}  responde pero auth falla: {msg[:70]}")
            # Los fallos de red o host inexistente se ignoran
        if encontrada:
            break

    if not encontrada:
        print()
        print("  No encontré la región por el puerto 5432.")
        print("  Probando el puerto 6543 (transaction mode)...")
        for pref in ("aws-0", "aws-1"):
            for reg in REGIONES:
                host = f"{pref}-{reg}.pooler.supabase.com"
                ok, msg = probar(host, 6543, f"postgres.{REF}")
                if ok:
                    print(f"  OK  {host}  (puerto 6543, transaction mode)")
                    encontrada = (host, 6543)
                    break
            if encontrada:
                break

    if not encontrada:
        print()
        print("  FALLO: no pude conectar por ninguna región ni puerto.")
        print("  Posibles causas:")
        print("   - la contraseña es incorrecta")
        print("   - el proyecto está en pausa (el plan gratis lo hace)")
        print("   - el pooler requiere otra combinación de usuario")
        return 1

    host, puerto = encontrada
    print()
    print("=" * 72)
    print("CONECTADO — DATOS DEL SERVIDOR")
    print("=" * 72)

    def q(sql):
        args = [DOCKER, "exec", "-e", f"PGPASSWORD={PWD}",
                "-e", "PGSSLMODE=require", "barberia-postgres",
                "psql", "-h", host, "-p", str(puerto),
                "-U", f"postgres.{REF}", "-d", "postgres",
                "-t", "-A", "-F", " | ", "-c", sql]
        p = subprocess.run(args, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=60)
        return (p.stdout or "").strip(), (p.stderr or "").strip()

    out, _ = q("SELECT current_user, current_database();")
    print(f"  usuario/base: {out}")
    out, _ = q("SELECT substring(version() from 1 for 60);")
    print(f"  version: {out}")

    print()
    print("=== extensiones disponibles que nos interesan ===")
    for ext in ("btree_gist", "unaccent", "pg_trgm", "vector", "pgcrypto"):
        out, _ = q(f"SELECT count(*) FROM pg_available_extensions "
                   f"WHERE name = '{ext}';")
        print(f"  {ext:<14} {'SI' if out == '1' else 'no'}")

    print()
    print("=== tablas existentes en public ===")
    out, _ = q("SELECT count(*) FROM information_schema.tables "
               "WHERE table_schema = 'public';")
    print(f"  total: {out}")

    print()
    print("=== puedo crear tablas? ===")
    out, err = q("CREATE TABLE _prueba_permiso (x int); "
                 "DROP TABLE _prueba_permiso; SELECT 'puedo crear' AS r;")
    print(f"  {out or err[:120]}")

    # Guardar los datos de conexión para los demás scripts
    with open(r"G:\Barberia\archivos\.supabase-conn.txt", "w",
              encoding="utf-8") as f:
        f.write(f"{host}\n{puerto}\npostgres.{REF}\n")
    print()
    print(f"  guardado en archivos\\.supabase-conn.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
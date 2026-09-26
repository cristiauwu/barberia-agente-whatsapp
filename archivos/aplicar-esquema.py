#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""aplicar-esquema.py - aplica y verifica el esquema Postgres de la barberia.

QUE HACE
  1. Lee las credenciales (POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB) de
     G:\\Barberia\\.env  (o de las variables de entorno si el .env no las trae).
  2. Copia el SQL dentro del contenedor barberia-postgres y lo ejecuta con psql
     usando ON_ERROR_STOP=1.
  3. Verifica: lista las tablas barber_* creadas y el numero de filas de cada
     una, y confirma la fila del operador dueno.
  4. Imprime un resumen en espanol en cada fase y muestra los errores crudos.

DEPENDENCIAS
  Solo libreria estandar (os, sys, re, argparse, subprocess, pathlib).
  NO usa psycopg: se habla con Postgres a traves de `docker exec ... psql`.
  Por eso el script debe correr en un host con acceso al Docker Desktop.

IDEMPOTENTE
  El SQL usa CREATE ... IF NOT EXISTS y ON CONFLICT DO NOTHING, asi que correr
  este script varias veces no rompe nada ni duplica datos.

SEGURIDAD
  La contrasena nunca se imprime ni se escribe en disco: se inyecta al
  contenedor por variable de entorno del proceso `docker exec`. Queda visible
  unos instantes en la lista de procesos del host (limitacion conocida de
  `docker exec -e`).

CODIGOS DE SALIDA
  0 = esquema aplicado y verificado.   1 = algo fallo (ver mensaje).

USO
  python archivos\\aplicar-esquema.py
  python archivos\\aplicar-esquema.py --help
"""

import argparse
import os
import re
import subprocess
import sys

# ------------------------------------------------------------------ constantes
BASE = r"G:\Barberia"
ENV_POR_DEFECTO = os.path.join(BASE, ".env")
SQL_POR_DEFECTO = os.path.join(BASE, "archivos", "esquema-postgres.sql")
DOCKER_POR_DEFECTO = (
    r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
)
DOCKER_CONFIG_POR_DEFECTO = os.path.join(BASE, ".docker")
CONTENEDOR = "barberia-postgres"
RUTA_REMOTA_SQL = "/tmp/_barber_esquema.sql"
TIMEOUT = 180

PATRON_TABLAS = r"barber\_%"

TABLAS_ESPERADAS = [
    "barber_clientes",
    "barber_citas",
    "barber_escalaciones",
    "barber_operadores",
    "barber_bloqueos",
    "barber_lista_espera",
    "barber_auditoria",
    "barber_consentimiento",
]

errores = []


# ------------------------------------------------------------------- impresion
def titulo(texto):
    print("\n" + "=" * 70)
    print(texto)
    print("=" * 70)


def bien(texto):
    print("  [OK]    " + texto)


def ojo(texto):
    print("  [AVISO] " + texto)


def fallo(texto):
    errores.append(texto)
    print("  [FALLO] " + texto)


# ------------------------------------------------------------ lectura del .env
def leer_env(ruta):
    """Lee un .env tipo CLAVE=VALOR. Devuelve (diccionario, problema)."""
    datos = {}
    if not os.path.isfile(ruta):
        return datos, "no existe el archivo %s" % ruta
    with open(ruta, "r", encoding="utf-8-sig", errors="replace") as fh:
        for linea in fh:
            linea = linea.strip()
            if not linea or linea.startswith("#"):
                continue
            if linea.lower().startswith("export "):
                linea = linea[7:].strip()
            if "=" not in linea:
                continue
            clave, valor = linea.split("=", 1)
            clave = clave.strip()
            valor = valor.strip()
            if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in ("'", '"'):
                valor = valor[1:-1]
            datos[clave] = valor
    return datos, None


# ---------------------------------------------------------------- capa docker
class Docker:
    """Envoltorio minimo sobre docker.exe con su DOCKER_CONFIG correcto."""

    def __init__(self, ejecutable, config):
        self.ejecutable = ejecutable
        self.entorno = dict(os.environ)
        self.entorno["DOCKER_CONFIG"] = config

    def correr(self, argumentos):
        """Devuelve (codigo, salida, errout) o (None, None, mensaje_de_error)."""
        comando = [self.ejecutable] + argumentos
        try:
            proc = subprocess.run(
                comando,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=TIMEOUT,
                env=self.entorno,
            )
        except FileNotFoundError:
            return None, None, "no se encontro el ejecutable: %s" % self.ejecutable
        except subprocess.TimeoutExpired:
            return None, None, "timeout de %ss ejecutando docker" % TIMEOUT
        except OSError as exc:
            return None, None, "no se pudo ejecutar docker: %s" % exc
        salida = (proc.stdout or b"").decode("utf-8", "replace")
        errout = (proc.stderr or b"").decode("utf-8", "replace")
        return proc.returncode, salida, errout

    def psql(self, usuario, base, contrasena, sql, formato_tuplas=True):
        """Ejecuta SQL dentro del contenedor. Devuelve (salida, error)."""
        argumentos = [
            "exec", "-i",
            "-e", "PGPASSWORD=" + contrasena,
            CONTENEDOR,
            "psql", "-U", usuario, "-d", base,
            "-X", "-q", "-v", "ON_ERROR_STOP=1",
        ]
        if formato_tuplas:
            argumentos += ["-t", "-A"]
        comando = [self.ejecutable] + argumentos
        try:
            proc = subprocess.run(
                comando,
                input=sql.encode("utf-8"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=TIMEOUT,
                env=self.entorno,
            )
        except subprocess.TimeoutExpired:
            return None, "timeout de %ss ejecutando psql" % TIMEOUT
        except OSError as exc:
            return None, "no se pudo ejecutar psql: %s" % exc
        salida = (proc.stdout or b"").decode("utf-8", "replace")
        errout = (proc.stderr or b"").decode("utf-8", "replace")
        if proc.returncode != 0:
            detalle = errout.strip() or salida.strip() or "(sin salida)"
            return None, "psql termino con codigo %s:\n%s" % (proc.returncode, detalle)
        return salida.strip(), None


# ------------------------------------------------------------------------ main
def main():
    analizador = argparse.ArgumentParser(
        description="Aplica y verifica el esquema Postgres de la barberia."
    )
    analizador.add_argument("--env", default=ENV_POR_DEFECTO,
                            help="ruta del .env con las credenciales")
    analizador.add_argument("--sql", default=SQL_POR_DEFECTO,
                            help="ruta del archivo .sql a aplicar")
    analizador.add_argument("--docker", default=DOCKER_POR_DEFECTO,
                            help="ruta del ejecutable docker.exe")
    analizador.add_argument("--docker-config", default=DOCKER_CONFIG_POR_DEFECTO,
                            help="carpeta que se usara como DOCKER_CONFIG")
    args = analizador.parse_args()

    print("=" * 70)
    print("APLICAR ESQUEMA POSTGRES - Barberia 'Barber Chinos'")
    print("=" * 70)
    print("  Contenedor    : %s" % CONTENEDOR)
    print("  Archivo SQL   : %s" % args.sql)
    print("  Archivo .env  : %s" % args.env)

    # ---------------------------------------------------- PASO 1: credenciales
    titulo("PASO 1/4 - Credenciales")
    datos_env, problema = leer_env(args.env)
    if problema:
        ojo(problema)
    else:
        bien("archivo .env leido (%s claves)" % len(datos_env))

    def credencial(nombre):
        valor = datos_env.get(nombre) or os.environ.get(nombre, "")
        if valor:
            bien("%s obtenido (desde %s)" % (
                nombre, ".env" if datos_env.get(nombre) else "variable de entorno"))
        else:
            fallo("falta %s en el .env y en el entorno" % nombre)
        return valor

    usuario = credencial("POSTGRES_USER")
    contrasena = credencial("POSTGRES_PASSWORD")
    base = credencial("POSTGRES_DB")

    if errores:
        titulo("RESUMEN")
        print("  No se puede continuar sin credenciales completas.")
        return 1

    # --------------------------------------------------------- PASO 2: docker
    titulo("PASO 2/4 - Docker")
    if not os.path.isfile(args.docker):
        fallo("no existe el ejecutable de Docker: %s" % args.docker)
    else:
        bien("ejecutable de Docker encontrado")
    if not os.path.isdir(args.docker_config):
        ojo("no existe la carpeta DOCKER_CONFIG %s (docker puede quejarse)" % args.docker_config)
    else:
        bien("DOCKER_CONFIG = %s" % args.docker_config)

    docker = Docker(args.docker, args.docker_config)

    if not errores:
        codigo, salida, errout = docker.correr(["version", "--format", "{{.Server.Version}}"])
        if codigo == 0 and salida.strip():
            bien("Docker responde, version de servidor: %s" % salida.strip())
        else:
            fallo("Docker no responde: %s" % (errout.strip() or salida.strip() or codigo))

    if not errores:
        codigo, salida, errout = docker.correr([
            "inspect", "-f", "{{.State.Running}}", CONTENEDOR])
        if codigo == 0 and salida.strip() == "true":
            bien("contenedor %s esta corriendo" % CONTENEDOR)
        else:
            fallo("el contenedor %s no esta corriendo (%s)"
                  % (CONTENEDOR, errout.strip() or salida.strip()))

    if errores:
        titulo("RESUMEN")
        print("  Fallo la preparacion de Docker. No se aplico nada.")
        for e in errores:
            print("   - %s" % e)
        return 1

    # --------------------------------------------------- PASO 3: aplicar SQL
    titulo("PASO 3/4 - Aplicar el esquema")
    if not os.path.isfile(args.sql):
        fallo("no existe el SQL: %s" % args.sql)
    else:
        try:
            with open(args.sql, "rb") as fh:
                crudo = fh.read()
            bien("SQL leido (%.1f KB)" % (len(crudo) / 1024.0))
        except OSError as exc:
            crudo = None
            fallo("no se pudo leer el SQL: %s" % exc)

    if crudo is not None:
        # copiar el archivo al contenedor (dentro del contenedor no hay rutas G:\)
        codigo, salida, errout = docker.correr([
            "exec", CONTENEDOR, "sh", "-c", "true"])
        if codigo != 0:
            fallo("no se pudo entrar al contenedor: %s" % (errout.strip() or salida.strip()))
        else:
            codigo, salida, errout = docker.correr([
                "cp", args.sql, "%s:%s" % (CONTENEDOR, RUTA_REMOTA_SQL)])
            if codigo != 0:
                fallo("docker cp fallo: %s" % (errout.strip() or salida.strip()))
            else:
                bien("SQL copiado a %s:%s" % (CONTENEDOR, RUTA_REMOTA_SQL))

    if crudo is not None and not errores:
        argumentos = [
            "exec", "-e", "PGPASSWORD=" + contrasena, CONTENEDOR,
            "psql", "-U", usuario, "-d", base,
            "-X", "-q", "-v", "ON_ERROR_STOP=1", "-f", RUTA_REMOTA_SQL,
        ]
        try:
            proc = subprocess.run(
                [args.docker] + argumentos,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=TIMEOUT,
                env=docker.entorno,
            )
            salida = (proc.stdout or b"").decode("utf-8", "replace")
            errout = (proc.stderr or b"").decode("utf-8", "replace")
        except (OSError, subprocess.TimeoutExpired) as exc:
            proc, salida, errout = None, "", str(exc)
        if proc is not None and proc.returncode == 0:
            bien("psql aplico el esquema sin errores")
            for linea in (salida + errout).splitlines():
                if linea.strip():
                    print("        | %s" % linea.strip())
        else:
            codigo = proc.returncode if proc is not None else "?"
            fallo("psql termino con codigo %s" % codigo)
            for linea in (errout + salida).splitlines():
                if linea.strip():
                    print("        | %s" % linea.strip())

    # ------------------------------------------------------ PASO 4: verificar
    titulo("PASO 4/4 - Verificacion")
    tablas = []
    if not errores:
        consulta = (
            "SELECT tablename FROM pg_tables "
            "WHERE schemaname = current_schema() "
            "AND tablename LIKE '%s' "
            "ORDER BY tablename;" % PATRON_TABLAS
        )
        salida, error = docker.psql(usuario, base, contrasena, consulta)
        if error:
            fallo("no se pudieron listar las tablas: %s" % error)
        else:
            tablas = [t.strip() for t in salida.splitlines() if t.strip()]

    if not errores:
        print("  Tablas barber_* encontradas: %d de %d esperadas"
              % (len(tablas), len(TABLAS_ESPERADAS)))
        for t in tablas:
            print("    - %s" % t)
        faltan = [t for t in TABLAS_ESPERADAS if t not in tablas]
        extra = [t for t in tablas if t not in TABLAS_ESPERADAS]
        if faltan:
            fallo("faltan tablas: %s" % ", ".join(faltan))
        else:
            bien("estan las 8 tablas esperadas")
        if extra:
            ojo("tablas barber_* adicionales: %s" % ", ".join(extra))

    if tablas:
        partes = [
            "SELECT '%s'::text AS tabla, count(*) AS filas FROM %s" % (t, t)
            for t in tablas
        ]
        consulta = " UNION ALL ".join(partes) + " ORDER BY tabla;"
        salida, error = docker.psql(usuario, base, contrasena, consulta)
        if error:
            fallo("no se pudieron contar las filas: %s" % error)
        else:
            print("\n  Filas por tabla:")
            print("    %-26s %8s" % ("TABLA", "FILAS"))
            print("    " + "-" * 35)
            for linea in salida.splitlines():
                if "|" not in linea:
                    continue
                nombre, filas = linea.split("|", 1)
                print("    %-26s %8s" % (nombre.strip(), filas.strip()))

    total_operadores = None
    if not errores:
        consulta = (
            "SELECT jid || ' | ' || coalesce(nombre, '') || ' | ' || "
            "coalesce(rol, '') || ' | ' || coalesce(activo::text, '') "
            "FROM barber_operadores ORDER BY jid;"
        )
        salida, error = docker.psql(usuario, base, contrasena, consulta)
        if error:
            fallo("no se pudo leer barber_operadores: %s" % error)
        else:
            filas = [l for l in salida.splitlines() if l.strip()]
            total_operadores = len(filas)
            print("\n  Operadores registrados (%d):" % total_operadores)
            for fila in filas:
                print("    - %s" % fila)
            if "5215520894522@s.whatsapp.net" in salida:
                bien("el operador dueno 5215520894522@s.whatsapp.net existe")
            else:
                fallo("no aparece el operador dueno 5215520894522@s.whatsapp.net")

    # ------------------------------------------------------------ resumen
    titulo("RESUMEN")
    print("  Usuario Postgres : %s" % usuario)
    print("  Base de datos    : %s" % base)
    print("  Tablas barber_*  : %d" % len(tablas))
    if total_operadores is not None:
        print("  Operadores       : %d" % total_operadores)

    if errores:
        print("\n  RESULTADO: FALLO")
        for e in errores:
            print("   - %s" % e)
        print("\n  Codigo de salida: 1")
        return 1

    print("\n  RESULTADO: OK - esquema aplicado y verificado.")
    print("  El esquema es idempotente: puedes volver a correr este script sin riesgo.")
    print("\n  Codigo de salida: 0")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.exit(main())
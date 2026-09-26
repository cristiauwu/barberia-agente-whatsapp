"""Helper de acceso a Postgres/n8n para el modulo de reportes.

Se apoya en subprocess.run(capture_output=True) porque en este Windows lanzar
procesos directamente desde PowerShell puede devolver salida vacia.
"""
import os
import subprocess
import sys

DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
CONTAINER = "barberia-postgres"
N8N = "http://localhost:5678"
N8N_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJzdWIiOiJjYmQ1ZGQ2Yi05NzJlLTRlZmYtYWVlNC03MTAzOWJmM2E5MDIiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiYmZkZmNiNDQtZmRiMi00MDUwLTg3MWMtMGJkMDI5NGRiOTYwIiwiaWF0IjoxNzkwMjk4ODczfQ."
    "s04weO8S72yEn6ip2rCGE4wCt-wPw22xVWJij-lF4wc"
)


def _env():
    env = dict(os.environ)
    env["DOCKER_CONFIG"] = r"G:\Barberia\.docker"
    return env


def docker(*args, timeout=120):
    """Ejecuta docker y devuelve (rc, stdout, stderr)."""
    p = subprocess.run(
        [DOCKER, *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        env=_env(), timeout=timeout,
    )
    return p.returncode, p.stdout or "", p.stderr or ""


def psql(sql, timeout=120):
    """Ejecuta SQL con psql -c.

    ojo: psql NO sustituye variables :'x' con -c; para plantillas usar
    psql_file().
    """
    return docker("exec", CONTAINER, "psql", "-U", "barberia", "-d", "barberia",
                  "-t", "-A", "-F", "|", "-v", "ON_ERROR_STOP=1", "-c", sql,
                  timeout=timeout)


def psql_file(local_path, remote_name, extra_vars=None, timeout=180):
    """Copia un .sql al contenedor y lo ejecuta con psql -f.

    extra_vars: dict de variables psql -> valor (se pasan con -v).
    """
    rc, out, err = docker("cp", local_path, f"{CONTAINER}:/tmp/{remote_name}")
    if rc != 0:
        return rc, out, f"docker cp fallo: {err}"
    args = ["exec", CONTAINER, "psql", "-U", "barberia", "-d", "barberia",
            "-t", "-A", "-F", "|", "-v", "ON_ERROR_STOP=1"]
    for k, v in (extra_vars or {}).items():
        args += ["-v", f"{k}={v}"]
    args += ["-f", f"/tmp/{remote_name}"]
    rc, out, err = docker(*args, timeout=timeout)
    docker("exec", CONTAINER, "rm", "-f", f"/tmp/{remote_name}")
    return rc, out, err


def psql_script(local_path, remote_name="script.sql", extra_vars=None):
    return psql_file(local_path, remote_name, extra_vars)


def query(sql):
    """Devuelve filas (lista de listas) de un SELECT; lanza si hay error."""
    rc, out, err = psql(sql)
    if rc != 0:
        raise RuntimeError(f"SQL fallo rc={rc}\nSTDERR: {err}\nSQL: {sql}")
    return [line.split("|") for line in out.splitlines() if line.strip()]


def query1(sql):
    rows = query(sql)
    return rows[0] if rows else []


def scalar(sql):
    r = query1(sql)
    if not r:
        return None
    v = r[0]
    return None if v == "" else v


if __name__ == "__main__":
    rc, out, err = psql("SELECT version();")
    print("rc", rc)
    print(out)
    print("ERR", err)
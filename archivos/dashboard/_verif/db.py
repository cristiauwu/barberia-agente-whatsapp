#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Helper de verificacion: ejecuta SQL en barberia-postgres y devuelve CSV por seccion."""
from __future__ import annotations
import csv
import io
import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(r"G:\Barberia")
ENV_FILE = RAIZ / ".env"
DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
CONTENEDOR = "barberia-postgres"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def leer_env():
    cfg = {}
    for linea in ENV_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        k, v = linea.split("=", 1)
        cfg[k.strip()] = v.strip()
    return cfg


def consultar(sql: str) -> dict:
    cfg = leer_env()
    env = dict(os.environ)
    env["DOCKER_CONFIG"] = str(RAIZ / ".docker")
    env["PGPASSWORD"] = cfg.get("POSTGRES_PASSWORD", "")
    usuario = cfg.get("POSTGRES_USER", "barberia")
    basedatos = cfg.get("POSTGRES_DB", "barberia")

    cmd = [DOCKER, "exec", "-i", "-e", "PGPASSWORD", CONTENEDOR,
           "psql", "-U", usuario, "-d", basedatos,
           "-v", "ON_ERROR_STOP=1", "-q", "--csv", "-f", "-"]
    res = subprocess.run(cmd, input=sql.encode("utf-8"),
                         capture_output=True, env=env, timeout=300)
    texto = res.stdout.decode("utf-8", "replace")
    error = res.stderr.decode("utf-8", "replace").strip()
    secciones: dict = {}
    actual = None
    buffer: list = []
    for linea in texto.splitlines():
        if linea.startswith("===@@") and linea.rstrip().endswith("@@==="):
            if actual is not None:
                secciones[actual] = _parsear(buffer)
            actual = linea.rstrip()[5:-5]
            buffer = []
        elif actual is not None:
            buffer.append(linea)
    if actual is not None:
        secciones[actual] = _parsear(buffer)
    secciones["_rc"] = res.returncode
    secciones["_err"] = error
    return secciones


def _parsear(lineas):
    limpias = [l for l in lineas if l.strip() != ""]
    if not limpias:
        return []
    return [dict(f) for f in csv.DictReader(io.StringIO("\n".join(limpias)))]


def ejecutar(sql: str):
    """Ejecuta SQL sin esperar secciones. Devuelve (rc, stdout, stderr)."""
    cfg = leer_env()
    env = dict(os.environ)
    env["DOCKER_CONFIG"] = str(RAIZ / ".docker")
    env["PGPASSWORD"] = cfg.get("POSTGRES_PASSWORD", "")
    cmd = [DOCKER, "exec", "-i", "-e", "PGPASSWORD", CONTENEDOR,
           "psql", "-U", cfg.get("POSTGRES_USER", "barberia"),
           "-d", cfg.get("POSTGRES_DB", "barberia"),
           "-v", "ON_ERROR_STOP=1", "-q", "-f", "-"]
    res = subprocess.run(cmd, input=sql.encode("utf-8"),
                         capture_output=True, env=env, timeout=600)
    return (res.returncode,
            res.stdout.decode("utf-8", "replace"),
            res.stderr.decode("utf-8", "replace"))
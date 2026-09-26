#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueba los CHECK en transacciones INDEPENDIENTES capturando stderr.

Leccion: psql manda los ERRORES a stderr, no a stdout. Mi comprobacion
anterior leia stdout y por eso reportaba "MAL" aunque los CHECK si
rechazaban. Aqui cada prueba va en su propia transaccion con ROLLBACK,
asi ninguna contamina las tablas.
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

# (etiqueta, SQL valido?, SQL a probar)
CASOS = [
    ("estado invalido en citas", False,
     "INSERT INTO barber_citas (id,jid,estado) VALUES ('t1','t2','inventado');"),
    ("etiqueta invalida", False,
     "INSERT INTO barber_clientes (jid,etiqueta) VALUES ('t3','basura');"),
    ("rol invalido", False,
     "INSERT INTO barber_operadores (jid,rol) VALUES ('t4','superadmin');"),
    ("motivo invalido en escalaciones", False,
     "INSERT INTO barber_escalaciones (jid,motivo) VALUES ('t5','loquesea');"),
    ("visitas negativas", False,
     "INSERT INTO barber_clientes (jid,visitas) VALUES ('t6',-5);"),
    ("fin antes de inicio", False,
     "INSERT INTO barber_bloqueos (inicio,fin) VALUES (now(), now() - interval '1 hour');"),
    # estos SI deben entrar (con el cliente creado antes por la FK)
    ("estado valido 'agendado'", True,
     "INSERT INTO barber_clientes (jid) VALUES ('ok2'); "
     "INSERT INTO barber_citas (id,jid,estado) VALUES ('ok1','ok2','agendado');"),
    ("etiqueta valida 'vip'", True,
     "INSERT INTO barber_clientes (jid,etiqueta) VALUES ('ok3','vip');"),
    ("estado NULL permitido", True,
     "INSERT INTO barber_clientes (jid) VALUES ('ok5'); "
     "INSERT INTO barber_citas (id,jid,estado) VALUES ('ok4','ok5',NULL);"),
    # la FK debe impedir una cita de un cliente inexistente
    ("cita de cliente inexistente (FK)", False,
     "INSERT INTO barber_citas (id,jid,estado) "
     "VALUES ('x1','no-existe','agendado');"),
]


def psql(sql):
    """Devuelve (stdout, stderr). Los errores van a stderr."""
    p = subprocess.run([DOCKER, "exec", "barberia-postgres", "psql", "-U",
                        "barberia", "-d", "barberia", "-v",
                        "ON_ERROR_STOP=1", "-c",
                        f"BEGIN; {sql} ROLLBACK;"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return (p.stdout or ""), (p.stderr or "")


def main():
    print("=" * 74)
    print("PRUEBA DE LOS CHECK (cada caso en su transaccion con ROLLBACK)")
    print("=" * 74)
    fallos = 0
    for etiqueta, debe_entrar, sql in CASOS:
        out, err = psql(sql)
        hubo_error = "ERROR" in err
        # Si debia entrar y hubo error -> fallo. Si debia fallar y no hubo
        # error -> fallo.
        correcto = (not hubo_error) if debe_entrar else hubo_error
        if not correcto:
            fallos += 1
        marca = "OK  " if correcto else "MAL "
        accion = "ACEPTA" if not hubo_error else "RECHAZA"
        print(f"  {marca}{accion:<8} {etiqueta}")
        if hubo_error:
            primera = [l for l in err.splitlines() if "ERROR" in l]
            if primera:
                print(f"           {primera[0][:110]}")

    print()
    print("=" * 74)
    print("LAS TABLAS QUEDARON LIMPIAS? (nada de lo anterior debe persistir)")
    print("=" * 74)
    for t in ("barber_clientes", "barber_citas", "barber_operadores",
              "barber_bloqueos", "barber_escalaciones"):
        out, _ = subprocess.run(
            [DOCKER, "exec", "barberia-postgres", "psql", "-U", "barberia",
             "-d", "barberia", "-t", "-A", "-c",
             f"SELECT count(*) FROM {t};"],
            capture_output=True, text=True, encoding="utf-8").stdout, None
        n = out.strip()
        esperado = "1" if t == "barber_operadores" else "0"
        print(f"  {'OK  ' if n == esperado else 'MAL '} {t}: {n} filas "
              f"(esperado {esperado})")
        if n != esperado:
            fallos += 1

    print()
    print("=" * 74)
    print(f"RESULTADO: {'TODO OK' if fallos == 0 else str(fallos) + ' FALLOS'}")
    print("=" * 74)
    return 0 if fallos == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
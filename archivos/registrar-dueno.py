#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Registra al dueño con SU numero real, aceptando los dos formatos de Mexico.

El usuario dio 524521206246 (52 + 10 digitos). Pero WhatsApp en Mexico ha
usado historicamente DOS formatos para el mismo numero:

  - 52 + 10 digitos      -> 524521206246
  - 52 + 1 + 10 digitos  -> 5214521206246

No se puede saber de antemano cual reportara Evolution en remoteJid, asi
que se registran AMBOS como operadores validos. Si solo se registrara uno,
el dueño podria quedar fuera del router de comandos sin explicacion.

Se marca cual es el "canonico" (el que se usa como destino de los avisos).
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

SUF = "@s.whatsapp.net"
NUM = "524521206246"            # lo que dio el usuario
VARIANTE = "52" + "1" + NUM[2:]  # 5214521206246

CANONICO = NUM + SUF            # destino de los avisos
ALIAS = VARIANTE + SUF          # por si Evolution reporta el otro formato


def psql(sql):
    p = subprocess.run([DOCKER, "exec", "barberia-postgres", "psql", "-U",
                        "barberia", "-d", "barberia", "-t", "-A", "-c", sql],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return (p.stdout or "").strip(), (p.stderr or "").strip()


def main():
    print("=" * 70)
    print("REGISTRO DEL DUEÑO")
    print("=" * 70)
    print(f"  numero dado      : {NUM}")
    print(f"  canonico (avisos): {CANONICO}")
    print(f"  alias (variante) : {ALIAS}")
    print()

    # Quitar el operador anterior (el heredado del flujo del vendedor)
    out, err = psql("DELETE FROM barber_operadores WHERE jid NOT IN "
                    f"('{CANONICO}','{ALIAS}');")
    print(f"  limpieza: {out or err}")

    # Insertar ambos formatos
    for jid, nota in ((CANONICO, "formato 52+10"),
                      (ALIAS, "formato 52+1+10 (legacy)")):
        sql = ("INSERT INTO barber_operadores (jid, nombre, rol, activo) "
               f"VALUES ('{jid}', 'Dueno', 'dueno', true) "
               "ON CONFLICT (jid) DO UPDATE SET activo = true, "
               "nombre = 'Dueno', rol = 'dueno';")
        out, err = psql(sql)
        print(f"  {nota:<26} {jid}")
        if err:
            print(f"     ERROR: {err[:120]}")

    print()
    print("=" * 70)
    print("OPERADORES REGISTRADOS")
    print("=" * 70)
    out, _ = psql("SELECT jid || ' | ' || nombre || ' | ' || rol || "
                  "' | activo=' || activo::text FROM barber_operadores "
                  "ORDER BY jid;")
    print(out)

    print()
    print("=" * 70)
    print("VERIFICACION")
    print("=" * 70)
    n, _ = psql("SELECT count(*) FROM barber_operadores WHERE activo;")
    print(f"  operadores activos: {n}")
    for jid in (CANONICO, ALIAS):
        c, _ = psql(f"SELECT count(*) FROM barber_operadores "
                    f"WHERE jid='{jid}' AND activo;")
        print(f"  {'OK  ' if c == '1' else 'MAL '} {jid}")
    viejo = "5215520894522" + SUF
    c, _ = psql(f"SELECT count(*) FROM barber_operadores WHERE jid='{viejo}';")
    print(f"  {'OK  ' if c == '0' else 'AVISO'} el numero viejo del vendedor "
          f"{'fue eliminado' if c == '0' else 'SIGUE PRESENTE'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Saca dos archivos del repo y republica con historial limpio.

Los dos que sobran:
  - `archivos/publicar-limpio.py`: es la herramienta de publicacion, lleva
    la lista de claves dentro a proposito. No debe estar en el repo.
  - `archivos/.supabase-pass.txt`: tiene la password de Supabase.

Borrarlos del disco NO basta: el indice los conserva. Hay que rehacer el
indice entero (`git rm -r --cached .`) para que el .gitignore aplique.
"""
import os
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RAIZ = r"G:\Barberia"
GIT = r"C:\Program Files\Git\cmd\git.exe"
GCM = r"C:\Program Files\Git\mingw64\bin\git-credential-manager.exe"

CLAVES = ["DC64CCC7469D-4E50", "iWbaegXpWBjJ7PGs", "Chinos452@@",
          "vTcYIYR7h7n357m9dohntQ", "lXrbroKwpGHTqqCYoMpb3w"]

# No pueden estar en el repo
FUERA = {"archivos/publicar-limpio.py", "archivos/.supabase-pass.txt",
         "archivos/.supabase-conn.txt", ".env", ".env.evolution"}

# Archivos que llevan la lista de claves a proposito (no se publican)
MANTENIMIENTO = {"archivos/limpieza-git-final.py", "limpieza-final.py",
                 "archivos/github-limpiar-secretos.py",
                 "archivos/github-subir2.py", "archivos/github-verificar-repo.py",
                 "archivos/republicar.py", "archivos/verificar-repo-final.py",
                 "archivos/publicar-limpio.py", "archivos/limpiar11.py",
                 "archivos/quitar2.py"}


def git(args, extra_env=None):
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    if extra_env:
        env.update(extra_env)
    return subprocess.run([GIT] + args, cwd=RAIZ, env=env,
                          capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=900)


def tok_gcm():
    p = subprocess.run([GCM, "--no-ui", "get"],
                       input="protocol=https\nhost=github.com\n\n",
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=60)
    u = t = None
    for l in (p.stdout or "").splitlines():
        if l.startswith("username="):
            u = l.split("=", 1)[1]
        elif l.startswith("password="):
            t = l.split("=", 1)[1]
    return u, t


def main():
    usuario, tok = tok_gcm()
    if not tok:
        print("no hay token")
        return 1

    print("=" * 66)
    print("SACAR LOS DOS ARCHIVOS Y REPUBLICAR")
    print("=" * 66)

    git(["checkout", "--orphan", "final"])
    git(["rm", "-r", "--cached", "--quiet", "."])
    git(["add", "-A"])

    p = git(["ls-files"])
    indice = [l.strip() for l in (p.stdout or "").splitlines() if l.strip()]
    print(f"  archivos: {len(indice)}")

    # comprobaciones
    fallos = []
    for f in indice:
        rel = f.replace("\\", "/")
        if rel in FUERA:
            fallos.append((rel, "no debe estar en el repo"))
            continue
        if rel in MANTENIMIENTO:
            fallos.append((rel, "script de mantenimiento"))
            continue
        ruta = os.path.join(RAIZ, f)
        if not os.path.exists(ruta):
            continue
        try:
            if os.path.getsize(ruta) > 4_000_000:
                continue
            txt = open(ruta, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        for c in CLAVES:
            if c in txt:
                fallos.append((rel, f"contiene {c[:14]}..."))
                break

    if fallos:
        print("  MAL:")
        for f, m in fallos[:12]:
            print(f"    {f}  ->  {m}")
        return 1
    print("  OK  sin claves y sin archivos que sobren")

    total = sum(os.path.getsize(os.path.join(RAIZ, f)) for f in indice
                if os.path.exists(os.path.join(RAIZ, f)))
    print(f"  peso: {total/1024/1024:.1f} MB")

    p = git(["commit", "-m",
             "Sistema completo de citas por WhatsApp para barberia\n\n"
             "n8n + Evolution API + Google Calendar/Sheets + Postgres.\n\n"
             "- 12 comandos del dueno por WhatsApp (sin coste de tokens)\n"
             "- Panel visual para el barbero (sin dependencias externas)\n"
             "- Recordatorios automaticos a 24h y 1h\n"
             "- Restriccion anti-doble-reserva en la base de datos\n"
             "- 187 comprobaciones automatizadas\n\n"
             "Sin credenciales: se leen de variables de entorno."])
    print(f"  commit: {p.returncode}")

    git(["branch", "-M", "final", "main"])
    env = {"GIT_CONFIG_COUNT": "1",
           "GIT_CONFIG_KEY_0":
               f"url.https://{usuario}:{tok}@github.com/.insteadOf",
           "GIT_CONFIG_VALUE_0": "https://github.com/"}
    p = git(["push", "origin", "main", "--force"], extra_env=env)
    print(f"  push --force: {p.returncode}")
    for l in ((p.stdout or "") + (p.stderr or "")).splitlines()[:5]:
        print("  " + l.replace(tok, "***")[:140])
    if p.returncode == 0:
        print(f"\n  LISTO: https://github.com/{usuario}/barberia-agente-whatsapp")
    return 0 if p.returncode == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
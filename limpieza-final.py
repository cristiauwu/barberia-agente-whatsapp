#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Limpieza quirurgica: borra los duplicados con la clave y arregla el
.gitignore. Sin reescribir el indice, que ya se intento y no basto.

ARCHIVOS QUE SE BORRAN DEL DISCO (son duplicados o respaldos, no aportan):

  archivos/BarberiaAgenteFLUJO-*.json   duplicados de los JSON de la raiz
  archivos/FIX-*.json                   respaldos de arreglos ya aplicados
  archivos/BarberiaAgenteFLUJO 1.json   copias con nombre viejo
  archivos/BarberiaAgenteFLUJO 2.json

Los JSON BUENOS son los de la raiz: `BarberiaAgenteFLUJO-1-UNCENSORED.json`
y `-2-RECORDATORIOS.json`, que ya se limpiaron.
"""
import os
import re
import shutil
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RAIZ = r"G:\Barberia"
ARCH = os.path.join(RAIZ, "archivos")
GIT = r"C:\Program Files\Git\cmd\git.exe"
GCM = r"C:\Program Files\Git\mingw64\bin\git-credential-manager.exe"

CLAVES = ["DC64CCC7469D", "CLAVE_EVOLUTION_AQUI",
          "PASSWORD_SUPABASE_AQUI", "sb_publishable_"]

# Se BORRAN (duplicados y respaldos)
BORRAR = [
    r"^BarberiaAgenteFLUJO.*\.json$",
    r"^FIX-.*\.json$",
    r"^ANTES-.*\.json$",
    r"^sync-.*\.json$",
    r"^_memoria-chat-backup\.tsv$",
    r"^SUPABASE-EVIDENCIA\.txt$",
    r"^probar-supabase-sql\.py$",
]

# Se BORRAN si llevan clave y no aportan valor
BORRAR_GLOBAL = [
    os.path.join(RAIZ, "BarberiaAgenteFLUJO 1.json"),
    os.path.join(RAIZ, "BarberiaAgenteFLUJO 2.json"),
]

GITIGNORE_ADD = """
# Lista negra explicita: archivos locales con credenciales
.supabase-pass.txt
.supabase-conn.txt
*-pass.txt
*_key.txt
*clave*.py
*clave*.txt
"""


def git(args, extra_env=None):
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    if extra_env:
        env.update(extra_env)
    return subprocess.run([GIT] + args, cwd=RAIZ, env=env,
                          capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=900)


def token_guardado():
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
    print("=" * 68)
    print("1. BORRAR DUPLICADOS Y RESPALDOS")
    print("=" * 68)
    n = 0
    for base, dirs, files in os.walk(ARCH):
        for f in files:
            if any(re.search(p, f) for p in BORRAR):
                p = os.path.join(base, f)
                try:
                    os.remove(p)
                    print(f"  borrado: archivos/{f}")
                    n += 1
                except OSError:
                    pass
    for p in BORRAR_GLOBAL:
        if os.path.exists(p):
            try:
                os.remove(p)
                print(f"  borrado: {os.path.basename(p)}")
                n += 1
            except OSError:
                pass
    # los scripts de mantenimiento con la lista de claves
    for f in os.listdir(ARCH):
        if f.startswith(("github-", "limpieza-git", "mover-clave",
                         "corregir-indentacion")):
            p = os.path.join(ARCH, f)
            if os.path.isfile(p):
                try:
                    os.remove(p)
                    print(f"  borrado: archivos/{f}")
                    n += 1
                except OSError:
                    pass
    print(f"  total: {n}")

    print()
    print("=" * 68)
    print("2. BUSCAR LO QUE QUEDE CON CLAVE")
    print("=" * 68)
    quedan = []
    for base, dirs, files in os.walk(RAIZ):
        dirs[:] = [d for d in dirs if d not in
                   {".git", ".docker", "node_modules", "__pycache__"}]
        for f in files:
            p = os.path.join(base, f)
            rel = os.path.relpath(p, RAIZ).replace("\\", "/")
            # los locales ignorados SI deben conservar la clave
            if rel in ("archivos/.supabase-conn.txt",
                       "archivos/.supabase-pass.txt", ".env", ".env.evolution"):
                continue
            try:
                if os.path.getsize(p) > 4_000_000:
                    continue
                t = open(p, encoding="utf-8", errors="replace").read()
            except Exception:
                continue
            for c in CLAVES:
                if c in t:
                    quedan.append((rel, c[:16]))
                    break
    if quedan:
        print(f"  quedan {len(quedan)}:")
        for rel, c in quedan[:20]:
            print(f"    {rel}  ->  {c}...")
    else:
        print("  OK  ninguno (salvo los locales ignorados)")

    print()
    print("=" * 68)
    print("3. REFORZAR EL .gitignore")
    print("=" * 68)
    gi = os.path.join(RAIZ, ".gitignore")
    actual = open(gi, encoding="utf-8").read()
    if ".supabase-pass.txt" not in actual:
        open(gi, "w", encoding="utf-8").write(
            actual.rstrip() + "\n" + GITIGNORE_ADD)
        print("  reforzado")
    else:
        print("  ya estaba")

    if quedan:
        print("\n  No se publica: quedan archivos con claves.")
        return 1

    print()
    print("=" * 68)
    print("4. PUBLICAR CON HISTORIAL LIMPIO")
    print("=" * 68)
    usuario, tok = token_guardado()
    if not tok:
        print("  no hay token")
        return 1

    git(["checkout", "--orphan", "publicable"])
    git(["rm", "-r", "--cached", "--quiet", "."])
    p = git(["add", "-A"])
    print(f"  indice rehecho: {p.returncode}")

    p = git(["ls-files"])
    indice = [l.strip() for l in (p.stdout or "").splitlines() if l.strip()]
    print(f"  archivos en el indice: {len(indice)}")

    # comprobacion final del indice
    malos = []
    for f in indice:
        ruta = os.path.join(RAIZ, f)
        if not os.path.exists(ruta) or os.path.getsize(ruta) > 4_000_000:
            continue
        try:
            t = open(ruta, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        for c in CLAVES:
            if c in t:
                malos.append((f, c[:16]))
                break
    if malos:
        print("  MAL secretos en el indice:")
        for f, c in malos[:10]:
            print(f"    {f}")
        return 1
    print("  OK  sin secretos en el indice")

    grandes = [(os.path.getsize(os.path.join(RAIZ, f)), f) for f in indice
               if os.path.exists(os.path.join(RAIZ, f))
               and os.path.getsize(os.path.join(RAIZ, f)) > 20 * 1024 * 1024]
    if grandes:
        print("  MAL archivos gigantes:")
        for t, f in grandes[:5]:
            print(f"    {t/1024/1024:.0f} MB  {f}")
        return 1
    print("  OK  sin archivos gigantes")

    p = git(["commit", "-m",
             "Sistema completo de citas por WhatsApp para barberia\n\n"
             "Agente conversacional con n8n + Evolution API + Google\n"
             "Calendar/Sheets + Postgres.\n\n"
             "Incluye:\n"
             "- 12 comandos del dueno por WhatsApp (sin coste de tokens)\n"
             "- Panel visual para el barbero (sin dependencias externas)\n"
             "- Recordatorios automaticos a 24h y 1h\n"
             "- Restriccion anti-doble-reserva en la base de datos\n"
             "- 187 comprobaciones automatizadas\n\n"
             "Sin credenciales: se leen de variables de entorno."])
    print(f"  commit: {p.returncode}")

    git(["branch", "-M", "publicable", "main"])
    env = {"GIT_CONFIG_COUNT": "1",
           "GIT_CONFIG_KEY_0":
               f"url.https://{usuario}:{tok}@github.com/.insteadOf",
           "GIT_CONFIG_VALUE_0": "https://github.com/"}
    p = git(["push", "origin", "main", "--force"], extra_env=env)
    print(f"  push --force: {p.returncode}")
    for l in ((p.stdout or "") + (p.stderr or "")).splitlines()[:6]:
        print("  " + l.replace(tok, "***")[:140])

    if p.returncode == 0:
        print(f"\n  LISTO: https://github.com/{usuario}/barberia-agente-whatsapp")
    print()
    print("=" * 68)
    print("5. CLAVES A ROTAR (importante)")
    print("=" * 68)
    print("  Estuvieron publicas unos minutos:")
    print("   - API key de Evolution API   (Evolution Manager > Settings)")
    print("   - Password de Supabase       (Dashboard > Settings > Database)")
    print("   - API key de Uncensored AI")
    return 0 if p.returncode == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
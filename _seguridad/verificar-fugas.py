#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verifica las DOS FUGAS CRITICAS que reporta la auditoria.

Son las mas graves de todo el proyecto porque son brechas EN CURSO, no
riesgos teoricos. Se comprueban de forma independiente y anonima: sin
credenciales, como lo haria cualquiera que encuentre el repositorio.

  CR-01: la clave de administracion de n8n esta publicada en GitHub.
  CR-02: la hoja de Google con los telefonos de los clientes es publica.

Si alguna es cierta hay que actuar YA, no documentarlo y seguir.
"""
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

REPO = "cristiauwu/barberia-agente-whatsapp"
HOJA = "1lvSVFWU2ApvK7p5BsFHI68Icur46P6hI8o8r9ozhBfk"

# Los archivos que la auditoria dice que tienen la clave publicada
SOSPECHOSOS = ["_audit_dump.py", "_audit_final.py", "_inspeccion.py",
               "_inspeccion2.py", "_audit_pg_report.txt"]

# La clave REAL, para poder comparar (se lee, no se escribe)
CLAVE_REAL = open(r"G:\Barberia\archivos\.n8n-key.txt",
                  encoding="utf-8").read().strip()


def bajar(url, timeout=25):
    """Descarga SIN credenciales: como lo haria un atacante."""
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace"), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, "", {}
    except Exception as e:
        return None, str(e), {}


fallos = []

print("=" * 72)
print("CR-01: ¿ESTA LA CLAVE DE ADMINISTRACION DE n8n EN GITHUB?")
print("=" * 72)
print(f"  repositorio: https://github.com/{REPO}")
print()

try:
    p = subprocess.run(
        [r"C:\Program Files\Git\cmd\git.exe", "ls-files"],
        cwd=r"G:\Barberia", capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=60)
    rastreados = [l.strip() for l in (p.stdout or "").splitlines() if l.strip()]
except Exception as e:
    rastreados = []
    print(f"  no pude listar los archivos rastreados: {e}")

encontrados = []
for f in SOSPECHOSOS:
    # ¿esta rastreado por git en el repo local?
    p = subprocess.run(
        [r"C:\Program Files\Git\cmd\git.exe", "log", "--all", "--oneline",
         "--", f], cwd=r"G:\Barberia", capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=60)
    commits = [l for l in (p.stdout or "").splitlines() if l.strip()]
    if commits:
        encontrados.append((f, len(commits)))

print("  archivos con la clave, segun la auditoria:")
if encontrados:
    for f, n in encontrados:
        print(f"    GIT LO TIENE: {f}  ({n} commit(s))")
else:
    print("    ninguno aparece en el historial de git local")

# lo definitivo: pedirlo a GitHub en crudo, sin credenciales
print()
print("  --- comprobacion definitiva: descargarlo de GitHub sin credenciales ---")
descargado = False
for f in SOSPECHOSOS:
    for rama in ("main", "master"):
        url = f"https://raw.githubusercontent.com/{REPO}/{rama}/{f}"
        st, cuerpo, _ = bajar(url)
        if st == 200 and cuerpo:
            descargado = True
            tiene = CLAVE_REAL in cuerpo
            print(f"    HTTP 200  {f} ({len(cuerpo)} bytes)")
            print(f"      ¿contiene la clave REAL de n8n? "
                  f"{'SI  <<< BRECHA CONSUMADA' if tiene else 'no'}")
            if tiene:
                fallos.append(f"CR-01: la clave de n8n esta publica en {f}")
            break
if not descargado:
    print("    no pude descargar ninguno (404 o red)")

print()
print("=" * 72)
print("CR-02: ¿ES PUBLICA LA HOJA CON LOS TELEFONOS DE LOS CLIENTES?")
print("=" * 72)

ENDPOINTS = [
    ("CSV exportado", f"https://docs.google.com/spreadsheets/d/{HOJA}/export?format=csv"),
    ("gviz (JSON)", f"https://docs.google.com/spreadsheets/d/{HOJA}/gviz/tq?tqx=out:csv"),
    ("htmlview", f"https://docs.google.com/spreadsheets/d/{HOJA}/htmlview"),
    ("Texto plano", f"https://docs.google.com/spreadsheets/d/{HOJA}/export?format=txt"),
]

for nombre, url in ENDPOINTS:
    st, cuerpo, h = bajar(url)
    if st == 200 and cuerpo:
        # ¿hay datos de verdad, o solo la pantalla de "pide acceso"?
        tiene_datos = bool(re.search(r"\d{3}[\s-]?\d{3}[\s-]?\d{4}", cuerpo))
        es_login = ("ServiceLogin" in cuerpo or "accounts.google.com" in cuerpo
                    or "request access" in cuerpo.lower()
                    or "solicitar acceso" in cuerpo.lower())
        if tiene_datos and not es_login:
            print(f"  CRITICO  {nombre:16} HTTP 200 — DEVUELVE DATOS REALES "
                  f"({len(cuerpo)} bytes)")
            # mostrar una muestra enmascarada
            filas = [l for l in cuerpo.split("\n") if l.strip()]
            print(f"           filas: {len(filas)}")
            if len(filas) > 1:
                cab = filas[0][:100]
                print(f"           cabecera: {cab}")
                # enmascarar el telefono de la primera fila real
                muestra = filas[1][:120]
                muestra = re.sub(r"\d{10,}", "**********", muestra)
                print(f"           primera fila: {muestra}")
            fallos.append(f"CR-02: la hoja es publica ({nombre})")
        elif es_login:
            print(f"  OK       {nombre:16} HTTP {st} — pide iniciar sesion")
        else:
            print(f"  --       {nombre:16} HTTP {st} ({len(cuerpo)} bytes, "
                  f"sin datos reconocibles)")
    else:
        print(f"  OK       {nombre:16} HTTP {st or 'error'} — sin acceso")

print()
print("=" * 72)
print("RESUMEN")
print("=" * 72)
if fallos:
    print("  FUGAS CONFIRMADAS:")
    for f in fallos:
        print(f"    - {f}")
    print()
    print("  Hay que actuar AHORA, no documentarlo.")
else:
    print("  No pude confirmar ninguna de las dos fugas.")
    print("  (Puede ser que ya se hayan cerrado, o que mi acceso no sea")
    print("   suficiente para comprobarlo.)")
print("=" * 72)
sys.exit(1 if fallos else 0)
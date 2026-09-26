#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
probar-conocimiento.py
======================
Prueba la busqueda de FAQs del bot de barberia contra PostgreSQL.

Que hace:
  1. Comprueba que la tabla y la funcion existen.
  2. Lanza 18 preguntas de cliente (redactadas como las escribe la gente real,
     con faltas de ortografia, sin acentos, con relleno) y verifica que la
     funcion devuelve la FAQ esperada como PRIMER resultado.
  3. Mide el tiempo de cada busqueda.
  4. Prueba casos borde (vacio, basura, pregunta inexistente).
  5. Mide el tamano real del conocimiento (para decidir si cabe en el prompt).

Uso:
    uv run python G:\\Barberia\\archivos\\probar-conocimiento.py

No necesita credenciales: habla con el contenedor `barberia-postgres` por docker exec.
"""

import subprocess
import os
import sys
import time
import io
import json

# La consola de Windows suele venir en cp1252 y revienta con acentos y emojis.
# Se fuerza UTF-8 en stdout/stderr para que el script nunca muera al imprimir.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DOCKER = r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe"
CONTAINER = "barberia-postgres"
DB_USER = "barberia"
DB_NAME = "barberia"

env = dict(os.environ)
env["DOCKER_CONFIG"] = r"G:\Barberia\.docker"
env["PGCLIENTENCODING"] = "UTF8"

OUT_PATH = r"G:\Barberia\archivos\probar-conocimiento-salida.txt"
_out = io.open(OUT_PATH, "w", encoding="utf-8", newline="\n")


def say(*a):
    line = " ".join(str(x) for x in a)
    try:
        print(line)
    except UnicodeEncodeError:
        print(line.encode("ascii", "replace").decode("ascii"))
    _out.write(line + "\n")


def psql(sql):
    """Ejecuta SQL y devuelve (stdout, stderr) como texto UTF-8."""
    p = subprocess.run(
        [DOCKER, "exec", CONTAINER, "psql", "-U", DB_USER, "-d", DB_NAME,
         "-t", "-A", "-F", "\x1f", "-c", sql],
        capture_output=True, env=env, timeout=120,
    )
    return ((p.stdout or b"").decode("utf-8", "replace").strip(),
            (p.stderr or b"").decode("utf-8", "replace").strip())


def buscar(pregunta, limite=3):
    """Llama a barber_buscar_conocimiento y devuelve lista de dicts."""
    # Se usa dollar-quoting para no tener que escapar las comillas del cliente.
    sql = (
        "SELECT id, categoria, round(rank::numeric,4), pregunta, respuesta, origen "
        "FROM public.barber_buscar_conocimiento($q$" + pregunta + "$q$, " + str(limite) + ");"
    )
    out, err = psql(sql)
    filas = []
    if out:
        for linea in out.splitlines():
            partes = linea.split("\x1f")
            if len(partes) < 6:
                continue
            filas.append({
                "id": partes[0], "categoria": partes[1], "rank": partes[2],
                "pregunta": partes[3], "respuesta": partes[4], "origen": partes[5],
            })
    return filas, err


# ---------------------------------------------------------------------------
# 1) Comprobaciones previas
# ---------------------------------------------------------------------------
say("=" * 78)
say(" PRUEBA DE LA BASE DE CONOCIMIENTO - BARBER CHINOS")
say(" Búsqueda de texto completo de PostgreSQL (config 'spanish_unaccent')")
say("=" * 78)
say("")

out, err = psql("SELECT count(*) FROM public.barber_conocimiento;")
say("[0] FAQs cargadas en la tabla:", out if out else "(VACIO) err=" + err)

out, err = psql("SELECT extname FROM pg_extension WHERE extname='unaccent';")
say("[0] Extension unaccent:", out if out else "(NO) " + err)

out, err = psql(
    "SELECT n.nspname||'.'||c.cfgname FROM pg_ts_config c "
    "JOIN pg_namespace n ON n.oid=c.cfgnamespace WHERE c.cfgname='spanish_unaccent';")
say("[0] Configuración de texto:", out if out else "(NO) " + err)

out, err = psql("SELECT count(*) FROM pg_indexes WHERE indexname='barber_conocimiento_tsv_gin';")
say("[0] Índice GIN presente:", out if out else "(NO) " + err)
say("")

# ---------------------------------------------------------------------------
# 2) Tamano del conocimiento (para la decision prompt vs RAG)
# ---------------------------------------------------------------------------
out, err = psql("SELECT pg_size_pretty(pg_total_relation_size('public.barber_conocimiento'));")
say("[0] Tamaño en disco de la tabla:", out, "(incluye el índice GIN)")
out, err = psql("SELECT sum(length(pregunta)) , sum(length(respuesta)) FROM public.barber_conocimiento;")
say("[0] Caracteres pregunta|respuesta:", out)
out, err = psql("SELECT count(*) FROM public.barber_conocimiento WHERE origen='propuesta';")
say("[0] Respuestas marcadas como 'propuesta' (a confirmar por el dueño):", out)
say("")

# ---------------------------------------------------------------------------
# 3) Bateria principal: 18 preguntas reales
#    `esperado` = fragmento de la pregunta de la FAQ que debe salir PRIMERA.
# ---------------------------------------------------------------------------
CASOS = [
    ("Tienen estacionamiento?",                      "estacionamiento"),
    ("hay donde dejar el carro?",                    "estacionamiento"),
    ("Donde estan ubicados?",                        "ubicados"),
    ("cual es la direccion?",                        "ubicados"),
    ("Cual es el telefono?",                         "teléfono"),
    ("Hasta que hora abren?",                        "horario"),
    ("abren el domingo?",                            "domingo"),
    ("hasta que hora puedo agendar?",                "hasta qué hora puedo agendar"),
    ("cuanto cuesta el corte?",                      "cuesta el corte"),
    ("precio del corte de dama",                     "corte de dama"),
    ("cuanto cuesta la barba?",                      "cuesta la barba"),
    ("cuanto sale la ceja",                          "cuesta la ceja"),
    ("que servicios tienen?",                        "servicios tienen"),
    ("puedo cancelar mi cita?",                      "cancelar mi cita"),
    ("quiero mover mi cita a otro dia",              "cambiar mi cita"),
    ("necesito cita para la ceja?",                  "cita para la ceja"),
    ("quien me va a atender?",                       "va a atender"),
    ("hacen tinte de cabello?",                      "tintes"),
    ("me pueden dar la lista de precios completa?",  "lista de precios"),
    ("cuanto cuesta la depilacion?",                 "depilación"),
    ("tienen un mod cut?",                           "mod cut"),
]

say("-" * 78)
say(" BATERÍA PRINCIPAL — 21 preguntas de cliente")
say("-" * 78)
say("")

aciertos = 0
fallos = []
tiempos = []

for i, (pregunta, esperado) in enumerate(CASOS, 1):
    t0 = time.perf_counter()
    filas, err = buscar(pregunta)
    dt = (time.perf_counter() - t0) * 1000.0
    tiempos.append(dt)

    if not filas:
        say(f"{i:2d}. [SIN RESULTADO] {pregunta!r}  ({dt:.0f} ms)")
        if err:
            say(f"      stderr: {err[:200]}")
        fallos.append((pregunta, esperado, None))
        continue

    top = filas[0]
    ok = esperado.lower() in top["pregunta"].lower()
    if ok:
        aciertos += 1
        marca = "OK  "
    else:
        marca = "FALLO"
        fallos.append((pregunta, esperado, top["pregunta"]))

    say(f"{i:2d}. [{marca}] {pregunta!r}")
    say(f"      -> {top['pregunta']}   [{top['categoria']}] rank={top['rank']} ({dt:.0f} ms)")
    if len(filas) > 1:
        say(f"      alternativas: " + " | ".join(f["pregunta"] for f in filas[1:]))
    say("")

say("-" * 78)
say(f" RESULTADO: {aciertos}/{len(CASOS)} aciertos en el primer lugar")
if fallos:
    say(" Fallos:")
    for p, e, got in fallos:
        say(f"   - pregunta: {p!r}  esperaba ~{e!r}  obtuve: {got!r}")
say(f" Tiempo de búsqueda: mín {min(tiempos):.0f} ms | máx {max(tiempos):.0f} ms "
    f"| media {sum(tiempos)/len(tiempos):.0f} ms")
say("-" * 78)
say("")

# ---------------------------------------------------------------------------
# 4) Casos borde: no deben reventar ni inventar
# ---------------------------------------------------------------------------
say("-" * 78)
say(" CASOS BORDE (no deben fallar ni inventar)")
say("-" * 78)
say("")

BORDE = ["", "   ", "zzzz qqqq", "?", "a e i o u", "12345", "😀😀😀", "jdksl fjdksl"]
for p in BORDE:
    filas, err = buscar(p)
    estado = "vacío (correcto)" if not filas else f"{len(filas)} resultado(s)"
    err_txt = (" | stderr: " + err[:120]) if err else ""
    say(f"  consulta={p!r:18s} -> {estado}{err_txt}")

say("")
say("  Nota: una consulta sin palabras útiles devuelve 0 filas SIN error.")
say("        El bot debe caer a 'Notificar al encargado', no inventar.")
say("")

# ---------------------------------------------------------------------------
# 5) Cuantas FAQs caben en el prompt (para comparar opciones)
# ---------------------------------------------------------------------------
say("-" * 78)
say(" TAMAÑO DEL CONOCIMIENTO (comparación prompt vs búsqueda)")
say("-" * 78)
say("")
out, err = psql(
    "SELECT count(*), "
    "sum(length(pregunta) + length(respuesta) + 12) "
    "FROM public.barber_conocimiento WHERE activo;")
say("  FAQs activas y caracteres que ocuparían volcadas al prompt:", out)
out, err = psql(
    "SELECT count(*) FROM public.barber_conocimiento c "
    "WHERE c.tsv @@ to_tsquery('public.spanish_unaccent','estacionamiento');")
say("  FAQs que contienen 'estacionamiento' (búsqueda directa):", out)
say("")

say("=" * 78)
say(" VEREDICTO:", "TODAS LAS PRUEBAS PASARON" if aciertos == len(CASOS)
    else f"{len(fallos)} prueba(s) con problema")
say("=" * 78)

_out.close()
print(f"\n[Salida guardada en {OUT_PATH}]")
sys.exit(0 if aciertos == len(CASOS) else 1)
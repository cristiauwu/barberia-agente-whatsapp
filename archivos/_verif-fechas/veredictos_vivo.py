#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verificacion con Python (referencia) de cada dia nombrado en vivo."""
import datetime
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
DIR = r"G:\Barberia\archivos\_verif-fechas"
DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado",
        "domingo"]
MESES = {m: i for i, m in enumerate(
    ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
     "agosto", "septiembre", "octubre", "noviembre", "diciembre"], 1)}

print("=" * 74)
print("REFERENCIA PYTHON (verdad del calendario)")
print("=" * 74)
for s in ("2026-09-25", "2026-09-26", "2026-09-27", "2026-09-28",
          "2026-09-29", "2026-09-30", "2026-10-01", "2026-10-02",
          "2026-10-03", "2026-10-04"):
    d = datetime.date.fromisoformat(s)
    print(f"  {s} = {DIAS[d.weekday()]}")

print()
print("=" * 74)
print("CASOS EN VIVO")
print("=" * 74)

# Verdad esperada de cada caso en vivo, con el "hoy" del momento de la prueba
CASOS = {
    "c1": ("¿Qué día cae el 27 de septiembre de 2026?",
           "domingo", "2026-09-27"),
    "c2": ("¿Qué día es el 1 de octubre de 2026?", "jueves", "2026-10-01"),
    "c3": ("Quiero un corte el viernes a las 4", "viernes 2026-10-02 o "
           "viernes 2026-09-25 (hoy)", None),
    "c4": ("¿Qué día de la semana es mañana?", "sabado", "2026-09-26"),
    "c5": ("Agéndame un corte el 30 de septiembre a las 3", "miercoles",
           "2026-09-30"),
    "c6": ("muéstrame mis próximas citas", "(varias)", None),
    "h1": ("corte 19:30 lunes 28 sep", "debe RECHAZAR", "2026-09-28"),
    "h2": ("corte 20:00 lunes 28 sep", "debe RECHAZAR", "2026-09-28"),
    "h3": ("corte 9:00 lunes 28 sep", "debe RECHAZAR", "2026-09-28"),
    "h4": ("corte domingo 27 sep 12:00", "debe decir CERRADO", "2026-09-27"),
    "h5": ("corte jueves 24 sep (pasado)", "debe RECHAZAR", "2026-09-24"),
}

# fecha/hora en que corrio cada prueba (de los .json guardados)
for cid, (texto, esperado, fecha) in CASOS.items():
    p = DIR + r"\vivo\\" + cid + ".json"
    if not os.path.exists(p):
        print(f"\n[{cid}] SIN DATOS")
        continue
    datos = json.load(open(p, encoding="utf-8"))
    print(f"\n[{cid}] {texto}")
    print(f"   esperado (Python): {esperado}")
    for r in datos:
        enviado = r.get("enviado") or r.get("respuesta") or ""
        print(f"   exec {r['id']}")
        print(f"   SALIDA LITERAL: {enviado!r}")
        print(f"   herramientas usadas: {list((r.get('herramientas') or {}).keys())}")
        # dias nombrados en la salida
        t = enviado.lower()
        for m in re.finditer(
                r"(lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo)"
                r"[ ,]+(\d{1,2})\s+de\s+([a-záéíóú]+)", t):
            dia = (m.group(1).replace("é", "e").replace("á", "a"))
            mm = MESES.get(m.group(3))
            if not mm:
                continue
            real = datetime.date(2026, mm, int(m.group(2)))
            esp = DIAS[real.weekday()]
            ver = "OK" if dia == esp else "*** MAL ***"
            print(f"     dia dicho '{m.group(0)}' -> real {real} "
                  f"{esp}  {ver}")
        # fecha numerica
        for m in re.finditer(r"(\d{2})/(\d{2})", t):
            print(f"     fecha numerica: {m.group(0)}")
        # eventos creados
        for tname in ("Agendar cita", "Registrar en hoja de citas"):
            v = (r.get("herramientas") or {}).get(tname)
            if v:
                print(f"     {tname}: {json.dumps(v, ensure_ascii=False)[:260]}")
        nl = enviado.count("\n") + 1
        sangria = [l for l in enviado.split("\n") if l.startswith("   ") and l.strip()]
        print(f"     lineas={nl} sangria3={len(sangria)} "
              f"caracteres={len(enviado)}")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRUEBA DEFINITIVA de la herramienta 'Que dia es'.

Extrae el jsCode REAL del nodo del workflow, lo ejecuta en el MISMO Node
(mismo V8) dentro del contenedor barberia-n8n (misma zona horaria), y
compara cada resultado contra la verdad calculada con datetime de Python.

Escribe resultados.json con todo.
"""
import datetime
import json
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DIR = r"G:\Barberia\archivos\_verif-fechas"
DOCKER = (r"C:\Users\kimbo\AppData\Local\Programs\DockerDesktop"
          r"\resources\bin\docker.exe")
os.environ["DOCKER_CONFIG"] = r"G:\Barberia\.docker"

DIAS_ES = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado",
           "domingo"]
MESES_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
            "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def docker(args, timeout=120):
    p = subprocess.run([DOCKER] + args, capture_output=True, text=True,
                       timeout=timeout, encoding="utf-8", errors="replace")
    return p.stdout, p.stderr


# ------------------------------------------------------------- el codigo
wf = json.load(open(DIR + r"\wf_agente.json", encoding="utf-8"))
nodo = next(n for n in wf["nodes"] if n["name"] == "Que dia es")
js = nodo["parameters"]["jsCode"]
print("jsCode extraido del nodo 'Que dia es':", len(js), "caracteres")

# ------------------------------------------------------------- referencia
def ref_desde_iso_mx(s):
    """Verdad de Python: la fecha CIVIL en Mexico del instante dado.

    's' es un ISO. Si tiene offset, se respeta (momento absoluto) y se
    convierte a -06:00. Si NO tiene offset, se interpreta como hora de
    Mexico (que es la zona del negocio).
    """
    try:
        d = datetime.datetime.fromisoformat(s)
    except ValueError:
        return None
    if d.tzinfo is None:
        return d.date().isoformat()
    return (d.astimezone(datetime.timezone(datetime.timedelta(hours=-6)))
            ).date().isoformat()


def ref_civil(y, m, d):
    try:
        return datetime.date(y, m, d).isoformat()
    except ValueError:
        return None


# ------------------------------------------------------------- los casos
# cid, entrada_js, esperado (ISO | None=error), nota
CASOS = [
    # ---- 1. los 7 dias de la semana (fecha conocida) ----
    ("1a", "'2026-09-28T12:00:00-06:00'", "2026-09-28", "lunes 28 sep 2026"),
    ("1b", "'2026-09-29T12:00:00-06:00'", "2026-09-29", "martes 29 sep 2026"),
    ("1c", "'2026-09-30T12:00:00-06:00'", "2026-09-30", "miercoles 30 sep 2026"),
    ("1d", "'2026-10-01T12:00:00-06:00'", "2026-10-01", "jueves 1 oct 2026"),
    ("1e", "'2026-10-02T12:00:00-06:00'", "2026-10-02", "viernes 2 oct 2026"),
    ("1f", "'2026-10-03T12:00:00-06:00'", "2026-10-03", "sabado 3 oct 2026"),
    ("1g", "'2026-09-27T12:00:00-06:00'", "2026-09-27", "domingo 27 sep 2026 (EL DIA DEL FALLO)"),

    # ---- 2. frontera de zona horaria: 19:00 Mexico = dia siguiente en UTC ----
    ("2a", "'2026-09-28T19:00:00-06:00'", "2026-09-28", "19:00 Mexico, offset explicito"),
    ("2b", "'2026-09-29T01:00:00Z'", "2026-09-28", "LA MISMA cita en UTC (en UTC es el 29)"),
    ("2c", "'2026-09-29T01:00:00+00:00'", "2026-09-28", "LA MISMA cita, offset +00:00"),
    ("2d", "'2026-09-29T01:00:00.000Z'", "2026-09-28", "LA MISMA cita, con milisegundos"),
    ("2e", "'2026-09-28T18:59:00-06:00'", "2026-09-28", "18:59 Mexico"),
    ("2f", "'2026-09-28T20:00:00-06:00'", "2026-09-28", "20:00 Mexico"),
    ("2g", "'2026-09-28T06:00:00Z'", "2026-09-28", "00:00 Mexico en UTC"),
    ("2h", "'2026-09-27T19:00:00-06:00'", "2026-09-27", "19:00 Mexico un DOMINGO"),
    ("2i", "'2026-09-28T01:00:00Z'", "2026-09-27", "01:00Z = 19:00 del 27 en Mexico"),

    # ---- 3. frontera de medianoche ----
    ("3a", "'2026-09-28T00:00:00-06:00'", "2026-09-28", "00:00:00 Mexico"),
    ("3b", "'2026-09-28T23:59:00-06:00'", "2026-09-28", "23:59 Mexico"),
    ("3c", "'2026-09-29T05:59:00Z'", "2026-09-28", "23:59 Mexico en UTC"),
    ("3d", "'2026-09-29T06:00:00Z'", "2026-09-29", "00:00 del 29 en Mexico"),
    ("3e", "'2026-09-29T05:59:59Z'", "2026-09-28", "23:59:59 Mexico en UTC"),

    # ---- 4. cambio de mes ----
    ("4a", "'2026-08-31T10:00:00-06:00'", "2026-08-31", "31 agosto"),
    ("4b", "'2026-09-01T10:00:00-06:00'", "2026-09-01", "1 septiembre"),
    ("4c", "'2026-08-31T23:59:00-06:00'", "2026-08-31", "31 ago 23:59 Mexico (1 sep en UTC)"),
    ("4d", "'2026-09-01T06:00:00Z'", "2026-09-01", "1 sep 00:00 Mexico"),
    ("4e", "'2026-09-30T23:00:00-06:00'", "2026-09-30", "30 sep 23:00 Mexico (1 oct en UTC)"),
    ("4f", "'2026-10-01T05:00:00Z'", "2026-09-30", "la misma, en UTC"),

    # ---- 5. cambio de anio ----
    ("5a", "'2026-12-31T22:00:00-06:00'", "2026-12-31", "31 dic 22:00"),
    ("5b", "'2027-01-01T04:00:00Z'", "2026-12-31", "la misma en UTC (1 ene 2027)"),
    ("5c", "'2027-01-01T00:30:00-06:00'", "2027-01-01", "1 ene 2027 00:30"),
    ("5d", "'2026-12-31T23:59:00-06:00'", "2026-12-31", "31 dic 23:59 Mexico"),

    # ---- 6. 29 de febrero ----
    ("6a", "'2028-02-29T12:00:00-06:00'", "2028-02-29", "29 feb 2028"),
    ("6b", "'2028-02-29T18:00:00Z'", "2028-02-29", "29 feb 2028 en UTC"),
    ("6c", "'2028-02-28T23:00:00-06:00'", "2028-02-28", "28 feb 2028 (vispera)"),
    ("6d", "'2028-03-01T02:00:00-06:00'", "2028-03-01", "1 mar 2028"),

    # ---- 7. ISO con offset explicito y sin offset ----
    ("7a", "'2026-09-27T15:00:00-06:00'", "2026-09-27", "ISO con offset -06:00"),
    ("7b", "'2026-09-27T15:00:00'", "2026-09-27", "ISO SIN offset, 15:00"),
    ("7c", "'2026-09-27T23:00:00'", "2026-09-27", "ISO SIN offset, 23:00"),
    ("7d", "'2026-09-27T00:30:00'", "2026-09-27", "ISO SIN offset, 00:30"),
    ("7e", "'2026-09-27T15:00:00.000-06:00'", "2026-09-27", "ISO con milisegundos"),
    ("7f", "'2026-09-27'", "2026-09-27", "SOLO FECHA (evento de dia completo de Google Calendar)"),

    # ---- 8. texto en espanol ----
    ("8a", "'27 de septiembre de 2026'", "2026-09-27", "texto largo"),
    ("8b", "'27 septiembre'", None, "sin anio"),
    ("8c", "'27/09/2026'", "2026-09-27", "dd/mm/aaaa"),
    ("8d", "'27 de septiembre'", "2026-09-27", "sin anio, con mes"),
    ("8e", "'domingo 27 de septiembre de 2026'", "2026-09-27", "con el dia delante"),
    ("8f", "'27 de sep de 2026'", "2026-09-27", "mes abreviado"),
    ("8g", "'septiembre 27 de 2026'", "2026-09-27", "mes delante"),
    ("8h", "'27/12/2026'", "2026-12-27", "dd/mm con mes 12"),
    ("8i", "'05/01/2027'", "2027-01-05", "dd/mm con dia 05"),
    ("8j", "'1 de octubre de 2026'", "2026-10-01", "texto sin cero a la izquierda"),

    # ---- 9. entradas basura: DEBE devolver error ----
    ("9a", "''", None, "cadena vacia"),
    ("9b", "'hola'", None, "texto sin fecha"),
    ("9c", "'32/13/2026'", None, "dia 32, mes 13"),
    ("9d", "null", None, "null"),
    ("9e", "undefined", None, "undefined"),
    ("9f", "'   '", None, "solo espacios"),
    ("9g", "'2026-13-01'", None, "mes 13 en ISO"),
    ("9h", "'9999-99-99'", None, "ISO imposible"),
    ("9i", "'2026'", None, "solo el anio"),
    ("9j", "20260927", None, "numero, no texto"),
]

# ------------------------------------------------------------- ejecutar
out = json.dumps([{"id": c[0], "entrada": c[1], "esperado": c[2],
                   "nota": c[3]} for c in CASOS], ensure_ascii=False)

prelude = r"""
'use strict';
const CASOS = %s;
const INFO = {node: process.version,
              tz: Intl.DateTimeFormat().resolvedOptions().timeZone,
              offset: new Date().getTimezoneOffset(),
              ahora: new Date().toISOString()};
function herramienta(query) {
%s
}
const res = [];
for (const c of CASOS) {
  let entrada; try { entrada = eval(c.entrada); } catch(e) { entrada = '__EVALERR__'; }
  let salida; try { salida = herramienta(entrada); } catch(e) { salida = '__THROW__: ' + e.message; }
  res.push({id:c.id, entrada_js:c.entrada, entrada_repr:JSON.stringify(entrada),
            esperado:c.esperado, nota:c.nota, salida:salida});
}
console.log(JSON.stringify({info:INFO, res:res}));
""" % (out, js)

open(DIR + r"\harness_final.js", "w", encoding="utf-8").write(prelude)

so, se = docker(["cp", DIR + r"\harness_final.js", "barberia-n8n:/tmp/hf.js"])
so, se = docker(["exec", "barberia-n8n", "node", "/tmp/hf.js"])
if not so.strip():
    print("FALLO al ejecutar:", se)
    sys.exit(1)
datos = json.loads(so)
info = datos["info"]
print("Node:", info["node"], "| TZ del contenedor:", info["tz"],
      "| offset(min):", info["offset"])
print("Ahora (UTC) del contenedor:", info["ahora"])
print()

# ------------------------------------------------------------- evaluar
DIAS_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
           "Saturday", "Sunday"]
resultados = []
for r in datos["res"]:
    salida = r["salida"]
    es_error = salida.startswith("Error:")
    # dia que devolvio la herramienta (si devolvio una fecha)
    dia_salida = None
    for tok in ("lunes", "martes", "miercoles", "jueves", "viernes",
                "sabado", "domingo"):
        if salida.startswith(tok):
            dia_salida = tok
            break
    fecha_salida = None
    if "(" in salida and salida.rstrip().endswith(")"):
        fecha_salida = salida.rstrip()[:-1].rsplit("(", 1)[-1]
    # verdad con Python
    esperado = r["esperado"]
    if esperado:
        d = datetime.date.fromisoformat(esperado)
        dia_esperado = DIAS_ES[d.weekday()]
        fecha_esperada = esperado
    else:
        dia_esperado = None
        fecha_esperada = None
    if esperado and not es_error:
        ok = (fecha_salida == esperado and dia_salida == dia_esperado)
    elif esperado is None:
        ok = es_error
    else:
        ok = False
    r2 = dict(r, es_error=es_error, dia_salida=dia_salida,
              fecha_salida=fecha_salida, dia_esperado=dia_esperado,
              fecha_esperada=fecha_esperada, ok=ok)
    resultados.append(r2)
    est = "OK " if ok else "MAL"
    print(f"[{est}] {r['id']:>3} {r['entrada_js'][:42]:<42} "
          f"-> {salida[:58]}")
    if not ok:
        print(f"          esperado: {esperado or 'ERROR legible'} "
              f"({dia_esperado or '-'})")

total = len(resultados)
pasan = sum(1 for r in resultados if r["ok"])
print()
print("=" * 70)
print(f"TOTAL {total} casos | aciertos {pasan} | fallos {total-pasan} "
      f"| {100.0*pasan/total:.1f}%")
print("=" * 70)

json.dump({"info": info, "resultados": resultados,
           "total": total, "pasan": pasan},
          open(DIR + r"\resultados.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("guardado:", DIR + r"\resultados.json")
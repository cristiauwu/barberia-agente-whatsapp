#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genera el arnes de pruebas en Node para la herramienta 'Que dia es'.

Extrae el jsCode REAL del nodo del workflow, lo envuelve en una funcion y
lo ejecuta contra una lista de casos. Escribe el resultado a JSON.
"""
import json, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DIR = r"G:\Barberia\archivos\_verif-fechas"
wf = json.load(open(DIR + r"\wf_agente.json", encoding="utf-8"))
nodo = next(n for n in wf["nodes"] if n["name"] == "Que dia es")
js = nodo["parameters"]["jsCode"]

# ------------------------------------------------------------------ casos
# (id, entrada_js, esperado_dia_ISO | None si se espera error, nota)
CASOS = [
    # --- 1. los 7 dias de la semana ---
    ("7d-lunes",     "'2026-09-28'", "2026-09-28", "lunes"),
    ("7d-martes",    "'2026-09-29'", "2026-09-29", "martes"),
    ("7d-miercoles", "'2026-09-30'", "2026-09-30", "miercoles"),
    ("7d-jueves",    "'2026-10-01'", "2026-10-01", "jueves"),
    ("7d-viernes",   "'2026-10-02'", "2026-10-02", "viernes"),
    ("7d-sabado",    "'2026-10-03'", "2026-10-03", "sabado"),
    ("7d-domingo",   "'2026-09-27'", "2026-09-27", "domingo (el dia del fallo)"),

    # --- 2. frontera de zona horaria: 19:00 Mexico = dia siguiente en UTC ---
    ("tz-1900-mx-offset", "'2026-09-28T19:00:00-06:00'", "2026-09-28",
     "19:00 Mexico con offset explicito"),
    ("tz-1900-mx-z",      "'2026-09-29T01:00:00Z'",      "2026-09-28",
     "la MISMA cita en UTC (ya es dia 29 en UTC)"),
    ("tz-1900-mx-utc-off", "'2026-09-29T01:00:00+00:00'", "2026-09-28",
     "la MISMA cita en UTC con offset +00:00"),
    ("tz-1859-mx",        "'2026-09-28T18:59:00-06:00'", "2026-09-28", "18:59 Mexico"),
    ("tz-2000-mx",        "'2026-09-28T20:00:00-06:00'", "2026-09-28", "20:00 Mexico"),
    ("tz-0000-utc",       "'2026-09-28T06:00:00Z'",      "2026-09-28",
     "00:00 Mexico expresado en UTC"),

    # --- 3. frontera de medianoche ---
    ("mid-0000-mx",  "'2026-09-28T00:00:00-06:00'", "2026-09-28", "00:00:00 Mexico"),
    ("mid-0001-mx",  "'2026-09-28T00:01:00-06:00'", "2026-09-28", "00:01 Mexico"),
    ("mid-2359-mx",  "'2026-09-28T23:59:00-06:00'", "2026-09-28", "23:59 Mexico"),
    ("mid-2359utc",  "'2026-09-29T05:59:00Z'",      "2026-09-28",
     "23:59 Mexico expresado en UTC"),
    ("mid-0000utc",  "'2026-09-29T06:00:00Z'",      "2026-09-29",
     "00:00 del dia 29 en Mexico (en UTC ya es dia 29 tambien)"),

    # --- 4. cambio de mes ---
    ("mes-31ago",  "'2026-08-31T10:00:00-06:00'", "2026-08-31", "31 de agosto"),
    ("mes-01sep",  "'2026-09-01T10:00:00-06:00'", "2026-09-01", "1 de septiembre"),
    ("mes-31ago-2359", "'2026-08-31T23:59:00-06:00'", "2026-08-31",
     "31 ago 23:59 Mexico (1 sep en UTC)"),
    ("mes-01sep-0000utc", "'2026-09-01T06:00:00Z'", "2026-09-01",
     "1 sep 00:00 Mexico"),

    # --- 5. cambio de anio ---
    ("anio-31dic",  "'2026-12-31T22:00:00-06:00'", "2026-12-31", "31 dic 2026 22:00"),
    ("anio-31dic-utc", "'2027-01-01T04:00:00Z'",  "2026-12-31",
     "la misma, en UTC ya es 1 ene 2027"),
    ("anio-01ene",  "'2027-01-01T00:30:00-06:00'", "2027-01-01", "1 ene 2027 00:30"),

    # --- 6. 29 de febrero ---
    ("bisiesto-2028", "'2028-02-29T12:00:00-06:00'", "2028-02-29",
     "29 feb 2028 (bisiesto)"),
    ("bisiesto-2028-utc", "'2028-02-29T18:00:00Z'", "2028-02-29",
     "29 feb 2028 mediodia Mexico en UTC"),

    # --- 7. ISO con y sin offset ---
    ("iso-con-offset",   "'2026-09-27T15:00:00-06:00'", "2026-09-27", "ISO con offset"),
    ("iso-sin-offset",   "'2026-09-27T15:00:00'",       "2026-09-27",
     "ISO sin offset (se interpreta en la zona del proceso)"),
    ("iso-sin-offset-noche", "'2026-09-27T23:00:00'",   "2026-09-27",
     "ISO sin offset a las 23:00"),
    ("iso-solo-fecha",   "'2026-09-27'",                "2026-09-27", "solo YYYY-MM-DD"),

    # --- 8. texto en espanol ---
    ("txt-completo",  "'27 de septiembre de 2026'", "2026-09-27", "texto largo"),
    ("txt-corto",     "'27 septiembre'", None, "sin anio: comportamiento a documentar"),
    ("txt-barras",    "'27/09/2026'",   None, "formato con barras"),
    ("txt-acentos",   "'27 de septiembre'", None, "sin anio, con mes"),
    ("txt-domingo",   "'domingo 27 de septiembre de 2026'", None,
     "texto con dia de la semana delante"),

    # --- 9. basura: DEBE devolver error, no un dia inventado ---
    ("bas-vacio",    "''",         None, "cadena vacia"),
    ("bas-hola",     "'hola'",     None, "texto sin fecha"),
    ("bas-3213",     "'32/13/2026'", None, "dia y mes fuera de rango"),
    ("bas-null",     "null",       None, "null"),
    ("bas-undefined","undefined",  None, "undefined"),
    ("bas-9999",     "'9999-99-99'", None, "fecha imposible ISO"),
    ("bas-solo-num", "'12345'",    None, "solo digitos"),
]

out = {
    "js": js,
    "casos": [{"id": c[0], "entrada": c[1], "esperado": c[2], "nota": c[3]}
              for c in CASOS],
}
with open(DIR + r"\casos.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

# ---- generar el .js que se ejecutara en Node ----
prelude = """
'use strict';
const CASOS = %s;
const TZINFO = Intl.DateTimeFormat().resolvedOptions().timeZone;
const OFFSET = new Date().getTimezoneOffset();
const NODE = process.version;

function herramienta(query) {
%s
}

const res = [];
for (const c of CASOS) {
  let entrada;
  try { entrada = eval(c.entrada); } catch (e) { entrada = '__EVALERR__'; }
  let salida;
  try {
    salida = herramienta(entrada);
  } catch (e) {
    salida = '__THROW__: ' + e.message;
  }
  res.push({id: c.id, entrada_js: c.entrada, entrada_repr: JSON.stringify(entrada),
            esperado: c.esperado, nota: c.nota, salida: salida});
}
console.log(JSON.stringify({node: NODE, tz: TZINFO, offset: OFFSET, res: res},
                           null, 1));
""" % (json.dumps([{"id": c[0], "entrada": c[1], "esperado": c[2], "nota": c[3]}
                  for c in CASOS], ensure_ascii=False), js)

with open(DIR + r"\harness.js", "w", encoding="utf-8") as f:
    f.write(prelude)

print("arnes escrito:", DIR + r"\harness.js", len(prelude), "bytes")
print("casos:", len(CASOS))
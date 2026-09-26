#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Segunda ronda: casos extra + sondeo del parser de fechas de V8."""
import json, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DIR = r"G:\Barberia\archivos\_verif-fechas"
wf = json.load(open(DIR + r"\wf_agente.json", encoding="utf-8"))
js = next(n for n in wf["nodes"] if n["name"] == "Que dia es")["parameters"]["jsCode"]

CASOS = [
    ("x-vers-ms",        "'2026-09-27T15:00:00.000-06:00'", "2026-09-27", "ISO con milisegundos"),
    ("x-sin-pad",        "'2026-9-28'",   "2026-09-28", "fecha sin cero a la izquierda"),
    ("x-barras-dic",     "'27/12/2026'",  "2026-12-27", "27/12/2026 (mes explicito)"),
    ("x-barras-ene",     "'05/01/2027'",  "2027-01-05", "05/01/2027"),
    ("x-mes-antes",      "'septiembre 27 de 2026'", "2026-09-27", "mes delante"),
    ("x-abrev",          "'27 de sep de 2026'", "2026-09-27", "mes abreviado con 'de'"),
    ("x-all-day",        "'2026-09-27'",  "2026-09-27", "evento de dia completo de Google Calendar"),
    ("x-txt-sin-anio",   "'27 de septiembre'", "2026-09-27", "texto sin anio (anio actual)"),
    ("x-gc-full",        "'2026-09-27T09:00:00-06:00'", "2026-09-27", "cita manana de domingo"),
    ("x-finde",          "'2026-10-04T11:00:00-06:00'", "2026-10-04", "domingo 4 oct"),
    ("x-garbage-space",  "'   '", None, "solo espacios"),
    ("x-garbage-abc",    "'2026'", None, "solo anio"),
    ("x-garbage-iso-mal","'2026-13-01'", None, "mes 13 ISO"),
    ("x-num",            "20260927", None, "numero, no texto"),
]

out = json.dumps([{"id": c[0], "entrada": c[1], "esperado": c[2], "nota": c[3]}
                  for c in CASOS], ensure_ascii=False)

prelude = """
'use strict';
const CASOS = %s;
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
// ---- sondeo del parser de fechas de V8 (no pasa por la herramienta) ----
const crudo = {};
for (const s of ['2026-09-28','27 septiembre','12345','2026','2032',
                 '32/13/2026','9999-99-99','2026-9-28','27/12/2026',
                 'septiembre 27 de 2026','2026-13-01','hola']) {
  const d = new Date(s);
  crudo[s] = isNaN(d.getTime()) ? 'INVALID' : d.toISOString();
}
console.log(JSON.stringify({res:res, crudo:crudo}, null, 1));
""" % (out, js)

open(DIR + r"\harness2.js", "w", encoding="utf-8").write(prelude)
print("escrito harness2.js casos:", len(CASOS))
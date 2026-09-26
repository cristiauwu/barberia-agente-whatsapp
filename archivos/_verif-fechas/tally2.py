#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TALLY DEFINITIVO — usa resultados_n8n.json, que es la ejecucion del
jsCode REAL dentro del runtime de n8n (TZ=UTC), que es el que usa el agente.

Cada caso se compara contra la verdad calculada con datetime de Python.
"""
import datetime
import json
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
DIR = r"G:\Barberia\archivos\_verif-fechas"
d = json.load(open(DIR + r"\resultados_n8n.json", encoding="utf-8"))
print("TZ del runtime de n8n:", d["tz"], "| offset(min):", d["offset"])
res = d["res"]

DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado",
        "domingo"]
MESES = {m: i for i, m in enumerate(
    ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
     "agosto", "septiembre", "octubre", "noviembre", "diciembre"], 1)}
MX = datetime.timezone(datetime.timedelta(hours=-6))

# esperado: (fecha ISO civil esperada | None=error, motivo)
EXP = {
    # 1. los 7 dias
    "1a": ("2026-09-28", ""), "1b": ("2026-09-29", ""),
    "1c": ("2026-09-30", ""), "1d": ("2026-10-01", ""),
    "1e": ("2026-10-02", ""), "1f": ("2026-10-03", ""),
    "1g": ("2026-09-27", "el dia del fallo original"),
    # 2. frontera de zona horaria (19:00 Mexico)
    "2a": ("2026-09-28", "19:00 Mexico con offset"),
    "2b": ("2026-09-28", "misma cita en Z (en UTC ya es 29)"),
    "2c": ("2026-09-28", "misma cita con +00:00"),
    "2d": ("2026-09-28", "misma cita con milisegundos y Z"),
    "2e": ("2026-09-28", "18:59 Mexico"), "2f": ("2026-09-28", "20:00 Mexico"),
    "2g": ("2026-09-28", "00:00 Mexico en UTC"),
    "2h": ("2026-09-27", "19:00 Mexico un domingo"),
    "2i": ("2026-09-27", "01:00Z = 19:00 del 27 en Mexico"),
    # 3. medianoche
    "3a": ("2026-09-28", "00:00:00 Mexico"),
    "3b": ("2026-09-28", "23:59 Mexico"),
    "3c": ("2026-09-28", "23:59 Mexico en UTC"),
    "3d": ("2026-09-29", "00:00 del 29 en Mexico"),
    "3e": ("2026-09-28", "23:59:59 Mexico en UTC"),
    # 4. cambio de mes
    "4a": ("2026-08-31", ""), "4b": ("2026-09-01", ""),
    "4c": ("2026-08-31", "31 ago 23:59 Mexico"),
    "4d": ("2026-09-01", "1 sep 00:00 Mexico"),
    "4e": ("2026-09-30", "30 sep 23:00 Mexico"),
    "4f": ("2026-09-30", "la misma en UTC"),
    # 5. cambio de anio
    "5a": ("2026-12-31", ""), "5b": ("2026-12-31", "la misma en UTC"),
    "5c": ("2027-01-01", ""), "5d": ("2026-12-31", ""),
    # 6. 29 de febrero
    "6a": ("2028-02-29", ""), "6b": ("2028-02-29", ""),
    "6c": ("2028-02-28", ""), "6d": ("2028-03-01", ""),
    # 7. ISO con y sin offset
    "7a": ("2026-09-27", "ISO con offset -06:00"),
    "7b": ("2026-09-27", "ISO SIN offset a las 15:00"),
    "7c": ("2026-09-27", "ISO SIN offset a las 23:00"),
    "7d": ("2026-09-27", "ISO SIN offset a las 00:30"),
    "7e": ("2026-09-27", "ISO con milisegundos"),
    "7f": ("2026-09-27", "SOLO FECHA (evento de dia completo)"),
    "7g": ("2026-09-27", "ISO SIN offset a las 05:59"),
    "7h": ("2026-09-27", "ISO SIN offset a las 06:00"),
    "7i": ("2026-09-27", "ISO SIN offset a la 01:00"),
    "7j": ("2026-09-28", "ISO SIN offset 28 sep 02:00"),
    # 8. texto en espanol
    "8a": ("2026-09-27", "27 de septiembre de 2026"),
    "8b": (None, "sin anio -> debe pedir aclaracion o error"),
    "8c": ("2026-09-27", "27/09/2026 (dd/mm/aaaa)"),
    "8d": ("2026-09-27", "27 de septiembre (anio en curso)"),
    "8e": ("2026-09-27", "con el dia delante"),
    "8f": ("2026-09-27", "mes abreviado"),
    "8g": ("2026-09-27", "mes delante"),
    "8h": ("2026-12-27", "27/12/2026 (dd/mm: mes 12)"),
    "8i": ("2027-01-05", "05/01/2027 (dd/mm)"),
    "8j": ("2026-10-01", "1 de octubre de 2026"),
    # 9. basura -> ERROR
    "9a": (None, "cadena vacia"), "9b": (None, "texto sin fecha"),
    "9c": (None, "dia 32, mes 13"), "9d": (None, "null"),
    "9e": (None, "undefined"), "9f": (None, "solo espacios"),
    "9g": (None, "mes 13 en ISO"), "9h": (None, "ISO imposible"),
    "9i": (None, "solo el anio"), "9j": (None, "numero"),
}

filas = []
for r in res:
    cid = r["id"]
    esp, motivo = EXP.get(cid, (None, "?"))
    sal = r["salida"]
    es_error = isinstance(sal, str) and sal.startswith("Error:")
    # fecha que devolvio
    fecha_sal = None
    if isinstance(sal, str) and sal.rstrip().endswith(")"):
        fecha_sal = sal.rstrip()[:-1].rsplit("(", 1)[-1]
    # dia en espanol que devolvio
    dia_sal = None
    if isinstance(sal, str):
        for k in DIAS:
            if sal.startswith(k):
                dia_sal = k
                break
    if esp:
        f = datetime.date.fromisoformat(esp)
        dia_esp = DIAS[f.weekday()]
        ok = (fecha_sal == esp and dia_sal == dia_esp)
    else:
        dia_esp = None
        ok = es_error
    filas.append({"id": cid, "entrada": r["entrada"], "salida": sal,
                  "esperado": esp, "dia_esperado": dia_esp,
                  "fecha_salida": fecha_sal, "dia_salida": dia_sal,
                  "error": es_error, "ok": ok, "motivo": motivo})

tot = len(filas)
ok = sum(1 for f in filas if f["ok"])
print(f"\nCASOS: {tot}   ACIERTOS: {ok}   FALLOS: {tot-ok}   "
      f"{100.0*ok/tot:.1f}%")

grupos = [("1. los 7 dias de la semana", "1"),
          ("2. frontera de zona horaria (19:00 Mexico)", "2"),
          ("3. frontera de medianoche", "3"),
          ("4. cambio de mes", "4"), ("5. cambio de anio", "5"),
          ("6. 29 de febrero de 2028", "6"),
          ("7. ISO con offset y sin offset", "7"),
          ("8. texto en espanol", "8"), ("9. entradas basura", "9")]
print()
for nom, ini in grupos:
    xs = [f for f in filas if f["id"].startswith(ini)]
    o = sum(1 for f in xs if f["ok"])
    print(f"  {nom:44} {o}/{len(xs)}")

print()
print("FALLOS:")
for f in filas:
    if f["ok"]:
        continue
    esperado = (f"{f['esperado']} ({f['dia_esperado']})"
                if f["esperado"] else "ERROR legible")
    print(f"  {f['id']:>3} entrada={f['entrada']!r}")
    print(f"       salida real : {f['salida']}")
    print(f"       esperado    : {esperado}  [{f['motivo']}]")

json.dump({"total": tot, "aciertos": ok, "filas": filas,
           "tz_runtime": d["tz"]},
          open(DIR + r"\tally_final.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\nguardado tally_final.json")
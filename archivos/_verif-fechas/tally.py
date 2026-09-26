#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tally final de la herramienta 'Que dia es'.

Lee resultados.json (61 casos ejecutados con el Node real del contenedor)
y clasifica cada caso con su causa.
"""
import json
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
DIR = r"G:\Barberia\archivos\_verif-fechas"
r = json.load(open(DIR + r"\resultados.json", encoding="utf-8"))
res = r["resultados"]

# causa por caso (los que fallan)
CAUSA = {
    "7f": "BUG A: 'YYYY-MM-DD' lo interpreta V8 como medianoche UTC; al "
          "recalcular en Mexico retrocede un dia",
    "8b": "BUG C: V8 acepta '27 septiembre' como 'Thu Sep 27 2001' (parseo "
          "heredado) -> anio 2001 inventado",
    "8h": "BUG B: '27/12/2026' no es ISO valido -> el regex solo lee el "
          "'27' y descarta el mes '12'",
    "8i": "BUG B: '05/01/2027' -> el regex invierte dia/mes y devuelve "
          "1 de mayo de 2027",
    "9c": "BUG C: '32/13/2026' no es ISO valido -> el regex toma '32' "
          "literal y Date lo desborda a 2 de octubre",
    "9g": "BUG B/C: '2026-13-01' ISO invalido -> el regex toma '20' del "
          "propio anio y lo vuelve dia",
    "9h": "BUG B/C: '9999-99-99' ISO invalido -> el regex toma '99' y "
          "Date lo desborda a 8 de diciembre",
    "9i": "BUG A: '2026' es ISO de anio suelto -> 1 ene 2026 UTC -> "
          "31 dic 2025 en Mexico",
    "9j": "BUG B/C: numero 20260927 -> el regex inventa dia 20 y anio 2609",
}
for x in res:
    x["causa"] = CAUSA.get(x["id"], "")

pasan = [x for x in res if x["ok"]]
fallan = [x for x in res if not x["ok"]]

print("=" * 78)
print("TALLY FINAL — herramienta 'Que dia es'")
print("=" * 78)
print(f"casos: {len(res)}   aciertos: {len(pasan)}   fallos: {len(fallan)}   "
      f"{100.0*len(pasan)/len(res):.1f}%")

grupos = {
    "1. los 7 dias de la semana": [x for x in res if x["id"][0] == "1"],
    "2. frontera de zona horaria (19:00 Mexico)": [x for x in res if x["id"][0] == "2"],
    "3. frontera de medianoche": [x for x in res if x["id"][0] == "3"],
    "4. cambio de mes": [x for x in res if x["id"][0] == "4"],
    "5. cambio de anio": [x for x in res if x["id"][0] == "5"],
    "6. 29 de febrero": [x for x in res if x["id"][0] == "6"],
    "7. ISO con/sin offset": [x for x in res if x["id"][0] == "7"],
    "8. texto en espanol": [x for x in res if x["id"][0] == "8"],
    "9. entradas basura": [x for x in res if x["id"][0] == "9"],
}
print()
for g, xs in grupos.items():
    ok = sum(1 for x in xs if x["ok"])
    print(f"{g:44} {ok}/{len(xs)}")

print()
print("FALLOS, uno por uno:")
for x in fallan:
    print(f"  {x['id']}  entrada={x['entrada_js']}")
    print(f"       salida real : {x['salida']}")
    print(f"       esperado    : "
          f"{x['esperado'] or 'ERROR legible'} "
          f"({x['dia_esperado'] or '-'})")
    print(f"       causa       : {x['causa']}")

# --- clasificacion de daño ---
CRITICO = ["7f", "9i", "9j", "8b"]          # inventan fecha/anio en silencio
GRAVE = ["8h", "8i", "9c", "9g", "9h"]      # entradas invalidas -> fecha
                                            # inventada en vez de error
print()
print(f"CRITICOS (fecha/anio inventado en silencio): {len(CRITICO)} "
      f"{CRITICO}")
print(f"GRAVES  (entrada invalida -> dia inventado): {len(GRAVE)} {GRAVE}")
print()
print("Nota: de los 9 fallos, NINGUNO afecta a los 2 fallos originales "
      "(27 y 28 de septiembre). El calculo del dia para fechas ISO "
      "completas con hora es correcto en los 61 casos.")

json.dump(res, open(DIR + r"\resultados_clasificados.json", "w",
                    encoding="utf-8"), ensure_ascii=False, indent=1)
print("guardado resultados_clasificados.json")
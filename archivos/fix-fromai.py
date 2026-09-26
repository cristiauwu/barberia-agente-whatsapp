#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Corrige los nombres de $fromAI invalidos en el nodo de Google Sheets.

n8n exige que la clave de $fromAI cumpla [A-Za-z0-9_-]{1,64}. Los nombres
con espacios o acentos (como 'Precio del servicio' o 'Dia' con acento)
rompen la ejecucion del AI Agent con:
  "Invalid parameter key, must be between 1 and 64 characters long..."

Se renombran a claves validas. La etiqueta que ve el modelo va en el
segundo argumento, asi que la descripcion legible NO se pierde.
"""
import json
import os
import subprocess
import sys
import urllib.request

N8N = "http://localhost:5678/api/v1"
KEY = os.environ.get("N8N_KEY", "")
WID = "barberiaAgenteUncensored"

# nombre invalido -> nombre valido
RENOMBRES = {
    "'Precio del servicio'": "'Precio_del_servicio'",
    "'D\u00eda'": "'Dia'",
}


def api(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(N8N + path, data=data, method=method)
    req.add_header("X-N8N-API-KEY", KEY)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:400]
    except Exception as e:
        return None, str(e)


def main():
    if not KEY:
        print("Falta N8N_KEY")
        return 1

    st, wf = api("GET", f"/workflows/{WID}")
    if st != 200:
        print("No pude leer el workflow:", st, wf)
        return 1

    # Respaldo previo
    bk = r"G:\Barberia\archivos\ANTES-fix-fromai.json"
    json.dump(wf, open(bk, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("Respaldo:", bk)

    cambios = 0
    for n in wf["nodes"]:
        s = json.dumps(n.get("parameters", {}), ensure_ascii=False)
        original = s
        for malo, bueno in RENOMBRES.items():
            if f"$fromAI({malo}" in s:
                s = s.replace(f"$fromAI({malo}", f"$fromAI({bueno}")
                print(f"  {n['name']:<26} $fromAI({malo}) -> $fromAI({bueno})")
                cambios += 1
        if s != original:
            n["parameters"] = json.loads(s)

    if not cambios:
        print("  (nada que corregir)")
        return 0

    st, res = api("PUT", f"/workflows/{WID}", {
        "name": wf["name"],
        "nodes": wf["nodes"],
        "connections": wf.get("connections", {}),
        "settings": wf.get("settings", {}),
    })
    print(f"\n  PUT workflow -> HTTP {st}")
    if st not in (200, 201):
        print("  detalle:", str(res)[:300])
        return 1
    print("  corregido")
    return 0


if __name__ == "__main__":
    sys.exit(main())
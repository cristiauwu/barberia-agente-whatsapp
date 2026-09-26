#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sincroniza el `schema` del nodo Sheets con las columnas REALES.

ERROR: "Column names were updated after the node's setup".

QUÉ SIGNIFICA: n8n guarda en el nodo una copia de los nombres de columna
(`columns.schema`) que vio cuando se configuró. Al reapuntar el nodo a otra
hoja, ese `schema` quedó obsoleto respecto a la hoja real. n8n se niega a
escribir para no meter datos en columnas equivocadas.

SOLUCIÓN: reconstruir el `schema` con los nombres REALES de la hoja del
usuario, manteniendo el orden del encabezado. Los nombres deben coincidir
carácter por carácter, INCLUIDO el espacio final de "Día ".

El encabezado real verificado es:
  ID, Estatus, Nombre, Servicio, Precio del servicio, Día , Hora,
  Numero celular, Execution ID
"""
import json
import os
import sys
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

N8N = "http://localhost:5678/api/v1"
KEY = os.environ.get("N8N_KEY", "")
WID = "barberiaRecordatorios"

# Columnas reales de la hoja, en orden. OJO: "Día " lleva espacio al final
# porque así está en el encabezado de la hoja del usuario.
COLUMNAS = [
    "ID", "Estatus", "Nombre", "Servicio", "Precio del servicio",
    "Día ", "Hora", "Numero celular", "Execution ID",
]


def api(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(N8N + path, data=data, method=method)
    req.add_header("X-N8N-API-KEY", KEY)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:400]
    except Exception as e:
        return None, str(e)


def esquema():
    return [{
        "id": c, "displayName": c, "required": False, "defaultMatch": False,
        "display": True, "type": "string", "canBeUsedToMatch": True,
        "removed": False,
    } for c in COLUMNAS]


def main():
    st, wf = api("GET", f"/workflows/{WID}")
    if st != 200:
        print("no pude leer:", st)
        return 1
    activo = wf.get("active")
    json.dump(wf, open(r"G:\Barberia\archivos\ANTES-schema.json", "w",
                       encoding="utf-8"), ensure_ascii=False, indent=2)

    cambios = 0
    for n in wf["nodes"]:
        if "googleSheets" not in n["type"]:
            continue
        cols = n["parameters"].get("columns")
        if not isinstance(cols, dict):
            continue
        viejo = [s.get("id") for s in (cols.get("schema") or [])]
        cols["schema"] = esquema()
        # Los valores a escribir: solo las columnas que el nodo llena
        vals = cols.get("value") or {}
        # Verificar que las claves de 'value' existan en el esquema
        faltan = [k for k in vals if k not in COLUMNAS]
        if faltan:
            print(f"  {n['name']}: AVISO claves fuera del esquema: {faltan}")
        cols["mappingMode"] = cols.get("mappingMode") or "defineBelow"
        print(f"  {n['name']}")
        print(f"     schema: {viejo}")
        print(f"     schema: {COLUMNAS}")
        cambios += 1

    if not cambios:
        print("sin cambios")
        return 0

    if activo:
        api("POST", f"/workflows/{WID}/deactivate", {})
    st2, res = api("PUT", f"/workflows/{WID}", {
        "name": wf["name"], "nodes": wf["nodes"],
        "connections": wf["connections"], "settings": wf.get("settings", {}),
    })
    print(f"\nPUT -> HTTP {st2}")
    if st2 not in (200, 201):
        print("detalle:", str(res)[:300])
        return 1
    if activo:
        st3, r3 = api("POST", f"/workflows/{WID}/activate", {})
        print(f"reactivado -> HTTP {st3} active={r3.get('active')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
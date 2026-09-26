#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Corrige las notificaciones falsas al barbero.

PROBLEMA (MEJORAS-BARBERIA.md seccion 12):
  El nodo 'Notificar cita nueva al encargado' (flujo 2) dispara con
  CUALQUIER fila nueva de la hoja, incluidas:
    - cancelaciones (Estatus 'cancelado')
    - las 2 filas de un reagendado ('cancelado' + 'agendado')
  Asi el barbero recibe avisos de "cita nueva" que no lo son.

SOLUCION:
  Insertar un IF antes del aviso que solo deje pasar Estatus = 'agendado'.
  Las cancelaciones y reprogramaciones no generan aviso de cita nueva.
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
NODO_AVISO = "Notificar cita nueva al encargado"
NODO_IF = "IF - Es cita agendada"


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


def main():
    st, wf = api("GET", f"/workflows/{WID}")
    if st != 200:
        print("no pude leer:", st)
        return 1
    activo = wf.get("active")
    json.dump(wf, open(r"G:\Barberia\archivos\ANTES-filtro-aviso.json", "w",
                       encoding="utf-8"), ensure_ascii=False, indent=2)

    nodos = wf["nodes"]
    conns = wf["connections"]

    # 1) Crear el IF si no existe
    if not any(n["name"] == NODO_IF for n in nodos):
        nodos.append({
            "parameters": {
                "conditions": {
                    "options": {"caseSensitive": False, "leftValue": "",
                                "typeValidation": "loose", "version": 2},
                    "conditions": [{
                        "id": "esagendado-0001",
                        "leftValue": "={{ $('Code').item.json.Estatus }}",
                        "rightValue": "agendado",
                        "operator": {"type": "string", "operation": "equals"},
                    }],
                    "combinator": "and",
                },
                "options": {},
            },
            "type": "n8n-nodes-base.if",
            "typeVersion": 2.2,
            "position": [-40, 100],
            "id": "ifesagendada0000000000000000001",
            "name": NODO_IF,
            "notes": ("Solo avisa al barbero cuando la fila es una cita AGENDADA.\n"
                      "Evita avisos falsos en cancelaciones y en las dos filas\n"
                      "de un reagendado."),
            "notesInFlow": True,
        })
        print(f"  nodo creado: {NODO_IF}")

    # 2) Recablear: Code -> IF -> Notificar (true) ; (false) -> nada
    conns["Code"] = {"main": [[
        {"node": NODO_IF, "type": "main", "index": 0}]]}
    conns[NODO_IF] = {"main": [
        [{"node": NODO_AVISO, "type": "main", "index": 0}],
        [],
    ]}
    print(f"  recableado: Code -> {NODO_IF} -> {NODO_AVISO}")

    if activo:
        api("POST", f"/workflows/{WID}/deactivate", {})
    st2, res = api("PUT", f"/workflows/{WID}", {
        "name": wf["name"], "nodes": nodos,
        "connections": conns, "settings": wf.get("settings", {}),
    })
    print(f"  PUT -> HTTP {st2}")
    if st2 not in (200, 201):
        print("  detalle:", str(res)[:300])
        return 1
    if activo:
        st3, r3 = api("POST", f"/workflows/{WID}/activate", {})
        print(f"  reactivado -> HTTP {st3} active={r3.get('active')}")

    # Verificacion: quien alimenta al aviso
    st4, fin = api("GET", f"/workflows/{WID}")
    entradas = []
    for src, ramas in fin["connections"].items():
        for salidas in ramas.values():
            for i, g in enumerate(salidas):
                for c in g:
                    if c["node"] == NODO_AVISO:
                        entradas.append(f"{src} [salida {i}]")
    print(f"\n=== VERIFICACION ===")
    ok = entradas == [f"{NODO_IF} [salida 0]"]
    print(f"  {'OK  ' if ok else 'MAL '} '{NODO_AVISO}' lo alimenta: {entradas}")
    print(f"  {'OK  ' if ok else 'MAL '} solo pasa Estatus='agendado'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
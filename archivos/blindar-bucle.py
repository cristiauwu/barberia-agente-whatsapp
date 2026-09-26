#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Blindaje del flujo contra el bucle de auto-respuesta.

Dos cambios:
  1. 'Normalizacion' ahora calcula 'from_me' con el campo fromMe del payload.
  2. Se inserta un nodo IF despues de Normalizacion que CORTA si el mensaje
     lo envio el propio bot. Sin esto, el bot se responde a si mismo.

Esto protege incluso si en el futuro se vuelve a activar algun evento de
Evolution que notifique mensajes salientes.
"""
import json
import os
import subprocess
import sys
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

N8N = "http://localhost:5678/api/v1"
KEY = os.environ.get("N8N_KEY", "")
WID = "barberiaAgenteUncensored"
TMP = r"G:\Barberia\archivos"


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
        print("no pude leer:", st, wf)
        return 1

    # Respaldo
    json.dump(wf, open(os.path.join(TMP, "ANTES-blindaje.json"), "w",
                       encoding="utf-8"), ensure_ascii=False, indent=2)

    nodos = wf["nodes"]
    norm = next(n for n in nodos if n["name"] == "Normalizacion")

    # --- 1. Añadir la asignacion from_me -----------------------------
    ya = any(a["name"] == "from_me"
             for a in norm["parameters"]["assignments"]["assignments"])
    if not ya:
        norm["parameters"]["assignments"]["assignments"].append({
            "id": "fromme0001-0000-4000-8000-000000000001",
            "name": "from_me",
            "value": "={{ $json.body.data.key.fromMe ? 'si' : 'no' }}",
            "type": "string",
        })
        print("  Normalizacion: añadido campo 'from_me'")

    # --- 2. Nodo IF de corte -----------------------------------------
    if not any(n["name"] == "IF - No es del bot" for n in nodos):
        nodos.append({
            "parameters": {
                "conditions": {
                    "options": {"caseSensitive": True, "leftValue": "",
                                "typeValidation": "loose", "version": 2},
                    "conditions": [{
                        "id": "ifnotbot-0000-4000-8000-000000000001",
                        "leftValue": "={{ $json.from_me }}",
                        "rightValue": "no",
                        "operator": {"type": "string", "operation": "equals"},
                    }],
                    "combinator": "and",
                },
                "options": {},
            },
            "type": "n8n-nodes-base.if",
            "typeVersion": 2.2,
            "position": [-380, 180],
            "id": "ifnotbot000000000000000000000001",
            "name": "IF - No es del bot",
            "notes": ("Corta los mensajes que envia el propio bot (fromMe=true). "
                      "Sin esto el agente se responde a si mismo en bucle."),
            "notesInFlow": True,
        })
        print("  añadido nodo 'IF - No es del bot'")

    # --- 3. Recablear: Normalizacion -> IF -> Switch ------------------
    conns = wf["connections"]
    conns["Normalizacion"] = {"main": [[
        {"node": "IF - No es del bot", "type": "main", "index": 0}]]}
    conns["IF - No es del bot"] = {"main": [
        [{"node": "Switch", "type": "main", "index": 0}],
        [],
    ]}
    print("  recableado: Normalizacion -> IF - No es del bot -> Switch")

    st, res = api("PUT", f"/workflows/{WID}", {
        "name": wf["name"],
        "nodes": nodos,
        "connections": conns,
        "settings": wf.get("settings", {}),
    })
    print(f"\n  PUT -> HTTP {st}")
    if st not in (200, 201):
        print("  detalle:", str(res)[:300])
        return 1
    print("  blindaje aplicado")
    return 0


if __name__ == "__main__":
    sys.exit(main())
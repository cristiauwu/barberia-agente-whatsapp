#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Corrige '¿Es operador?' para que use TU número, leyendo la tabla.

EL BUG: el nodo tenía hardcodeado el número del VENDEDOR
(5215520894522). Por eso los comandos del dueño nunca entraban al router:
'¿Es operador?' daba falso y el mensaje seguía al agente como si fuera
de un cliente. Los 9 comandos de prueba acabaron gastando tokens.

SOLUCIÓN: consultar la tabla barber_operadores, que es la fuente única de
verdad. Así, agregar o quitar operadores no requiere tocar el workflow.
"""
import json
import os
import sys
import urllib.request
import uuid

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

N8N = "http://localhost:5678/api/v1"
KEY = os.environ.get("N8N_KEY", "")
WID = "barberiaAgenteUncensored"
PG_CRED = {"postgres": {"id": "NUrqrDWN8OsBFmgV", "name": "Postgres account"}}


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
    activo = wf.get("active")
    json.dump(wf, open(r"G:\Barberia\archivos\ANTES-operador.json", "w",
                       encoding="utf-8"), ensure_ascii=False, indent=2)

    # --- 1. Nodo que lee los operadores de la tabla -------------------
    nodo_pg = {
        "parameters": {
            "operation": "executeQuery",
            "query": "SELECT jid FROM barber_operadores WHERE activo;",
            "options": {},
        },
        "type": "n8n-nodes-base.postgres",
        "typeVersion": 2.6,
        "position": [-700, 120],
        "id": str(uuid.uuid4()),
        "name": "Leer operadores",
        "credentials": PG_CRED,
        "notes": ("Fuente única de verdad de quién puede mandar comandos.\n"
                  "Así se agregan o quitan operadores sin tocar el workflow."),
        "notesInFlow": True,
    }
    wf["nodes"] = [n for n in wf["nodes"] if n["name"] != "Leer operadores"]
    wf["nodes"].append(nodo_pg)

    # --- 2. Nodo que decide si el remitente es operador ---------------
    # El IF original comparaba contra UN número. Ahora se compara contra
    # la lista que devolvió Postgres, en un nodo Code para poder usar la
    # lógica de "últimos 10 dígitos" (52+10 vs 52+1+10).
    nodo_chk = {
        "parameters": {"jsCode": """// ¿El remitente es un operador autorizado?
// Compara por los ÚLTIMOS 10 dígitos para tolerar los dos formatos
// mexicanos de WhatsApp (52+10 y 52+1+10).
const item = $('Normalizacion').first().json;
const remitente = String(item.user_number || '');
const ultimos = s => String(s || '').replace(/\\D/g, '').slice(-10);

const autorizados = $input.all()
  .map(i => i.json.jid)
  .filter(Boolean);

const esOperador = autorizados.some(j => ultimos(j) === ultimos(remitente));

return [{ json: { ...item, es_operador: esOperador,
                  operadores: autorizados } }];"""},
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [-500, 120],
        "id": str(uuid.uuid4()),
        "name": "Comprobar operador",
        "notes": ("Decide si el mensaje viene de un operador. Usa los\n"
                  "últimos 10 dígitos: en México un mismo número aparece\n"
                  "como 52+10 o 52+1+10 según el caso."),
        "notesInFlow": True,
    }
    wf["nodes"] = [n for n in wf["nodes"] if n["name"] != "Comprobar operador"]
    wf["nodes"].append(nodo_chk)

    # --- 3. El IF ahora mira el campo calculado -----------------------
    n_if = next((x for x in wf["nodes"] if x["name"] == "¿Es operador?"), None)
    n_if["parameters"] = {
        "conditions": {
            "options": {"caseSensitive": False, "leftValue": "",
                        "typeValidation": "loose", "version": 2},
            "conditions": [{
                "id": "esoperador0001",
                "leftValue": "={{ $json.es_operador }}",
                "rightValue": True,
                "operator": {"type": "boolean", "operation": "true",
                             "singleValue": True},
            }],
            "combinator": "and",
        },
        "options": {},
    }
    n_if["position"] = [-300, 120]
    n_if["notes"] = ("Rama true = operador -> router de comandos.\n"
                     "Rama false = cliente -> flujo normal del agente.")
    n_if["notesInFlow"] = True

    # --- 4. Recablear: Normalizacion -> Leer operadores -> Comprobar -> IF
    c = wf["connections"]
    c["Normalizacion"] = {"main": [[
        {"node": "Leer operadores", "type": "main", "index": 0}]]}
    c["Leer operadores"] = {"main": [[
        {"node": "Comprobar operador", "type": "main", "index": 0}]]}
    c["Comprobar operador"] = {"main": [[
        {"node": "¿Es operador?", "type": "main", "index": 0}]]}
    # Las ramas del IF no cambian (true -> router, false -> flujo normal)

    if activo:
        api("POST", f"/workflows/{WID}/deactivate", {})
    st2, res = api("PUT", f"/workflows/{WID}", {
        "name": wf["name"], "nodes": wf["nodes"],
        "connections": c, "settings": wf.get("settings", {}),
    })
    print(f"PUT -> HTTP {st2}")
    if st2 not in (200, 201):
        print("detalle:", str(res)[:400])
        return 1
    if activo:
        st3, r3 = api("POST", f"/workflows/{WID}/activate", {})
        print(f"reactivado -> HTTP {st3} active={r3.get('active')}")

    # --- Verificacion -------------------------------------------------
    print("\n=== VERIFICACION ===")
    st4, fin = api("GET", f"/workflows/{WID}")
    txt = json.dumps(fin, ensure_ascii=False)
    print(f"  {'OK  ' if '5215520894522' not in txt else 'MAL '} "
          f"sin el numero del vendedor")
    n2 = next((x for x in fin["nodes"] if x["name"] == "¿Es operador?"), None)
    cond = n2["parameters"]["conditions"]["conditions"][0]
    print(f"  compara: {cond['leftValue']} == {cond['rightValue']}")
    print(f"  nodos totales: {len(fin['nodes'])}")
    cadena = fin["connections"]
    print(f"  Normalizacion -> "
          f"{cadena['Normalizacion']['main'][0][0]['node']}")
    print(f"  Leer operadores -> "
          f"{cadena['Leer operadores']['main'][0][0]['node']}")
    print(f"  Comprobar operador -> "
          f"{cadena['Comprobar operador']['main'][0][0]['node']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
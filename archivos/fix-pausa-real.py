#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hace que el comando PAUSA se RESPETE de verdad.

PROBLEMA: la tabla barber_pausas solo se ESCRIBÍA (nodo 'Aplicar pausa').
Nunca se consultaba. Así que 'PAUSA 452... 2h' guardaba el registro pero
el bot seguía contestándole al cliente. El comando no servía para nada.

SOLUCIÓN: insertar la consulta en el camino del CLIENTE, justo después de
'IF - No es del bot' (que ya descartó los mensajes propios del bot) y antes
de 'Switch':

    IF - No es del bot (true)
      -> Leer pausa            (consulta barber_pausas)
      -> IF - Cliente pausado?
           true  -> (sin salida: el bot se queda callado a propósito)
           false -> Switch (sigue el flujo normal)

DETALLE CRÍTICO: si el cliente NO está pausado, la consulta devuelve 0
filas y n8n CORTA la cadena — el bot nunca respondería. Por eso:
  - el nodo Postgres lleva `alwaysOutputData: true` (siempre emite un item)
  - la consulta devuelve `count(*)`, que siempre da una fila con 0 o 1
  - la decisión se toma en un IF explícito, no por ausencia de datos.
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

CONSULTA = """SELECT count(*) AS pausado,
       coalesce(max(hasta), null) AS hasta,
       coalesce(max(motivo), '') AS motivo
FROM barber_pausas
WHERE jid = '{{ $json.user_number }}'
  AND hasta > now();"""

CODIGO = r"""// Decide si hay que quedarse callado con este cliente.
// La consulta devuelve count(*) = 0 o 1 y SIEMPRE una fila, así que el
// flujo no se corta cuando el cliente no está pausado.
const base = $('Normalizacion').first().json;
const fila = $input.first().json || {};
const pausado = Number(fila.pausado || 0) > 0;
return [{ json: { ...base, pausado, hasta: fila.hasta || null } }];"""


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
    json.dump(wf, open(r"G:\Barberia\archivos\ANTES-pausa.json", "w",
                       encoding="utf-8"), ensure_ascii=False, indent=2)

    # --- 1. Nodo que consulta la pausa --------------------------------
    nodo_pg = {
        "parameters": {"operation": "executeQuery", "query": CONSULTA,
                       "options": {}},
        "type": "n8n-nodes-base.postgres", "typeVersion": 2.6,
        "position": [-560, -80], "id": str(uuid.uuid4()),
        "name": "Leer pausa",
        "credentials": PG_CRED,
        "alwaysOutputData": True,
        "notes": ("¿Este cliente está pausado ahora? Devuelve count(*) para\n"
                  "que SIEMPRE haya una fila: si devolviera 0 filas, n8n\n"
                  "cortaría la cadena y el bot no contestaría a nadie."),
        "notesInFlow": True,
    }
    # --- 2. Nodo que decide -------------------------------------------
    nodo_code = {
        "parameters": {"jsCode": CODIGO},
        "type": "n8n-nodes-base.code", "typeVersion": 2,
        "position": [-360, -80], "id": str(uuid.uuid4()),
        "name": "Calcular pausa",
        "notes": "Convierte el conteo en un booleano claro.",
        "notesInFlow": True,
    }
    # --- 3. El IF -------------------------------------------------------
    nodo_if = {
        "parameters": {
            "conditions": {
                "options": {"caseSensitive": False, "leftValue": "",
                            "typeValidation": "loose", "version": 2},
                "conditions": [{
                    "id": "espausado0001",
                    "leftValue": "={{ $json.pausado }}",
                    "rightValue": True,
                    "operator": {"type": "boolean", "operation": "true",
                                 "singleValue": True},
                }],
                "combinator": "and",
            },
            "options": {},
        },
        "type": "n8n-nodes-base.if", "typeVersion": 2.2,
        "position": [-160, -80], "id": str(uuid.uuid4()),
        "name": "IF - Cliente pausado",
        "notes": ("true  = el dueño tomó la conversación -> el bot se queda\n"
                  "        callado a propósito (sin salida conectada).\n"
                  "false = sigue el flujo normal hacia Switch."),
        "notesInFlow": True,
    }

    nombres = {"Leer pausa", "Calcular pausa", "IF - Cliente pausado"}
    wf["nodes"] = [n for n in wf["nodes"] if n["name"] not in nombres]
    wf["nodes"] += [nodo_pg, nodo_code, nodo_if]

    # --- 4. Recablear --------------------------------------------------
    c = wf["connections"]

    def uno(n):
        return [{"node": n, "type": "main", "index": 0}]

    # IF - No es del bot (salida true) ya iba a Switch; ahora pasa por pausa.
    # Su salida 0 es 'true' (no es del bot).
    salidas = c.get("IF - No es del bot", {}).get("main", [[], []])
    while len(salidas) < 2:
        salidas.append([])
    salidas[0] = uno("Leer pausa")
    c["IF - No es del bot"] = {"main": salidas}

    c["Leer pausa"] = {"main": [uno("Calcular pausa")]}
    c["Calcular pausa"] = {"main": [uno("IF - Cliente pausado")]}
    # true -> [] (silencio deliberado) ; false -> Switch
    c["IF - Cliente pausado"] = {"main": [[], uno("Switch")]}

    print("cadena:")
    print("  IF - No es del bot (true) -> Leer pausa")
    print("  Leer pausa -> Calcular pausa -> IF - Cliente pausado")
    print("     true  -> (nada: el bot calla)")
    print("     false -> Switch")

    if activo:
        api("POST", f"/workflows/{WID}/deactivate", {})
    st2, res = api("PUT", f"/workflows/{WID}", {
        "name": wf["name"], "nodes": wf["nodes"],
        "connections": c, "settings": wf.get("settings", {}),
    })
    print(f"\nPUT -> HTTP {st2}")
    if st2 not in (200, 201):
        print("detalle:", str(res)[:400])
        return 1
    if activo:
        st3, r3 = api("POST", f"/workflows/{WID}/activate", {})
        print(f"reactivado -> HTTP {st3} active={r3.get('active')}")

    # --- Verificacion --------------------------------------------------
    print("\n=== VERIFICACION ===")
    st4, fin = api("GET", f"/workflows/{WID}")
    nombres_fin = {n["name"] for n in fin["nodes"]}
    for x in nombres:
        print(f"  {'OK  ' if x in nombres_fin else 'MAL '} existe '{x}'")
    n = next((n for n in fin["nodes"] if n["name"] == "Leer pausa"), None)
    print(f"  {'OK  ' if n and n.get('alwaysOutputData') else 'MAL '} "
          f"'Leer pausa' tiene alwaysOutputData")
    cad = fin["connections"]
    camino = (cad.get("IF - No es del bot", {}).get("main", [[{}]])[0][0]["node"]
              if cad.get("IF - No es del bot", {}).get("main") else "(vacio)")
    print(f"  {'OK  ' if camino == 'Leer pausa' else 'MAL '} "
          f"IF - No es del bot -> {camino}")
    s = cad.get("IF - Cliente pausado", {}).get("main", [[], []])
    print(f"  pausado -> {s[0] or '(vacio: calla)'}")
    print(f"  no pausado -> {[x['node'] for x in s[1]] if len(s) > 1 else '?'}")
    print(f"  nodos totales: {len(fin['nodes'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
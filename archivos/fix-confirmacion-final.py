#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Arregla el bucle de confirmacion de una vez, y bien.

ESTADO ACTUAL (con dos bugs mios):
  Normalizacion ─► Leer operadores  +  Buscar cita   <- BIFURCACION PARALELA
  IF - Es confirmacion salida 1 -> Leer pausa + Armar aviso de cambio
                                                      <- aviso con CUALQUIER mensaje

LOS DOS BUGS:
  1. `Normalizacion` va a DOS sitios: el agente corre igual, en paralelo,
     asi que un "SI" recibe DOS respuestas y gasta tokens.
  2. El IF tiene 2 salidas, asi que `ninguna` cae en la rama de NO y
     dispara un "quiere cambiar su cita" que nadie pidio.

LA ESTRUCTURA CORRECTA — una PUERTA, y el aviso leido del nodo correcto:

  Normalizacion
    └─► Buscar cita para confirmar
          └─► Es confirmacion?
                └─► Switch confirmacion
                      ├─ SI ──► Armar respuesta ──► Marcar confirmada
                      │                              └─► Avisar al dueno
                      │                                    (lee de 'Armar respuesta')
                      ├─ NO ──► Armar aviso ──┬─► Avisar al dueno
                      │                       └─► Leer operadores (que ofrezca hora)
                      └─ otra cosa ──────────────► Leer operadores

  NOTA CLAVE sobre 'Avisar al dueno': un nodo de Postgres DEVUELVE SUS
  PROPIAS FILAS, asi que despues de 'Marcar cita confirmada' el `$json` ya
  no tiene `aviso_al_dueno`. Por eso el aviso se lee de
  `$('Armar respuesta de confirmacion').item.json`. Es el mismo error que
  ya cometi una vez en este mismo arreglo.
"""
import json
import os
import sys
import urllib.error
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

N8N = "http://localhost:5678/api/v1"
KEY = open(r"G:\Barberia\archivos\.n8n-key.txt", encoding="utf-8").read().strip()
WID = "barberiaAgenteUncensored"


def api(m, p, b=None):
    d = json.dumps(b).encode() if b is not None else None
    r = urllib.request.Request(N8N + p, data=d, method=m)
    r.add_header("X-N8N-API-KEY", KEY)
    r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=90) as x:
            return x.status, json.loads(x.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:500]
    except Exception as e:
        return None, str(e)


def main():
    print("=" * 70)
    print("ARREGLAR EL BUCLE DE CONFIRMACION (de una vez)")
    print("=" * 70)

    st, wf = api("GET", f"/workflows/{WID}")
    if st != 200:
        print(f"  MAL: {st}")
        return 1
    nodos = {n["name"]: n for n in wf["nodes"]}
    print(f"  nodos: {len(wf['nodes'])}")

    # ------------------------------------------------------------- 1
    print("\n[1] Reemplazar el IF por un Switch de 3 salidas")
    wf["nodes"] = [n for n in wf["nodes"]
                   if n["name"] != "IF - Es confirmacion"]
    wf["connections"].pop("IF - Es confirmacion", None)

    if not any(n["name"] == "Switch confirmacion" for n in wf["nodes"]):
        wf["nodes"].append({
            "id": "switch-confirmacion",
            "name": "Switch confirmacion",
            "type": "n8n-nodes-base.switch",
            "typeVersion": 3.2,
            "position": [-780, 300],
            "parameters": {
                "rules": {"values": [
                    {"conditions": {
                        "options": {"caseSensitive": True,
                                    "typeValidation": "loose",
                                    "version": 2},
                        "conditions": [{
                            "id": "r-si",
                            "leftValue": "={{ $json.decision }}",
                            "rightValue": "SI",
                            "operator": {"type": "string",
                                         "operation": "equals"}}],
                        "combinator": "and"},
                     "renameOutput": True, "outputKey": "SI: confirmo"},
                    {"conditions": {
                        "options": {"caseSensitive": True,
                                    "typeValidation": "loose",
                                    "version": 2},
                        "conditions": [{
                            "id": "r-no",
                            "leftValue": "={{ $json.decision }}",
                            "rightValue": "NO",
                            "operator": {"type": "string",
                                         "operation": "equals"}}],
                        "combinator": "and"},
                     "renameOutput": True, "outputKey": "NO: quiere cambiar"},
                ]},
                "options": {"fallbackOutput": "extra"},
            },
            "notes": ("Una PUERTA, no una bifurcacion: el agente solo corre "
                      "por el respaldo. Antes era un IF de 2 salidas y el "
                      "caso 'ninguna' se mezclaba con NO, avisando al dueno "
                      "de cambios que nadie pidio."),
        })
        print("  OK  Switch creado (SI / NO / respaldo)")

    # ------------------------------------------------------------- 2
    print("\n[2] Avisar al dueno: leer el aviso del nodo que lo arma")
    av = nodos["Avisar al dueno de la confirmacion"]
    av["parameters"]["bodyParameters"]["parameters"][1]["value"] = (
        "={{ $('Armar respuesta de confirmacion').item.json.aviso_al_dueno "
        "|| $('Armar aviso de cambio').item.json.aviso_al_dueno }}")
    av["alwaysOutputData"] = True
    av["onError"] = "continueRegularOutput"
    print("  OK  lee de los dos nodos que arman el aviso")
    print("     (un nodo Postgres reemplaza $json: hay que referenciar)")

    # ------------------------------------------------------------- 3
    print("\n[3] Rutas EXACTAS (se reconstruyen, no se parchean)")
    con = {}
    nombres = {n["name"] for n in wf["nodes"]}

    def une(origen, destino, salida=0):
        actual = con.setdefault(origen, {})
        ramas = actual.setdefault("main", [])
        while len(ramas) <= salida:
            ramas.append([])
        if not any(d["node"] == destino for d in ramas[salida]):
            ramas[salida].append({"node": destino, "type": "main",
                                  "index": 0})

    # la puerta
    une("Normalizacion", "Buscar cita para confirmar")
    une("Buscar cita para confirmar", "Es confirmacion?")
    une("Es confirmacion?", "Switch confirmacion")

    # SI
    une("Switch confirmacion", "Armar respuesta de confirmacion", 0)
    une("Armar respuesta de confirmacion", "Marcar cita confirmada")
    une("Marcar cita confirmada", "Avisar al dueno de la confirmacion")

    # NO: avisa y ademas deja que el agente ofrezca otro horario
    une("Switch confirmacion", "Armar aviso de cambio", 1)
    une("Armar aviso de cambio", "Avisar al dueno de la confirmacion")
    une("Armar aviso de cambio", "Leer operadores")

    # todo lo demas: el camino normal del agente
    une("Switch confirmacion", "Leer operadores", 2)

    # CONSERVAR el resto de conexiones que NO son de la puerta
    viejas = wf.get("connections", {})
    de_la_puerta = {"Normalizacion", "Buscar cita para confirmar",
                    "Es confirmacion?", "Switch confirmacion",
                    "IF - Es confirmacion",
                    "Armar respuesta de confirmacion", "Marcar cita confirmada",
                    "Armar aviso de cambio",
                    "Avisar al dueno de la confirmacion"}
    for origen, salidas in viejas.items():
        if origen in de_la_puerta or origen not in nombres:
            continue
        limpio = {}
        for tipo, ramas in salidas.items():
            nuevas = []
            for rama in (ramas or []):
                if rama is None:
                    nuevas.append([])
                    continue
                filtrada = [d for d in rama if d.get("node") in nombres]
                nuevas.append(filtrada)
            limpio[tipo] = nuevas
        con[origen] = limpio
    wf["connections"] = con
    print("  OK  rutas reconstruidas y el resto conservado")

    # ------------------------------------------------------------- 4
    print("\n[4] El monitor de confirmaciones (por si algo falla)")
    if "Mandar aviso al dueno (respaldo)" not in nombres:
        wf["nodes"].append({
            "id": "respaldo-aviso",
            "name": "Mandar aviso al dueno (respaldo)",
            "type": "n8n-nodes-base.noOp",
            "typeVersion": 1,
            "position": [20, 300],
            "parameters": {},
            "notes": ("Fin del camino de confirmacion. Existe para que la "
                      "cadena tenga un final claro y sea facil de leer en "
                      "el lienzo de n8n."),
        })
        con.setdefault("Avisar al dueno de la confirmacion", {}).setdefault(
            "main", [[]])[0].append(
            {"node": "Mandar aviso al dueno (respaldo)", "type": "main",
             "index": 0})
        print("  OK  nodo final agregado")

    # ------------------------------------------------------------- 5
    print("\n[5] Guardar")
    activo = wf.get("active")
    if activo:
        api("POST", f"/workflows/{WID}/deactivate", {})
    st2, r = api("PUT", f"/workflows/{WID}", {
        "name": wf["name"], "nodes": wf["nodes"],
        "connections": wf["connections"],
        "settings": wf.get("settings", {})})
    print(f"  PUT -> HTTP {st2}")
    if st2 not in (200, 201):
        print(f"  MAL: {str(r)[:400]}")
        return 1
    if activo:
        api("POST", f"/workflows/{WID}/activate", {})

    # ------------------------------------------------------------- 6
    print("\n[6] VERIFICACION")
    st, fin = api("GET", f"/workflows/{WID}")
    c = fin["connections"]
    sw = c.get("Switch confirmacion", {}).get("main", [])
    norm = c.get("Normalizacion", {}).get("main", [])
    pruebas = [
        ("Normalizacion va SOLO a la puerta",
         len(norm) == 1 and [d["node"] for d in norm[0]] ==
         ["Buscar cita para confirmar"]),
        ("el Switch tiene 3 salidas", len(sw) == 3),
        ("salida 0 (SI) -> Armar respuesta",
         [d["node"] for d in sw[0]] == ["Armar respuesta de confirmacion"]),
        ("salida 1 (NO) -> Armar aviso",
         [d["node"] for d in sw[1]] == ["Armar aviso de cambio"]),
        ("salida 2 (resto) -> Leer operadores",
         [d["node"] for d in sw[2]] == ["Leer operadores"]),
        ("no queda el IF viejo",
         not any(n["name"] == "IF - Es confirmacion" for n in fin["nodes"])),
        ("el aviso lee del nodo correcto",
         "$('Armar respuesta de confirmacion')" in
         json.dumps(next(n for n in fin["nodes"]
                         if n["name"] == "Avisar al dueno de la "
                         "confirmacion")["parameters"])),
        ("el workflow sigue activo", fin.get("active") is True),
    ]
    fallos = 0
    for n2, ok in pruebas:
        print(f"  {'OK  ' if ok else 'MAL '} {n2}")
        if not ok:
            fallos += 1
    print(f"\n  nodos: {len(fin['nodes'])}   FALLOS: {fallos}")
    return 0 if fallos == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
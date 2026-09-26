#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quita el nodo 'Comando pendiente', que quedó obsoleto.

Se creó cuando solo COMANDOS estaba implementado, para responder
"🚧 todavía no está activo" a los demás. Ahora los 12 comandos funcionan,
así que ese nodo no tiene a dónde conectarse y quedaría huérfano.
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
WID = "barberiaAgenteUncensored"


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
    antes = len(wf["nodes"])

    wf["nodes"] = [n for n in wf["nodes"] if n["name"] != "Comando pendiente"]
    wf["connections"].pop("Comando pendiente", None)
    print(f"nodos: {antes} -> {len(wf['nodes'])}")

    if activo:
        api("POST", f"/workflows/{WID}/deactivate", {})
    st2, _ = api("PUT", f"/workflows/{WID}", {
        "name": wf["name"], "nodes": wf["nodes"],
        "connections": wf["connections"], "settings": wf.get("settings", {}),
    })
    print(f"PUT -> HTTP {st2}")
    if activo:
        api("POST", f"/workflows/{WID}/activate", {})

    # Verificacion
    st3, fin = api("GET", f"/workflows/{WID}")
    destinos = set()
    for ramas in fin["connections"].values():
        for sal in ramas.values():
            for g in sal:
                for x in g:
                    destinos.add(x["node"])
    fuente_ai, ai_dest = set(), set()
    for src, ramas in fin["connections"].items():
        for tipo, sal in ramas.items():
            if tipo != "main":
                fuente_ai.add(src)
                for g in sal:
                    for x in g:
                        ai_dest.add(x["node"])
    huerfanos = []
    for n in fin["nodes"]:
        nm, t = n["name"], n["type"]
        if nm in destinos:
            continue
        if ("Trigger" in t or t.endswith(".webhook") or "manualTrigger" in t
                or nm in fuente_ai or nm in ai_dest):
            continue
        huerfanos.append(nm)
    print(f"\n=== VERIFICACION ===")
    print(f"  nodos totales: {len(fin['nodes'])}")
    print(f"  {'OK  ' if not huerfanos else 'MAL '} huerfanos: "
          f"{huerfanos or 'ninguno'}")
    print(f"  {'OK  ' if 'Comando pendiente' not in json.dumps(fin) else 'MAL '}"
          f" el nodo obsoleto ya no existe")
    return 0


if __name__ == "__main__":
    sys.exit(main())
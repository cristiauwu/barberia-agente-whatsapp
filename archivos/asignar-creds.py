#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Asigna las credenciales nuevas a los nodos correctos del workflow.

Se hace por la API publica de n8n (PATCH /workflows/{id}), que no exige
reconstruir el workflow completo: solo se envian los nodos afectados.
"""
import json
import os
import subprocess
import sys
import urllib.request

N8N = "http://localhost:5678/api/v1"
KEY = os.environ.get("N8N_KEY", "")
WID = "barberiaAgenteUncensored"

# id de credencial -> como se llama en el nodo
ASIGNAR = {
    "OpenAI Chat Model": ("openAiApi", "KhicsxnD4N314cKC",
                          "Uncensored AI (OpenAI-compatible)"),
    "Postgres Chat Memory": ("postgres", "NUrqrDWN8OsBFmgV", "Postgres account"),
}


def api(method, path, body=None):
    url = N8N + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
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
        print("Falta N8N_KEY en el entorno")
        return 1

    st, wf = api("GET", f"/workflows/{WID}")
    if st != 200:
        print("No pude leer el workflow:", st, wf)
        return 1

    nodos = wf.get("nodes", [])
    cambios = 0
    for n in nodos:
        if n["name"] in ASIGNAR:
            ctype, cid, cname = ASIGNAR[n["name"]]
            antes = (n.get("credentials") or {}).get(ctype, {}).get("id")
            n.setdefault("credentials", {})[ctype] = {"id": cid, "name": cname}
            print(f"  {n['name']:<24} {ctype}: {antes} -> {cid} ({cname})")
            cambios += 1

    if not cambios:
        print("  (nada que cambiar)")
        return 0

    st, res = api("PUT", f"/workflows/{WID}", {
        "name": wf["name"],
        "nodes": nodos,
        "connections": wf.get("connections", {}),
        "settings": wf.get("settings", {}),
    })
    print(f"\n  PATCH workflow -> HTTP {st}")
    if st not in (200, 201):
        print("  detalle:", str(res)[:400])
        return 1
    print("  asignacion aplicada")
    return 0


if __name__ == "__main__":
    sys.exit(main())
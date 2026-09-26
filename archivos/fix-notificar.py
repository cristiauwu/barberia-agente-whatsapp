#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Corrige el nodo 'Notificar al encargado' (toolHttpRequest) del flujo 1.

Se me escapo en el primer intento: los nodos de tipo `toolHttpRequest`
(los que son herramientas del agente) guardan los headers en
`parametersHeaders.values[]`, NO en `headerParameters.parameters[]`.

Este nodo:
  - Apunta al servidor del vendedor (easypanel.host)
  - Lleva su API key en texto plano

Ambos se corrigen.
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
NODO = "Notificar al encargado"
EVO_LOCAL = "http://evolution_api:8080"


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
    cred_id = None
    st, creds = api("GET", "/credentials")
    for c in creds.get("data", []):
        if c.get("name") == "Evolution API":
            cred_id = c["id"]
    if not cred_id:
        print("no encontre la credencial 'Evolution API'")
        return 1
    print(f"credencial: {cred_id}")

    st, wf = api("GET", f"/workflows/{WID}")
    if st != 200:
        print("no pude leer:", st)
        return 1
    activo = wf.get("active")
    json.dump(wf, open(r"G:\Barberia\archivos\ANTES-notificar.json", "w",
                       encoding="utf-8"), ensure_ascii=False, indent=2)

    n = next((x for x in wf["nodes"] if x["name"] == NODO), None)
    if not n:
        print("no existe el nodo", NODO)
        return 1
    p = n["parameters"]

    print("\n--- ANTES ---")
    print(f"  url: {p.get('url')}")
    print(f"  headers: {json.dumps(p.get('parametersHeaders'), ensure_ascii=False)[:120]}")

    # Corregir URL
    url = p.get("url", "")
    if "easypanel.host" in url:
        sufijo = url.split("easypanel.host", 1)[1]
        p["url"] = EVO_LOCAL + sufijo
    p["method"] = "POST"

    # Corregir headers: quitar el apikey literal y usar credencial
    p["parametersHeaders"] = {"values": []}
    p["specifyHeaders"] = "keypair"
    p["authentication"] = "genericCredentialType"
    p["genericAuthType"] = "httpHeaderAuth"
    n.setdefault("credentials", {})["httpHeaderAuth"] = {
        "id": cred_id, "name": "Evolution API"}

    print("\n--- DESPUES ---")
    print(f"  url: {p['url']}")
    print(f"  authentication: {p['authentication']} / {p['genericAuthType']}")
    print(f"  headers: {json.dumps(p['parametersHeaders'])}")
    print(f"  credencial: {cred_id}")

    if activo:
        api("POST", f"/workflows/{WID}/deactivate", {})
    st2, res = api("PUT", f"/workflows/{WID}", {
        "name": wf["name"], "nodes": wf["nodes"],
        "connections": wf["connections"], "settings": wf.get("settings", {}),
    })
    print(f"\n  PUT -> HTTP {st2}")
    if st2 not in (200, 201):
        print("  detalle:", str(res)[:300])
        return 1
    if activo:
        st3, r3 = api("POST", f"/workflows/{WID}/activate", {})
        print(f"  reactivado -> HTTP {st3} active={r3.get('active')}")

    # Verificacion
    print("\n=== VERIFICACION ===")
    st4, fin = api("GET", f"/workflows/{WID}")
    nodos_txt = json.dumps(fin["nodes"], ensure_ascii=False)
    print(f"  {'OK  ' if 'easypanel.host' not in nodos_txt else 'MAL '} "
          f"sin el servidor del vendedor en los nodos")
    print(f"  {'OK  ' if 'CLAVE_DEL_PROVEEDOR' not in nodos_txt else 'MAL '} "
          f"sin la clave del vendedor en los nodos")
    if fin.get("pinData"):
        pin = json.dumps(fin["pinData"], ensure_ascii=False)
        print(f"  {'AVISO' if 'DC64CCC' in pin else 'OK  '} pinData: "
              f"{'aun tiene la clave' if 'DC64CCC' in pin else 'limpio'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
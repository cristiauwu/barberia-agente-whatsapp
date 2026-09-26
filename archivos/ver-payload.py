#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Comprueba que campos manda realmente Evolution en su webhook.

Levanta un receptor temporal en n8n (via el webhook de prueba) o, mas
simple: revisa una ejecucion real y muestra el item de entrada del nodo
Normalizacion, que es donde se lee body.server_url y body.apikey.
"""
import json
import os
import subprocess
import sys
import urllib.request

N8N = "http://localhost:5678/api/v1"
KEY = os.environ.get("N8N_KEY", "")


def api(path):
    req = urllib.request.Request(N8N + path)
    req.add_header("X-N8N-API-KEY", KEY)
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode())


def main():
    # Buscar la ultima ejecucion del workflow del agente
    ex = api("/executions?workflowId=barberiaAgenteUncensored&limit=5")
    for e in ex.get("data", []):
        eid = e["id"]
        try:
            det = api(f"/executions/{eid}?includeData=true")
        except Exception as ex2:
            print(eid, "no se pudo leer:", ex2)
            continue
        rd = (det.get("data") or {}).get("resultData") or {}
        run = rd.get("runData") or {}
        if "Normalizacion" not in run:
            continue
        print("=" * 74)
        print("EJECUCION", eid, "| estado:", det.get("status"))
        print("=" * 74)
        # El item de salida de Normalizacion trae los campos leidos del body
        for intento in run["Normalizacion"]:
            salida = ((intento.get("data") or {}).get("main") or [[]])[0]
            for item in salida:
                j = item.get("json", {})
                for k in ("instance_server_url", "instance_name",
                          "instance_apikey", "user_number", "message_content"):
                    if k in j:
                        v = str(j[k])
                        if k == "instance_apikey" and v:
                            v = v[:6] + "..." + v[-4:] + f" (len {len(str(j[k]))})"
                        print(f"  {k} = {v}")
            break
        return 0
    print("No encontre ejecuciones con datos del webhook.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
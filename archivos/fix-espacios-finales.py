#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Limpia deterministicamente los espacios finales de renglon al enviar.

Por que: el modelo imita el "hard break" de Markdown y cierra cada renglon
de la lista con dos espacios ("texto  \\n"). En WhatsApp eso NO es un salto:
deja huecos y puede romper la negrita. El prompt lo prohibe, pero es un
habito tan automatico que se repite en el 100% de las listas.

Solucion: al mandar, se recortan los espacios/tabuladores finales de cada
renglon. Asi la regla se cumple SIEMPRE, sin depender del humor del modelo.
Se respeta todo lo demas del nodo y se respalda el workflow antes.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

KEY = open(r"G:\Barberia\archivos\.n8n-key.txt").read().strip()
N8N = "http://localhost:5678/api/v1"
WID = "barberiaAgenteUncensored"
BACKUP = r"G:\Barberia\archivos\ANTES-mandar-trim.json"

# Solo espacios y tabuladores al final de cada renglon. NO toca \n.
NUEVA_EXPR = "={{ $json.output.replace(/[ \\t]+$/gm, '') }}"


def api(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(N8N + path, data=data, method=method)
    r.add_header("X-N8N-API-KEY", KEY)
    r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=90) as x:
            return x.status, json.loads(x.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:400]
    except Exception as e:
        return None, str(e)


st, wf = api("GET", f"/workflows/{WID}")
if st != 200:
    print("no pude leer el workflow:", st, wf)
    sys.exit(1)

nodos_antes = [n["name"] for n in wf["nodes"]]
activo = wf.get("active")
json.dump(wf, open(BACKUP, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("respaldo:", BACKUP, "(%d nodos)" % len(nodos_antes))

nodo = next(n for n in wf["nodes"] if n["name"] == "Mandar mensaje")
params = nodo["parameters"]["bodyParameters"]["parameters"]
campo = next(p for p in params if p["name"] == "text")
print("text ANTES :", campo["value"])
campo["value"] = NUEVA_EXPR
print("text DESPUES:", campo["value"])

if activo:
    api("POST", f"/workflows/{WID}/deactivate", {})
st2, res = api("PUT", f"/workflows/{WID}", {
    "name": wf["name"], "nodes": wf["nodes"],
    "connections": wf["connections"], "settings": wf.get("settings", {}),
})
print("PUT -> HTTP", st2)
if st2 not in (200, 201):
    print("detalle:", str(res)[:400])
    sys.exit(1)
if activo:
    api("POST", f"/workflows/{WID}/activate", {})
    print("reactivado")

time.sleep(3)
st3, wf2 = api("GET", f"/workflows/{WID}")
nodos_despues = [n["name"] for n in wf2["nodes"]]
faltan = set(nodos_antes) - set(nodos_despues)
print()
print("nodos antes: %d | despues: %d | faltan: %s"
      % (len(nodos_antes), len(nodos_despues), sorted(faltan) or "ninguno"))
n2 = next(n for n in wf2["nodes"] if n["name"] == "Mandar mensaje")
v2 = next(p for p in n2["parameters"]["bodyParameters"]["parameters"]
          if p["name"] == "text")["value"]
print("text en vivo:", v2)
print("activo:", wf2.get("active"))
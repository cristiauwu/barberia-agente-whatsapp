#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Recon 3: webhook mode, credenciales, y prueba de envio a Evolution con JID falso."""
import json
import sys

sys.path.insert(0, r"G:\Barberia\archivos\_carga")
import lib
lib.init()

lib.h("1) NODO WEBHOOK")
st, wf = lib.api("/workflows/" + lib.WF_AGENTE)
for n in wf.get("nodes", []):
    if n["type"].endswith(".webhook"):
        print("  nombre:", n["name"])
        print("  params:", json.dumps(n.get("parameters", {}), ensure_ascii=False))
        print("  webhookId:", n.get("webhookId"))

lib.h("2) CREDENCIALES (id/name/type)")
st, d = lib.api("/credentials?limit=100")
print("status", st)
if st == 200:
    for c in d.get("data", []):
        print("  id=%-22s type=%-32s name=%s" % (c.get("id"), c.get("type"), c.get("name")))
else:
    print(str(d)[:400])

lib.h("3) A QUE NODO APUNTA 'Mandar mensaje' -> entrada/salida del AI Agent")
for n in wf.get("nodes", []):
    if n["name"] in ("Mandar mensaje", "IF - Respuesta no vacia", "Respuesta sin texto",
                     "Aviso solo texto", "IF - Cliente pausado", "Switch"):
        print("  ---", n["name"], n["type"])
        print("     ", json.dumps(n.get("parameters", {}), ensure_ascii=False)[:600])

lib.h("4) CONEXIONES")
conn = wf.get("connections", {})
for k, v in conn.items():
    outs = []
    for i, br in enumerate(v.get("main") or []):
        outs.append("out%d->%s" % (i, [x["node"] for x in (br or [])]))
    print("  %-38s %s" % (k, " | ".join(outs) or "(sin salida)"))

lib.h("5) EVOLUTION: estado de la instancia hector (solo lectura)")
st, d = lib.api_evo("/instance/connectionState/hector") if hasattr(lib, "api_evo") else (None, None)
# lectura directa, sin mandar mensajes a nadie
import urllib.request, urllib.error
req = urllib.request.Request("http://localhost:8080/instance/fetchInstances",
                             method="GET")
req.add_header("apikey", lib.ENV["EVOKEY"])
try:
    with urllib.request.urlopen(req, timeout=40) as r:
        raw = r.read().decode()
        print("  HTTP", r.status)
        try:
            dd = json.loads(raw)
            for it in (dd if isinstance(dd, list) else [dd]):
                print("   ", json.dumps({k: it.get(k) for k in
                      ("name", "connectionStatus", "number") if k in it},
                      ensure_ascii=False))
        except Exception:
            print("  ", raw[:400])
except urllib.error.HTTPError as e:
    print("  HTTP", e.code, e.read().decode()[:300])
except Exception as e:
    print("  EXC", str(e)[:200])
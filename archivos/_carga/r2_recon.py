#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Recon 2: recordatorios (Wait), y donde se escribe barber_citas/hoja."""
import json
import sys

sys.path.insert(0, r"G:\Barberia\archivos\_carga")
import lib
lib.init()

lib.h("A) WORKFLOW RECORDATORIOS - nodos")
st, wf = lib.api("/workflows/" + lib.WF_RECORDATORIOS)
print("status", st)
for n in wf.get("nodes", []):
    print("  %-40s %-52s" % (n["name"][:40], n["type"]))
print("  triggers:", [n["name"] for n in wf.get("nodes", []) if "trigger" in n["type"].lower() or "Trigger" in n["name"]])

lib.h("B) NODOS WAIT / SCHEDULE / LIMIT en recordatorios")
for n in wf.get("nodes", []):
    t = n["type"].lower()
    if "wait" in t or "schedule" in t or "limittimes" in t:
        print("  %-40s %s" % (n["name"], n["type"]))
        print("     ", json.dumps(n.get("parameters", {}), ensure_ascii=False)[:500])

lib.h("C) NODOS WAIT en CUALQUIER workflow")
for wid in (lib.WF_AGENTE, lib.WF_RECORDATORIOS, "5zd5go4TFKqIsgdT"):
    st, w = lib.api("/workflows/" + wid)
    waits = [n["name"] for n in (w.get("nodes") or []) if "wait" in n["type"].lower()]
    print("  %-28s waits=%s" % (wid, waits or "(ninguno)"))

lib.h("D) NODOS QUE TOCAN barber_citas EN EL AGENTE")
st, wf = lib.api("/workflows/" + lib.WF_AGENTE)
for n in wf.get("nodes", []):
    s = json.dumps(n.get("parameters", {}), ensure_ascii=False)
    if "barber_citas" in s:
        print("  %-40s %s" % (n["name"], n["type"]))
        # mostrar solo los fragmentos con barber_citas
        import re
        for m in re.finditer(r".{140}barber_citas.{200}", s):
            print("      ...", m.group(0).replace("\\n", " ")[:340])

lib.h("E) NODOS QUE ESCRIBEN A POSTGRES EN EL AGENTE")
for n in wf.get("nodes", []):
    if n["type"].endswith(".postgres"):
        p = n.get("parameters", {})
        print("  %-34s op=%s table=%s schema=%s" % (
            n["name"], p.get("operation"), p.get("table", {}).get("value") if isinstance(p.get("table"), dict) else p.get("table"),
            p.get("schema", {}).get("value") if isinstance(p.get("schema"), dict) else p.get("schema")))

lib.h("F) CREDENCIALES USADAS (tipos)")
tipos = {}
for n in wf.get("nodes", []):
    for k, v in (n.get("credentials") or {}).items():
        tipos.setdefault(k, set()).add((v.get("name") or v.get("id")))
for k, v in tipos.items():
    print("  %-40s %s" % (k, v))

lib.h("G) NODO 'Mandar mensaje' - URL y cuerpo")
for n in wf.get("nodes", []):
    if n["name"] in ("Mandar mensaje", "Responder al operador"):
        print(" ", n["name"])
        print("   ", json.dumps(n.get("parameters", {}), ensure_ascii=False)[:900])

lib.h("H) NODO 'Notificar al encargado'")
for n in wf.get("nodes", []):
    if "Notificar" in n["name"]:
        print("   ", json.dumps(n.get("parameters", {}), ensure_ascii=False)[:900])

lib.h("I) NODO Switch / Router: como decide")
for n in wf.get("nodes", []):
    if n["name"] in ("Switch", "Router de comandos"):
        print(" ", n["name"])
        print("   ", json.dumps(n.get("parameters", {}), ensure_ascii=False)[:800])

lib.h("J) NODO Normalizacion")
for n in wf.get("nodes", []):
    if n["name"] == "Normalizacion":
        print("   ", json.dumps(n.get("parameters", {}), ensure_ascii=False)[:1200])
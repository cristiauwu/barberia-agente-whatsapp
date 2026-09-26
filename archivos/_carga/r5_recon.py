#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Recon 5: Normalizacion completa, Edit Fields, y comprobacion SEGURA de JIDs."""
import json
import sys

sys.path.insert(0, r"G:\Barberia\archivos\_carga")
import lib
lib.init()

st, wf = lib.api("/workflows/" + lib.WF_AGENTE)
byname = {n["name"]: n for n in wf.get("nodes", [])}

lib.h("1) NORMALIZACION - asignaciones completas")
p = byname["Normalizacion"]["parameters"]["assignments"]["assignments"]
for a in p:
    print("  %-26s = %s" % (a["name"], a.get("value")))

lib.h("2) EDIT FIELDS / EDIT FIELDS2")
for nm in ("Edit Fields", "Edit Fields2"):
    print("  ---", nm)
    print("   ", json.dumps(byname[nm]["parameters"], ensure_ascii=False)[:900])

lib.h("3) ¿COMO SE EXTRAE user_number? (busco en normalizacion + code nodes)")
for n in wf.get("nodes", []):
    s = json.dumps(n.get("parameters", {}), ensure_ascii=False)
    if "remoteJid" in s or "user_number" in s:
        print("  ---", n["name"], n["type"])
        for frag in s.split(","):
            if "remoteJid" in frag or "user_number" in frag:
                print("      ", frag[:220])

lib.h("4) COMPROBACION SEGURA: que numeros candidatos NO estan en WhatsApp")
import urllib.request, urllib.error
candidatos = [
    "5214501111805",   # cliente real de pruebas
    "5214521206246",   # dueno (operador)
    "524521206246",    # dueno (contexto)
    "529990000001",
    "529990000002",
    "529990000003",
    "529990000004",
    "529990000005",
    "529990000006",
    "529990000007",
    "529990000008",
    "529990000009",
    "529990000010",
]
body = {"numbers": candidatos}
req = urllib.request.Request(
    "http://localhost:8080/chat/whatsappNumbers/hector",
    data=json.dumps(body).encode(), method="POST")
req.add_header("Content-Type", "application/json")
req.add_header("apikey", lib.ENV["EVOKEY"])
try:
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read().decode())
        for it in d:
            print("  %-16s exists=%s jid=%s" % (it.get("number"), it.get("exists"),
                                                it.get("jid")))
except urllib.error.HTTPError as e:
    print("  HTTP", e.code, e.read().decode()[:400])
except Exception as e:
    print("  EXC", str(e)[:300])
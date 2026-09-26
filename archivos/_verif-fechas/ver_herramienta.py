#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

wf = json.load(open(r"G:\Barberia\archivos\_verif-fechas\wf_agente.json", encoding="utf-8"))
for n in wf["nodes"]:
    if n["name"] in ("Que dia es",):
        print("### NODO:", n["name"], n["type"], "v", n.get("typeVersion"))
        print(json.dumps(n["parameters"], ensure_ascii=False, indent=1))
        print("=" * 70)

# herramientas conectadas al agente
conns = wf.get("connections", {})
print("Conexiones ai_tool hacia AI Agent:")
for src, c in conns.items():
    for out in (c.get("main") or []):
        pass
for src, c in conns.items():
    if "ai_tool" in c:
        for grp in c["ai_tool"]:
            for t in grp:
                print(f"  {src} -> {t['node']}")
print()
print("Conexiones del nodo IA:")
print(json.dumps(conns.get("Que dia es", {}), ensure_ascii=False))
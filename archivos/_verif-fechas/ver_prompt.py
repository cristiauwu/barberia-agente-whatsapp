#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
DIR = r"G:\Barberia\archivos\_verif-fechas"
wf = json.load(open(DIR + r"\wf_agente.json", encoding="utf-8"))
for n in wf["nodes"]:
    if n["name"] in ("AI Agent", "Consultar agenda", "Agendar cita"):
        print("=" * 72)
        print("NODO:", n["name"], "|", n["type"], "v", n.get("typeVersion"))
        p = n["parameters"]
        if n["name"] == "AI Agent":
            txt = p.get("text") or p.get("options", {}).get("systemMessage") or ""
            print("[longitud prompt]:", len(txt))
            for kw in ("Que dia es", "dia de la semana", "semana", "19:", "20:00",
                       "domingo", "fecha", "10 lineas", "lineas"):
                idxs = [i for i in range(len(txt)) if txt.startswith(kw, i)]
                print(f"  '{kw}': {len(idxs)} apariciones")
        else:
            print(json.dumps(p, ensure_ascii=False, indent=1)[:4000])